"""Small, inspectable first-run flow using the existing external check-trust gate."""

from pathlib import Path

from .checktrust import CheckTrust
from .common import ErolError, digest
from .connections import ConnectionStore, Settings
from .execution import load_checks
from .identity import detect_project
from .store import Store


def onboard(
    root: Path,
    home: Path,
    *,
    connection: str | None = None,
    budget: float | None = None,
    checks: str | None = None,
    apply: bool = False,
    trust_checks: bool = False,
    expected_checks_digest: str | None = None,
    automatic_connection: bool = False,
) -> dict:
    project = detect_project(root)
    root = Path(project.root)
    connections = ConnectionStore(home, root)
    values = connections.settings.to_dict()
    if automatic_connection:
        values["preferred_connection"] = None
    if budget is not None:
        values["api_budget_usd"] = budget
    if connection is not None:
        connections.get(connection)
        values["preferred_connection"] = connection
    path = Path(checks).expanduser() if checks else None
    if path is not None:
        path = (
            (root / path).resolve(strict=True)
            if not path.is_absolute()
            else path.resolve(strict=True)
        )
        manifest = load_checks(path)
        values["checks_path"] = str(path)
    else:
        manifest = None
    validated = Settings.load(values)
    if expected_checks_digest is not None and digest(manifest) != expected_checks_digest:
        raise ErolError("Check manifest changed after preview; inspect the new commands first")
    if trust_checks and (not apply or manifest is None):
        raise ErolError("--trust-checks requires --apply and an inspected --checks manifest")
    result = {
        "project": project.to_dict(),
        "connection": connection,
        "api_budget_usd": validated.api_budget_usd,
        "checks_path": str(path) if path else None,
        "test_commands": [c["argv"] for c in manifest["checks"]] if manifest else [],
        "applied": apply,
        "checks_authorized": False,
        "checks_digest": digest(manifest) if manifest is not None else None,
        "next_step": "Inspect test_commands, then repeat with --apply --trust-checks"
        if manifest and not trust_checks
        else "Run erol doctor; then erol chat --prompt TASK",
    }
    if apply:
        with Store(home, project) as store:
            if trust_checks:
                assert manifest is not None
                CheckTrust(store.directory, root).approve(manifest)
                result["checks_authorized"] = True
        connections.settings = validated
        connections.save()
    return result


def wizard(root: Path, home: Path, *, read=input, write=print) -> dict:
    write("EROL: project → connection → API budget → acceptance checks")
    root = Path(read(f"Project [{root}]: ").strip() or root)
    project = detect_project(root)
    connections = ConnectionStore(home, Path(project.root))
    ids = [c.id for c in connections.settings.connections if c.enabled]
    write(
        "Connections: "
        + (", ".join(ids) if ids else "none; use erol terminal --command '/connect codex'")
    )
    connection = read("Connection ID (blank = automatic): ").strip() or None
    budget = float(
        read(f"API budget USD [{connections.settings.api_budget_usd}]: ").strip()
        or connections.settings.api_budget_usd
    )
    checks = read("Acceptance manifest path (blank = configure later): ").strip() or None
    preview = onboard(
        root,
        home,
        connection=connection,
        budget=budget,
        checks=checks,
        automatic_connection=connection is None,
    )
    for argv in preview["test_commands"]:
        write(repr(argv))
    approval = (
        read(
            "Save settings"
            + (" and authorize these exact check commands" if checks else "")
            + "? Type YES: "
        )
        == "YES"
    )
    if not approval:
        return preview
    return onboard(
        root,
        home,
        connection=connection,
        budget=budget,
        checks=checks,
        apply=True,
        trust_checks=bool(checks),
        expected_checks_digest=preview["checks_digest"],
        automatic_connection=connection is None,
    )
