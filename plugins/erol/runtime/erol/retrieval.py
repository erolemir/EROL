"""Project-bound revision index with BM25 and explicit bilingual concept expansion."""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path

from .common import ErolError, canonical, digest, reject_links

KINDS = {"state", "architecture", "decisions", "learnings", "incidents", "patterns", "handoff"}
GROUPS = (
    "retry retries timeout timeouts yeniden tekrar zamanasimi",
    "database sql postgres postgresql veritabani",
    "research sources citation evidence arastirma kaynak kanit",
    "security permission permissions guvenlik izin yetki",
    "test tests regression acceptance dogrulama kabul regresyon",
    "queue jobs scheduler kuyruk gorev zamanlayici",
    "competitor competitors competition rakip rekabet",
    "product products customer customers urun musteri",
)


def tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold().replace("ı", "i"))
    text = "".join(c for c in normalized if not unicodedata.combining(c))
    for phrase, combined in (
        (r"\bzaman\s+asimi\b", "zamanasimi"),
        (r"\bveri\s+tabani\b", "veritabani"),
    ):
        text = re.sub(phrase, combined, text)
    return re.findall(r"[a-z0-9_]+", text)


def projection(item: dict) -> str:
    return " | ".join(
        str(item.get(key, ""))
        for key in ("title", "text", "symptom", "error", "root_cause", "solution", "component")
    )[:16000]


