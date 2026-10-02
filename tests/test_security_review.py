"""Regression contracts for independently reproduced trust and concurrency faults."""

import os
import sqlite3
import stat
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from erol.common import ErolError
from erol.config import Config
from erol.identity import detect_project
from erol.learning import LearningEngine
from erol.registry import evaluate_skill
from erol.security import scan_secrets
from erol.store import Store


def verification(reference="fixture:security-review"):
    return {
        "implementer": "fixture-builder",
        "reviewer": "fixture-reviewer",
        "tests": [{"name": "regression", "passed": True, "reference": reference}],
    }


class SecurityReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "project"
        self.root.mkdir()
        with patch("erol.identity._git", return_value=None):
            self.project = detect_project(self.root)
        self.home = self.base / "external-home"
        self.store = Store(self.home, self.project)
        self.addCleanup(self.store.close)
        self.engine = LearningEngine(self.store)

    def candidate(self):
        for index in range(3):
            result = self.engine.record_incident(
                {
                    "id": f"incident-{index}",
                    "task_id": f"repair-{index}",
                    "symptom": "Widget processor loses rows",
                    "error": "cursor boundary mismatch",
                    "component": "widget processor",
                    "root_cause": "Cursor ordering is not unique",
                    "solution": "Use a stable composite cursor and verify row coverage",
                    "confidence": 0.95,
                    "verification": verification(f"fixture:repair-{index}"),
                }
            )
        return result["candidate"]

    def evaluate(self, candidate):
        trigger = candidate["skill"]["triggers"][0]
        return self.engine.evaluate(
            candidate["id"],
            {
                "positive_tasks": [f"Investigate {trigger}"],
                "negative_tasks": ["CSS button layout", f"{trigger} different root cause"],
                "behavior": verification(),
            },
        )

    def active(self):
        candidate = self.candidate()
        self.assertTrue(self.evaluate(candidate)["passed"])
        return self.engine.activate(candidate["id"])

    def promotion(self):
        skill = self.active()
        for index in range(3):
            key = f"verified-use-{index}"
            self.engine.begin_task(key, skill["triggers"][0])
            self.engine.complete_task(key, verification(f"fixture:use-{index}"))
        return skill, self.engine.promotion_candidate(skill["name"])

    def blocked_writer(self, operation):
        """Prepare a second connection before the primary acquires its write lock.

        A short SQLite timeout avoids deadlocking the callback. It proves an
        interleaved lifecycle mutation cannot enter the primary gate's transaction.
        """
        ready, proceed, done = threading.Event(), threading.Event(), threading.Event()
        result = {}

        def worker():
            try:
                with Store(self.home, self.project) as other:
                    other.db.execute("PRAGMA busy_timeout=100")
                    ready.set()
                    if not proceed.wait(5):
                        raise TimeoutError("Concurrent writer was never released")
                    operation(LearningEngine(other))
            except BaseException as error:
                result["error"] = error
            finally:
                ready.set()
                done.set()

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        self.addCleanup(lambda: (proceed.set(), thread.join(5)))
        self.assertTrue(ready.wait(5), "Second database connection was not ready")
        self.assertNotIn("error", result, "Second connection failed during setup")

        def probe():
            proceed.set()
            self.assertTrue(done.wait(5), "Concurrent write did not finish within its timeout")
            self.assertIsInstance(result.get("error"), sqlite3.OperationalError)
            self.assertIn("locked", str(result["error"]).lower())

        return probe

    def test_short_and_numeric_labelled_credentials_never_persist(self):
        for index, payload in enumerate(
            (
                {"password": 12345},
                {"api_key": "abc"},
                {"password": "a"},
                {"token": 123456},
                {"authorization": ["short"]},
            )
        ):
            with self.subTest(payload_type=next(iter(payload))):
                self.assertTrue(scan_secrets(payload))
                with self.assertRaises(ErolError):
                    self.store.put("state", {"id": f"unsafe-{index}", "data": payload})
        self.assertEqual(self.store.list("state"), [])
        self.assertFalse(scan_secrets({"context_tokens": 4000, "max_active_skills": 4}))

    def test_normalized_project_hash_is_not_a_credential_but_labels_still_are(self):
        identity = "working-project-2fca346db6561871"
        self.assertFalse(scan_secrets(identity))
        self.assertFalse(scan_secrets({"project_id": identity}))
        self.assertFalse(scan_secrets({"id": identity, "source_project_id": identity}))
        with Store(self.base / "identity-home", replace(self.project, id=identity)) as store:
            self.assertEqual(store.project_id, identity)
        self.store.put("state", {"id": "identity-record", "project_id": identity})
        self.assertEqual(self.store.get("state", "identity-record")["project_id"], identity)
        self.assertTrue(scan_secrets({"password": identity}))
        self.assertTrue(scan_secrets(f"token={identity}"))
        self.assertTrue(scan_secrets("aB3dE7fG9hJ2kL4mN6pQ8rS0tU5vW1xY"))

    def test_short_labelled_credentials_in_raw_logs_never_persist(self):
        for index, text in enumerate(("password=abc", "api_key=x", "token=12")):
            with self.subTest(credential_field=text.partition("=")[0]):
                self.assertTrue(scan_secrets(text))
                with self.assertRaises(ErolError):
                    self.store.put("state", {"id": f"unsafe-log-{index}", "text": text})
        self.assertEqual(self.store.list("state"), [])

    def test_promotion_approval_revalidates_stale_evaluation(self):
        skill, candidate = self.promotion()
        self.store.mark_stale("evals", skill["eval_id"])
        with self.assertRaises(ErolError):
            self.engine.promote(
                candidate["id"],
                approve=True,
                cross_project_report={
                    "project_id": "independent-project",
                    "verification": verification(),
                },
            )
        self.assertEqual(
            self.store.get("promotions", candidate["id"])["status"], "promotion_candidate"
        )

    def test_promotion_approval_revalidates_withdrawn_real_use_evidence(self):
        skill, candidate = self.promotion()
        for use in self.store.list("uses"):
            self.store.mark_stale("uses", use["id"])
        self.assertEqual(self.engine.metrics(skill["name"])["successful_tasks"], 0)
        with self.assertRaises(ErolError):
            self.engine.promote(
                candidate["id"],
                approve=True,
                cross_project_report={
                    "project_id": "independent-project",
                    "verification": verification(),
                },
            )

    def test_promotion_approval_serializes_concurrent_failed_usage(self):
        skill, candidate = self.promotion()
        self.engine.begin_task("pending-failure", skill["triggers"][0])
        failure = {"reason": "Regression failed", "reference": "fixture:failure"}
        probe = self.blocked_writer(lambda other: other.failed_task("pending-failure", failure))
        original_valid_eval = self.engine._valid_eval

        def interleave(selected_skill, evaluation):
            probe()
            original_valid_eval(selected_skill, evaluation)

        with patch.object(self.engine, "_valid_eval", side_effect=interleave):
            result = self.engine.promote(
                candidate["id"],
                approve=True,
                cross_project_report={
                    "project_id": "independent-project",
                    "verification": verification(),
                },
            )
        self.assertEqual(result["status"], "approved_for_generalization")
        self.assertFalse(result["global_registry_modified"])
        self.engine.failed_task("pending-failure", failure)
        with self.assertRaises(ErolError):
            self.engine.promote(
                candidate["id"],
                approve=True,
                cross_project_report={
                    "project_id": "independent-project",
                    "verification": verification(),
                },
            )

    def test_project_skill_export_requires_current_passing_eval(self):
        skill = self.active()
        self.store.mark_stale("evals", skill["eval_id"])
        with self.assertRaises(ErolError):
            self.engine.export_skill(skill["name"])

    def test_rollback_respects_disabled_activation_policy(self):
        skill = self.active()
        engine = LearningEngine(self.store, replace(Config(), project_skill_activation=False))
        with self.assertRaises(ErolError):
            engine.rollback(skill["name"], skill["version"])

    def test_evaluation_serializes_concurrent_activation(self):
        candidate = self.candidate()
        self.assertTrue(self.evaluate(candidate)["passed"])
        probe = self.blocked_writer(lambda other: other.activate(candidate["id"]))

        def interleave(skill, cases):
            probe()
            return evaluate_skill(skill, cases)

        with patch("erol.learning.evaluate_skill", side_effect=interleave):
            self.assertTrue(self.evaluate(candidate)["passed"])
        self.assertEqual(self.store.get("candidates", candidate["id"])["status"], "evaluated")
        self.assertEqual(self.store.list("skills"), [])
        active = self.engine.activate(candidate["id"])
        self.assertEqual(active["status"], "project_active")

    def test_rollback_serializes_concurrent_failed_usage(self):
        skill = self.active()
        self.engine.begin_task("failing-use", skill["triggers"][0])
        failure = {"reason": "Regression failed", "reference": "fixture:regression-failure"}
        probe = self.blocked_writer(lambda other: other.failed_task("failing-use", failure))
        original_put = self.store.put

        def interleave(kind, data, **kwargs):
            if kind == "skills":
                probe()
            return original_put(kind, data, **kwargs)

        with patch.object(self.store, "put", side_effect=interleave):
            self.assertEqual(
                self.engine.rollback(skill["name"], skill["version"])["status"], "project_active"
            )
        # Once the rollback releases its lock, a failed use disables that revision.
        self.engine.failed_task("failing-use", failure)
        self.assertEqual(self.store.get("skills", skill["name"])["status"], "needs_revision")
        with self.assertRaises(ErolError):
            self.engine.rollback(skill["name"], skill["version"])

    def test_windows_reparse_attribute_is_rejected_without_is_junction_api(self):
        original_stat = Path.stat

        def fake_stat(path, **kwargs):
            current = original_stat(path, **kwargs)
            if path == self.home:
                return SimpleNamespace(st_mode=current.st_mode, st_file_attributes=0x400)
            return current

        with patch.object(Path, "stat", autospec=True, side_effect=fake_stat):
            with self.assertRaises(ErolError):
                Store(self.home, self.project)

    @unittest.skipIf(os.name == "nt", "POSIX permission bits do not validate Windows ACLs")
    def test_new_state_directories_and_database_are_private(self):
        self.store.put("state", {"id": "private-state", "text": "Project memory"})
        for path in (
            self.home,
            self.home / "state",
            self.store.directory,
            self.store.directory / "memory.db",
        ):
            with self.subTest(path=path.name):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode) & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
