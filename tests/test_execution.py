"""Real child-process fixtures for the execution contract (not live model evidence)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path, PurePosixPath
from unittest.mock import Mock, patch

from test_learning import incident, verification

from erol.common import ErolError, canonical
from erol.config import Config
from erol.execution import Limits, Runner, load_checks, snapshot
from erol.harness import CliHarness, EventDecoder
from erol.identity import detect_project
from erol.learning import LearningEngine
from erol.registry import Registry
from erol.runprocess import observe, stop_process
from erol.runstore import RunStore, pid_alive
from erol.security import scan_secrets
from erol.store import Store

FAKE = r"""
import json, pathlib, sys, time
from datetime import date
args = sys.argv[1:]
name, scenario = args[:2]
args = args[2:]
if '--version' in args:
    print('fixture-cli 1.2.3'); sys.exit(0)
if '--help' in args:
    print('--json --output-schema --sandbox --output-format --json-schema --resume '
          '--tools --allowedTools --permission-mode dontAsk --strict-mcp-config --search')
    sys.exit(0)
if args[:2] == ['login', 'status']:
    sys.exit(0)
if args[:2] == ['auth', 'status']:
    print(json.dumps({'loggedIn': scenario != 'no-login'})); sys.exit(0)
prompt = sys.stdin.read()
if name == 'codex':
    schema = json.loads(pathlib.Path(args[args.index('--output-schema') + 1]).read_text())
else:
    schema = json.loads(args[args.index('--json-schema') + 1])
review = 'findings' in schema['properties']
session = ('22222222-2222-4222-8222-222222222222' if review
           else '11111111-1111-4111-8111-111111111111')
def event(value):
    print(json.dumps(value), flush=True)
if name == 'codex':
    event({'type': 'thread.started', 'thread_id': session})
else:
    event({'type': 'system', 'subtype': 'init', 'session_id': session})
if scenario == 'malformed':
    print('bad stream password=synthetic-private-value', flush=True); sys.exit(0)
if scenario == 'truncated':
    sys.exit(0)
if scenario == 'timeout' and not review and not ('resume' in args or '--resume' in args):
    time.sleep(20)
if not review:
    if scenario != 'no-fix':
        path = pathlib.Path('calculator.py')
        path.write_text(path.read_text().replace('a - b', 'a + b'))
    if scenario == 'new-file':
        pathlib.Path('notes.txt').write_text('Reviewed new file\n')
    if scenario.startswith('research'):
        directory = pathlib.Path('research'); directory.mkdir(exist_ok=True)
        ledger = {'schema_version': 1, 'question': 'Compare arithmetic options',
                  'scope': 'Synthetic technical research fixture',
                  'sources': [{'id': 'S1', 'url': 'https://example.test/arithmetic',
                               'title': 'Arithmetic fixture', 'publisher': 'Fixture',
                               'accessed_on': date.today().isoformat(), 'published_on': None,
                               'kind': 'primary'}],
                  'claims': [{'id': 'C1', 'statement': 'Addition returns a sum',
                              'source_ids': ['S1'], 'kind': 'fact', 'confidence': 'high'}],
                  'conflicts': [], 'limitations': ['Synthetic fixture, no live retrieval']}
        if scenario == 'research-bad-ledger':
            ledger['claims'][0]['source_ids'] = ['unknown']
        (directory / 'sources.json').write_text(json.dumps(ledger))
        (directory / 'report.md').write_text('Addition returns a sum. '
                                          '[S1](https://example.test/arithmetic)\n')
    result = {'summary': 'Fixed arithmetic', 'strategy': 'Correct operator',
              'status': 'implemented'}
    if scenario == 'secret':
        result['summary'] = 'password=synthetic-private-value'
