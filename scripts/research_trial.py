"""Explicit live technical-research trial; local requirements are not factual graders."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from erol.checktrust import CheckTrust
from erol.common import atomic_write, canonical
from erol.config import Config
from erol.execution import Runner, load_checks
from erol.identity import detect_project
from erol.learning import LearningEngine
from erol.registry import Registry
from erol.runstore import RunStore
from erol.store import Store


def trial(harness: str) -> dict:
    base = Path(tempfile.mkdtemp(prefix="erol-live-research-"))
    root = base / "project"
    root.mkdir()
    (root / "README.md").write_text(
        "Local dependency-free Python memory service.\n", encoding="utf-8"
    )
    for args in (
        ("init",),
        ("config", "user.name", "EROL fixture"),
        ("config", "user.email", "fixture@example.test"),
        ("add", "."),
        ("commit", "-m", "research fixture"),
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    check = base / "acceptance.py"
    check.write_text(
        "import json,pathlib\nfrom urllib.parse import urlsplit\n"
        "root=pathlib.Path('research')\n"
        "report=(root/'report.md').read_text(encoding='utf-8').lower()\n"
        "ledger=json.loads((root/'sources.json').read_text(encoding='utf-8'))\n"
        "terms=['sqlite','postgresql','concurrency','deployment']\n"
        "assert all(term in report for term in terms)\n"
        "hosts={urlsplit(s['url']).hostname for s in ledger['sources']}\n"
        "assert any(h and (h=='sqlite.org' or h.endswith('.sqlite.org')) for h in hosts)\n"
        "assert any(h and (h=='postgresql.org' or h.endswith('.postgresql.org')) for h in hosts)\n"
        "assert len(ledger['claims'])>=4 and ledger['limitations']\n"
        "assert all(s['kind']=='primary' for s in ledger['sources'])\n",
        encoding="utf-8",
    )
    manifest = base / "checks.json"
    atomic_write(
        manifest,
        canonical(
            {
                "schema_version": 1,
                "checks": [
                    {
                        "name": "research-requirements",
                        "kind": "acceptance",
                        "argv": [sys.executable, "-B", str(check)],
                        "timeout_seconds": 30,
                    }
                ],
            }
        ),
    )
    project = detect_project(root)
    with (
        Store(base / "external home", project) as store,
        RunStore(store.directory, project.id) as runs,
    ):
        # The opt-in trial owns the fixed manifest and generated fixture code.
        CheckTrust(store.directory, root).approve(load_checks(manifest))
        engine = LearningEngine(store, Config(), Registry(project_store=store))
        result = Runner(store, engine, runs).start(
            "In English, compare SQLite and PostgreSQL for a local Python project-memory service "
            "with no third-party Python runtime dependencies. Use original official documentation "
            "from sqlite.org and postgresql.org. Explain concurrency, deployment, dependencies "
            "tradeoffs and when the recommendation changes. Keep this narrow: four to six material "
            "claims, two or three sources, a comparison table, a recommendation and limitations. "
            "Use explicit words concurrency and deployment so the supplied requirements check can "
            "detect coverage. Do not make performance claims or propose paid services.",
            harness,
            manifest,
            mode="research",
        )
        return {
            key: result.get(key)
            for key in (
                "id",
                "status",
                "reason",
                "mode",
                "capabilities",
                "sessions",
                "baseline",
                "checks",
                "review",
                "tested_digest",
                "reviewed_digest",
                "worktree",
                "patch",
                "source_access_receipts",
            )
        } | {
            "fixture": str(base),
            "passed": result["status"] == "completed",
            "limitations": (
                "Local checks cover report requirements and structure. Source accuracy relies on "
                "a separate native model review; no externally authenticated source evidence."
            ),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=("codex", "claude"), required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = trial(args.harness)
    atomic_write(args.report, canonical(report) + "\n")
    print(canonical(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
