"""Projectless settings/conversation boundaries; no paid provider calls."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from erol.chat import ChatEngine
from erol.cli import main
from erol.common import ErolError
from erol.connections import Connection, ConnectionStore, Model
from erol.console import Screen, command, launch
from erol.general import GeneralEngine, ResearchTools
from erol.providers import APIAdapter, BudgetExhausted, CLIAdapter, Request, event
from erol.sources import fetch_source


class GeneralTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.home = self.base / ".erol"
        self.seen = []
        seen = self.seen

        class Provider:
            def __init__(self, connection, root):
                self.connection, self.root = connection, root

            def capabilities(self):
                return {"available": True, "stream": True}

            def models(self):
                return self.connection.models

            def cancel(self):
                pass

            def stream(self, request, **options):
                seen.append((self.root, request, options))
                if request.mode == "research":
                    self.result = options["dispatch"](
                        "read_source", {"url": "https://example.test"}
                    )
                yield event("text_delta", request, text="Synthetic answer")
                yield event("final", request, completed=True)

        self.factory = Provider

    def make(self):
        engine = GeneralEngine(self.base, self.home, factory=self.factory, fetcher=self.fetch)
        connection = engine.connections.connect("openai")
        connection.models = [Model("fixture", level=3, input_price=0.1, output_price=0.2)]
        engine.connections.save()
        return engine

    def fetch(self, url, **options):
        return {
            "url": url,
            "status": "accessed",
            "bytes": 12,
            "text": "untrusted page text",
            "evidence_type": "synthetic_source_fixture",
        }

    def test_global_settings_without_project_or_memory(self):
        engine = GeneralEngine(self.base, self.home, factory=self.factory)
        command(engine, "/connect codex")
        command(engine, "/connect openai")
        command(engine, "/language tr")
        command(engine, "/settings api_budget_usd 7")
        self.assertEqual(len(command(engine, "/providers")["providers"]), 2)
        self.assertTrue(command(engine, "/models")["profiles"])
        self.assertIsNone(command(engine, "/status")["project"])
        self.assertFalse(command(engine, "/status")["project_tools"])
        self.assertEqual(ConnectionStore(self.home).settings.api_budget_usd, 7)
        self.assertEqual(list(self.home.iterdir()), [self.home / "connections.json"])
        for name in ("diff", "tests"):
            with self.assertRaisesRegex(ErolError, "/project"):
                command(engine, "/" + name)

    def test_cancel_during_preflight_does_not_start_model(self):
        engine = self.make()

        def cancelled_plan(task):
            engine.cancel()
            return {"selection": {}}

        with patch.object(engine, "plan", side_effect=cancelled_plan):
            self.assertEqual(engine.execute("Hello")["status"], "cancelled")
        self.assertEqual(self.seen, [])
        self.assertFalse((self.home / "global").exists())

    def test_source_failure_reports_unavailable_without_raw_error(self):
        def failing(*args, **kwargs):
            raise OSError("private diagnostic fixture")

        tools = ResearchTools(threading.Event(), time.monotonic() + 60, fetcher=failing)
        with self.assertRaisesRegex(ErolError, "Source request failed"):
            tools.dispatch("read_source", {"url": "https://example.test"})
        self.assertEqual(tools.receipts[0]["status"], "unavailable")
        self.assertNotIn("private diagnostic", json.dumps(tools.receipts))

    def test_uncertain_cleanup_cannot_be_bypassed_by_scope_or_session(self):
        engine = self.make()
        engine.execute("Hello")
        identifier = engine.session_id
        engine.record["cleanup_uncertain"] = True
        project = self.base / "project"
        project.mkdir()
        for action in (
            engine.new,
            lambda: engine.resume(identifier),
            lambda: engine.execute("Hello"),
            lambda: command(engine, "/project project"),
        ):
            with self.assertRaisesRegex(ErolError, "cleanup"):
                action()

    def test_source_credentials_never_reach_fetch_or_saved_failure_receipt(self):
        fetcher = unittest.mock.Mock()
        tools = ResearchTools(threading.Event(), time.monotonic() + 60, fetcher=fetcher)
        with self.assertRaises(ErolError):
            tools.dispatch("read_source", {"url": "https://example.test/?api_key=synthetic"})
        fetcher.assert_not_called()
        self.assertEqual(tools.receipts, [])

    def test_general_cancellation_and_completion_emit_correct_status(self):
        engine = self.make()

        def interrupted(request, **options):
            yield event("text_delta", request, text="Partial answer")
            engine.cancel()
            yield event("final", request, completed=True)

        output = []
        with patch.object(self.factory, "stream", side_effect=interrupted):
            result = engine.execute("Hello", output.append)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(output[-1]["data"]["status"], "cancelled")
        self.assertFalse(result["verified"])
        self.assertEqual(engine.execute("Hello")["status"], "completed")

    def test_active_api_session_cannot_resume_or_replace_live_record(self):
        engine = self.make()
        started, release = threading.Event(), threading.Event()
        results = []

        def blocked(request, **options):
            started.set()
            release.wait(5)
            yield event("final", request, completed=True)

        with patch.object(self.factory, "stream", side_effect=blocked):
            worker = threading.Thread(target=lambda: results.append(engine.execute("Hello")))
            worker.start()
            try:
                self.assertTrue(started.wait(2))
                other = GeneralEngine(self.base, self.home, factory=self.factory)
                with self.assertRaisesRegex(ErolError, "already running"):
                    other.resume(engine.session_id)
                for action in (
                    engine.new,
                    lambda: engine.execute("Hello"),
                    lambda: engine.resume(engine.session_id),
                ):
                    with self.assertRaisesRegex(ErolError, "already running"):
                        action()
            finally:
                release.set()
                worker.join(5)
        self.assertEqual(results[0]["status"], "completed")
        self.assertFalse(engine.busy)
        other.resume(engine.session_id)

    def test_os_session_lease_blocks_duplicate_turn_and_recovers_after_release(self):
        from erol.runstore import file_lease

        engine = self.make()
        engine.execute("Hello")
        other = GeneralEngine(self.base, self.home, factory=self.factory)
        other.resume(engine.session_id)
        old = engine.sessions.load(engine.session_id)
        with file_lease(engine.sessions.directory / (engine.session_id + ".lock")):
            with self.assertRaisesRegex(ErolError, "lease"):
                other.execute("Hello", resume=True)
            self.assertEqual(old, engine.sessions.load(engine.session_id))
        self.assertEqual(other.execute("Hello", resume=True)["status"], "completed")

    def test_session_lease_is_released_when_another_process_exits(self):
        engine = self.make()
        engine.execute("Hello")
        lease = engine.sessions.directory / (engine.session_id + ".lock")
        ready = self.base / "lease-ready"
        code = (
            "import sys,time; from pathlib import Path; from erol.runstore import file_lease; "
            "lock=file_lease(Path(sys.argv[1])); lock.__enter__(); "
            "Path(sys.argv[2]).write_text('ready'); time.sleep(30)"
        )
        child = subprocess.Popen([sys.executable, "-c", code, str(lease), str(ready)])
        try:
            until = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < until:
                time.sleep(0.02)
            self.assertTrue(ready.exists())
            other = GeneralEngine(self.base, self.home, factory=self.factory)
            other.resume(engine.session_id)
            with self.assertRaisesRegex(ErolError, "lease"):
                other.execute("Hello", resume=True)
        finally:
            child.terminate()
            child.wait(timeout=5)
        self.assertEqual(other.execute("Hello", resume=True)["status"], "completed")

    def test_lease_descriptor_closes_even_if_native_unlock_fails(self):
        from erol.runstore import file_lease

        module = unittest.mock.Mock()
        module.LOCK_EX, module.LOCK_NB, module.LOCK_UN = 1, 2, 4
        method = module.locking if os.name == "nt" else module.flock
        method.side_effect = [None, OSError("synthetic unlock failure")]
        with (
            patch("erol.runstore.os.close", wraps=os.close) as close,
            patch("erol.runstore.importlib.import_module", return_value=module),
        ):
            with self.assertRaisesRegex(OSError, "unlock"):
                with file_lease(self.base / "test.lock"):
                    pass
            close.assert_called_once()
            with self.assertRaises(OSError):
                os.fstat(close.call_args[0][0])

    def test_antigravity_manual_general_model_is_rejected_without_fallback(self):
        engine = GeneralEngine(self.base, self.home, factory=self.factory)
        connection = engine.connections.connect("antigravity")
        engine.selected_model = "antigravity:" + connection.models[0].id
        with self.assertRaisesRegex(ErolError, "No eligible model"):
            engine.execute("Hello")
        self.assertTrue(engine.selected_model.startswith("antigravity:"))
        self.assertEqual(self.seen, [])

    def test_general_api_formats_omit_empty_tools_and_accept_text_models(self):
        frames = {
            "openai": [
                {"type": "response.output_text.delta", "delta": "API reply"},
                {"type": "response.completed", "response": {"output": []}},
            ],
            "anthropic": [
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": "API reply"},
                },
                {"type": "message_delta", "delta": {"stop_reason": "end_turn"}},
            ],
            "gemini": [
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "API reply"}]}, "finishReason": "STOP"}
                    ]
                }
            ],
            "compatible": [
                {"choices": [{"delta": {"content": "API reply"}, "finish_reason": "stop"}]}
            ],
        }
        for kind, packets in frames.items():
            captured = []
            engine = GeneralEngine(self.base, self.home, factory=APIAdapter)
            connection = engine.connections.connect(
                kind, base_url="http://127.0.0.1:1", key_env="EROL_FIXTURE_KEY"
            )
            engine.connections.settings.connections = [connection]
            connection.models = [
                Model("fixture", level=3, tools=False, input_price=0.1, output_price=0.2)
            ]
            engine.connections.save()

            def chunks(client, path, payload, packets=packets, captured=captured):
                captured.append(payload)
                yield from packets

            with (
                patch.object(APIAdapter, "capabilities", return_value={"available": True}),
                patch.object(APIAdapter, "discover_models", return_value={"fixture"}),
                patch.object(APIAdapter, "_chunks", chunks),
            ):
                result = engine.execute("Hello")
            self.assertEqual(result["status"], "completed", kind)
            self.assertEqual(result["answer"], "API reply")
            self.assertNotIn("tools", captured[0])
            self.assertEqual(result["usage"]["api_calls"], 1)

    def test_general_response_no_workspace_or_project_context_and_safe_persistence(self):
        engine = self.make()
        (self.base / "private-project.txt").write_text("private fixture content", "utf-8")
        with patch("erol.chat.Store") as store, patch("erol.chat.Workspace") as workspace:
            result = engine.execute("Explain arithmetic")
            store.assert_not_called()
            workspace.assert_not_called()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["answer"], "Synthetic answer")
        self.assertIsNone(result["project_id"])
        self.assertFalse(result["verified"])
        cwd, request, options = self.seen[0]
        self.assertNotEqual(cwd, self.base)
        self.assertFalse(cwd.exists())
        self.assertEqual(options["tools"], [])
        self.assertIsNone(request.native_session)
        self.assertNotIn("private fixture content", request.prompt)
        with self.assertRaisesRegex(ErolError, "no tools"):
            options["dispatch"]("write_file", {"path": "x"})
        saved = engine.sessions.load(engine.session_id)
        self.assertNotIn("Synthetic answer", json.dumps(saved))
        self.assertFalse((self.home / "state").exists())
        self.assertFalse(list(self.home.rglob("memory.db")))

    def test_skills_are_selected_automatically_and_bodies_reach_model_without_project(self):
        engine = self.make()
        output = []
        with patch("erol.chat.Store") as store, patch("erol.chat.Workspace") as workspace:
            result = engine.execute("Pazar araştırması ve rakip analizi yap", output.append)
            store.assert_not_called()
            workspace.assert_not_called()
        self.assertIn("market-research", result["selected_skills"])
        self.assertIn("# Market Research", self.seen[0][1].prompt)
        self.assertIn('"memory":[]', self.seen[0][1].prompt)
        self.assertTrue(
            any(
                item["type"] == "skills" and "market-research" in item["data"]["names"]
                for item in output
            )
        )
        self.assertEqual(self.seen[0][2]["tools"], [])
        self.assertFalse((self.home / "state").exists())
        # An unrelated simple prompt does not retain the previous task's skills.
        direct = engine.execute("Hello")
        self.assertEqual(direct["selected_skills"], [])
        self.assertNotIn("# Market Research", self.seen[-1][1].prompt)

    def test_context_omitted_skill_is_not_reported_or_sent(self):
        from erol.orchestration import Orchestrator

        engine = self.make()
        task = "Pazar araştırması ve rakip analizi yap"
        small = Orchestrator().plan(task, token_budget=120)
        self.assertTrue(small["context"]["omitted"])
        self.assertEqual(small["context"]["selected_skills"], [])
        with patch("erol.general.Orchestrator.plan", return_value=small):
            result = engine.execute(task)
        self.assertEqual(result["selected_skills"], [])
        self.assertNotIn("# Market Research", self.seen[0][1].prompt)

    def test_research_only_public_source_tool_and_receipts_not_body(self):
        engine = self.make()
        engine.mode = "research"
        result = engine.execute("Research arithmetic sources")
        self.assertEqual(result["status"], "completed")
        self.assertEqual([t["name"] for t in self.seen[0][2]["tools"]], ["read_source"])
        self.assertEqual(len(result["source_access_receipts"]), 1)
        self.assertNotIn("untrusted page text", json.dumps(engine.sessions.load(engine.session_id)))
        with self.assertRaisesRegex(ErolError, "Only public"):
            self.seen[0][2]["dispatch"]("run_command", {"argv": ["python"]})

    def test_source_count_deadline_cancellation_and_private_targets(self):
        stopped = threading.Event()
        tools = ResearchTools(stopped, time.monotonic() + 60, fetcher=self.fetch)
        for _ in range(8):
            result = json.loads(tools.dispatch("read_source", {"url": "https://example.test"}))
            self.assertTrue(result["untrusted_source"])
        with self.assertRaisesRegex(ErolError, "budget"):
            tools.dispatch("read_source", {"url": "https://example.test"})
        stopped.set()
        with self.assertRaisesRegex(ErolError, "cancelled"):
            ResearchTools(stopped, time.monotonic() + 60).dispatch(
                "read_source", {"url": "https://example.test"}
            )
        with self.assertRaises(ErolError):
            ResearchTools(threading.Event(), time.monotonic() + 60).dispatch(
                "read_source", {"url": "file:///private"}
            )
        with self.assertRaises(ErolError):
            ResearchTools(threading.Event(), time.monotonic() + 60).dispatch(
                "read_source", {"url": "https://127.0.0.1"}
            )

    def test_scope_resume_and_budget_continuation(self):
        engine = self.make()
        result = engine.execute("Explain arithmetic")
        identifier = engine.session_id
        engine.new()
        self.assertEqual(engine.resume(identifier)["mode"], "general")
        project = self.base / "project"
        project.mkdir()
        with self.assertRaises(ErolError):
            ChatEngine(project, self.home).resume(identifier)
        engine.record["usage"]["accounted_usd"] = 6
        engine._save()
        with patch("erol.general.Budget.reserve", side_effect=BudgetExhausted("budget exhausted")):

            def failing(request, **options):
                options["budget"].reserve(request.model, {"model": request.model.id})
                yield

            with patch.object(self.factory, "stream", side_effect=failing):
                result = engine.execute("Explain arithmetic", resume=True)
        self.assertEqual(result["status"], "waiting_budget")
        self.assertEqual(result["usage"]["accounted_usd"], 6)

    def test_projectless_cli_settings_and_missing_provider_no_project_state(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(
                [
                    "--project",
                    str(self.base),
                    "--home",
                    str(self.home),
                    "terminal",
                    "--command",
                    "/connect codex",
                ]
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["connection"]["kind"], "codex")
        self.assertFalse((self.home / "state").exists())
        with (
            patch.object(GeneralEngine, "providers", return_value=([], {})),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(
                main(
                    [
                        "--project",
                        str(self.base),
                        "--home",
                        str(self.home),
                        "chat",
                        "--mode",
                        "general",
                        "--prompt",
                        "Hello",
                    ]
                ),
                2,
            )
        self.assertFalse((self.home / "global").exists())

    def test_interactive_commands_and_model_survive_project_selection(self):
        project = self.base / "project"
        project.mkdir()
        output = io.StringIO()
        inputs = [
            "/connect codex",
            "/settings api_budget_usd 7",
            "/language en",
            "/model codex:gpt-6.1-sol",
            "/project project",
            "/model",
            "/status",
            "/general",
            "/model",
            "/status",
            "/exit",
        ]
        screen = Screen(output)

        def inventory(engine, refresh=False):
            models = {c.id: c.models for c in engine.connections.settings.connections if c.enabled}
            return (
                [
                    {
                        "id": c.id,
                        "kind": c.kind,
                        "available": True,
                        "model_access": "synthetic_fixture",
                    }
                    for c in engine.connections.settings.connections
                    if c.enabled
                ],
                models,
            )

        with (
            patch("erol.console.Screen", return_value=screen),
            patch("erol.console.read_prompt", side_effect=inputs),
            patch("erol.console.read_choice", return_value="/model codex:gpt-6.1-sol"),
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdout, "isatty", return_value=True),
            patch.object(ChatEngine, "providers", autospec=True, side_effect=inventory),
            patch.object(GeneralEngine, "providers", autospec=True, side_effect=inventory),
            patch("erol.console.run_task") as task,
        ):
            self.assertEqual(launch(self.base, self.home), 0)
            task.assert_not_called()
        self.assertIn("No project selected · general conversation", output.getvalue())
        self.assertIn(str(project), output.getvalue())
        self.assertEqual(ConnectionStore(self.home).settings.api_budget_usd, 7)
        # Selection, two menus and two status views all expose the retained preference.
        self.assertEqual(output.getvalue().count("Model: codex:gpt-6.1-sol"), 5)

    def test_native_general_readonly_and_research_web_tools(self):
        for kind in ("codex", "claude"):
            for mode in ("general", "research"):
                captures = []
                connection = Connection("fixture", kind)

                def observed(argv, cwd, captures=captures, kind=kind, **options):
                    captures.append(argv)
                    data = (
                        {"type": "turn.completed"}
                        if kind == "codex"
                        else {"type": "result", "subtype": "success", "is_error": False}
                    )
                    options["on_line"](json.dumps(data))
                    return {"exit_code": 0, "reason": None}

                with (
                    patch("erol.providers.command_prefix", return_value=[sys.executable]),
                    patch("erol.providers.observe", side_effect=observed),
                ):
                    result = list(
                        CLIAdapter(connection, self.base).stream(
                            Request(
                                "fixture",
                                connection,
                                Model("fixture"),
                                "Hello",
                                role="assistant",
                                mode=mode,
                            )
                        )
                    )
                self.assertTrue(result[-1]["data"]["completed"])
                argv = captures[0]
                if kind == "codex":
                    self.assertIn("read-only", argv)
                    self.assertIn("features.shell_tool=false", argv)
                    self.assertIn(
                        'web_search="live"' if mode == "research" else 'web_search="disabled"', argv
                    )
                    self.assertNotIn("--output-schema", argv)
                else:
                    self.assertEqual(
                        argv[argv.index("--tools") + 1],
                        "WebSearch,WebFetch" if mode == "research" else "",
                    )
                    self.assertIn("--strict-mcp-config", argv)

    def test_unrecognized_native_projectless_restrictions_fail_closed(self):
        with patch("erol.providers.command_prefix", return_value=[sys.executable]):
            provider = CLIAdapter(Connection("fixture", "codex"), self.base)
        with patch("erol.providers.probe", return_value="unknown_feature stable true"):
            with self.assertRaisesRegex(ErolError, "shell disabling"):
                provider.projectless_capabilities("general")
        with patch(
            "erol.providers.probe", side_effect=["shell_tool stable true", "no web feature"]
        ):
            with self.assertRaisesRegex(ErolError, "web search"):
                provider.projectless_capabilities("research")


class SourceTextTests(unittest.TestCase):
    def test_text_opt_in_extracts_html_without_changing_default_receipts(self):
        class Response:
            status = 200

            def __init__(self):
                self.chunks = [b"<p>Observed source</p><script>hidden script</script>", b""]

            def getheader(self, name, default=None):
                return "text/html" if name == "Content-Type" else default

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
            receipt = fetch_source("https://example.test", deadline=time.monotonic() + 10)
            text = fetch_source(
                "https://example.test", deadline=time.monotonic() + 10, include_text=True
            )
        self.assertNotIn("text", receipt)
        self.assertEqual(text["text"], "Observed source")
        self.assertEqual(receipt["content_sha256"], text["content_sha256"])
