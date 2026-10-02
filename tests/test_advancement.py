"""Behavioral queue, parallel review, indexed retrieval, receipt and panel boundaries."""

from __future__ import annotations

import hashlib
import http.client
import json
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import test_execution

from erol.benchmark import behavioral_benchmark, load_suite
from erol.common import ErolError, canonical
from erol.execution import git
from erol.panel import make_server, panel_state
from erol.retrieval import MemoryIndex
from erol.runstore import RunStore, pid_alive
from erol.sources import fetch_source, fetch_sources, public_target
from erol.work import Queue, WorkStore, discover, load_policy


class AdvancementTests(unittest.TestCase):
    setUp = test_execution.ExecutionTests.setUp
    write_checks = test_execution.ExecutionTests.write_checks
    start = test_execution.ExecutionTests.start

    def policy(self, **limits):
        data = {
            "schema_version": 1,
            "project_id": self.project.id,
            "limits": {
                "max_tasks": 3,
                "max_total_seconds": 120,
                "task_seconds": 60,
                "session_seconds": 20,
                "check_seconds": 5,
                "reviewers": 1,
                **limits,
            },
            "rules": [
                {
                    "id": "repair",
                    "kinds": ["check", "todo", "issue"],
                    "paths": ["*"],
                    "harness": "codex",
                    "review_harness": "claude",
                    "mode": "development",
                    "checks": str(self.manifest),
                }
            ],
        }
        path = self.base / "policy.json"
        path.write_text(canonical(data), encoding="utf-8")
        return load_policy(path, self.project.id)

    def work(self):
        work = WorkStore(self.store.directory, self.project.id)
        self.addCleanup(work.close)
        return work

    def parallel_fixture(self):
        # Stable native IDs differ per specialist's artifact directory, including resume.
        body = self.fake.read_text(encoding="utf-8")
        body = body.replace(
            "import json, pathlib, sys, time", "import json, pathlib, sys, time, uuid"
        )
        body = body.replace(
            "def event(value):",
            "if review and 'Review focus:' in prompt:\n"
            "    session = str(uuid.uuid5(uuid.NAMESPACE_URL, "
            "prompt.split('Review focus:')[-1]))\ndef event(value):",
        )
        self.fake.write_text(body, encoding="utf-8")

    def test_parallel_readonly_reviews_have_distinct_sessions_and_blocking_findings(self):
        self.parallel_fixture()
        outcome = self.start(reviewers=3)
        self.assertEqual("completed", outcome["status"])
        sessions = [peer["session_id"] for peer in outcome["peer_reviews"]]
        self.assertEqual(3, len(set(sessions)))
        self.assertNotIn(outcome["worker_session"], sessions)
        self.assertEqual(outcome["tested_digest"], outcome["reviewed_digest"])
        self.scenario = "review-fail"
        failed = self.start(reviewers=2)
        self.assertEqual("needs_attention", failed["status"])
        self.assertEqual(3, len(failed["attempts"]))

    def test_parallel_reused_native_id_and_unknown_peer_prevent_completion(self):
        outcome = self.start(reviewers=2)
        self.assertEqual("needs_attention", outcome["status"])
        self.assertIn("distinct", outcome["reason"])
        outcome["peer_reviews"][0].update({"started": True, "session_id": None})
        self.runs.save(outcome)
        with self.assertRaisesRegex(ErolError, "unacknowledged"):
            self.runner.resume(outcome["id"])

    def test_parallel_review_callbacks_overlap(self):
        self.parallel_fixture()
        barrier = threading.Barrier(2, timeout=10)
        original = self.factory.execute

        def execute(harness, role, *args, **kwargs):
            if role == "reviewer":
                barrier.wait()
            return original(harness, role, *args, **kwargs)

        with patch.object(self.factory, "execute", execute):
            self.assertEqual("completed", self.start(reviewers=2)["status"])

    def test_parallel_cancellation_stops_both_owned_native_processes(self):
        self.parallel_fixture()
        body = self.fake.read_text(encoding="utf-8")
        body = body.replace(
            "if not review:\n",
            "if review and scenario == 'peer-timeout': time.sleep(20)\nif not review:\n",
        )
        self.fake.write_text(body, encoding="utf-8")
        self.scenario = "peer-timeout"
        observed = []
        stop = threading.Event()

        def cancel():
            with RunStore(self.store.directory, self.project.id) as runs:
                until = time.monotonic() + 15
                while not stop.is_set() and time.monotonic() < until:
                    records = runs.list()
                    if records:
                        peers = records[0].get("peer_reviews", [])
                        if len(peers) == 2 and all(
                            peer.get("session_id") and peer.get("child_pid") for peer in peers
                        ):
                            observed.extend(peer["child_pid"] for peer in peers)
                            runs.request_cancel(records[0]["id"])
                            return
                    stop.wait(0.02)

        thread = threading.Thread(target=cancel, daemon=True)
        thread.start()
        try:
            result = self.start(reviewers=2)
        finally:
            stop.set()
            thread.join(timeout=20)
        self.assertEqual("cancelled", result["status"])
        self.assertEqual(2, len(observed))
        self.assertTrue(all(not pid_alive(pid) for pid in observed))

    def test_parallel_completed_peers_resume_without_relaunch(self):
        self.parallel_fixture()
        original = self.runner._parallel_review

        def interrupt(record, patch):
            original(record, patch)
            raise KeyboardInterrupt

        with patch.object(self.runner, "_parallel_review", interrupt):
            first = self.start(reviewers=2)
        before = len([call for call in self.calls if call[1] == "reviewer"])
        resumed = self.runner.resume(first["id"])
        self.assertEqual("completed", resumed["status"])
        self.assertEqual(before, len([call for call in self.calls if call[1] == "reviewer"]))

    def test_observed_discovery_queue_dedup_and_unchanged_original(self):
        work = self.work()
        scan = discover(self.repo, work, checks_path=self.manifest)
        self.assertEqual("runner_observed", scan["candidates"][0]["evidence"]["evidence_type"])
        queue = Queue(work, self.runner)
        policy = self.policy(max_tasks=1)
        jobs = queue.enqueue(policy)
        self.assertEqual(1, len(jobs))
        self.assertEqual([], queue.enqueue(policy))
        outcome = queue.execute(policy)
        self.assertEqual("completed", outcome[0]["status"])
        self.assertIn("a - b", (self.repo / "calculator.py").read_text())
        self.assertEqual([], queue.execute(policy))
        self.assertEqual([], queue.enqueue(policy))

    def test_changed_source_checks_or_policy_rejects_launch(self):
        work = self.work()
        discover(self.repo, work, checks_path=self.manifest)
        queue = Queue(work, self.runner)
        policy = self.policy()
        queue.enqueue(policy)
        with self.assertRaisesRegex(ErolError, "changed"):
            queue.execute(self.policy(max_tasks=2))
        (self.repo / "calculator.py").write_text("def add(a,b): return 9\n")
        with self.assertRaisesRegex(ErolError, "changed"):
            queue.execute(policy)
        self.assertEqual([], self.runs.list())

    def test_changed_check_definition_rejected_even_with_cached_policy(self):
        work = self.work()
        discover(self.repo, work, checks_path=self.manifest)
        queue, policy = Queue(work, self.runner), self.policy()
        queue.enqueue(policy)
        self.checks["checks"][0]["timeout_seconds"] = 4
        self.write_checks()
        with self.assertRaisesRegex(ErolError, "check definition changed"):
            queue.execute(policy)
        self.assertEqual([], self.runs.list())

    def test_public_policy_command_binds_turkish_project_without_execution(self):
        output = self.base / "reviewed policy.json"
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "erol",
                "--project",
                str(self.repo),
                "--home",
                str(self.store.home),
                "queue",
                "policy",
                "--harness",
                "claude",
                "--checks",
                str(self.manifest),
                "--output",
                str(output),
                "--reviewers",
                "2",
            ],
            capture_output=True,
            encoding="utf-8",
            check=True,
        )
        self.assertFalse(json.loads(process.stdout)["executes"])
        self.assertEqual(self.project.id, load_policy(output, self.project.id)["project_id"])
        self.assertEqual([], self.runs.list())

    def test_work_and_search_index_reject_other_project(self):
        self.work()
        with self.assertRaisesRegex(ErolError, "project mismatch"):
            WorkStore(self.store.directory, "other-project")
        index = MemoryIndex(self.store)
        index.db.execute("UPDATE meta SET value='other-project' WHERE key='project_id'")
        index.db.commit()
        index.close()
        with self.assertRaisesRegex(ErolError, "project or schema mismatch"):
            MemoryIndex(self.store)

    def test_interrupted_queue_claim_never_starts_duplicate_and_reconciles_completed(self):
        work = self.work()
        discover(self.repo, work, checks_path=self.manifest)
        queue, policy = Queue(work, self.runner), self.policy()
        job = queue.enqueue(policy)[0]
        job.update({"status": "running", "owner_pid": None})
        work.put("jobs", job)
        with self.assertRaisesRegex(ErolError, "no run receipt"):
            queue.execute(policy, resume_id=job["id"])
        completed = self.runner.start(job["task"], "codex", self.manifest, task_id=job["task_id"])
        outcome = queue.execute(policy, resume_id=job["id"])[0]
        self.assertEqual(completed["id"], outcome["run_id"])
        self.assertEqual(1, len(self.runs.list()))

    def test_queue_cancel_is_durable_against_late_payload_write(self):
        work = self.work()
        discover(self.repo, work, checks_path=self.manifest)
        queue, policy = Queue(work, self.runner), self.policy()
        job = queue.enqueue(policy)[0]
        queue.cancel(job["id"])
        work.put("jobs", job)  # stale worker checkpoint cannot erase the cancellation
        self.assertTrue(work.get("jobs", job["id"])["cancel_requested"])
        self.assertEqual([], queue.execute(policy))

    def test_queue_cancellation_during_native_turn_blocks_checks(self):
        work = self.work()
        discover(self.repo, work, checks_path=self.manifest)
        queue, policy = Queue(work, self.runner), self.policy()
        job = queue.enqueue(policy)[0]
        original = self.factory.execute

        def execute(harness, role, *args, **kwargs):
            result = original(harness, role, *args, **kwargs)
            if role == "implementer":
                queue.cancel(job["id"])
            return result

        with patch.object(self.factory, "execute", execute):
            outcome = queue.execute(policy)[0]
        self.assertEqual("cancelled", outcome["status"])
        self.assertEqual([], self.runs.get(outcome["run_id"])["checks"])

    def test_queue_live_owner_lock_and_cycle_rejected(self):
        (self.repo / "notes.txt").write_text("TODO: repair arithmetic\nTODO: review arithmetic\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "todos")
        work = self.work()
        discover(self.repo, work)
        queue, policy = Queue(work, self.runner), self.policy()
        first, second = queue.enqueue(policy)
        queue.depend(second["id"], [first["id"]])
        with self.assertRaisesRegex(ErolError, "cycle"):
            queue.depend(first["id"], [second["id"]])
        with self.runs.lease(work.directory / "queue.lock"):
            with self.assertRaises(ErolError):
                queue.execute(policy)

    def test_dependency_applies_verified_parent_patch_and_rejects_changed_parent(self):
        (self.repo / "notes.txt").write_text("TODO: repair arithmetic\nTODO: inspect sum\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "todos")
        work = self.work()
        discover(self.repo, work)
        queue, policy = Queue(work, self.runner), self.policy(max_tasks=1)
        first, second = queue.enqueue(policy)
        queue.depend(second["id"], [first["id"]])
        queue.execute(policy)
        parent = self.runs.get(work.get("jobs", first["id"])["run_id"])
        (Path(parent["worktree"]) / "calculator.py").write_text("def add(a,b): return 7\n")
        with self.assertRaisesRegex(ErolError, "verified"):
            queue.execute(policy)
        (Path(parent["worktree"]) / "calculator.py").write_text("def add(a, b): return a + b\n")
        child = queue.execute(policy)[0]
        run = self.runs.get(child["run_id"])
        self.assertTrue(run["baseline"][0]["passed"])
        self.assertEqual(parent["id"], run["initial_patches"][0]["run_id"])

    def test_hybrid_retrieval_revision_freshness_bindings_and_budget(self):
        self.store.put(
            "learnings",
            {"id": "retry", "text": "Retry a database timeout", "evidence": ["synthetic"]},
        )
        result = self.store.search("veritabanı", mode="hybrid")
        self.assertEqual("retry", result[0]["id"])
        self.assertEqual("retry", self.store.search("zaman aşımı", mode="hybrid")[0]["id"])
        self.assertEqual([], self.store.search("veritabanı", mode="hybrid", max_chars=10))
        self.store.mark_stale("learnings", "retry")
        self.assertEqual([], self.store.search("veritabanı", mode="hybrid"))
        body = (self.repo / "calculator.py").read_bytes()
        self.store.put(
            "decisions",
            {
                "id": "bound",
                "text": "Database strategy",
                "evidence": ["synthetic"],
                "source_revisions": [
                    {"path": "calculator.py", "sha256": hashlib.sha256(body).hexdigest()}
                ],
            },
        )
        self.assertTrue(self.store.search("database", mode="hybrid"))
        (self.repo / "calculator.py").write_text("changed\n")
        self.assertEqual([], self.store.search("database", mode="hybrid"))
        index = MemoryIndex(self.store)
        self.addCleanup(index.close)
        self.assertEqual(self.project.id, index.sync()["project_id"])

    def test_transitive_dependencies_compose_each_verified_delta_once(self):
        (self.repo / "notes.txt").write_text("TODO: first\nTODO: second\nTODO: third\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "three todos")
        work = self.work()
        discover(self.repo, work)
        queue, policy = Queue(work, self.runner), self.policy(max_tasks=1)
        first, second, third = queue.enqueue(policy)
        queue.depend(second["id"], [first["id"]])
        queue.depend(third["id"], [first["id"], second["id"]])
        self.assertEqual("completed", queue.execute(policy)[0]["status"])
        self.assertEqual("completed", queue.execute(policy)[0]["status"])
        final = queue.execute(policy)[0]
        self.assertEqual("completed", final["status"])
        run = self.runs.get(final["run_id"])
        self.assertEqual(2, len(run["initial_patches"]))
        self.assertTrue(run["baseline"][0]["passed"])

    def test_panel_excludes_context_and_uses_text_content_and_readonly_http(self):
        result = self.start()
        state = panel_state(self.store.directory, self.project.id)
        serialized = canonical(state)
        self.assertNotIn('"context"', serialized)
        self.assertNotIn('"task"', serialized)
        self.assertIn(result["id"], serialized)
        server = make_server(self.store.directory, self.project.id, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
        self.addCleanup(connection.close)
        connection.request("GET", "/api/state")
        response = connection.getresponse()
        self.assertEqual(200, response.status)
        self.assertTrue(json.loads(response.read())["read_only"])
        connection.request("POST", "/api/state", body="mutate")
        response = connection.getresponse()
        self.assertEqual(405, response.status)
        response.read()
        connection.request("GET", "/", headers={"Host": "attacker.test"})
        response = connection.getresponse()
        self.assertEqual(403, response.status)
        response.read()

    def test_paired_benchmark_same_fixture_checks_and_no_context_credit(self):
        case = {
            "id": "sum",
            "task": "Repair arithmetic",
            "files": {"calculator.py": "def add(a, b): return a - b\n"},
            "checks": self.checks,
            "mode": "development",
            "memory": [
                {
                    "id": "hint",
                    "text": "Addition uses a plus operator",
                    "evidence": ["synthetic-fixture"],
                }
            ],
        }
        suite = self.base / "suite.json"
        suite.write_text(canonical({"schema_version": 1, "cases": [case]}), encoding="utf-8")

        def factory(store, engine, runs, **kwargs):
            from erol.execution import Runner

            return Runner(store, engine, runs, harness_factory=self.factory, **kwargs)

        report = behavioral_benchmark(
            suite, "codex", self.base / "report.json", runner_factory=factory
        )
        self.assertTrue(report["passed"])
        self.assertEqual("paired_context_ablation", report["kind"])
        control = report["pairs"][0]["arms"]["control"]
        self.assertEqual([], control["selected_skills"])
        self.assertIsNone(control["cost_usd"])
        self.assertEqual(2, len(report["pairs"][0]["arms"]))
        case["files"]["../escape.txt"] = "invalid"
        suite.write_text(canonical({"schema_version": 1, "cases": [case]}), encoding="utf-8")
        with self.assertRaisesRegex(ErolError, "Unsafe"):
            load_suite(suite)


class SourceReceiptTests(unittest.TestCase):
    def test_private_mixed_dns_credentials_and_redirects_rejected(self):
        answers = [(2, 1, 6, "", ("127.0.0.1", 443))]
        with patch("erol.sources.socket.getaddrinfo", return_value=answers):
            with self.assertRaises(ErolError):
                public_target("https://example.test/a")
        answers.append((2, 1, 6, "", ("8.8.8.8", 443)))
        with patch("erol.sources.socket.getaddrinfo", return_value=answers):
            with self.assertRaises(ErolError):
                public_target("https://example.test/a")
        for url in (
            "http://example.test/a",
            "https://user:secret@example.test/a",
            "https://example.test:8443/a",
        ):
            with self.assertRaises(ErolError):
                public_target(url)

    def test_access_hash_is_observed_and_bounded_no_body_persistence(self):
        class Response:
            status = 200
            chunks = [b"public source", b""]

            def getheader(self, name, default=None):
                return "text/plain" if name == "Content-Type" else default

            def read1(self, size):
                return self.chunks.pop(0)

        class Connection:
            sock = None

            def __init__(self, *args):
                pass

            def request(self, *args, **kwargs):
                pass

            def getresponse(self):
                return Response()

            def close(self):
                pass

        with (
            patch("erol.sources.public_target", return_value=("example.test", "8.8.8.8", "/")),
            patch("erol.sources.PinnedHTTPS", Connection),
        ):
            result = fetch_source("https://example.test", deadline=time.monotonic() + 10)
        self.assertEqual(hashlib.sha256(b"public source").hexdigest(), result["content_sha256"])
        self.assertNotIn("body", result)
        unavailable = fetch_sources(
            {"sources": [{"id": "S1", "url": "https://127.0.0.1/a"}]}, seconds=0
        )
        self.assertEqual("unavailable", unavailable[0]["status"])

    def test_redirect_target_is_revalidated_and_oversized_body_is_not_receipted(self):
        class Response:
            status = 302

            def getheader(self, name, default=None):
                return "https://127.0.0.1/a" if name == "Location" else "text/plain"

            def read1(self, size):
                return b"x" * 1048577

        class Connection:
            sock = None

            def __init__(self, *args):
                pass

            def request(self, *args, **kwargs):
                pass

            def getresponse(self):
                return Response()

            def close(self):
                pass

        with (
            patch(
                "erol.sources.public_target",
                side_effect=[("example.test", "8.8.8.8", "/"), ErolError("Private target blocked")],
            ) as targets,
            patch("erol.sources.PinnedHTTPS", Connection),
        ):
            with self.assertRaisesRegex(ErolError, "Private"):
                fetch_source("https://example.test", deadline=time.monotonic() + 10)
            self.assertEqual("https://127.0.0.1/a", targets.call_args.args[0])
        Response.status = 200
        with (
            patch("erol.sources.public_target", return_value=("example.test", "8.8.8.8", "/")),
            patch("erol.sources.PinnedHTTPS", Connection),
        ):
            with self.assertRaisesRegex(ErolError, "one MiB"):
                fetch_source("https://example.test", deadline=time.monotonic() + 10)
