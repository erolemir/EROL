"""External execution records and an OS-held project lease, separate from memory."""

from __future__ import annotations

import importlib
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .common import ErolError, canonical, identifier, reject_links
from .security import assert_project_path_safe, assert_secret_safe


@contextmanager
def file_lease(path: Path):
    """An OS-held lock released on process exit; never steal a live session."""
    reject_links(path)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    held = False
    try:
        if os.fstat(descriptor).st_size == 0:
            os.write(descriptor, b"0")
        os.lseek(descriptor, 0, os.SEEK_SET)
        module = importlib.import_module("msvcrt" if os.name == "nt" else "fcntl")
        try:
            if os.name == "nt":
                module.locking(descriptor, module.LK_NBLCK, 1)
            else:
                module.flock(descriptor, module.LOCK_EX | module.LOCK_NB)
            held = True
        except OSError as exc:
            raise ErolError("Another execution owns this session lease") from exc
        yield
    finally:
        try:
            if held:
                os.lseek(descriptor, 0, os.SEEK_SET)
                if os.name == "nt":
                    module.locking(descriptor, module.LK_UNLCK, 1)
                else:
                    module.flock(descriptor, module.LOCK_UN)
        finally:
            os.close(descriptor)


def pid_alive(pid: int | None) -> bool:
    """Unknown process state counts as alive. Never signal an unrelated Windows PID."""
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle:
            # Invalid PID is dead; access denied is uncertain.
            return ctypes.get_last_error() != 87  # type: ignore[attr-defined]
        try:
            return kernel.WaitForSingleObject(handle, 0) != 0
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        # An observed POSIX process-group leader may leave live descendants after
        # abrupt runner death. Unknown group state must prevent a second worker.
        try:
            os.killpg(pid, 0)  # type: ignore[attr-defined]
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
    except PermissionError:
        return True


class RunStore:
    def __init__(self, directory: Path, project_id: str):
        self.directory = directory
        self.project_id = project_id
        path = directory / "runs.db"
        reject_links(path)
        self.db = sqlite3.connect(path, timeout=15, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('schema_version','1')")
        version = self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if version != ("1",):
            self.close()
            raise ErolError("Unsupported execution schema")
        self.db.execute("INSERT OR IGNORE INTO meta VALUES('project_id',?)", (project_id,))
        if self.db.execute("SELECT value FROM meta WHERE key='project_id'").fetchone() != (
            project_id,
        ):
            self.close()
            raise ErolError("Execution database belongs to another project")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,task_id TEXT UNIQUE NOT NULL,"
            "payload TEXT NOT NULL,cancel_requested INTEGER NOT NULL DEFAULT 0)"
        )
        if os.name == "posix":
            path.chmod(0o600)

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> RunStore:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def create(self, record: dict) -> None:
        self._validate(record)
        try:
            self.db.execute(
                "INSERT INTO runs(id,task_id,payload) VALUES(?,?,?)",
                (record["id"], record["task_id"], canonical(record)),
            )
        except sqlite3.IntegrityError as exc:
            raise ErolError("Run or task ID already used") from exc

    def save(self, record: dict) -> None:
        self._validate(record)
        cursor = self.db.execute(
            "UPDATE runs SET payload=? WHERE id=? AND task_id=?",
            (canonical(record), record["id"], record["task_id"]),
        )
        if cursor.rowcount != 1:
            raise ErolError("Execution record not found")

    def _validate(self, record: dict) -> None:
        identifier(record["id"])
        identifier(record["task_id"])
        if record.get("project_id") != self.project_id:
            raise ErolError("Execution project identity mismatch")
        # These fields are generated filesystem metadata. On POSIX a slash-joined
        # path with a run UUID can resemble one high-entropy base64 credential.
        # Keep full-pattern and per-component checks for these exact fields;
        # arbitrary model text, context and nested fields retain full-value scans.
        path_fields = {
            "project_root",
            "worktree",
            "directory",
            "checks_path",
            "patch",
            "delta_patch",
            "artifact_directory",
        }
        for key in path_fields & record.keys():
            if not isinstance(record[key], str):
                raise ErolError("Execution path must be an absolute string")
            assert_project_path_safe(Path(record[key]))
        assert_secret_safe({key: value for key, value in record.items() if key not in path_fields})
        if len(canonical(record).encode("utf-8")) > 1048576:
            raise ErolError("Execution record exceeds storage limit")

    def get(self, run_id: str) -> dict:
        import json

        row = self.db.execute(
            "SELECT payload,cancel_requested FROM runs WHERE id=?", (identifier(run_id),)
        ).fetchone()
        if row is None:
            raise ErolError("Execution record not found")
        record = json.loads(row[0])
        record["cancel_requested"] = bool(row[1])
        return record

    def list(self) -> list[dict]:
        return [self.get(row[0]) for row in self.db.execute("SELECT id FROM runs ORDER BY rowid")]

    def cancelled(self, run_id: str) -> bool:
        return self.get(run_id)["cancel_requested"]

    def request_cancel(self, run_id: str) -> dict:
        record = self.get(run_id)
        if record["status"] not in {"completed", "cancelled"}:
            self.db.execute("UPDATE runs SET cancel_requested=1 WHERE id=?", (run_id,))
        return self.get(run_id)

    @contextmanager
    def lease(self, path: Path | None = None):
        """Kernel releases this lock on owner exit; no stale-PID lock stealing."""
        path = path or self.directory / "run.lock"
        reject_links(path)
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        held = False
        try:
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"0")
            os.lseek(descriptor, 0, os.SEEK_SET)
            try:
                if os.name == "nt":
                    msvcrt = importlib.import_module("msvcrt")

                    msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
                else:
                    fcntl = importlib.import_module("fcntl")

                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held = True
            except OSError as exc:
                raise ErolError("Another execution owns this project's lease") from exc
            yield
        finally:
            if held:
                os.lseek(descriptor, 0, os.SEEK_SET)
                if os.name == "nt":
                    msvcrt = importlib.import_module("msvcrt")

                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                else:
                    fcntl = importlib.import_module("fcntl")

                    fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)