else:
    findings = []
    if scenario == 'review-fail':
        findings = [{'severity': 'high', 'resolved': False, 'message': 'Acceptance gap'}]
    if scenario == 'review-edits':
        pathlib.Path('calculator.py').write_text('def add(a,b): return 0\n')
    result = {'summary': 'Independent diff review', 'findings': findings}
    if 'source_checks' in schema['properties']:
        result['source_checks'] = [{'source_id': 'S1',
                                   'status': 'unavailable' if scenario == 'research-unavailable'
                                             else 'verified',
                                   'reason': 'Synthetic source assertion fixture'}]
if name == 'codex':
    event({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps(result)}})
    event({'type': 'turn.completed', 'usage': {'input_tokens': 100, 'output_tokens': 20}})
else:
    event({'type': 'result', 'subtype': 'success', 'is_error': False, 'session_id': session,
           'structured_output': result, 'usage': {'input_tokens': 100, 'output_tokens': 20},
           'total_cost_usd': 0.01})
"""


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="erol-execution-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "proje Türkçe spaces"
        self.repo.mkdir()
        (self.repo / "calculator.py").write_text("def add(a, b): return a - b\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        for args in (
            ("init",),
            ("config", "user.name", "Fixture"),
            ("config", "user.email", "fixture@example.test"),
            ("add", "."),
            ("commit", "-m", "fixture"),
        ):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)
        self.fake = self.base / "fake harness.py"
        self.fake.write_text(FAKE, encoding="utf-8")
        self.manifest = self.base / "checks.json"
        self.checks = {
            "schema_version": 1,
            "checks": [
                {
                    "name": "arithmetic",
                    "kind": "acceptance",
                    "argv": [
                        sys.executable,
                        "-B",
                        "-c",
                        "from calculator import add; assert add(2,3)==5",
                    ],
                    "timeout_seconds": 5,
                }
            ],
        }
        self.write_checks()
        self.project = detect_project(self.repo)
        self.store = Store(self.base / "external home", self.project)
        self.addCleanup(self.store.close)
        self.runs = RunStore(self.store.directory, self.project.id)
        self.addCleanup(self.runs.close)
        self.engine = LearningEngine(self.store, Config(), Registry(project_store=self.store))
        self.scenario = "success"
        self.calls: list[tuple] = []
        fixture = self

        class Harness(CliHarness):
            def __init__(self, name, cwd):
                self.name = name
                self.cwd = cwd
                self.prefix = [sys.executable, str(fixture.fake), name, fixture.scenario]

            def execute(self, role, prompt, artifact_directory, **kwargs):
                fixture.calls.append((self.name, role, kwargs["session_id"], prompt))
                return super().execute(role, prompt, artifact_directory, **kwargs)

        self.factory = Harness
        self.runner = Runner(self.store, self.engine, self.runs, harness_factory=Harness)
        self.runner.source_fetcher = lambda ledger, **kwargs: [
            {
                "source_id": source["id"],
                "url": source["url"],
                "status": "accessed",
                "evidence_type": "synthetic_source_access_fixture",
            }
            for source in ledger["sources"]
        ]

    def write_checks(self):
        self.manifest.write_text(json.dumps(self.checks), encoding="utf-8")

    def start(self, harness="codex", **kwargs):
        return self.runner.start("Repair arithmetic", harness, self.manifest, **kwargs)

    def test_run_path_metadata_does_not_join_components_into_false_secret(self):
        path = "/private/var/folders/q7/z8r9wm4xc6sgd2fkv5qbh3p00000gn/T/runs/"
        path += "run-0cb91d3213644e348b7912889c9536e0/worktree"
        self.assertIn("high-entropy-value", scan_secrets(path))
        record = {
            "id": "run-path-fixture",
            "task_id": "task-path-fixture",
            "project_id": self.project.id,
            "task": "Repair arithmetic",
            **dict.fromkeys(
                ("project_root", "worktree", "directory", "checks_path", "patch", "delta_patch"),
                path,
            ),
        }
        with patch("erol.runstore.Path", PurePosixPath):
            self.runs.create(record)
            self.runs.save(record)
        self.assertEqual(path, self.runs.get(record["id"])["worktree"])

    def test_run_path_exception_keeps_credentials_and_arbitrary_text_rejected(self):
        record = {
            "id": "run-path-guard",
            "task_id": "task-path-guard",
            "project_id": self.project.id,
        }
        unsafe_path = "/home/aB3dE7fG9hJ2kL4mN6pQ8rS0tU5vW1xY/worktree"
        joined = "/home/runner/work/_temp/run-0cb91d3213644e348b7912889c9536e0/worktree"
        with patch("erol.runstore.Path", PurePosixPath):
            for fields in (
                {"worktree": unsafe_path},
                {"worktree": "/home/password=private-fixture/src"},
                {"worktree": "relative/project"},
                {"worktree": 123},
                {"task": joined},
                {"context": {"worktree": joined}},
            ):
                with self.subTest(fields=fields), self.assertRaises(ErolError):
                    self.runs.create({**record, **fields})

    def test_both_harnesses_observe_repair_review_and_usage(self):
        for harness in ("codex", "claude"):
            with self.subTest(harness=harness):
                result = self.start(harness, task_id="task-" + harness)
                self.assertEqual("completed", result["status"], result.get("reason"))
                self.assertFalse(result["baseline"][0]["passed"])
                self.assertTrue(result["checks"][0]["passed"])
                self.assertEqual(result["tested_digest"], result["reviewed_digest"])
                self.assertEqual("runner_observed", result["evidence_type"])
                self.assertNotEqual(result["worker_session"], result["reviewer_session"])
                task = self.store.get("tasks", result["task_id"])
                self.assertTrue(task["verification"]["checks_executed_by_erol"])
                self.assertEqual([], result["selected_skills"])
                self.assertEqual([], self.store.list("uses"))  # builtins get no learned usage
                self.assertIn("a + b", Path(result["patch"]).read_text())
                self.assertIn("a - b", (self.repo / "calculator.py").read_text())
                self.assertEqual(self.project.id, result["project_id"])
                self.assertFalse((self.repo / "runs.db").exists())

    def test_cross_harness_review(self):
        result = self.start(review_harness="claude")
        self.assertEqual("completed", result["status"])
        self.assertEqual(["codex", "claude"], [item[0] for item in self.calls])

    def test_distinct_homes_cannot_launch_duplicate_project_workers(self):
        self.scenario = "truncated"
        pending = self.start()
        with Store(self.base / "another external home", self.project) as store:
            with RunStore(store.directory, self.project.id) as runs:
                engine = LearningEngine(store, Config(), Registry(project_store=store))
                other = Runner(store, engine, runs, harness_factory=self.factory)
                with self.assertRaisesRegex(ErolError, "Another EROL home"):
                    other.start("Repair arithmetic", "codex", self.manifest)
                self.assertEqual([], store.list("tasks"))
                self.runner.cancel(pending["id"])
                self.scenario = "success"
                with self.runner._lease():
                    with self.assertRaisesRegex(ErolError, "lease"):
                        other.start("Repair arithmetic", "codex", self.manifest)
                result = other.start("Repair arithmetic", "codex", self.manifest)
                self.assertEqual("completed", result["status"], result.get("reason"))

    def test_research_mode_gates_artifacts_and_independent_source_review(self):
        self.scenario = "research-success"
        result = self.start(mode="research", review_harness="claude")
        self.assertEqual("completed", result["status"], result.get("reason"))
        self.assertEqual("research", result["mode"])
        self.assertEqual("static", result["checks"][-1]["kind"])
        self.assertEqual("model_review_assertion", result["review"]["source_evidence_type"])
        self.assertIn("vendor", self.calls[0][3].lower())
        self.assertIn("Open every cited source", self.calls[-1][3])
        self.assertTrue((Path(result["worktree"]) / "research/report.md").is_file())

    def test_research_unavailable_sources_and_invalid_claims_block_completion(self):
        for scenario in ("research-unavailable", "research-bad-ledger"):
            self.scenario = scenario
            result = self.start(mode="research")
            self.assertEqual("needs_attention", result["status"])
            self.assertEqual(3, len(result["attempts"]))
            self.assertEqual([], self.store.list("uses"))
            self.runner.cancel(result["id"])

    def test_failed_checks_use_bounded_retries_and_replan(self):
        self.scenario = "no-fix"
        result = self.start()
        self.assertEqual("needs_attention", result["status"])
        self.assertEqual(3, len(result["attempts"]))
        self.assertTrue(result["replan_required"])
        self.assertIn('"replan_required":true', self.calls[-1][3])
        self.assertEqual("started", self.store.get("tasks", result["task_id"])["status"])
        self.assertEqual([], self.store.list("uses"))

    def test_blocking_review_never_credits_completion(self):
        self.scenario = "review-fail"
        result = self.start()
        self.assertEqual("needs_attention", result["status"])
        self.assertEqual(3, len(result["attempts"]))
        self.assertTrue(result["checks"][0]["passed"])
        self.assertIsNone(result["reviewed_digest"])

    def test_review_mutation_invalidates_evidence(self):
        self.scenario = "review-edits"
        result = self.start()
        self.assertEqual("needs_attention", result["status"])
        self.assertIsNone(result["tested_digest"])
        self.assertIsNone(result["review"])

    def test_malformed_truncated_and_secret_streams_are_not_persisted(self):
        for scenario in ("malformed", "truncated", "secret"):
            with self.subTest(scenario=scenario):
                self.scenario = scenario
                result = self.start()
                self.assertEqual("needs_attention", result["status"])
                row = self.runs.db.execute(
                    "SELECT payload FROM runs WHERE id=?", (result["id"],)
                ).fetchone()
                self.assertNotIn("synthetic-private-value", row[0])
                self.runner.cancel(result["id"])

    def test_timeout_resumes_acknowledged_session_without_new_attempt(self):
        self.scenario = "timeout"
        self.runner.limits = Limits(session_seconds=2)
        result = self.start()
        self.assertEqual("needs_attention", result["status"])
        self.assertIsNotNone(result["worker_session"])
        self.assertFalse(pid_alive(result["child_pid"]))
        self.runner.limits = Limits()
        resumed = self.runner.resume(result["id"])
        self.assertEqual("completed", resumed["status"], resumed.get("reason"))
        self.assertEqual(1, len(resumed["attempts"]))
        self.assertEqual(result["worker_session"], self.calls[1][2])

    def test_resume_rejects_changed_manifest_and_living_child(self):
        self.scenario = "truncated"
        result = self.start()
        record = self.runs.get(result["id"])
        record["child_pid"] = os.getpid()
        self.runs.save(record)
        with self.assertRaisesRegex(ErolError, "second worker"):
            self.runner.resume(result["id"])
        record["child_pid"] = None
        self.runs.save(record)
        self.checks["checks"][0]["argv"][-1] = "print('altered')"
        self.write_checks()
        resumed = self.runner.resume(result["id"])
        self.assertEqual("needs_attention", resumed["status"])
        self.assertEqual([], resumed["checks"])

    def test_changed_source_requires_new_checks_and_review_on_resume(self):
        self.scenario = "review-fail"
        result = self.start()
        # Simulate interruption after checks, before launching independent review.
        result.update({"phase": "review", "review_started": False, "reviewer_session": None})
        self.runs.save(result)
        worktree = Path(result["worktree"])
        (worktree / "calculator.py").write_text("def add(a,b): return a + b + 1\n")
        self.scenario = "success"
        self.calls.clear()
        resumed = self.runner.resume(result["id"])
        self.assertEqual("needs_attention", resumed["status"])
        self.assertFalse(resumed["checks"][0]["passed"])
        self.assertEqual([], self.calls)  # exhausted attempts cannot silently restart

    def test_project_lease_unfinished_run_dirty_source_and_replayed_ids(self):
        with self.runs.lease(), self.assertRaises(ErolError):
            with self.runs.lease():
                self.fail("second owner acquired lease")
        (self.repo / "new.txt").write_text("dirty")
        with self.assertRaisesRegex(ErolError, "clean Git"):
            self.start()
        (self.repo / "new.txt").unlink()
        completed = self.start(task_id="unique-task")
        self.assertEqual("completed", completed["status"], completed.get("reason"))
        with self.assertRaisesRegex(ErolError, "Task ID already used"):
            self.start(task_id="unique-task")
        with self.assertRaisesRegex(ErolError, "immutable"):
            self.runner.resume(completed["id"])
        self.scenario = "truncated"
        pending = self.start()
        with self.assertRaisesRegex(ErolError, "unfinished"):
            self.start()
        self.assertEqual("cancelled", self.runner.cancel(pending["id"])["status"])

    def test_new_file_patch_can_be_applied_to_original_base(self):
        self.scenario = "new-file"
        result = self.start()
        self.assertEqual("completed", result["status"], result.get("reason"))
        subprocess.run(
            ["git", "-C", str(self.repo), "apply", "--check", result["patch"]],
            capture_output=True,
            check=True,
        )
        self.assertIn("notes.txt", Path(result["patch"]).read_text())

    def test_missing_login_and_nested_execution_have_no_task_side_effects(self):
        self.scenario = "no-login"
        with self.assertRaisesRegex(ErolError, "authentication"):
            self.start("claude")
        with patch.dict(os.environ, {"EROL_RUN_ACTIVE": "1"}), self.assertRaises(ErolError):
            self.start()
        self.assertEqual([], self.runs.list())
        self.assertEqual([], self.store.list("tasks"))

    def test_check_mutation_and_time_budget_never_complete(self):
        self.checks["checks"][0]["argv"] = [
            sys.executable,
            "-c",
            "from pathlib import Path; Path('calculator.py').write_text('changed')",
        ]
        self.write_checks()
        result = self.start()
        self.assertEqual("needs_attention", result["status"])
        self.assertIn("changed source", result["reason"])
        self.runner.cancel(result["id"])
        self.runner.limits = Limits(task_seconds=0)
        result = self.start()
        self.assertEqual("needs_attention", result["status"])
        self.assertEqual([], result["attempts"])

    def test_manifest_contract_rejects_static_only_duplicates_and_secret(self):
        for mutate in (
            lambda data: data["checks"][0].update(kind="static"),
            lambda data: data["checks"].append(data["checks"][0].copy()),
            lambda data: data["checks"][0].update(timeout_seconds=True),
            lambda data: data["checks"][0]["argv"].append("password=synthetic-private-value"),
        ):
            value = json.loads(json.dumps(self.checks))
            mutate(value)
            self.manifest.write_text(json.dumps(value))
            with self.assertRaises(ErolError):
                load_checks(self.manifest)

    def test_cancel_request_interrupts_owned_process(self):
        with self.assertRaises(ErolError):
            self.runs.get("missing")
        self.scenario = "truncated"
        result = self.start()
        self.runs.request_cancel(result["id"])
        outcome = observe(
            [sys.executable, "-c", "import time; time.sleep(20)"],
            self.repo,
            timeout=5,
            cancelled=lambda: self.runs.cancelled(result["id"]),
        )
        self.assertEqual("cancelled", outcome["reason"])
        self.assertLess(outcome["elapsed_seconds"], 5)

    def test_execution_schema_project_binding_and_unknown_session(self):
        self.runs.db.execute("UPDATE meta SET value='2' WHERE key='schema_version'")
        with self.assertRaisesRegex(ErolError, "schema"):
            RunStore(self.store.directory, self.project.id)
        self.runs.db.execute("UPDATE meta SET value='1' WHERE key='schema_version'")
        with self.assertRaisesRegex(ErolError, "another project"):
            RunStore(self.store.directory, "different-project")
        self.scenario = "truncated"
        result = self.start()
        result["worker_session"] = None
        result["attempts"][-1]["worker"] = None
        self.runs.save(result)
        self.assertIn("no acknowledged", self.runner.resume(result["id"])["reason"])

    def test_snapshot_covers_untracked_and_staged_changes(self):
        base_commit = (
            subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD"])
            .decode()
            .strip()
        )
        before, _ = snapshot(self.repo, base_commit)
        (self.repo / "calculator.py").write_text("def add(a,b): return a + b\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "calculator.py"], check=True)
        staged, _ = snapshot(self.repo, base_commit)
        self.assertNotEqual(before, staged)
        (self.repo / "notes.txt").write_text("note")
        after, _ = snapshot(self.repo, base_commit)
        self.assertNotEqual(staged, after)

    def active_skill(self):
        for index in range(1, 4):
            candidate = self.engine.record_incident(incident(index))["candidate"]
        trigger = candidate["skill"]["triggers"][0]
        self.engine.evaluate(
            candidate["id"],
            {
                "positive_tasks": [trigger],
                "negative_tasks": ["CSS layout"],
                "behavior": verification("fixture:runner-skill"),
            },
        )
        return self.engine.activate(candidate["id"])

    def test_learned_revision_usage_and_context_omission(self):
        skill = self.active_skill()
        task = "Repair arithmetic while investigating " + skill["triggers"][0]
        result = self.runner.start(task, "codex", self.manifest)
        self.assertEqual("completed", result["status"], result.get("reason"))
        uses = self.store.list("uses")
        self.assertEqual(1, len(uses))
        self.assertEqual(skill["digest"], uses[0]["digest"])
        self.assertEqual(result["reviewed_digest"], uses[0]["verification"]["source_digest"])
        self.engine.config = replace(self.engine.config, context_tokens=200)
        omitted = self.runner.start(task, "codex", self.manifest)
        self.assertEqual("completed", omitted["status"], omitted.get("reason"))
        self.assertEqual([], omitted["selected_skills"])
        self.assertEqual(1, len(self.store.list("uses")))

    def test_finalization_crash_cannot_double_credit_usage(self):
        skill = self.active_skill()
        original_save = self.runs.save
        crashed = False

        def save(record):
            nonlocal crashed
            if record["status"] == "completed" and not crashed:
                crashed = True
                raise OSError("fixture checkpoint failure")
            original_save(record)

        with patch.object(self.runs, "save", side_effect=save):
            result = self.runner.start(skill["triggers"][0], "codex", self.manifest)
        self.assertEqual("needs_attention", result["status"])
        self.assertEqual(1, len(self.store.list("uses")))
        self.calls.clear()
        resumed = self.runner.resume(result["id"])
        self.assertEqual("completed", resumed["status"], resumed.get("reason"))
        self.assertEqual(1, len(self.store.list("uses")))
        self.assertEqual([], self.calls)

    def test_revision_changed_during_task_cannot_receive_success_credit(self):
        skill = self.active_skill()
        execute = self.factory.execute
        fixture = self

        def change_revision(harness, role, prompt, directory, **kwargs):
            result = execute(harness, role, prompt, directory, **kwargs)
            if role == "reviewer":
                record = fixture.store.get("skills", skill["name"])
                record["status"] = "disabled"
                fixture.store.put("skills", record, replace=True)
            return result

        with patch.object(self.factory, "execute", change_revision):
            result = self.runner.start(skill["triggers"][0], "codex", self.manifest)
        self.assertEqual("needs_attention", result["status"])
        self.assertEqual([], self.store.list("uses"))

    def test_process_output_limit_and_descendant_cleanup(self):
        outcome = observe(
            [sys.executable, "-c", "print('x' * (1024*1024+1))"], self.repo, timeout=10
        )
        self.assertEqual("output_limit", outcome["reason"])
        child_file = self.base / "descendant.pid"
        program = (
            "import subprocess,sys,pathlib; "
            "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
            f"pathlib.Path({str(child_file)!r}).write_text(str(p.pid))"
        )
        outcome = observe([sys.executable, "-c", program], self.repo, timeout=2)
        self.assertEqual("timeout", outcome["reason"])
        child_pid = int(child_file.read_text())
        if os.name == "nt":
            # Job close dispatches termination asynchronously. Require observed
            # death within a bounded kernel completion window, not same-tick loss.
            deadline = time.monotonic() + 5
            while pid_alive(child_pid) and time.monotonic() < deadline:
                time.sleep(0.05)
        if sys.platform.startswith("linux") and pid_alive(child_pid):
            # Linux init may retain an orphan's zombie entry after SIGKILL.
            # The duplicate-worker guard conservatively treats an existing PID
            # as alive; cleanup evidence requires that no descendant can execute.
            try:
                stat = Path(f"/proc/{child_pid}/stat").read_text()
            except FileNotFoundError:
                pass  # already reaped
            else:
                self.assertEqual("Z", stat.rsplit(")", 1)[1].split()[0])
        else:
            if sys.platform == "darwin" and pid_alive(child_pid):
                state = subprocess.run(
                    ["/bin/ps", "-p", str(child_pid), "-o", "stat="],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                self.assertIn(state.returncode, (0, 1))
                self.assertTrue(not state.stdout.strip() or state.stdout.strip().startswith("Z"))
            else:
                self.assertFalse(pid_alive(child_pid))

    def test_public_cli_reads_and_cancels_external_run_records(self):
        completed = self.start()
        prefix = [
            sys.executable,
            "-m",
            "erol",
            "--project",
            str(self.repo),
            "--home",
            str(self.store.home),
            "runs",
        ]
        shown = subprocess.run(
            [*prefix, "show", "--id", completed["id"]],
            capture_output=True,
            encoding="utf-8",
            check=True,
            timeout=20,
        )
        self.assertEqual(completed["reviewed_digest"], json.loads(shown.stdout)["reviewed_digest"])
        listed = subprocess.run([*prefix, "list"], capture_output=True, check=True, timeout=20)
        self.assertEqual(completed["id"], json.loads(listed.stdout)["runs"][0]["id"])
        self.scenario = "truncated"
        pending = self.start()
        cancelled = subprocess.run(
            [*prefix, "cancel", "--id", pending["id"]], capture_output=True, check=True, timeout=20
        )
        self.assertEqual("cancelled", json.loads(cancelled.stdout)["status"])
        refused = subprocess.run(
            [*prefix, "resume", "--id", completed["id"]], capture_output=True, timeout=20
        )
        self.assertEqual(2, refused.returncode)
        self.assertEqual(
            "1",
            self.store.db.execute(
                "SELECT value FROM metadata WHERE key='schema_version'"
            ).fetchone()[0],
        )

    def test_check_diagnostics_redact_credentials(self):
        fixture = self.base / "diagnostic check.py"
        fixture.write_text("print('password=synthetic-private-value')", encoding="utf-8")
        self.checks["checks"][0]["argv"] = [
            sys.executable,
            str(fixture),
        ]
        self.write_checks()
        result = self.start()
        self.assertEqual("completed", result["status"], result.get("reason"))
        self.assertIn("redacted", result["checks"][0]["diagnostic_excerpt"])
        self.assertNotIn("synthetic-private-value", canonical(self.runs.get(result["id"])))


class AdapterProtocolTests(unittest.TestCase):
    def test_capabilities_and_permission_argv(self):
        with tempfile.TemporaryDirectory() as temporary:
            schema = Path(temporary) / "schema.json"
            schema.write_text("{}")
            with patch("erol.harness.command_prefix", return_value=["fixture-cli"]):
                for name in ("codex", "claude"):
                    harness = CliHarness(name, Path(temporary))
                    worker = harness.argv("implementer", schema, None)
                    reviewer = harness.argv("reviewer", schema, None)
                    self.assertNotIn("--dangerously-skip-permissions", worker)
                    self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", worker)
                    if name == "codex":
                        self.assertIn("workspace-write", worker)
                        self.assertIn("read-only", reviewer)
                    else:
                        self.assertIn("Read,Glob,Grep", reviewer)
                        self.assertNotIn("Edit", reviewer)
                    with patch(
                        "erol.harness.probe", side_effect=["version 1.2.3", "no capabilities"]
                    ):
                        with self.assertRaises((ErolError, StopIteration)):
                            harness.preflight()

    def test_event_schema_session_and_usage_validation(self):
        decoder = EventDecoder("codex", "implementer", "one-session")
        with self.assertRaises(ErolError):
            decoder.line(canonical({"type": "thread.started", "thread_id": "another-session"}))
        with self.assertRaises(ErolError):
            decoder.line("[]")
        decoder.line(canonical({"type": "turn.completed", "usage": {"input_tokens": True}}))
        self.assertEqual({}, decoder.usage)

    def test_run_evidence_reference_is_not_mistaken_for_encoded_credentials(self):
        reference = "run:run-1234567890abcdef1234567890abcdef#check:arithmetic"
        self.assertEqual([], scan_secrets(reference))

    def test_research_tool_policy_and_native_authentication_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            schema = Path(temporary) / "schema.json"
            schema.write_text("{}")
            with patch("erol.harness.command_prefix", return_value=["fixture-cli"]):
                for name in ("codex", "claude"):
                    harness = CliHarness(name, Path(temporary)).configure("research")
                    args = harness.argv("reviewer", schema, "native-session")
                    if name == "codex":
                        self.assertIn("--search", args)
                        self.assertIn("read-only", args)
                        with patch(
                            "erol.harness.probe",
                            side_effect=[
                                "version 1.2.3",
                                "--json --output-schema --sandbox",
                                "--json --output-schema",
                                "",
                                "no search",
                            ],
                        ):
                            with self.assertRaisesRegex(ErolError, "web-search"):
                                harness.preflight()
                    else:
                        self.assertIn("Read,Glob,Grep,WebSearch,WebFetch", args)
                        self.assertNotIn("Write", args)
        decoder = EventDecoder("claude", "implementer")
        decoder.line(
            canonical(
                {
                    "type": "result",
                    "subtype": "success",
                    "is_error": True,
                    "result": "OAuth access token has expired. Re-authenticate to continue.",
                }
            )
        )
        self.assertTrue(decoder.failed)
        self.assertIn("OAuth access token has expired", decoder.diagnostics[-1])


class ProcessCleanupTests(unittest.TestCase):
    def test_darwin_cleanup_permission_exception_requires_observed_terminal_group(self):
        process = Mock(pid=1234)
        process.poll.return_value = 0
        for output, returncode, allowed in (
            ("1234 Z\n5678 S\n", 0, True),
            ("5678 S\n", 0, True),
            ("1234 S\n", 0, False),
            ("1234 Z\n1234 R\n", 0, False),
            ("unknown state\n", 0, False),
            ("", 1, False),
        ):
            with (
                self.subTest(output=output, returncode=returncode),
                patch("erol.runprocess.os.name", "posix"),
                patch("erol.runprocess.sys.platform", "darwin"),
                patch("erol.runprocess.signal.SIGKILL", 9, create=True),
                patch("erol.runprocess.os.killpg", create=True, side_effect=PermissionError),
                patch(
                    "erol.runprocess.subprocess.run",
                    return_value=Mock(stdout=output, returncode=returncode),
                ) as probe,
            ):
                if allowed:
                    stop_process(process)
                else:
                    with self.assertRaises(PermissionError):
                        stop_process(process)
                self.assertEqual(["/bin/ps", "-axo", "pgid=,stat="], probe.call_args.args[0])
        process.poll.return_value = None
        with (
            patch("erol.runprocess.os.name", "posix"),
            patch("erol.runprocess.sys.platform", "darwin"),
            patch("erol.runprocess.signal.SIGKILL", 9, create=True),
            patch("erol.runprocess.os.killpg", create=True, side_effect=PermissionError),
            patch("erol.runprocess.subprocess.run") as probe,
            self.assertRaises(PermissionError),
        ):
            stop_process(process)
        probe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
