"""Canonical SQLite memory with transactional writes and optional Markdown projections."""

from __future__ import annotations

import builtins
import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from erol.common import ErolError, atomic_write, canonical, identifier, now, reject_links
from erol.identity import Project
from erol.security import assert_project_path_safe, assert_secret_safe

MEMORY_CLASSES = (
    "state",
    "decisions",
    "architecture",
    "learnings",
    "incidents",
    "patterns",
    "tasks",
    "handoff",
    "candidates",
    "skills",
    "evals",
    "uses",
    "promotions",
    "skill_revisions",
    "failures",
)
MARKDOWN_NAMES = {"candidates": "SKILL_CANDIDATES", "learnings": "LEARNINGS"}
SOFT_BUDGETS = {
    "state": 32768,
    "handoff": 32768,
    "learnings": 262144,
    "incidents": 4194304,
    "patterns": 524288,
    "candidates": 1048576,
}


class Store:
    @property
    def project_id(self) -> str:
        return self.project.id

    def __init__(self, home: Path, project: Project):
        original_home = home.expanduser().absolute()
        reject_links(original_home)
        self.home = home.expanduser().resolve()
        root = Path(project.root).resolve()
        if self.home == root or root in self.home.parents:
            raise ErolError("EROL home must be outside the repository")
        self.project = project
        self.directory = self.home / "state" / identifier(project.id)
        # Refuse preexisting linked parents before opening a database.
        for path in (self.home, self.home / "state", self.directory):
            reject_links(path)
        metadata = project.to_dict()
        assert_project_path_safe(Path(metadata["root"]))
        assert_secret_safe({key: value for key, value in metadata.items() if key != "root"})
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        (self.home / "state").mkdir(exist_ok=True, mode=0o700)
        self.directory.mkdir(exist_ok=True, mode=0o700)
        if os.name == "posix":
            self.directory.chmod(0o700)
        database = self.directory / "memory.db"
        reject_links(database)
        self.db = sqlite3.connect(database, timeout=15, isolation_level=None)
        if os.name == "posix":
            database.chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)"
        )
        version = self.db.execute(
            "SELECT value FROM metadata WHERE key='schema_version'"
        ).fetchone()
        if version and version[0] != "1":
            self.close()
            raise ErolError("Unsupported memory schema")
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES('schema_version','1')")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL,id TEXT NOT NULL,"
            "payload TEXT NOT NULL,stale INTEGER NOT NULL DEFAULT 0,updated TEXT NOT NULL,"
            "PRIMARY KEY(kind,id))"
        )
        self.db.execute(
            "INSERT OR REPLACE INTO metadata VALUES('project',?)", (canonical(project.to_dict()),)
        )

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self.db.in_transaction:
            yield
            return
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def put(self, kind: str, data: dict, *, replace: bool = False) -> dict:
        if kind not in MEMORY_CLASSES:
            raise ErolError("Unknown memory class")
        key = identifier(data.get("id", ""))
        assert_secret_safe(data)
        payload = canonical(data)
        if len(payload.encode("utf-8")) > 131072:
            raise ErolError("Memory record exceeds the write budget")
        with self.transaction():
            prior = self.get(kind, key, include_stale=True)
            if prior:
                if prior == data:
                    return prior
                if not replace:
                    raise ErolError("Record ID already exists with different content")
            self.db.execute(
                "INSERT INTO records(kind,id,payload,updated) VALUES(?,?,?,?) "
                "ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload,"
                "updated=excluded.updated,stale=0",
                (kind, key, payload, now()),
            )
        return data

    def get(self, kind: str, key: str, *, include_stale: bool = False) -> dict | None:
        row = self.db.execute(
            "SELECT payload,stale FROM records WHERE kind=? AND id=?", (kind, key)
        ).fetchone()
        return json.loads(row[0]) if row and (include_stale or not row[1]) else None

    def list(self, kind: str, *, include_stale: bool = False) -> list[dict]:
        rows = self.db.execute(
            "SELECT payload,stale FROM records WHERE kind=? ORDER BY updated,id", (kind,)
        )
        return [json.loads(row[0]) for row in rows if include_stale or not row[1]]

    def mark_stale(self, kind: str, key: str) -> None:
        with self.transaction():
            result = self.db.execute(
                "UPDATE records SET stale=1,updated=? WHERE kind=? AND id=?",
                (now(), kind, identifier(key)),
            )
            if result.rowcount == 0:
                raise ErolError("Memory record does not exist")

    def search(self, query: str, *, max_chars: int = 6000, limit: int = 10) -> builtins.list[dict]:
        if max_chars < 1 or limit < 1:
            raise ErolError("Retrieval budgets must be positive")
        words = set(query.lower().split())
        scored = []
        for row in self.db.execute("SELECT kind,id,payload FROM records WHERE stale=0"):
            if row[0] not in {
                "state",
                "architecture",
                "decisions",
                "learnings",
                "incidents",
                "patterns",
                "handoff",
            }:
                continue
            payload = json.loads(row[2])
            # Searchable projections keep tests/logs from swallowing the context budget.
            excerpt = " | ".join(
                str(payload.get(field, ""))
                for field in (
                    "title",
                    "text",
                    "symptom",
                    "error",
                    "root_cause",
                    "solution",
                    "component",
                )
            )
            score = sum(1 for word in words if word in excerpt.lower())
            if score or row[0] == "state":
                scored.append((score, row[0], row[1], excerpt))
        result: list[dict] = []
        cost = 0
        for score, kind, key, excerpt in sorted(scored, reverse=True):
            item = {
                "kind": kind,
                "id": key,
                "relevance": score,
                "excerpt": excerpt,
                "untrusted_memory": True,
                "verify_against_current_code": True,
            }
            size = len(canonical(item))
            if cost + size > max_chars:
                continue
            result.append(item)
            cost += size
            if len(result) == limit:
                break
        return result

    def learn(self, key: str, text: str, evidence: builtins.list[str]) -> dict:
        from erol.common import required_text

        required_text(text, "learning text")
        if not evidence or any(not isinstance(e, str) or not e.strip() for e in evidence):
            raise ErolError("Learning requires evidence references")
        assert_secret_safe({"text": text, "evidence": evidence})
        identifier(key)
        with self.transaction():
            active = [
                item
                for item in self.list("learnings")
                if item.get("logical_key", item["id"]) == key
            ]
            prior = active[-1] if active else None
            if prior and prior["text"] == text:
                return prior
            if prior:
                # Preserve the previous revision. Current code evidence wins.
                self.mark_stale("learnings", prior["id"])
                revision = key + "." + str(len(self.list("learnings", include_stale=True)))
                return self.put(
                    "learnings",
                    {
                        "id": revision,
                        "text": text,
                        "evidence": evidence,
                        "supersedes": prior["id"],
                        "logical_key": key,
                        "confidence": "verified",
                    },
                )
            return self.put(
                "learnings",
                {
                    "id": key,
                    "text": text,
                    "evidence": evidence,
                    "logical_key": key,
                    "confidence": "verified",
                },
            )

    def compact(self) -> dict:
        # Exact duplicates only; incident history and decisions are never dropped.
        removed = 0
        with self.transaction():
            for kind in ("state", "handoff", "learnings"):
                seen: set[str] = set()
                for item in self.list(kind):
                    content = canonical({k: v for k, v in item.items() if k != "id"})
                    if content in seen:
                        self.mark_stale(kind, item["id"])
                        removed += 1
                    seen.add(content)
        return {"duplicates_marked_stale": removed, "history_preserved": True}

    def budget_report(self) -> dict:
        sizes = {
            row[0]: row[1]
            for row in self.db.execute(
                "SELECT kind,SUM(length(CAST(payload AS BLOB))) FROM records "
                "WHERE stale=0 GROUP BY kind"
            )
        }
        return {
            kind: {
                "bytes": sizes.get(kind, 0),
                "soft_budget_bytes": budget,
                "over_soft_budget": sizes.get(kind, 0) > budget,
            }
            for kind, budget in SOFT_BUDGETS.items()
        }

    def export_markdown(self) -> dict:
        written = []
        for kind in MEMORY_CLASSES[:9]:
            name = MARKDOWN_NAMES.get(kind, kind.upper())
            lines = [f"# {name}", "", "Generated view. SQLite is the canonical source.", ""]
            for item in self.list(kind):
                lines.extend(
                    [
                        f"## {item['id']}",
                        "",
                        "```json",
                        json.dumps(item, ensure_ascii=False, indent=2),
                        "```",
                        "",
                    ]
                )
            atomic_write(self.directory / f"{name}.md", "\n".join(lines))
            written.append(f"{name}.md")
        return {"written": written, "directory": str(self.directory)}