class MemoryIndex:
    def __init__(self, store):
        self.store = store
        path = store.directory / "search.db"
        reject_links(path)
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT)")
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('schema_version','2')")
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('project_id',?)", (store.project_id,))
        metadata = dict(self.db.execute("SELECT key,value FROM meta"))
        if metadata.get("project_id") != store.project_id or metadata.get("schema_version") not in {
            "1",
            "2",
        }:
            self.db.close()
            raise ErolError("Search index project or schema mismatch")
        if metadata["schema_version"] == "1":
            self.db.execute("DROP TABLE IF EXISTS documents")
            self.db.execute("UPDATE meta SET value='2' WHERE key='schema_version'")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS documents(kind TEXT,id TEXT,revision TEXT,"
            "excerpt TEXT,terms TEXT,PRIMARY KEY(kind,id))"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS terms(token TEXT,kind TEXT,id TEXT,count INTEGER,"
            "PRIMARY KEY(token,kind,id))"
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS term_document ON terms(kind,id)")
        self.db.commit()
        if os.name == "posix":
            path.chmod(0o600)

    def close(self):
        self.db.close()

    def sync(self) -> dict:
        if self.store.db.in_transaction:
            raise ErolError("Sync memory after the owning transaction commits")
        with self.store.transaction():
            return self._sync_revision()

    def _sync_revision(self) -> dict:
        cursor_revision = int(
            self.store.db.execute(
                "SELECT value FROM metadata WHERE key='record_revision'"
            ).fetchone()[0]
        )
        previous = dict(self.db.execute("SELECT key,value FROM meta")).get("record_revision")
        full = previous is None or int(previous) > cursor_revision
        if full:
            active = {(kind, item["id"]): item for kind in KINDS for item in self.store.list(kind)}
            deleted = None
        else:
            assert previous is not None
            active = {}
            deleted = set()
            for kind, key in self.store.db.execute(
                "SELECT kind,id FROM record_changes WHERE revision>? AND revision<=?",
                (int(previous), cursor_revision),
            ):
                if kind not in KINDS:
                    continue
                item = self.store.get(kind, key)
                if item is not None:
                    active[kind, key] = item
                else:
                    deleted.add((kind, key))
        stored = (
            {
                (kind, key): revision
                for kind, key, revision in self.db.execute("SELECT kind,id,revision FROM documents")
            }
            if full
            else {
                key: row[0]
                for key in active
                if (
                    row := self.db.execute(
                        "SELECT revision FROM documents WHERE kind=? AND id=?", key
                    ).fetchone()
                )
            }
        )
        changed = 0
        with self.db:
            for (kind, key), item in active.items():
                revision = digest(item)
                if stored.get((kind, key)) == revision:
                    continue
                excerpt = projection(item)
                counts = Counter(tokens(excerpt))
                self.db.execute(
                    "INSERT INTO documents VALUES(?,?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET "
                    "revision=excluded.revision,excerpt=excluded.excerpt,terms=excluded.terms",
                    (kind, key, revision, excerpt, canonical(counts)),
                )
                self.db.execute("DELETE FROM terms WHERE kind=? AND id=?", (kind, key))
                self.db.executemany(
                    "INSERT INTO terms VALUES(?,?,?,?)",
                    [(word, kind, key, count) for word, count in counts.items()],
                )
                changed += 1
            for kind, key in stored.keys() - active.keys() if full else deleted:
                self.db.execute("DELETE FROM documents WHERE kind=? AND id=?", (kind, key))
                self.db.execute("DELETE FROM terms WHERE kind=? AND id=?", (kind, key))
                changed += 1
            self.db.execute(
                "INSERT OR REPLACE INTO meta VALUES('record_revision',?)", (str(cursor_revision),)
            )
        return {
            "indexed": self.db.execute("SELECT count(*) FROM documents").fetchone()[0],
            "changed": changed,
            "schema_version": 2,
            "project_id": self.store.project_id,
            "sync_mode": "full" if full else "incremental",
            "records_examined": len(active) + (len(deleted) if deleted is not None else 0),
        }

    def search(self, query: str, *, max_chars: int = 6000, limit: int = 10) -> list[dict]:
        if max_chars < 1 or limit < 1 or len(query) > 16000:
            raise ErolError("Invalid retrieval budget")
        self.sync()  # never serve a stale, withdrawn or superseded revision
        words = set(tokens(query)[:128])
        weights = dict.fromkeys(words, 1.0)
        for group in GROUPS:
            aliases = set(group.split())
            if words & aliases:
                for word in aliases - words:
                    weights[word] = 0.35
        placeholders = ",".join("?" for _ in weights) or "NULL"
        candidates = self.db.execute(
            "SELECT d.* FROM documents d JOIN (SELECT kind,id FROM terms "
            f"WHERE token IN ({placeholders}) UNION SELECT kind,id FROM documents "
            "WHERE kind='state') matches ON matches.kind=d.kind AND matches.id=d.id",
            tuple(weights),
        )
        rows = [
            (kind, key, revision, excerpt, json.loads(terms))
            for kind, key, revision, excerpt, terms in candidates
        ]
        count = self.db.execute("SELECT count(*) FROM documents").fetchone()[0]
        total = self.db.execute("SELECT coalesce(sum(count),0) FROM terms").fetchone()[0]
        average = total / max(1, count) or 1
        frequency = {
            word: self.db.execute("SELECT count(*) FROM terms WHERE token=?", (word,)).fetchone()[0]
            for word in weights
        }
        ranked = []
        for kind, key, revision, excerpt, terms in rows:
            current = self.store.get(kind, key)
            if not current or digest(current) != revision:
                continue
            bindings = current.get("source_revisions", [])
            if not isinstance(bindings, list) or len(bindings) > 30:
                continue
            valid = True
            for binding in bindings:
                try:
                    import hashlib

                    path = Path(self.store.project.root) / binding["path"]
                    reject_links(path)
                    if (
                        Path(binding["path"]).is_absolute()
                        or ".." in Path(binding["path"]).parts
                        or path.stat().st_size > 4 * 1024 * 1024
                        or hashlib.sha256(path.read_bytes()).hexdigest() != binding["sha256"]
                    ):
                        valid = False
                except (OSError, KeyError, TypeError, ErolError):
                    valid = False
            if not valid:
                continue
            size = sum(terms.values())
            score = sum(
                weight
                * math.log(1 + (count - frequency[word] + 0.5) / (frequency[word] + 0.5))
                * (terms.get(word, 0) * 2.2)
                / (terms.get(word, 0) + 1.2 * (0.25 + 0.75 * size / average))
                for word, weight in weights.items()
            )
            if score or kind == "state":
                ranked.append(
                    {
                        "kind": kind,
                        "id": key,
                        "relevance": round(score, 6),
                        "revision_digest": revision,
                        "excerpt": excerpt,
                        "untrusted_memory": True,
                        "verify_against_current_code": True,
                        "source_revision_bound": bool(bindings),
                        "retrieval": "bm25+explicit-bilingual-concepts",
                    }
                )
        result, used = [], 0
        for item in sorted(ranked, key=lambda item: (-item["relevance"], item["kind"], item["id"])):
            size = len(canonical(item))
            if used + size <= max_chars:
                result.append(item)
                used += size
            if len(result) >= limit:
                break
        return result
