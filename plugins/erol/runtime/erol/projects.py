"""Visited local project checkouts; metadata only, outside repositories."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from .common import (
    ErolError,
    atomic_write,
    canonical,
    digest,
    identifier,
    now,
    reject_links,
    required_text,
)
from .identity import Project
from .runstore import file_lease
from .security import assert_project_path_safe, assert_secret_safe


class ProjectCatalog:
    def __init__(self, home: Path):
        self.home = home.expanduser().absolute()
        self.path = self.home / "global" / "projects.json"
        reject_links(self.path)

    @staticmethod
    def _entry(project: dict, updated: str = "") -> dict:
        root = Path(project["root"])
        if not root.is_absolute():
            raise ErolError("Saved project root must be absolute")
        assert_project_path_safe(root)
        project_id = identifier(project["id"])
        name = required_text(project["name"], "Project name", 10000)[:255]
        if any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in name):
            raise ErolError("Project name must be printable")
        assert_secret_safe(name)
        return {
            "id": "project-" + digest(os.path.normcase(str(root)))[:16],
            "project_id": project_id,
            "name": name,
            "root": str(root),
            "updated": updated,
        }

    def _saved(self) -> list[dict]:
        reject_links(self.path)
        if not self.path.exists():
            return []
        if self.path.stat().st_size > 1024 * 1024:
            raise ErolError("Project catalog exceeds size limit")
        try:
            data = json.loads(self.path.read_text("utf-8"))
            if data.get("schema_version") != 1 or not isinstance(data.get("projects"), list):
                raise ValueError
            rows = data["projects"]
            if len(rows) > 500:
                raise ValueError
            for row in rows:
                if not isinstance(row["updated"], str) or len(row["updated"]) > 100:
                    raise ValueError
                expected = self._entry(
                    {"id": row["project_id"], "name": row["name"], "root": row["root"]},
                    row["updated"],
                )
                if expected != row:
                    raise ValueError
            return rows
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise ErolError("Invalid project catalog") from exc

    def remember(self, project: Project) -> None:
        row = self._entry(project.to_dict(), now())
        root = Path(project.root)
        if root == self.home or root in self.home.parents:
            raise ErolError("EROL home cannot be selected as a project")
        reject_links(root)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with file_lease(self.path.parent / "projects.lock"):
            rows = [r for r in self._saved() if r["id"] != row["id"]]
            rows = sorted([row, *rows], key=lambda r: r["updated"], reverse=True)[:500]
            atomic_write(self.path, canonical({"schema_version": 1, "projects": rows}) + "\n")

    def list(self) -> list[dict]:
        rows = {r["id"]: r for r in self._saved()}
        # Discover old EROL project metadata without opening writable memory stores.
        state = self.home / "state"
        reject_links(state)
        if state.is_dir():
            for database in sorted(state.glob("*/memory.db"))[:500]:
                try:
                    reject_links(database)
                    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
                        value = db.execute(
                            "SELECT value FROM metadata WHERE key='project' AND length(value)<8192"
                        ).fetchone()
                    if value:
                        project = json.loads(value[0])
                        if project["id"] != database.parent.name:
                            continue
                        row = self._entry(project)
                        rows.setdefault(row["id"], row)
                except (ErolError, sqlite3.Error, ValueError, KeyError, TypeError, AttributeError):
                    continue
        return [
            {**r, "available": Path(r["root"]).is_dir()}
            for r in sorted(rows.values(), key=lambda r: (r["updated"], r["id"]), reverse=True)
        ][:500]


def choose(rows: list[dict], selection: str) -> dict:
    """Numbers use the caller's displayed snapshot; names must be unambiguous."""
    if selection.isdecimal():
        index = int(selection) - 1
        if 0 <= index < len(rows):
            return rows[index]
        raise ErolError("Selection number is outside the displayed list")
    matches = [r for r in rows if selection in {r["id"], r.get("title"), r.get("name")}]
    if len(matches) != 1:
        raise ErolError("Selection is missing or ambiguous; use a listed number or ID")
    return matches[0]
