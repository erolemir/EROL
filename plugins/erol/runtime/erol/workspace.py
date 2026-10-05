"""Direct-workspace tools, task-relative snapshots, and observed acceptance checks."""

from __future__ import annotations

import codecs
import difflib
import hashlib
import os
import subprocess
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .checktrust import CheckTrust, command_environment
from .common import ErolError, atomic_write, canonical, reject_links
from .execution import load_checks
from .providers import visible
from .runprocess import observe
from .security import scan_secrets

IGNORED = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".pytest_cache",
    ".dart_tool",
    ".gradle",
    ".next",
}
MAX_FILES = 10000
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024


def capture_output(lines: list[str]) -> Callable[[bool, bytes], None]:
    def collect(stdout: bool, line: bytes) -> None:
        if len(lines) < 100:
            lines.append(visible(line.decode("utf-8", errors="replace"))[:2000])

    return collect


def protected(path: Path) -> bool:
    return any(
        p.casefold() in IGNORED
        or p.casefold() == ".env"
        or p.casefold().startswith(".env.")
        or p.casefold() in {".ssh", ".aws", ".codex", ".claude", ".gemini"}
        for p in path.parts
    )


def file_names(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            git_names = {s.decode("utf-8") for s in result.stdout.split(b"\0") if s}
            if len(git_names) > MAX_FILES:
                raise ErolError("Project exceeds snapshot file limit; narrow the project")
            return sorted(n for n in git_names if not protected(Path(n)))
    except (OSError, subprocess.SubprocessError):
        pass
    names = []
    for directory, directories, files in os.walk(root, followlinks=False):
        directories[:] = [
            n
            for n in directories
            if not protected(Path(n)) and not (Path(directory) / n).is_symlink()
        ]
        for name in files:
            path = (Path(directory) / name).relative_to(root)
            if not protected(path):
                names.append(path.as_posix())
                if len(names) > MAX_FILES:
                    raise ErolError("Project exceeds snapshot file limit; narrow the project")
    return sorted(names)


@dataclass(frozen=True)
class Fingerprint:
    sha256: str
    size: int


Snapshot = dict[str, bytes | Fingerprint]


def digest(content: bytes | Fingerprint | None) -> str | None:
    if content is None:
        return None
    return (
        content.sha256 if isinstance(content, Fingerprint) else hashlib.sha256(content).hexdigest()
    )


def snapshot(root: Path) -> Snapshot:
    result: Snapshot = {}
    total = 0
    for name in file_names(root):
        path = root / name
        if not path.exists() or path.is_symlink():
            continue
        reject_links(path)
        if not path.is_file():
            continue
        size = path.stat().st_size
        total += size
        if total > MAX_TOTAL:
            raise ErolError("Project snapshot exceeds 64 MiB; select a smaller /project folder")
        with path.open("rb") as stream:
            prefix = stream.read(min(size, 8192))
            if size > MAX_FILE:
                binary = b"\x00" in prefix or prefix.startswith(
                    (b"PK\x03\x04", b"%PDF-", b"\x89PNG", b"\xff\xd8\xff")
                )
                if not binary:
                    try:
                        codecs.getincrementaldecoder("utf-8")().decode(prefix, final=False)
                    except UnicodeError:
                        binary = True
                if not binary:
                    raise ErolError(
                        f"Source file {name} exceeds 2 MiB ({size} bytes); "
                        "select a smaller /project folder"
                    )
                hasher = hashlib.sha256(prefix)
                observed = len(prefix)
                while chunk := stream.read(65536):
                    observed += len(chunk)
                    if observed > MAX_TOTAL - (total - size):
                        raise ErolError("Project snapshot exceeds 64 MiB during read")
                    hasher.update(chunk)
                result[name] = Fingerprint(hasher.hexdigest(), observed)
                total += observed - size
            else:
                content = prefix + stream.read(MAX_FILE + 1 - len(prefix))
                if len(content) > MAX_FILE:
                    raise ErolError(f"File grew beyond snapshot limit: {name}")
                total += len(content) - size
                if total > MAX_TOTAL:
                    raise ErolError("Project snapshot exceeds 64 MiB during read")
                result[name] = content
    return result


def changes(before: Snapshot, after: Snapshot) -> list[dict]:
    result = []
    for name in sorted(before.keys() | after.keys()):
        old, new = before.get(name), after.get(name)
        if old == new:
            continue
        kind = "added" if old is None else "deleted" if new is None else "modified"
        item: dict[str, Any] = {
            "path": name,
            "status": kind,
            "before_sha256": digest(old),
            "after_sha256": digest(new),
        }
        try:
            if isinstance(old, Fingerprint) or isinstance(new, Fingerprint):
                raise UnicodeError
            old_text = (old or b"").decode("utf-8")
            new_text = (new or b"").decode("utf-8")
            if "\x00" in old_text + new_text:
                raise UnicodeError
            patch_lines = list(
                difflib.unified_diff(
                    old_text.splitlines(keepends=True),
                    new_text.splitlines(keepends=True),
                    fromfile=f"a/{name}",
                    tofile=f"b/{name}",
                )
            )
            patch = "".join(
                line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                for line in patch_lines
            )
            item.update(
                {
                    "diff": visible(patch[:64000]),
                    "diff_truncated": len(patch) > 64000,
                    "binary": False,
                }
            )
        except UnicodeError:
            item.update({"diff": "[binary file changed]", "diff_truncated": False, "binary": True})
        result.append(item)
    return result


def tool_schema(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


TEXT = {"type": "string"}
TOOLS = [
    tool_schema(
        "list_files", "List nonignored project files, excluding credential folders.", {}, []
    ),
    tool_schema(
        "read_file",
        "Read a project UTF-8 file and its SHA256. Inspect before editing.",
        {"path": TEXT},
        ["path"],
    ),
    tool_schema(
        "search",
        "Search literal text in project UTF-8 files; results are bounded.",
        {"query": TEXT},
        ["query"],
    ),
    tool_schema(
        "write_file",
        (
            "Create/update UTF-8 file. Existing files require the read_file "
            "SHA256; new files require null."
        ),
        {"path": TEXT, "content": TEXT, "expected_sha256": {"type": ["string", "null"]}},
        ["path", "content", "expected_sha256"],
    ),
    tool_schema(
        "delete_file",
        "Delete one file only if its current SHA256 matches the observed hash.",
        {"path": TEXT, "expected_sha256": TEXT},
        ["path", "expected_sha256"],
    ),
    tool_schema(
        "run_command",
        (
            "Run an exact command argv explicitly enabled in terminal settings or"
            " the check manifest. Shell strings are not interpreted."
        ),
        {"argv": {"type": "array", "items": TEXT}},
        ["argv"],
    ),
]


class Workspace:
    def __init__(
        self,
        root: Path,
        *,
        readonly: bool = False,
        allowed_commands: list[list[str]] | None = None,
        check_trust: CheckTrust | None = None,
        checks_manifest: dict | None = None,
        stopped: threading.Event | None = None,
        deadline: float | None = None,
        on_process: Callable[[int | None], None] = lambda pid: None,
    ):
        self.root = root.resolve(strict=True)
        self.readonly = readonly
        self.allowed_commands = allowed_commands or []
        self.check_trust, self.checks_manifest = check_trust, checks_manifest
        self.stopped = stopped or threading.Event()
        self.command_evidence: list[dict] = []
        self.deadline = deadline
        self.on_process = on_process

    @property
    def tools(self) -> list[dict]:
        return [
            t
            for t in TOOLS
            if not self.readonly or t["name"] in {"list_files", "read_file", "search"}
        ]

    def path(self, name: str) -> Path:
        if not isinstance(name, str) or not name or len(name) > 1000 or "\x00" in name:
            raise ErolError("File path must be a bounded relative path")
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or protected(relative):
            raise ErolError("File is outside the permitted project scope")
        path = self.root / relative
        reject_links(path)
        resolved = path.resolve()
        if resolved == self.root or not resolved.is_relative_to(self.root):
            raise ErolError("File is outside the permitted project scope")
        return path

    def read(self, name: str) -> dict:
        path = self.path(name)
        if not path.is_file() or path.stat().st_size > MAX_FILE:
            raise ErolError("File unavailable or exceeds reading limit")
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeError as exc:
            raise ErolError("File is not UTF-8 text") from exc
        return {
            "path": name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "content": visible(text[:64000]),
            "truncated": len(text) > 64000,
        }

    def dispatch(self, name: str, arguments: dict) -> str:
        if self.stopped.is_set():
            raise ErolError("Task cancelled")
        schema = next((t["parameters"] for t in self.tools if t["name"] == name), None)
        if schema is None:
            raise ErolError("Tool unavailable for this role")
        if set(arguments) - set(schema["properties"]) or set(schema["required"]) - set(arguments):
            raise ErolError("Invalid tool argument fields")
        if name == "list_files":
            names = file_names(self.root)
            return canonical({"files": names[:1000], "truncated": len(names) > 1000})
        if name == "read_file":
            return canonical(self.read(arguments["path"]))
        if name == "search":
            query = arguments["query"]
            if not isinstance(query, str) or not query or len(query) > 500:
                raise ErolError("Search query must be 1..500 characters")
            matches = []
            for filename in file_names(self.root):
                try:
                    read = self.read(filename)
                except ErolError:
                    continue
                for i, line in enumerate(read["content"].splitlines(), 1):
                    if query.casefold() in line.casefold():
                        matches.append({"path": filename, "line": i, "text": line[:300]})
                        if len(matches) >= 100:
                            return canonical({"matches": matches, "truncated": True})
            return canonical({"matches": matches, "truncated": False})
        if name in {"write_file", "delete_file"}:
            path = self.path(arguments["path"])
            current = path.read_bytes() if path.is_file() else None
            expected = arguments.get("expected_sha256")
            actual = hashlib.sha256(current).hexdigest() if current is not None else None
            if actual != expected:
                raise ErolError("File changed or was not read; read it again before editing")
            if name == "delete_file":
                if current is None:
                    raise ErolError("Delete requires an existing observed file")
                path.unlink()
            else:
                content = arguments["content"]
                if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_FILE:
                    raise ErolError("File content exceeds writing limit")
                if scan_secrets(content):
                    raise ErolError(
                        "Refusing to write credential-like content through the API tool"
                    )
                atomic_write(path, content)
            return canonical(
                {
                    "path": arguments["path"],
                    "status": "deleted" if name == "delete_file" else "written",
                }
            )
        argv = arguments["argv"]
        if argv not in self.allowed_commands:
            raise ErolError(
                "Command is not enabled; add its literal argv in /settings allowed_commands"
            )
        lines: list[str] = []
        policy: dict = {"environment": [], "prefix": []}
        if self.checks_manifest and any(argv == c["argv"] for c in self.checks_manifest["checks"]):
            if self.check_trust is None:
                raise ErolError("Unreviewed check command")
            self.check_trust.assert_root(self.root)
            policy = self.check_trust.require(self.checks_manifest)
        timeout = min(300, self.deadline - time.monotonic()) if self.deadline else 300
        if timeout <= 0:
            raise ErolError("Task time budget exhausted")
        result = observe(
            policy["prefix"] + argv,
            self.root,
            timeout=timeout,
            on_start=self.on_process,
            on_output=capture_output(lines),
            cancelled=self.stopped.is_set,
            environment=command_environment(policy["environment"]),
        )
        evidence = {
            "argv": argv,
            "exit_code": result["exit_code"],
            "reason": result["reason"],
            "output": "".join(lines)[-16000:],
            "evidence_type": "erol_observed_command",
        }
        self.command_evidence.append(evidence)
        return canonical(evidence)


def check_manifest(root: Path, configured: str | None, *, trust: CheckTrust | None = None) -> dict:
    if not configured:
        return {"checks": [], "reason": "No check manifest configured; use /settings checks_path"}
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = root / path
    reject_links(path)
    manifest = load_checks(path.resolve(strict=True))
    if trust is None:
        raise ErolError("Unreviewed check manifest; use erol checks trust --file PATH")
    trust.assert_root(root)
    trust.require(manifest)
    return manifest


def run_checks(
    root: Path,
    manifest: dict,
    stopped: threading.Event,
    *,
    deadline: float | None = None,
    on_process: Callable[[int | None], None] = lambda pid: None,
    trust: CheckTrust | None = None,
) -> list[dict]:
    reports = []
    if manifest["checks"]:
        if trust is None:
            raise ErolError("Unreviewed check manifest; use erol checks trust --file PATH")
        trust.assert_root(root)
    for check in manifest["checks"]:
        if stopped.is_set():
            break
        lines: list[str] = []
        assert trust is not None
        policy = trust.require(manifest)
        timeout = check["timeout_seconds"]
        if deadline is not None:
            timeout = min(timeout, deadline - time.monotonic())
            if timeout <= 0:
                raise ErolError("Task time budget exhausted before acceptance check")
        result = observe(
            policy["prefix"] + check["argv"],
            root,
            timeout=timeout,
            on_start=on_process,
            cancelled=stopped.is_set,
            on_output=capture_output(lines),
            environment=command_environment(policy["environment"]),
        )
        reports.append(
            {
                "name": check["name"],
                "kind": check["kind"],
                "argv": check["argv"],
                "passed": result["exit_code"] == 0 and not result["reason"],
                "exit_code": result["exit_code"],
                "reason": result["reason"],
                "output": "".join(lines)[-16000:],
                "evidence_type": "erol_observed_command",
            }
        )
    return reports
