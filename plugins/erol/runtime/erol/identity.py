"""Credential-free project identity, shared by all harness adapters."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit

from erol.common import ErolError


def normalized_remote(raw: str) -> str | None:
    raw = raw.strip()
    if "://" not in raw:
        match = re.fullmatch(r"(?:[^@/]+@)?([^:/]+):(.+)", raw)
        if match and not re.match(r"^[A-Za-z]:[\\/]", raw):
            host, path = match.groups()
            return host.lower() + "/" + path.strip("/").removesuffix(".git")
        return None
    try:
        parsed = urlsplit(raw)
        if parsed.scheme not in {"https", "http", "ssh", "git"} or not parsed.hostname:
            return None
        host = parsed.hostname.lower()
        if parsed.port and parsed.port not in {22, 80, 443}:
            host += f":{parsed.port}"
        path = parsed.path.strip("/").removesuffix(".git")
        if not path:
            return None
        return f"{host}/{path}"
    except ValueError:
        return None


def _git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    root: str
    source: str
    remote: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def detect_project(path: Path) -> Project:
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise ErolError("Project must be a directory")
    git_root = _git(path, "rev-parse", "--show-toplevel")
    root = Path(git_root).resolve() if git_root else path
    remote = normalized_remote(_git(root, "remote", "get-url", "origin") or "")
    name_source = remote.rsplit("/", 1)[-1] if remote else root.name
    name = re.sub(r"[^a-z0-9]+", "-", name_source.lower()).strip("-") or "project"
    identity = remote or os.path.normcase(str(root))
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return Project(f"{name[:48]}-{suffix}", name, str(root), "remote" if remote else "path", remote)
