"""Explicit live Codex policy queue and parallel review/resume trial; external fixture only."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from erol.common import atomic_write, canonical
from erol.config import Config
from erol.execution import Runner, git
from erol.identity import detect_project
from erol.learning import LearningEngine
from erol.registry import Registry
from erol.runstore import RunStore
from erol.store import Store
from erol.work import Queue, WorkStore, discover, load_policy


def trial() -> dict:
    import sys

    base = Path(tempfile.mkdtemp(prefix="erol-live-queue-"))
    root = base / "proje Türkçe spaces"
    root.mkdir()
    atomic_write(root / "calculator.py", "def add(a, b):\n    return a - b\n")
    atomic_write(root / ".gitignore", "__pycache__/\n")
    atomic_write(
        root / "test_sum.py",
        "import unittest\nfrom calculator import add\n"
        "class SumTests(unittest.TestCase):\n"
        "    def test_positive(self): self.assertEqual(add(2,3),5)\n"
        "    def test_negative(self): self.assertEqual(add(-2,-3),-5)\n"
        "    def test_zero(self): self.assertEqual(add(0,4),4)\n",
    )
    git(root, "init")
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.test",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "Controlled sum fixture",
    )
    checks = base / "checks.json"
    atomic_write(
        checks,
        canonical(
            {
                "schema_version": 1,
                "checks": [
                    {
                        "name": "sum-behavior",
                        "kind": "acceptance",
                        "argv": [sys.executable, "-B", "-m", "unittest", "discover", "-v"],
                        "timeout_seconds": 30,
                    }
                ],
            }
        ),
    )
    project = detect_project(root)
    policy = base / "policy.json"
    atomic_write(
        policy,
        canonical(
            {
                "schema_version": 1,
                "project_id": project.id,
                "limits": {
                    "max_tasks": 1,
                    "max_total_seconds": 900,
                    "task_seconds": 900,
                    "session_seconds": 300,
                    "check_seconds": 30,
                    "reviewers": 2,
                },
                "rules": [
                    {
                        "id": "repair",
                        "kinds": ["check"],
                        "paths": ["*"],
                        "harness": "codex",
                        "review_harness": "codex",
                        "mode": "development",
                        "checks": str(checks),
                    }
                ],
            }
        ),
    )
    interrupted = False

    class InterruptAfterReviews(Runner):
        def _parallel_review(self, record, patch):
            nonlocal interrupted
            result = super()._parallel_review(record, patch)
            if not interrupted and result["reason"] is None:
                interrupted = True
                raise KeyboardInterrupt
            return result

    with (
        Store(base / "external home", project) as store,
        RunStore(store.directory, project.id) as runs,
        WorkStore(store.directory, project.id) as work,
    ):
        engine = LearningEngine(store, Config(), Registry(project_store=store))
        queue = Queue(work, InterruptAfterReviews(store, engine, runs))
        scan = discover(root, work, checks_path=checks)
        loaded = load_policy(policy, project.id)
        job = queue.enqueue(loaded)[0]
        first = queue.execute(loaded)[0]
        saved = runs.get(first["run_id"])
        sessions = [peer["session_id"] for peer in saved["peer_reviews"]]
        final = queue.execute(loaded, resume_id=job["id"])[0] if interrupted else first
        record = runs.get(final["run_id"])
        return {
            "passed": final["status"] == "completed" and interrupted and len(set(sessions)) == 2,
            "fixture": str(base),
            "scan_id": scan["id"],
            "job_id": job["id"],
            "run_id": record["id"],
            "status": record["status"],
            "capabilities": record["capabilities"],
            "sessions": record["sessions"],
            "checks": record["checks"],
            "tested_digest": record["tested_digest"],
            "reviewed_digest": record["reviewed_digest"],
            "same_peer_sessions_after_resume": sessions
            == [peer["session_id"] for peer in record["peer_reviews"]],
            "peer_reviews": record["peer_reviews"],
            "reason": record.get("reason"),
            "limitations": (
                "One synthetic Codex repair, two read-only specialists; checkpoint interruption "
                "after native peer completion. No broad performance claim."
            ),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = trial()
    atomic_write(args.report, canonical(report) + "\n")
    print(canonical(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
