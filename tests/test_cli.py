"""Subprocess integration for the incident-to-project-skill CLI contract."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_learning import incident, verification


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "project with spaces"
        self.repo.mkdir()
        self.home = self.base / "external home"
        self.source = Path(__file__).resolve().parents[1] / "src"
        self.input_index = 0

    def input(self, value):
        self.input_index += 1
        path = self.base / f"input {self.input_index}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)

    def test_domain_catalog_filter_and_invalid_category(self):
        catalog = self.cli("skills", "list", "--category", "marketing")
        names = {entry["name"] for entry in catalog["skills"]}
        self.assertIn("paid-search-campaign", names)
        self.assertIn("marketing-copywriting", names)
        self.assertNotIn("incident-debugging", names)
        self.assertTrue(all(entry["category"] == "marketing" for entry in catalog["skills"]))
        self.assertFalse(catalog["bodies_loaded"])
        self.cli("skills", "list", "--category", "unknown-domain", expected_exit=2)

    def cli(self, *arguments, expected_exit=0):
        environment = {**os.environ, "PYTHONPATH": str(self.source), "PYTHONUTF8": "1"}
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "erol",
                "--project",
                str(self.repo),
                "--home",
                str(self.home),
                *arguments,
            ],
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
        self.assertEqual(process.returncode, expected_exit, process.stderr or process.stdout)
        stream = process.stdout if expected_exit == 0 else process.stderr
        return json.loads(stream)

    def test_cli_end_to_end_learning_activation_usage_and_review(self):
        first = self.cli("incident", "record", "--input", self.input(incident(1)))
        self.assertIsNone(first["candidate"])
        second = self.cli("incident", "record", "--input", self.input(incident(2)))
        self.assertEqual(second["repeat_matches"][0]["id"], first["incident"]["id"])
        third = self.cli("incident", "record", "--input", self.input(incident(3)))
        candidate = third["candidate"]
        candidate_id = candidate["id"]
        trigger = candidate["skill"]["triggers"][0]
        refusal = self.cli("learning", "activate", "--id", candidate_id, expected_exit=2)
        self.assertIn("evaluation", refusal["error"])
        report = {
            "positive_tasks": [f"Investigate {trigger}"],
            "negative_tasks": [f"{trigger} another project", "CSS colors"],
            "behavior": verification("fixture:cli-behavior"),
        }
        evaluated = self.cli(
            "learning", "eval", "--id", candidate_id, "--input", self.input(report)
        )
        self.assertTrue(evaluated["passed"])
        self.assertFalse(evaluated["behavior"]["checks_executed_by_erol"])
        skill = self.cli("learning", "activate", "--id", candidate_id)
        self.assertEqual(skill["scope"], "project")
        catalog = self.cli("skills", "list")
        self.assertFalse(catalog["bodies_loaded"])
        self.assertIn(skill["name"], [entry["name"] for entry in catalog["skills"]])
        for index in range(3):
            task_id = f"cli-use-{index}"
            started = self.cli("plan", "--task", trigger, "--task-id", task_id)
            self.assertFalse(started["plan"]["execution_supported"])
            self.assertIn(skill["name"], [entry["name"] for entry in started["selected_skills"]])
            completed = self.cli(
                "skill",
                "usage",
                "--task-id",
                task_id,
                "--input",
                self.input(verification(f"fixture:cli-use-{index}")),
            )
            self.assertTrue(completed["uses"][0]["successful"])
        metrics = self.cli("skill", "metrics", "--name", skill["name"])
        self.assertEqual(metrics["successful_tasks"], 3)
        self.cli(
            "skill",
            "usage",
            "--task-id",
            "cli-use-0",
            "--input",
            self.input(verification()),
            expected_exit=2,
        )
        promotion = self.cli("learning", "promotion", "--name", skill["name"])
        self.assertEqual(promotion["status"], "promotion_candidate")
        cross_project = {
            "project_id": "independent-cli-fixture-project",
            "verification": verification("fixture:cross-project"),
        }
        self.cli(
            "learning",
            "promote",
            "--id",
            promotion["id"],
            "--input",
            self.input(cross_project),
            expected_exit=2,
        )
        reviewed = self.cli(
            "learning",
            "promote",
            "--id",
            promotion["id"],
            "--approve",
            "--input",
            self.input(cross_project),
        )
        self.assertEqual(reviewed["status"], "approved_for_generalization")
        self.assertFalse(reviewed["global_registry_modified"])
        self.assertFalse((self.home / "skills").exists())
        status = self.cli("status")
        self.assertEqual(status["memory"]["incidents"], 3)
        self.assertEqual(status["memory"]["uses"], 3)
        self.assertEqual(status["memory"]["skills"], 1)

    def test_cli_rejects_secret_input_and_does_not_echo_payload(self):
        secret = "synthetic-access-value"
        value = incident(1, solution=f"token={secret}")
        error = self.cli("incident", "record", "--input", self.input(value), expected_exit=2)
        self.assertNotIn(secret, json.dumps(error))
        self.assertEqual(self.cli("status")["memory"]["incidents"], 0)

    def test_cli_rejects_unknown_input_and_bounded_evidence_contract(self):
        self.cli("incident", "record", "--input", self.input(["not an object"]), expected_exit=2)
        failed = verification()
        failed["findings"] = [{"severity": "critical", "resolved": False}]
        self.cli(
            "incident",
            "record",
            "--input",
            self.input(incident(1, verification=failed)),
            expected_exit=2,
        )
        self.assertEqual(self.cli("status")["memory"]["candidates"], 0)


if __name__ == "__main__":
    unittest.main()
