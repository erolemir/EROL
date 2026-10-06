"""Paired native behavioral trials using identical fixtures and a context ablation."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from .checktrust import CheckTrust
from .common import ErolError, atomic_write, canonical, digest, now, reject_links, required_text
from .config import Config
from .execution import Limits, Runner, git, load_checks, validate_checks
from .identity import detect_project
from .learning import LearningEngine
from .registry import Registry
from .runstore import RunStore
from .security import assert_secret_safe
from .store import Store


def load_suite(path: Path) -> dict:
    reject_links(path)
    if path.stat().st_size > 262144:
        raise ErolError("Behavior suite exceeds 256 KiB")
    suite = json.loads(path.read_text(encoding="utf-8-sig"))
    if (
        not isinstance(suite, dict)
        or set(suite) != {"schema_version", "cases"}
        or type(suite["schema_version"]) is not int
        or suite["schema_version"] != 1
        or not isinstance(suite["cases"], list)
        or not 1 <= len(suite["cases"]) <= 10
    ):
        raise ErolError("Invalid behavioral suite")
    seen = set()
    for case in suite["cases"]:
        if not isinstance(case, dict) or set(case) != {
            "id",
            "task",
            "files",
            "checks",
            "memory",
            "mode",
        }:
            raise ErolError("Invalid behavioral case")
        from .common import identifier

        key = identifier(case["id"])
        if key in seen:
            raise ErolError("Duplicate behavioral case")
        seen.add(key)
        required_text(case["task"], "benchmark task")
        validate_checks(case["checks"])
        if (
            case["mode"] not in {"development", "research"}
            or not isinstance(case["files"], dict)
            or not 1 <= len(case["files"]) <= 50
        ):
            raise ErolError("Invalid benchmark fixture")
        for name, body in case["files"].items():
            node = Path(name)
            if (
                node.is_absolute()
                or ".." in node.parts
                or any(part.casefold() == ".git" for part in node.parts)
                or not isinstance(body, str)
                or len(body) > 64000
            ):
                raise ErolError("Unsafe fixture file")
        if not isinstance(case["memory"], list) or len(case["memory"]) > 20:
            raise ErolError("Invalid synthetic benchmark memory")
        for memory in case["memory"]:
            if (
                not isinstance(memory, dict)
                or set(memory) != {"id", "text", "evidence"}
                or not isinstance(memory["evidence"], list)
                or not memory["evidence"]
            ):
                raise ErolError("Benchmark memory requires explicit synthetic evidence")
    assert_secret_safe(suite)
    return suite


def metrics(run: dict, elapsed: float) -> dict:
    turns = [attempt.get("worker") for attempt in run["attempts"]]
    for attempt in run["attempts"]:
        review = attempt.get("review")
        if review:
            turns.extend(review.get("peer_outcomes", [review]))
    if run.get("review") and not any(
        attempt.get("review") == run["review"] for attempt in run["attempts"]
    ):
        turns.extend(run["review"].get("peer_outcomes", [run["review"]]))
    usage: dict[str, float] = {}
    for turn in turns:
        if turn:
            for key, value in turn.get("usage", {}).items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    usage[key] = usage.get(key, 0) + value
    before = {item["name"]: item["passed"] for item in run["baseline"]}
    unresolved = [
        item
        for item in ((run.get("review") or {}).get("result") or {}).get("findings", [])
        if not item["resolved"]
    ]
    return {
        "completed": run["status"] == "completed" and not unresolved,
        "unresolved_findings": unresolved,
        "status": run["status"],
        "duration_seconds": elapsed,
        "attempts": len(run["attempts"]),
        "regressed_checks": [
            item["name"]
            for item in run["checks"]
            if before.get(item["name"]) and not item["passed"]
        ],
        "usage": usage,
        "cost_usd": usage.get("reported_cost_usd_estimate"),
        "run_id": run["id"],
        "capabilities": run["capabilities"],
        "worktree": run["worktree"],
        "selected_skills": run["selected_skills"],
        "base_commit": run["base_commit"],
        "checks_digest": run["checks_digest"],
        "task_digest": digest(run["task"]),
        "requested_model": run.get("requested_model"),
        "requested_effort": run.get("requested_effort"),
        "phase_timings": run.get("phase_timings", {}),
    }


def behavioral_benchmark(
    suite_path: Path,
    harness: str,
    report_path: Path,
    *,
    repeat: int = 1,
    model: str | None = None,
    effort: str | None = None,
    runner_factory=Runner,
    trust: CheckTrust | None = None,
    fixture_parent: Path | None = None,
) -> dict:
    if not 1 <= repeat <= 3:
        raise ErolError("Behavioral repeat must be 1..3")
    suite = load_suite(suite_path)
    if trust is None:
        raise ErolError("Behavioral suite contains unreviewed checks; use erol checks trust first")
    approved = {case["id"]: trust.require(case["checks"]) for case in suite["cases"]}
    # Retain controlled fixtures beside the caller's external report. Windows
    # mkdtemp/0700 DACLs prevent dedicated sandbox users traversing the root.
    parent = (
        report_path.expanduser().absolute().parent if fixture_parent is None else fixture_parent
    )
    # Keep metadata paths short on native Windows Git. Exclusive mkdir still
    # rejects the unlikely collision rather than reusing an earlier trial.
    retained = parent / ("b-" + uuid.uuid4().hex[:16])
    reject_links(retained)
    retained.mkdir(parents=True, mode=0o700 if os.name == "posix" else 0o777)
    report: dict = {
        "schema_version": 1,
        "id": "benchmark-" + uuid.uuid4().hex,
        "kind": "paired_context_ablation",
        "created": now(),
        "suite_digest": digest(suite),
        "harness": harness,
        "requested_model": model,
        "requested_effort": effort,
        "fixture_root": str(retained),
        "limitations": [
            "Both arms use the same EROL checks, permissions and independent review",
            "Control omits EROL skill and memory context; this is not a vanilla harness comparison",
            "Native user/plugin instructions stay active in both arms; "
            "only injected context is varied",
            "Costs are null when the native CLI does not report them",
            "Small trials do not establish general performance improvement",
        ],
        "pairs": [],
    }
    for case in suite["cases"]:
        seed = retained / case["id"] / "seed"
        seed.mkdir(parents=True)
        for name, body in case["files"].items():
            atomic_write(seed / name, body)
        git(seed, "init")
        git(seed, "add", ".")
        git(
            seed,
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            "Controlled fixture",
        )
        checks_path = seed.parent / "checks.json"
        atomic_write(checks_path, canonical(case["checks"]))
        checks_digest = digest(load_checks(checks_path))
        for iteration in range(repeat):
            pair = {
                "case_id": case["id"],
                "iteration": iteration + 1,
                "fixture_digest": digest(case["files"]),
                "checks_digest": checks_digest,
                "arms": {},
            }
            for arm in ("erol", "control") if iteration % 2 == 0 else ("control", "erol"):
                root = seed.parent / f"{iteration}-{arm}"
                git(seed, "clone", "--no-hardlinks", str(seed), str(root))
                # Both clone origins match; external homes prevent state leakage.
                with Store(
                    retained / "homes" / case["id"] / f"{iteration}-{arm}", detect_project(root)
                ) as store:
                    policy = approved[case["id"]]
                    CheckTrust(store.directory, root).approve(
                        case["checks"], environment=policy["environment"], prefix=policy["prefix"]
                    )
                    for memory in case["memory"]:
                        store.put("learnings", memory)
                    engine = LearningEngine(store, Config(), Registry(project_store=store))
                    with RunStore(store.directory, store.project_id) as runs:
                        runner = runner_factory(
                            store,
                            engine,
                            runs,
                            limits=Limits(task_seconds=900, session_seconds=300),
                        )
                        started = time.monotonic()
                        outcome = runner.start(
                            case["task"],
                            harness,
                            checks_path,
                            mode=case["mode"],
                            context_enabled=arm == "erol",
                            model=model,
                            effort=effort,
                        )
                        pair["arms"][arm] = metrics(outcome, time.monotonic() - started)
                # Persist every completed arm so interruption does not erase expensive evidence.
                atomic_write(report_path, canonical({**report, "in_progress_pair": pair}) + "\n")
            report["pairs"].append(pair)
            atomic_write(report_path, canonical(report) + "\n")
    report["case_comparisons"] = []
    for case in suite["cases"]:
        pairs = [p for p in report["pairs"] if p["case_id"] == case["id"]]
        results = {}
        for arm in ("erol", "control"):
            rows = [p["arms"][arm] for p in pairs]
            results[arm] = {
                "trials": len(rows),
                "completed": sum(r["completed"] for r in rows),
                "regressions": sum(len(r["regressed_checks"]) for r in rows),
                "duration_seconds": [r["duration_seconds"] for r in rows],
                "reported_input_tokens": [r["usage"].get("input_tokens") for r in rows],
                "reported_output_tokens": [r["usage"].get("output_tokens") for r in rows],
                "reported_cost_usd": [r["cost_usd"] for r in rows],
            }
        report["case_comparisons"].append({"case_id": case["id"], "arms": results})
    report["passed"] = all(
        arm["completed"] for pair in report["pairs"] for arm in pair["arms"].values()
    )
    atomic_write(report_path, canonical(report) + "\n")
    return report
