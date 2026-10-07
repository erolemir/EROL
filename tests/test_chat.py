"""Terminal contracts, real workspace/check behavior, and deterministic provider fixtures."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from erol.chat import ChatEngine, Sessions
from erol.checktrust import CheckTrust
from erol.cli import main
from erol.common import ErolError, canonical
from erol.connections import Connection, ConnectionStore, Model, Settings, classify, route
from erol.console import Editor, Screen, WindowsKeys, command, key_windows, launch, read_prompt
from erol.providers import (
    APIAdapter,
    Budget,
    BudgetExhausted,
    CleanupFailure,
    CLIAdapter,
    Request,
    event,
)
from erol.store import Store
from erol.workspace import Workspace, changes, run_checks, snapshot


class ConnectionTests(unittest.TestCase):
    def test_cli_and_api_same_provider_are_independent_and_external(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            home = Path(temporary) / "home"
            store = ConnectionStore(home, root)
            store.connect("codex", "subscription")
            store.connect("openai", "api")
            self.assertEqual(len(ConnectionStore(home, root).settings.connections), 2)
            self.assertEqual(list(root.iterdir()), [])
            with self.assertRaises(ErolError):
                ConnectionStore(root / "bad", root)

    def test_credentials_and_remote_http_urls_are_rejected(self):
        for data in (
            {"id": "a", "kind": "openai", "api_key": "private"},
            {"id": "a", "kind": "openai", "key_env": "actual-value"},
            {
                "id": "a",
                "kind": "compatible",
                "key_env": "TEST_KEY",
                "base_url": "http://example.com",
            },
            {"id": "a", "kind": "openai", "base_url": "https://user:pass@example.com"},
            {"id": "a", "kind": "codex", "enabled": "yes"},
        ):
            with self.subTest(data=data), self.assertRaises(ErolError):
                Connection.load(data)

    def test_budget_boolean_nan_unknown_fields_are_rejected(self):
        for data in (
            {"api_budget_usd": True},
            {"api_budget_usd": float("nan")},
            {"api_budget_usd": 0},
            {"schema_version": 2},
            {"max_parallel": 4},
            {"unknown": 1},
        ):
            with self.assertRaises(ErolError):
                Settings.load(data)

    def test_task_scope_affects_routing_without_skill_count_escalation(self):
        models = [Model("small", level=1), Model("medium", level=2), Model("large", level=3)]
        settings = Settings(connections=[Connection("local", "codex", models=models)])
        available = {"local": models}
        self.assertEqual(route(settings, "Small fix: typo in README", available)["model"], "small")
        self.assertEqual(route(settings, "Investigate this problem", available)["model"], "medium")
        self.assertEqual(
            route(settings, "Security authorization migration", available)["model"], "large"
        )
        self.assertEqual(
            route(settings, "Fix this", available, plan={"skills": [{}, {}, {}]})["model"], "medium"
        )
        self.assertEqual(classify("fix")["complexity"], "medium")

    def test_override_does_not_silently_change_and_agy_cannot_review(self):
        model = Model("small", level=1)
        settings = Settings(connections=[Connection("agy", "antigravity", models=[model])])
        with self.assertRaises(ErolError):
            route(settings, "Fix this", {"agy": [model]}, role="reviewer")
        with self.assertRaises(ErolError):
            route(settings, "Fix this", {"agy": [model]}, override="agy:missing")

    def test_simple_conversation_uses_economic_tier_without_downgrading_real_work(self):
        models = [Model("luna", level=1), Model("sol", level=3)]
        settings = Settings(connections=[Connection("subscription", "codex", models=models)])
        available = {"subscription": models}
        for task in ("selam", "MERHABA!", "Günaydın", "hello", "Thanks!"):
            chosen = route(settings, task, available, role="assistant", require_tools=False)
            self.assertEqual(chosen["model"], "luna")
            self.assertEqual(chosen["effort"], "low")
            self.assertEqual(chosen["transport"], "cli")
        for task in ("selam güvenlik hatasını çöz", "hello investigate this issue", "fix"):
            self.assertNotEqual(classify(task)["complexity"], "small")
        chosen = route(settings, "selam", {"subscription": [models[1]]}, role="assistant")
        self.assertEqual(chosen["model"], "sol")
        self.assertIn("no eligible lower-level profile", chosen["reason"])
        manual = route(settings, "selam", available, override="subscription:sol")
        self.assertEqual(manual["model"], "sol")
        self.assertNotIn("no eligible lower-level", manual["reason"])

    def test_missing_prices_and_context_remove_api_candidates(self):
        connection = Connection.load({"id": "api", "kind": "openai", "models": [{"id": "a"}]})
        with self.assertRaises(ErolError):
            route(Settings(connections=[connection]), "Fix", {"api": connection.models})
        model = Model("a", input_price=1, output_price=2, context_window=1024)
        connection.models = [model]
        with self.assertRaises(ErolError):
            route(Settings(connections=[connection]), "Fix", {"api": [model]})


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()

    def test_task_diff_preserves_initial_dirty_content_and_handles_new_delete_binary(self):
        (self.root / "existing.txt").write_text("prior edit\n", "utf-8")
        (self.root / "remove.txt").write_text("remove\n", "utf-8")
        before = snapshot(self.root)
        (self.root / "existing.txt").write_text("prior edit\nnew change\n", "utf-8")
        (self.root / "new.txt").write_text("new\n", "utf-8")
        (self.root / "binary.bin").write_bytes(b"\x00\xff")
        (self.root / "remove.txt").unlink()
        diff = changes(before, snapshot(self.root))
        paths = {d["path"]: d for d in diff}
        self.assertEqual(paths["remove.txt"]["status"], "deleted")
        self.assertEqual(paths["new.txt"]["status"], "added")
        self.assertTrue(paths["binary.bin"]["binary"])
        self.assertNotIn("-prior edit", paths["existing.txt"]["diff"])

    def test_api_write_requires_observed_hash_and_readonly_rejects_tools(self):
        file = self.root / "a.txt"
        file.write_text("before", "utf-8")
        workspace = Workspace(self.root)
        read = json.loads(workspace.dispatch("read_file", {"path": "a.txt"}))
        with self.assertRaises(ErolError):
            workspace.dispatch(
                "write_file", {"path": "a.txt", "content": "bad", "expected_sha256": None}
            )
        file.write_text("concurrent change", "utf-8")
        with self.assertRaises(ErolError):
            workspace.dispatch(
                "write_file", {"path": "a.txt", "content": "bad", "expected_sha256": read["sha256"]}
            )
        workspace.dispatch(
            "write_file", {"path": "new.txt", "content": "new", "expected_sha256": None}
        )
        readonly = Workspace(self.root, readonly=True)
        for tool, args in (("write_file", {}), ("run_command", {}), ("delete_file", {})):
            with self.assertRaises(ErolError):
                readonly.dispatch(tool, args)

    def test_paths_credentials_and_command_allowlist(self):
        workspace = Workspace(self.root)
        for path in ("../outside", ".env", ".git/config", str(self.root / "abs")):
            with self.assertRaises(ErolError):
                workspace.path(path)
        with self.assertRaises(ErolError):
            workspace.dispatch("run_command", {"argv": [sys.executable, "-c", "print(1)"]})
        with self.assertRaises(ErolError):
            workspace.dispatch(
                "write_file",
                {"path": "key.txt", "content": "password=secret", "expected_sha256": None},
            )

    def test_checks_are_observed_not_model_assertions(self):
        manifest = {
            "checks": [
                {
                    "name": "pass",
                    "kind": "acceptance",
                    "argv": [sys.executable, "-c", "print('observed')"],
                    "timeout_seconds": 10,
                },
                {
                    "name": "fail",
                    "kind": "acceptance",
                    "argv": [sys.executable, "-c", "raise SystemExit(1)"],
                    "timeout_seconds": 10,
                },
            ]
        }
        trust = CheckTrust(Path(self.temp.name) / "trust", self.root)
        trust.approve(manifest)
        result = run_checks(self.root, manifest, threading.Event(), trust=trust)
        self.assertTrue(result[0]["passed"])
        self.assertIn("observed", result[0]["output"])
        self.assertFalse(result[1]["passed"])
        self.assertEqual(result[1]["evidence_type"], "erol_observed_command")


class BudgetTests(unittest.TestCase):
    def test_missing_usage_is_accounted_and_budget_shared_across_calls(self):
        model = Model("a", input_price=100, output_price=100, output_limit=128)
        budget = Budget(0.02)
        reservation = budget.reserve(model, {"prompt": "x"})
        report = budget.settle(model, reservation, {})
        self.assertIsNone(report["estimated_cost_usd"])
        self.assertGreater(budget.summary()["unreported_reserved_usd"], 0)
        with self.assertRaises(ErolError):
            budget.reserve(model, {"prompt": "x"})

    def test_reported_token_usage_settles_reservation(self):
        model = Model("a", input_price=2, output_price=10)
        budget = Budget(5)
        reservation = budget.reserve(model, {"prompt": "hello"})
        report = budget.settle(model, reservation, {"input_tokens": 100, "output_tokens": 10})
        self.assertAlmostEqual(report["estimated_cost_usd"], 0.0003)
        self.assertEqual(budget.summary()["pending_reserved_usd"], 0)


class APITests(unittest.TestCase):
    def make(self, kind):
        model = Model("test-model", input_price=1, output_price=2)
        connection = Connection.load(
            {
                "id": "api",
                "kind": kind,
                "key_env": "EROL_TEST_KEY",
                "base_url": "http://127.0.0.1:12345",
                "models": [asdict(model)],
            }
        )
        return APIAdapter(connection, Path.cwd()), Request(
            "task", connection, model, "Fix the file", role="reviewer"
        )

    def test_each_provider_completes_and_schemas_are_native(self):
        fixtures = {
            "openai": [
                {"type": "response.output_text.delta", "delta": "hello"},
                {
                    "type": "response.completed",
                    "response": {
                        "status": "completed",
                        "output": [],
                        "usage": {"input_tokens": 10, "output_tokens": 1},
                    },
                },
            ],
            "anthropic": [
                {"type": "message_start", "message": {"usage": {"input_tokens": 10}}},
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                },
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": "hello"},
                },
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn"},
                    "usage": {"output_tokens": 1},
                },
            ],
            "gemini": [
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "hello"}]}, "finishReason": "STOP"}
                    ],
                    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 1},
                }
            ],
            "compatible": [
                {
                    "choices": [{"delta": {"content": "hello"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 1},
                }
            ],
        }
        for kind, chunks in fixtures.items():
            with self.subTest(kind=kind):
                provider, request = self.make(kind)
                captured = []

                def stream(path, payload, captured=captured, chunks=chunks):
                    captured.append(payload)
                    yield from chunks

                provider._chunks = stream
                result = list(
                    provider.stream(
                        request,
                        budget=Budget(5),
                        tools=Workspace(Path.cwd()).tools,
                        dispatch=lambda n, a: "ok",
                    )
                )
                self.assertTrue(result[-1]["data"]["completed"])
                self.assertEqual(
                    "".join(e["data"]["text"] for e in result if e["type"] == "text_delta"), "hello"
                )
                if kind == "gemini":
                    self.assertIn(
                        "parametersJsonSchema", captured[0]["tools"][0]["functionDeclarations"][0]
                    )

    def test_openai_tool_round_edits_real_file_and_accounts_each_call(self):
        provider, request = self.make("openai")
        request.role = "implementer"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace = Workspace(root)
            call = {
                "type": "function_call",
                "call_id": "call-1",
                "name": "write_file",
                "arguments": canonical(
                    {"path": "a.txt", "content": "written", "expected_sha256": None}
                ),
            }
            calls = []

            def stream(path, payload):
                calls.append(payload)
                if len(calls) == 2:
                    yield {
                        "type": "response.output_text.delta",
                        "delta": canonical(
                            {"summary": "hello", "strategy": "edit", "status": "implemented"}
                        ),
                    }
                yield {
                    "type": "response.completed",
                    "response": {
                        "status": "completed",
                        "output": [call] if len(calls) == 1 else [],
                        "usage": {"input_tokens": 10, "output_tokens": 2},
                    },
                }

            provider._chunks = stream
            budget = Budget(5)
            result = list(
                provider.stream(
                    request, budget=budget, tools=workspace.tools, dispatch=workspace.dispatch
                )
            )
            self.assertEqual((root / "a.txt").read_text("utf-8"), "written")
            self.assertEqual(budget.calls, 2)
            self.assertTrue(result[-1]["data"]["completed"])
            self.assertEqual(calls[1]["input"][-1]["type"], "function_call_output")

    def test_truncated_stream_is_not_success_and_generator_close_settles(self):
        provider, request = self.make("openai")
        provider._chunks = lambda path, payload: iter(
            [{"type": "response.output_text.delta", "delta": "partial"}]
        )
        budget = Budget(5)
        result = list(provider.stream(request, budget=budget, tools=[], dispatch=lambda n, a: ""))
        self.assertFalse(result[-1]["data"]["completed"])
        budget = Budget(5)
        stream = provider.stream(request, budget=budget, tools=[], dispatch=lambda n, a: "")
        next(stream)
        stream.close()
        self.assertEqual(budget.reserved, 0)
        self.assertGreater(budget.spent, 0)

    def test_real_http_sse_and_environment_credentials(self):
        captured = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append(
                    (
                        self.path,
                        self.headers.get("Authorization"),
                        json.loads(self.rfile.read(int(self.headers["Content-Length"]))),
                    )
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                data = {
                    "choices": [{"delta": {"content": "hello"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 1},
                }
                self.wfile.write(("data: " + json.dumps(data) + "\n\ndata: [DONE]\n\n").encode())

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            provider, request = self.make("compatible")
            provider.connection.base_url = f"http://127.0.0.1:{server.server_port}"
            with patch.dict(os.environ, {"EROL_TEST_KEY": "test-value"}):
                result = list(
                    provider.stream(request, budget=Budget(5), tools=[], dispatch=lambda n, a: "")
                )
            self.assertTrue(result[-1]["data"]["completed"])
            self.assertEqual(captured[0][0], "/chat/completions")
            self.assertEqual(captured[0][1], "Bearer test-value")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)

    def test_cli_events_and_agy_stream_input(self):
        for kind in ("codex", "claude", "antigravity"):
            connection = Connection(kind, kind, models=[Model("model")])
            request = Request("task", connection, connection.models[0], "hello")
            worker = {"summary": "hello", "strategy": "edit", "status": "implemented"}
            lines = {
                "codex": [
                    {"type": "thread.started", "thread_id": "native-1"},
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": canonical(worker)},
                    },
                    {"type": "turn.completed"},
                ],
                "claude": [
                    {
                        "type": "stream_event",
                        "event": {"delta": {"type": "text_delta", "text": "hello"}},
                    },
                    {
                        "type": "result",
                        "subtype": "success",
                        "structured_output": worker,
                        "is_error": False,
                        "session_id": "native-1",
                    },
                ],
                "antigravity": [
                    {
                        "event": "step_update",
                        "step_update": {
                            "step_type": "agent_response",
                            "text_delta": "hello",
                            "state": "DONE",
                        },
                    },
                    {
                        "event": "result",
                        "result": {
                            "status": "SUCCESS",
                            "conversation_id": "native-1",
                            "response": "hello",
                            "structured_output": worker,
                        },
                    },
                ],
            }[kind]
            captures = []

            def observed(argv, cwd, captures=captures, lines=lines, **options):
                captures.append((argv, options["prompt"]))
                for data in lines:
                    options["on_line"](json.dumps(data))
                return {"exit_code": 0, "reason": None}

            with (
                patch("erol.providers.command_prefix", return_value=[sys.executable]),
                patch("erol.providers.observe", side_effect=observed),
            ):
                result = list(CLIAdapter(connection, Path.cwd()).stream(request))
            self.assertTrue(result[-1]["data"]["completed"])
            self.assertIn(
                "hello", "".join(e["data"]["text"] for e in result if e["type"] == "text_delta")
            )
            if kind == "antigravity":
                self.assertNotIn("-p", captures[0][0])
                self.assertIn("--json-schema", captures[0][0])
                self.assertEqual(json.loads(captures[0][1])["event"], "user")

    def test_native_worker_missing_or_blocked_report_is_not_completion(self):
        for report in (
            None,
            [],
            {"status": "implemented"},
            {"summary": "Blocked", "strategy": "inspect", "status": "needs_attention"},
        ):
            with self.subTest(report=report):
                connection = Connection("cli", "codex", models=[Model("test")])
                request = Request("task", connection, connection.models[0], "fix")

                def observed(argv, cwd, report=report, **options):
                    options["on_line"](
                        canonical(
                            {
                                "type": "item.completed",
                                "item": {"type": "agent_message", "text": canonical(report)},
                            }
                        )
                    )
                    options["on_line"](canonical({"type": "turn.completed"}))
                    return {"exit_code": 0, "reason": None}

                with (
                    patch("erol.providers.command_prefix", return_value=[sys.executable]),
                    patch("erol.providers.observe", side_effect=observed),
                ):
                    events = list(CLIAdapter(connection, Path.cwd()).stream(request))
                self.assertFalse(events[-1]["data"]["completed"])

    def test_api_worker_blocked_json_is_not_completion(self):
        provider, request = self.make("openai")
        request.role = "implementer"
        provider._chunks = lambda path, payload: iter(
            [
                {
                    "type": "response.output_text.delta",
                    "delta": canonical(
                        {"summary": "Blocked", "strategy": "inspect", "status": "needs_attention"}
                    ),
                },
                {
                    "type": "response.completed",
                    "response": {
                        "status": "completed",
                        "output": [],
                        "usage": {"input_tokens": 10, "output_tokens": 10},
                    },
                },
            ]
        )
        events = list(
            provider.stream(request, budget=Budget(5), tools=[], dispatch=lambda n, a: "")
        )
        self.assertFalse(events[-1]["data"]["completed"])


class FakeProvider:
    def __init__(self, connection, root):
        self.connection, self.root = connection, root

    def capabilities(self):
        return {"available": True}

    def models(self):
        return self.connection.models

    def cancel(self):
        pass

    def stream(self, request, **options):
        if request.role == "implementer":
            path = self.root / "edited.txt"
            path.write_text(path.read_text("utf-8") + "\ntask change", "utf-8")
            text = canonical(
                {"summary": "Implemented", "strategy": "edit", "status": "implemented"}
            )
        elif request.role == "reviewer":
            text = '{"approved":true,"findings":[],"summary":"Reviewed"}'
        else:
            text = "Inspect, implement and verify"
        yield event("text_delta", request, text=text)
        yield event(
            "final",
            request,
            completed=True,
            native_session=f"native-{request.role}-{request.model.id}",
        )


class EngineTests(unittest.TestCase):
    def make(self, temporary):
        root, home = Path(temporary) / "project", Path(temporary) / "home"
        root.mkdir()
        (root / "edited.txt").write_text("existing user edit\n", "utf-8")
        engine = ChatEngine(root, home, factory=FakeProvider)
        engine.connections.connect("codex")
        return engine

    def test_direct_non_git_task_single_model_review_and_observed_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = self.make(temporary)
            # Exactly one model must still get an independent, fresh review.
            engine.connections.settings.connections[0].models = [Model("single", level=3)]
            manifest = Path(temporary) / "checks.json"
            manifest.write_text(
                canonical(
                    {
                        "schema_version": 1,
                        "checks": [
                            {
                                "name": "acceptance",
                                "kind": "acceptance",
                                "argv": [
                                    sys.executable,
                                    "-c",
                                    "from pathlib import Path; "
                                    "assert 'task change' in Path('edited.txt').read_text()",
                                ],
                                "timeout_seconds": 10,
                            }
                        ],
                    }
                ),
                "utf-8",
            )
            engine.connections.settings.checks_path = str(manifest)
            engine.check_trust.approve(json.loads(manifest.read_text("utf-8")))
            engine.connections.save()
            result = engine.execute("Implement this plan: expand the feature")
            self.assertEqual(result["status"], "completed", result)
            self.assertEqual(len(result["reviews"]), 1)
            self.assertTrue(result["verification"]["verified"])
            self.assertTrue(
                (engine.root / "edited.txt").read_text().startswith("existing user edit")
            )
            self.assertNotIn("-existing user edit", result["changes"][0]["diff"])
            self.assertEqual(engine.resume(engine.session_id)["status"], "completed")

    def test_no_checks_never_claims_verified_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = self.make(temporary)
            result = engine.execute("Small fix: typo")
            self.assertEqual(result["status"], "implemented_unverified")
            self.assertFalse(result["verification"]["verified"])

    def test_nested_task_is_rejected_and_help_does_not_create_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = self.make(temporary)
            with patch.dict(os.environ, {"EROL_RUN_ACTIVE": "1"}), self.assertRaises(ErolError):
                engine.execute("Fix")
            self.assertIn("/help", command(engine, "/help")["commands"])
            self.assertFalse(engine.directory.exists())

    def test_saved_session_cannot_cross_project_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            sessions = Sessions(Path(temporary), "project-a")
            with self.assertRaises(ErolError):
                sessions.save({"id": "session-a", "project_id": "project-b"})

    def test_review_findings_repair_within_attempt_limit(self):
        class ReviewOnce(FakeProvider):
            reviews = 0

            def stream(self, request, **options):
                if request.role == "reviewer":
                    ReviewOnce.reviews += 1
                    text = canonical(
                        {
                            "approved": ReviewOnce.reviews > 1,
                            "findings": [] if ReviewOnce.reviews > 1 else ["Fix bug"],
                            "summary": "review",
                        }
                    )
                    yield event("text_delta", request, text=text)
                    yield event("final", request, completed=True)
                else:
                    yield from super().stream(request, **options)

        with tempfile.TemporaryDirectory() as temporary:
            engine = self.make(temporary)
            engine.factory = ReviewOnce
            engine.selected_model = "codex:gpt-6.1-sol"
            result = engine.execute("Fix the feature")
            self.assertEqual(len(result["attempts"]), 2, result)
            self.assertTrue(result["reviews"][0]["approved"])
            self.assertEqual(result["status"], "implemented_unverified")

    def test_malformed_review_never_approves_or_crashes(self):
        class BadReview(FakeProvider):
            def stream(self, request, **options):
                if request.role == "reviewer":
                    yield event("text_delta", request, text="[]")
                    yield event("final", request, completed=True)
                else:
                    yield from super().stream(request, **options)

        with tempfile.TemporaryDirectory() as temporary:
            engine = self.make(temporary)
            engine.factory = BadReview
            engine.selected_model = "codex:gpt-6.1-sol"
            result = engine.execute("Fix the feature")
            self.assertEqual(result["status"], "needs_attention")
            self.assertEqual(len(result["attempts"]), 3)
            self.assertFalse(result["reviews"][0]["approved"])

    def test_cancellation_leaves_partial_diff_and_allows_next_task(self):
        holder = {}

        class Interrupted(FakeProvider):
            def stream(self, request, **options):
                yield from super().stream(request, **options)
                holder["engine"].cancel()

        with tempfile.TemporaryDirectory() as temporary:
            engine = self.make(temporary)
            holder["engine"] = engine
            engine.factory = Interrupted
            first = engine.execute("Small fix: typo")
            self.assertEqual(first["status"], "cancelled")
            self.assertTrue(first["changes"])
            engine.factory = FakeProvider
            self.assertEqual(engine.execute("Small fix: typo")["status"], "implemented_unverified")

    def test_budget_pause_continue_preserves_accounting_and_partial_changes(self):
        class Expensive(FakeProvider):
            def stream(self, request, **options):
                yield from super().stream(request, **options)
                options["budget"].spent = 0.75
                raise BudgetExhausted("Task budget exhausted")

        with tempfile.TemporaryDirectory() as temporary:
            engine = self.make(temporary)
            engine.factory = Expensive
            first = engine.execute("Small fix: typo")
            self.assertEqual(first["status"], "waiting_budget")
            self.assertTrue(first["changes"])
            engine.resume(engine.session_id)
            engine.factory = FakeProvider
            second = engine.execute(first["task"], resume=True)
            self.assertEqual(second["usage"]["accounted_usd"], 0.75)
            self.assertEqual(second["continuation_history"][0]["changes"], first["changes"])

    def test_two_homes_share_non_git_writer_lease_and_process_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = self.make(temporary)
            second = ChatEngine(first.root, Path(temporary) / "home-two", factory=FakeProvider)
            with Store(first.home, first.project) as store, first._lease(store) as marker:
                with Store(second.home, second.project) as other, self.assertRaises(ErolError):
                    with second._lease(other):
                        pass
                marker.write_text(canonical({"active_pids": [os.getpid()]}), "utf-8")
            try:
                with Store(second.home, second.project) as other, self.assertRaises(ErolError):
                    with second._lease(other):
                        pass
            finally:
                marker.write_text(canonical({"active_pids": []}), "utf-8")

    def test_real_checks_respect_whole_task_deadline_and_clear_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            processes = []
            manifest = {
                "checks": [
                    {
                        "name": "slow",
                        "kind": "acceptance",
                        "argv": [sys.executable, "-c", "import time; time.sleep(30)"],
                        "timeout_seconds": 30,
                    }
                ]
            }
            trust = CheckTrust(Path(temporary) / "trust", root)
            trust.approve(manifest)
            reports = run_checks(
                root,
                manifest,
                threading.Event(),
                deadline=time.monotonic() + 0.25,
                on_process=processes.append,
                trust=trust,
            )
            self.assertFalse(reports[0]["passed"])
            self.assertEqual(reports[0]["reason"], "timeout")
            self.assertEqual(processes[-1], None)
            self.assertTrue(processes[0])

    def test_brand_png_is_packaged_original(self):
        import hashlib
        from importlib.resources import files

        png = files("erol").joinpath("data/brand/erol.png").read_bytes()
        logo = json.loads(files("erol").joinpath("data/terminal-logo.json").read_text("utf-8"))
        self.assertEqual(hashlib.sha256(png).hexdigest(), logo["source_sha256"])

    def test_uncertain_cleanup_never_retries_another_writer(self):
        class Uncontained(FakeProvider):
            writers = 0

            def stream(self, request, **options):
                Uncontained.writers += 1
                yield from super().stream(request, **options)
                raise CleanupFailure("Cleanup uncertain")

        with tempfile.TemporaryDirectory() as temporary:
            engine = self.make(temporary)
            engine.factory = Uncontained
            result = engine.execute("Small fix: typo")
            self.assertEqual(result["status"], "needs_attention")
            self.assertEqual(Uncontained.writers, 1)
            self.assertTrue(result["changes"])


class StartupTests(unittest.TestCase):
    def start(self, root, home, inputs):
        output = io.StringIO()
        screen = Screen(output)
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch("erol.console.Screen", return_value=screen),
            patch("erol.console.read_prompt", side_effect=inputs),
            patch("erol.console.shutil.which", return_value=None),
            patch("erol.console.ChatEngine", wraps=ChatEngine) as engines,
        ):
            result = launch(root, home)
        return result, output.getvalue(), engines

    def test_user_directory_starts_picker_before_creating_engine(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / ".erol"
            project = root / "workspace with spaces"
            project.mkdir()
            with patch("erol.console.read_choice", return_value=None):
                result, output, engines = self.start(
                    root,
                    home,
                    [
                        "/help",
                        "Please fix something",
                        "/project .",
                        "/project missing",
                        '/project "workspace with spaces"',
                        "/exit",
                    ],
                )
            self.assertEqual(result, 0)
            self.assertIn("/project", output)
            self.assertIn(str(project), output)
            self.assertEqual(engines.call_count, 1)
            self.assertEqual(engines.call_args.args[0].resolve(), project.resolve())
            catalog = json.loads((home / "global/projects.json").read_text("utf-8"))
            self.assertEqual(catalog["projects"][0]["root"], str(project))
            self.assertFalse((home / "state").exists())
            self.assertFalse((home / "global/chat").exists())

    def test_picker_exit_and_interrupt_do_not_create_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / ".erol"
            result, _, engines = self.start(root, home, [KeyboardInterrupt, "/exit"])
            self.assertEqual(result, 0)
            engines.assert_not_called()
            self.assertFalse(home.exists())

    def test_regular_project_does_not_prompt_for_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            home = Path(temporary) / "external"
            result, _, engines = self.start(root, home, ["/exit"])
            self.assertEqual(result, 0)
            engines.assert_called_once()
            catalog = json.loads((home / "global/projects.json").read_text("utf-8"))
            self.assertEqual(catalog["projects"][0]["root"], str(root))
            self.assertFalse((home / "state").exists())
            self.assertFalse((home / "global/chat").exists())

    def test_headless_nested_home_uses_general_mode_without_project_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / ".erol"
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors), patch("erol.chat.adapter") as provider:
                code = main(
                    ["--project", str(root), "--home", str(home), "chat", "--prompt", "Fix typo"]
                )
            self.assertEqual(code, 2)
            self.assertIn("No eligible model", errors.getvalue())
            provider.assert_not_called()
            self.assertFalse(home.exists())


class EditorTests(unittest.TestCase):
    def test_windows_buffered_commands_survive_next_prompt(self):
        class Keys:
            def __init__(self, text):
                self.buffer = text

            def getwch(self):
                if not self.buffer:
                    raise EOFError
                char, self.buffer = self.buffer[0], self.buffer[1:]
                return char

            def kbhit(self):
                return bool(self.buffer)

        screen = Screen(io.StringIO())
        screen.rich = True
        with (
            patch("erol.console.os.name", "nt"),
            patch("erol.console.windows_console_mode", return_value=contextlib.nullcontext(True)),
            patch("erol.console.WindowsKeys", side_effect=[Keys("/help\r/exit\r"), Keys("")]),
            patch.object(sys.stdin, "fileno", return_value=0),
        ):
            self.assertEqual(read_prompt(screen, [], []), "/help")
            self.assertEqual(read_prompt(screen, [], []), "/exit")

    def test_windows_paste_end_crosses_native_read_buffer_boundary(self):
        import ctypes
        from ctypes import wintypes

        class Kernel:
            def __init__(self):
                # Escape lies at the exact 64-character boundary.
                self.chunks = ["x" * 63 + "\x1b", "[201~"]

            def ReadConsoleW(self, handle, buffer, maximum, count, reserved):
                buffer.value = self.chunks.pop(0)
                count._obj.value = len(buffer.value)
                return True

            def GetNumberOfConsoleInputEvents(self, handle, count):
                count._obj.value = len(self.chunks)
                return True

        reader = WindowsKeys.__new__(WindowsKeys)
        reader.kernel, reader.ctypes, reader.wintypes = Kernel(), ctypes, wintypes
        reader.handle, reader.buffer = 0, ""
        editor = Editor([], [])
        editor.key("paste_start")
        for _ in range(64):
            editor.key(key_windows(reader))
        self.assertFalse(editor.pasting)
        self.assertEqual(editor.key("enter"), "x" * 63)

    def test_windows_vt_cursor_and_delete_keys(self):
        class Keys:
            def __init__(self, sequence):
                self.buffer = sequence

            def getwch(self):
                char, self.buffer = self.buffer[0], self.buffer[1:]
                return char

            def kbhit(self):
                return bool(self.buffer)

        for sequence, expected in (("\x1b[H", "home"), ("\x1b[F", "end"), ("\x1b[3~", "delete")):
            self.assertEqual(key_windows(Keys(sequence)), expected)

    def test_multiline_paste_history_completion_and_cancel(self):
        editor = Editor(["old"], ["/help", "/models"])
        for key in ("paste_start", "a", "enter", "b", "paste_end"):
            self.assertIsNone(editor.key(key))
        self.assertEqual(editor.key("enter"), "a\nb")
        editor = Editor(["old"], ["/help"])
        editor.key("up")
        self.assertEqual(editor.text, "old")
        editor.key("down")
        for key in ("/", "h", "tab"):
            editor.key(key)
        self.assertEqual(editor.text, "/help")
        with self.assertRaises(KeyboardInterrupt):
            editor.key("cancel")

    def test_windows_bracketed_paste_decoding(self):
        class Keys:
            def __init__(self):
                self.keys = iter("\x1b[200~")

            def getwch(self):
                return next(self.keys)

            def kbhit(self):
                return True

        with patch("erol.console.importlib.import_module", return_value=Keys()):
            self.assertEqual(key_windows(), "paste_start")

    def test_non_terminal_no_args_does_not_launch_or_create_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "unused"
            output = io.StringIO()
            with (
                contextlib.redirect_stdout(output),
                patch.object(sys.stdin, "isatty", return_value=False),
            ):
                self.assertEqual(main(["--home", str(home)]), 2)
            self.assertIn("chat", output.getvalue())
            self.assertFalse(home.exists())


if __name__ == "__main__":
    unittest.main()
