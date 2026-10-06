"""Separate package, executable, connection and verification health."""

from pathlib import Path

from .chat import ConnectionContext
from .checktrust import CheckTrust
from .common import ErolError
from .harness import command_prefix
from .providers import visible
from .workspace import check_manifest


def health(store, pack: dict) -> dict:
    root = Path(store.project.root)
    executables = {}
    for name in ("codex", "claude"):
        try:
            executables[name] = {
                "found": True,
                "argv_prefix": command_prefix(name),
                "model_access_verified": False,
            }
        except ErolError as exc:
            executables[name] = {"found": False, "reason": str(exc), "model_access_verified": False}
    context = ConnectionContext(root, store.home, project=root)
    providers, _ = context.providers()
    try:
        checks = check_manifest(
            root, context.connections.settings.checks_path, trust=CheckTrust(store.directory, root)
        )
        validation = {
            "configured": bool(checks["checks"]),
            "authorized": bool(checks["checks"]),
            "acceptance_configured": any(c["kind"] == "acceptance" for c in checks["checks"]),
            "reason": checks.get("reason"),
        }
    except (ErolError, OSError, ValueError) as exc:
        validation = {
            "configured": bool(context.connections.settings.checks_path),
            "authorized": False,
            "acceptance_configured": False,
            "reason": visible(str(exc)),
        }
    return {
        "passed": pack["passed"],
        "skills": pack,
        "package_health": {"passed": pack["passed"]},
        "harnesses_found": {n: e["found"] for n, e in executables.items()},
        "executables": executables,
        "connections": providers,
        "validation": validation,
        "memory_schema": 1,
        "access_note": "Executable discovery/login/configuration does not prove a live model turn",
    }
