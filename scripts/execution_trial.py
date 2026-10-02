"""Explicit live acceptance trial; creates only an external temporary Git fixture."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from erol.common import atomic_write, canonical
from erol.config import Config
from erol.execution import Runner
from erol.harness import CliHarness
from erol.identity import detect_project
from erol.learning import LearningEngine
from erol.registry import Registry
from erol.runstore import RunStore
from erol.store import Store


def trial(harness: str) -> dict:
    # Retain the fixture for inspection. No local incident DB or credentials are copied.
    base = Path(tempfile.mkdtemp(prefix="erol-live-execution-"))
    root = base / "project"
    root.mkdir()
    (root / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (root / "test_calculator.py").write_text(
        "import unittest\nfrom calculator import add\n\n"
        "class ArithmeticTests(unittest.TestCase):\n"
        "    def test_positive(self): self.assertEqual(add(2, 3), 5)\n"
        "    def test_negative(self): self.assertEqual(add(-2, -3), -5)\n"
        "    def test_zero(self): self.assertEqual(add(0, 4), 4)\n",
        encoding="utf-8",
    )
    (root / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    for args in (
        ("init",),
        ("config", "user.name", "EROL local fixture"),
        ("config", "user.email", "fixture@example.test"),
        ("add", "."),
        ("commit", "-m", "arithmetic acceptance fixture"),
    ):
        subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)
    checks_path = base / "checks.json"
    atomic_write(
        checks_path,
        canonical(
            {
                "schema_version": 1,
                "checks": [
                    {
                        "name": "arithmetic-acceptance",
                        "kind": "acceptance",
                        "argv": [sys.executable, "-B", "-m", "unittest", "discover", "-v"],
                        "timeout_seconds": 30,
                    }
                ],
            }
        ),
    )
    interrupted = False

    class InterruptAfterWorker(CliHarness):
        def execute(self, role, prompt, artifact_directory, **kwargs):
            nonlocal interrupted
            result = super().execute(role, prompt, artifact_directory, **kwargs)
            if role == "implementer" and not interrupted and result["reason"] is None:
                interrupted = True
                raise KeyboardInterrupt  # native session finished, runner checkpoint interrupted
            return result

    project = detect_project(root)
    with Store(base / "external home", project) as store:
        engine = LearningEngine(store, Config(), Registry(project_store=store))
        with RunStore(store.directory, project.id) as runs:
            runner = Runner(store, engine, runs, harness_factory=InterruptAfterWorker)
            first = runner.start(
                "Repair calculator.add so it returns the sum for positive, negative and zero "
                "arguments. Preserve the supplied acceptance tests and public function signature.",
                harness,
                checks_path,
            )
            print(
                canonical(
                    {
                        "phase": "first",
                        "harness": harness,
                        "status": first["status"],
                        "run_id": first["id"],
                        "fixture": str(base),
                    }
                ),
                flush=True,
            )
            result = runner.resume(first["id"]) if interrupted else first
            report = {
                "harness": harness,
                "status": result["status"],
                "run_id": result["id"],
                "fixture": str(base),
                "capabilities": result["capabilities"],
                "baseline": result["baseline"],
                "checks": result["checks"],
                "sessions": result["sessions"],
                "tested_digest": result["tested_digest"],
                "reviewed_digest": result["reviewed_digest"],
                "runner_interruption_after_native_worker": interrupted,
                "same_worker_session_resumed": interrupted
                and (result["worker_session"] == first["worker_session"]),
                "worker_diagnostics": result["attempts"][-1]
                .get("interruption", {})
                .get("diagnostics", [])
                if result["attempts"]
                else [],
                "reason": result.get("reason"),
                "patch": result.get("patch"),
                "review": result["review"],
                "limitations": "Synthetic arithmetic fixture; no broad task-success claim. "
                "Interruption is injected between native worker completion and runner checkpoint.",
            }
            report["passed"] = (
                result["status"] == "completed"
                and interrupted
                and report["same_worker_session_resumed"]
                and any(not check["passed"] for check in result["baseline"])
                and (root / "calculator.py").read_text().endswith("return a - b\n")
            )
            return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=("codex", "claude"), required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = trial(args.harness)
    atomic_write(args.report, canonical(report) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
