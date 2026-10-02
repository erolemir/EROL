"""Small shared validation and persistence primitives."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ErolError(ValueError):
    """An actionable input or policy failure; messages never include raw payloads."""


def now() -> str:
    return datetime.now(UTC).isoformat()


def canonical(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}", value):
        raise ErolError("Invalid identifier")
    return value


def required_text(value: Any, field: str, limit: int = 16000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ErolError(f"{field} must be nonempty text of at most {limit} characters")
    return value.strip()


def confidence(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ErolError("confidence must be a number")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ErolError("confidence must be between 0 and 1")
    return float(value)


def atomic_write(path: Path, content: str) -> None:
    reject_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ErolError("Refusing to overwrite a symbolic link")
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".erol-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def reject_links(path: Path) -> None:
    """Reject links and Windows reparse points on supported Python versions."""
    for node in (path, *path.parents):
        if node.is_symlink():
            raise ErolError("Linked persistent paths are not supported")
        if node.exists():
            attrs = getattr(node.stat(follow_symlinks=False), "st_file_attributes", 0)
            if attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise ErolError("Linked persistent paths are not supported")
