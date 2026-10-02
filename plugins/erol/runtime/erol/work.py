"""Observed work discovery and explicit, bounded project-policy queue."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import sqlite3
import time
import uuid
from functools import partial
from pathlib import Path

from .common import ErolError, canonical, digest, identifier, now, reject_links, required_text
from .execution import Limits, Runner, git, load_checks, snapshot
from .runprocess import observe
from .runstore import pid_alive
from .security import assert_secret_safe, scan_secrets


def source_files(root: Path) -> list[tuple[str, bytes]]:
    names = sorted(
        set(git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0"))
        - {b""}
    )
    if len(names) > 10000:
        raise ErolError("Discovery file count exceeds 10000")
    total = 0
    result = []
    for encoded in names:
        name = encoded.decode("utf-8")
        path = root / name
        reject_links(path)
        if not path.exists():
            result.append((name, b""))
            continue
        if not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
            raise ErolError("Discovery file exceeds four MiB or is not regular")
        body = path.read_bytes()
        total += len(body)
        if total > 64 * 1024 * 1024:
            raise ErolError("Discovery exceeds 64 MiB")
        result.append((name, body))
    return result


def source_digest(root: Path) -> str:
    return digest(
        {
            "head": git(root, "rev-parse", "HEAD").decode().strip(),
            "files": [
                {
                    "path": name,
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "exists": (root / name).exists(),
                }
                for name, body in source_files(root)
            ],
        }
    )


class WorkStore:
    def __init__(self, directory: Path, project_id: str):
        self.directory, self.project_id = directory, project_id
        path = directory / "work.db"
        reject_links(path)
        self.db = sqlite3.connect(path, timeout=15, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('schema_version','1')")
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('project_id',?)", (project_id,))
        if dict(self.db.execute("SELECT key,value FROM meta")) != {
            "schema_version": "1",
            "project_id": project_id,
        }:
            self.close()
            raise ErolError("Work database schema or project mismatch")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS entries(kind TEXT,id TEXT,payload TEXT,"
            "PRIMARY KEY(kind,id))"
        )
        self.db.execute("CREATE TABLE IF NOT EXISTS cancellations(id TEXT PRIMARY KEY)")
        if os.name == "posix":
            path.chmod(0o600)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def put(self, kind: str, item: dict):
        identifier(item["id"])
        if item.get("project_id") != self.project_id:
            raise ErolError("Work project mismatch")
        assert_secret_safe(item)
        if len(canonical(item).encode()) > 1048576:
            raise ErolError("Work record exceeds one MiB")
        self.db.execute(
            "INSERT INTO entries VALUES(?,?,?) ON CONFLICT(kind,id) "
            "DO UPDATE SET payload=excluded.payload",
            (kind, item["id"], canonical(item)),
        )
        return item

    def get(self, kind: str, key: str) -> dict:
        row = self.db.execute(
            "SELECT payload FROM entries WHERE kind=? AND id=?", (kind, identifier(key))
        ).fetchone()
        if not row:
            raise ErolError("Work record not found")
        item = json.loads(row[0])
        if kind == "jobs":
            item["cancel_requested"] = self.cancelled(key)
        return item

    def cancelled(self, key: str) -> bool:
        # Called by model reader threads too; never share a SQLite connection.
        from contextlib import closing

        with closing(sqlite3.connect(self.directory / "work.db")) as db:
            return (
                db.execute("SELECT 1 FROM cancellations WHERE id=?", (key,)).fetchone() is not None
            )

    def list(self, kind: str) -> list[dict]:
        return [
            self.get(kind, row[0])
            for row in self.db.execute(
                "SELECT id FROM entries WHERE kind=? ORDER BY rowid", (kind,)
            )
        ]


def discover(
    root: Path, work: WorkStore, *, checks_path: Path | None = None, issues_path: Path | None = None
) -> dict:
    before = source_digest(root)
    candidates = []

    def add(kind, task, path="", line=0, priority=10, evidence=None):
        required_text(task, "candidate task", 1000)
        if scan_secrets(task):
            return
        item = {
            "kind": kind,
            "task": task,
            "path": path,
            "line": line,
            "priority": priority,
            "source_digest": before,
            "project_id": work.project_id,
            "evidence": evidence or {},
            "untrusted_reference": True,
            "effort": "unknown",
        }
        item["id"] = "candidate-" + digest(item)[:24]
        candidates.append(item)

    for name, body in source_files(root):
        if len(body) > 262144 or b"\0" in body:
            continue
        try:
            text = body.decode("utf-8")
        except UnicodeError:
            continue
        for line, content in enumerate(text.splitlines(), 1):
            match = re.search(r"\b(TODO|FIXME)\b[: ]*(.{1,500})", content)
            if match:
                add("todo", f"Resolve {match[1]} in {name}:{line}: {match[2]}", name, line)
            if len(candidates) >= 200:
                break
        if len(candidates) >= 200:
            break
    if issues_path:
        reject_links(issues_path)
        if issues_path.stat().st_size > 131072:
            raise ErolError("Issue import exceeds 128 KiB")
        data = json.loads(issues_path.read_text(encoding="utf-8-sig"))
        if (
            not isinstance(data, dict)
            or set(data) != {"schema_version", "issues"}
            or type(data["schema_version"]) is not int
            or data["schema_version"] != 1
            or not isinstance(data["issues"], list)
            or len(data["issues"]) > 50
        ):
            raise ErolError("Invalid issue import")
        assert_secret_safe(data)
        for item in data["issues"]:
            if not isinstance(item, dict) or set(item) != {"id", "title", "path"}:
                raise ErolError("Issue requires id, title and path")
            identifier(item["id"])
            path = required_text(item["path"], "issue path", 500)
            if Path(path).is_absolute() or ".." in Path(path).parts:
                raise ErolError("Issue path must be project relative")
            add(
                "issue",
                required_text(item["title"], "issue title", 1000),
                path,
                priority=30,
                evidence={"imported_id": item["id"]},
            )
    checks_digest = None
    if checks_path:
        checks = load_checks(checks_path)
        checks_digest = digest(checks)
        for check in checks["checks"]:
            outcome = observe(
                check["argv"],
                root,
                timeout=min(300, check["timeout_seconds"]),
                environment={**os.environ, "EROL_RUN_ACTIVE": "1"},
            )
            if outcome["exit_code"] != 0 or outcome["reason"]:
                add(
                    "check",
                    f"Repair failing {check['kind']} check {check['name']}",
                    priority=100 if check["kind"] == "acceptance" else 60,
                    evidence={
                        "check": check["name"],
                        "checks_digest": checks_digest,
                        **outcome,
                        "evidence_type": "runner_observed",
                    },
                )
    if source_digest(root) != before:
        raise ErolError("Discovery checks changed project files; scan was discarded")
    scan = {
        "id": "scan-" + uuid.uuid4().hex,
        "project_id": work.project_id,
        "created": now(),
        "source_digest": before,
        "checks_digest": checks_digest,
        "candidate_ids": [item["id"] for item in candidates],
        "priority_basis": (
            "observed acceptance failure, static failure, imported issue, TODO; no cost prediction"
        ),
    }
    work.db.execute("BEGIN IMMEDIATE")
    try:
        for item in candidates:
            work.put("candidates", item)
        work.put("scans", scan)
        work.db.execute("COMMIT")
    except BaseException:
        work.db.execute("ROLLBACK")
        raise
    return {**scan, "candidates": candidates}


def load_policy(path: Path, project_id: str) -> dict:
    reject_links(path)
    if path.stat().st_size > 131072:
        raise ErolError("Policy exceeds 128 KiB")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "project_id", "limits", "rules"}
        or type(value["schema_version"]) is not int
        or value["schema_version"] != 1
        or value["project_id"] != project_id
    ):
        raise ErolError("Policy must be versioned and explicitly bound to this project ID")
    bounds = {
        "max_tasks": 20,
        "max_total_seconds": 14400,
        "task_seconds": 3600,
        "session_seconds": 900,
        "check_seconds": 300,
        "reviewers": 3,
    }
    if not isinstance(value["limits"], dict) or set(value["limits"]) != set(bounds):
        raise ErolError("Policy requires all resource limits")
    for key, maximum in bounds.items():
        if type(value["limits"][key]) is not int or not 1 <= value["limits"][key] <= maximum:
            raise ErolError("Policy resource limit is invalid")
    if not isinstance(value["rules"], list) or not 1 <= len(value["rules"]) <= 20:
        raise ErolError("Policy requires 1..20 rules")
    ids = set()
    for rule in value["rules"]:
        if not isinstance(rule, dict) or set(rule) != {
            "id",
            "kinds",
            "paths",
            "harness",
            "review_harness",
            "mode",
            "checks",
        }:
            raise ErolError("Invalid policy rule")
        key = identifier(rule["id"])
        if key in ids:
            raise ErolError("Duplicate policy rule")
        ids.add(key)
        if (
            rule["harness"] not in {"codex", "claude"}
            or rule["review_harness"] not in {"codex", "claude"}
            or rule["mode"] not in {"development", "research"}
        ):
            raise ErolError("Invalid policy harness or mode")
        if (
            not isinstance(rule["kinds"], list)
            or not rule["kinds"]
            or any(kind not in {"todo", "check", "issue"} for kind in rule["kinds"])
        ):
            raise ErolError("Invalid policy kinds")
        if (
            not isinstance(rule["paths"], list)
            or not 1 <= len(rule["paths"]) <= 20
            or any(not isinstance(pattern, str) or len(pattern) > 500 for pattern in rule["paths"])
        ):
            raise ErolError("Invalid policy path patterns")
        checks_path = Path(required_text(rule["checks"], "policy checks path", 2000))
        if not checks_path.is_absolute():
            raise ErolError("Policy check paths must be absolute")
        rule["checks_digest"] = digest(load_checks(checks_path))
    assert_secret_safe(value)
    return value


class Queue:
    def __init__(self, work: WorkStore, runner: Runner):
        self.work, self.runner = work, runner

    def enqueue(self, policy: dict, candidate_ids: list[str] | None = None) -> list[dict]:
        current = source_digest(self.runner.root)
        candidates = self.work.list("candidates")
        if candidate_ids:
            candidates = [self.work.get("candidates", key) for key in candidate_ids]
        result = []
        with self.runner.runs.lease(self.work.directory / "queue.lock"):
            for item in sorted(candidates, key=lambda item: (-item["priority"], item["id"])):
                if item["source_digest"] != current:
                    continue
                for rule in policy["rules"]:
                    if item["kind"] not in rule["kinds"] or not any(
                        fnmatch.fnmatchcase(item["path"], pattern) for pattern in rule["paths"]
                    ):
                        continue
                    if (
                        item["kind"] == "check"
                        and item["evidence"]["checks_digest"] != rule["checks_digest"]
                    ):
                        continue
                    key = "job-" + digest({"candidate": item["id"], "policy": digest(policy)})[:24]
                    if any(job["id"] == key for job in self.work.list("jobs")):
                        break
                    job = {
                        "id": key,
                        "project_id": self.work.project_id,
                        "candidate_id": item["id"],
                        "task": item["task"],
                        "task_id": "queue-" + uuid.uuid4().hex,
                        "rule": rule,
                        "policy_digest": digest(policy),
                        "source_digest": current,
                        "status": "queued",
                        "dependencies": [],
                        "run_id": None,
                        "owner_pid": None,
                        "created": now(),
                    }
                    self.work.put("jobs", job)
                    result.append(job)
                    break
        return result

    def depend(self, key: str, predecessors: list[str]) -> dict:
        with self.runner.runs.lease(self.work.directory / "queue.lock"):
            job = self.work.get("jobs", key)
            if (
                job["status"] != "queued"
                or len(set(predecessors)) != len(predecessors)
                or not 1 <= len(predecessors) <= 20
            ):
                raise ErolError("Only queued jobs may receive unique dependencies")
            graph = {item["id"]: item["dependencies"] for item in self.work.list("jobs")}
            if any(parent not in graph for parent in predecessors):
                raise ErolError("Dependency is missing")
            graph[key] = predecessors

            def visit(node, path):
                if len(path) >= 20:
                    raise ErolError("Dependency depth exceeds 20")
                if node in path:
                    raise ErolError("Queue dependency cycle")
                for parent in graph[node]:
                    visit(parent, path | {node})

            visit(key, set())
            job["dependencies"] = predecessors
            return self.work.put("jobs", job)

    def cancel(self, key: str) -> dict:
        # Cancellation remains writable while the worker holds queue.lock.
        job = self.work.get("jobs", key)
        if job["status"] in {"completed", "cancelled"}:
            return job
        self.work.db.execute("INSERT OR IGNORE INTO cancellations VALUES(?)", (key,))
        runs = [run for run in self.runner.runs.list() if run["task_id"] == job["task_id"]]
        if runs:
            self.runner.cancel(runs[0]["id"])
        return self.work.get("jobs", key)

    def execute(self, policy: dict, *, resume_id: str | None = None) -> list[dict]:
        results: list[dict] = []
        deadline = time.time() + policy["limits"]["max_total_seconds"]
        with self.runner.runs.lease(self.work.directory / "queue.lock"):
            jobs = [self.work.get("jobs", resume_id)] if resume_id else self.work.list("jobs")
            depths: dict[str, int] = {}

            def depth(key, visiting):
                if len(visiting) >= 20:
                    raise ErolError("Dependency depth exceeds 20")
                if key in visiting:
                    raise ErolError("Queue dependency cycle")
                if key not in depths:
                    item = self.work.get("jobs", key)
                    depths[key] = 1 + max(
                        (depth(parent, visiting | {key}) for parent in item["dependencies"]),
                        default=-1,
                    )
                return depths[key]

            jobs.sort(key=lambda item: depth(item["id"], set()))
            for job in jobs:
                if len(results) >= policy["limits"]["max_tasks"] or time.time() >= deadline:
                    break
                if job["status"] in {"completed", "cancelled"}:
                    continue
                if job.get("cancel_requested"):
                    job["status"] = "cancelled"
                    self.work.put("jobs", job)
                    continue
                if job["policy_digest"] != digest(policy) or job["source_digest"] != source_digest(
                    self.runner.root
                ):
                    raise ErolError("Queued policy, checks or source changed; rescan and enqueue")
                if (
                    job["rule"] not in policy["rules"]
                    or digest(load_checks(Path(job["rule"]["checks"])))
                    != job["rule"]["checks_digest"]
                ):
                    raise ErolError("Queued check definition changed; rescan and enqueue")
                runs = [run for run in self.runner.runs.list() if run["task_id"] == job["task_id"]]
                if pid_alive(job.get("owner_pid")) and job["owner_pid"] != os.getpid():
                    raise ErolError("Queue worker may still be active")
                if job["status"] != "queued" and not runs:
                    raise ErolError(
                        "Interrupted claim has no run receipt; refusing duplicate launch"
                    )
                if job["status"] != "queued" and not resume_id:
                    continue
                patches = []
                waiting = False
                lineage: list[str] = []

                def collect(parent_id, visiting, ordered):
                    if len(visiting) >= 20:
                        raise ErolError("Dependency depth exceeds 20")
                    if parent_id in visiting:
                        raise ErolError("Queue dependency cycle")
                    if parent_id in ordered:
                        return
                    parent = self.work.get("jobs", parent_id)
                    for ancestor in parent["dependencies"]:
                        collect(ancestor, visiting | {parent_id}, ordered)
                    ordered.append(parent_id)

                for parent_id in job["dependencies"]:
                    collect(parent_id, {job["id"]}, lineage)
                for parent_id in lineage:
                    parent = self.work.get("jobs", parent_id)
                    if parent["status"] != "completed" or not parent["run_id"]:
                        waiting = True
                        break
                    prior = self.runner.runs.get(parent["run_id"])
                    expected = self.runner.runs.directory / "runs" / identifier(prior["id"])
                    if (
                        prior["directory"] != str(expected)
                        or prior["worktree"] != str(expected / "worktree")
                        or prior["project_root"] != str(self.runner.root)
                    ):
                        raise ErolError("Dependency worktree identity mismatch")
                    current, patch = snapshot(Path(prior["worktree"]), prior["base_commit"])
                    if (
                        prior["status"] != "completed"
                        or current != prior["reviewed_digest"]
                        or current != prior["tested_digest"]
                    ):
                        raise ErolError("Dependency no longer matches its verified changes")
                    if (
                        prior["base_commit"]
                        != git(self.runner.root, "rev-parse", "HEAD").decode().strip()
                    ):
                        raise ErolError("Dependency uses a different source base")
                    if prior.get("delta_patch"):
                        delta_path = Path(prior["delta_patch"])
                        reject_links(delta_path)
                        if (
                            delta_path != Path(prior["directory"]) / "delta.patch"
                            or delta_path.stat().st_size > 128000
                        ):
                            raise ErolError("Invalid dependency delta package")
                        patch = delta_path.read_text(encoding="utf-8")
                        if digest(patch) != prior["delta_digest"]:
                            raise ErolError("Dependency delta package changed")
                    elif prior.get("initial_patches"):
                        raise ErolError("Legacy dependency lacks a verified delta package")
                    patches.append(
                        {"run_id": prior["id"], "source_digest": current, "patch": patch}
                    )
                if waiting:
                    continue
                job.update({"status": "running", "owner_pid": os.getpid()})
                self.work.put("jobs", job)
                old_limits = self.runner.limits
                old_cancelled = self.runner.external_cancelled
                self.runner.external_cancelled = partial(self.work.cancelled, job["id"])
                limits = policy["limits"]
                self.runner.limits = Limits(
                    min(limits["task_seconds"], deadline - time.time()),
                    limits["session_seconds"],
                    limits["check_seconds"],
                )
                try:
                    if runs and runs[0]["status"] not in {"completed", "cancelled"}:
                        runs[0]["deadline_at"] = min(runs[0]["deadline_at"], deadline)
                        self.runner.runs.save(runs[0])
                    outcome = (
                        (
                            runs[0]
                            if runs[0]["status"] in {"completed", "cancelled"}
                            else self.runner.resume(runs[0]["id"])
                        )
                        if runs
                        else self.runner.start(
                            job["task"],
                            job["rule"]["harness"],
                            Path(job["rule"]["checks"]),
                            task_id=job["task_id"],
                            review_harness=job["rule"]["review_harness"],
                            mode=job["rule"]["mode"],
                            reviewers=limits["reviewers"],
                            initial_patches=patches,
                        )
                    )
                except (ErolError, KeyboardInterrupt):
                    job.update({"status": "needs_attention", "owner_pid": None})
                    self.work.put("jobs", job)
                    raise
                finally:
                    self.runner.limits = old_limits
                    self.runner.external_cancelled = old_cancelled
                refreshed = self.work.get("jobs", job["id"])
                job.update(
                    {
                        "run_id": outcome["id"],
                        "status": outcome["status"],
                        "owner_pid": None,
                        "cancel_requested": refreshed.get("cancel_requested", False),
                    }
                )
                self.work.put("jobs", job)
                results.append(job)
                if outcome["status"] == "needs_attention":
                    break
        return results
