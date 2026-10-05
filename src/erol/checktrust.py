"""Explicit, external check authorization. Approval is not an OS sandbox."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .common import ErolError, atomic_write, canonical, digest, reject_links
from .security import assert_secret_safe

ENVIRONMENT_NAMES = {
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "LC_MESSAGES",
    "TZ",
    "TERM",
    "NO_COLOR",
    "PYTHONIOENCODING",
    "PYTHONUTF8",
}
INJECTION_NAMES = {
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "NODE_OPTIONS",
    "BASH_ENV",
    "ENV",
    "RUBYOPT",
    "PERL5OPT",
    "PERL5LIB",
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
}


def command_environment(extra: list[str] | None = None) -> dict[str, str]:
    """Never inherit arbitrary account, credential or interpreter startup variables."""
    names = ENVIRONMENT_NAMES | {name.upper() for name in (extra or [])}
    if names & INJECTION_NAMES:
        raise ErolError("Interpreter injection variables cannot be inherited by checks")
    environment = {k: v for k, v in os.environ.items() if k.upper() in names}
    for name, value in environment.items():
        assert_secret_safe({name: value})
    environment["EROL_RUN_ACTIVE"] = "1"
    return environment


class CheckTrust:
    def __init__(self, directory: Path, root: Path):
        reject_links(directory.expanduser().absolute())
        reject_links(root.expanduser().absolute())
        self.root = os.path.normcase(str(root.resolve()))
        location = directory.expanduser().resolve()
        if location == root.resolve() or root.resolve() in location.parents:
            raise ErolError("Check trust must be external to the project")
        self.path = location / "check-trust" / (digest(self.root) + ".json")

    def records(self) -> list[dict]:
        reject_links(self.path)
        if not self.path.exists():
            return []
        if self.path.stat().st_size > 131072:
            raise ErolError("Check trust exceeds input budget")
        try:
            data = json.loads(self.path.read_text("utf-8"))
            if (
                not isinstance(data, dict)
                or set(data) != {"schema_version", "root", "approvals"}
                or type(data["schema_version"]) is not int
                or data["schema_version"] != 1
                or data["root"] != self.root
                or not isinstance(data["approvals"], list)
                or len(data["approvals"]) > 100
            ):
                raise ValueError
            return [self.validate(item) for item in data["approvals"]]
        except (ValueError, TypeError, KeyError) as exc:
            raise ErolError("Invalid external check trust record") from exc

    @staticmethod
    def validate(item: dict) -> dict:
        if (
            not isinstance(item, dict)
            or set(item) != {"manifest_digest", "environment", "prefix"}
            or not isinstance(item["manifest_digest"], str)
            or not re.fullmatch(r"[a-f0-9]{64}", item["manifest_digest"])
            or not isinstance(item["environment"], list)
            or len(item["environment"]) > 30
            or any(
                not isinstance(n, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", n)
                for n in item["environment"]
            )
            or not isinstance(item["prefix"], list)
            or len(item["prefix"]) > 100
            or any(not isinstance(a, str) or not a or "\x00" in a for a in item["prefix"])
        ):
            raise ErolError("Invalid check execution policy")
        if set(item["environment"]) & INJECTION_NAMES:
            raise ErolError("Interpreter injection variables cannot be inherited by checks")
        assert_secret_safe(item)
        return item

    def approve(
        self,
        manifest: dict,
        *,
        environment: list[str] | None = None,
        prefix: list[str] | None = None,
    ) -> dict:
        item = self.validate(
            {
                "manifest_digest": digest(manifest),
                "environment": [] if environment is None else environment,
                "prefix": [] if prefix is None else prefix,
            }
        )
        approvals = [r for r in self.records() if r["manifest_digest"] != item["manifest_digest"]]
        if len(approvals) >= 100:
            raise ErolError("Check trust exceeds approval limit")
        approvals.append(item)
        atomic_write(
            self.path,
            canonical({"schema_version": 1, "root": self.root, "approvals": approvals}) + "\n",
        )
        return item

    def require(self, manifest: dict) -> dict:
        for item in self.records():
            if item["manifest_digest"] == digest(manifest):
                return item
        raise ErolError(
            "Unreviewed check manifest; inspect commands and use erol checks trust --file PATH"
        )

    def assert_root(self, root: Path) -> None:
        if os.path.normcase(str(root.resolve())) != self.root:
            raise ErolError("Check trust belongs to a different original project root")

    def revoke(self, manifest: dict) -> None:
        approvals = [r for r in self.records() if r["manifest_digest"] != digest(manifest)]
        atomic_write(
            self.path,
            canonical({"schema_version": 1, "root": self.root, "approvals": approvals}) + "\n",
        )
