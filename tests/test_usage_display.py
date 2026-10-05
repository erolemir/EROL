"""Subscription tokens and API estimates stay distinct in human terminal views."""

import contextlib
import copy
import ctypes
import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from erol.connections import Connection, Settings
from erol.console import Screen, execute_task, windows_console_title
from erol.presentation import present


def usage_event(source="native_cli_usage", counts=None, **extra):
    return {
        "type": "usage",
        "connection": "fixture",
        "model": "small",
        "data": {
            "source": source,
            "counts": counts
            if counts is not None
            else {
                "input_tokens": 120,
                "output_tokens": 30,
            },
            **extra,
        },
    }


class UsageDisplayTests(unittest.TestCase):
    def screen(self):
        screen = Screen(io.StringIO())
        screen.set_language("en")
        return screen

    def test_cli_completion_shows_tokens_and_unknown_quota_without_dollars(self):
        screen = self.screen()
        screen.event(
            {
                "type": "routing",
                "data": {
                    "role": "assistant",
                    "connection": "fixture",
                    "model": "small",
                    "effort": "low",
                    "reason": "fixture",
                    "transport": "cli",
                },
            }
        )
        screen.event(usage_event())
        screen.event(
            {
                "type": "status",
                "data": {
                    "status": "completed",
                    "project_tools": False,
                    "usage": {"budget_usd": 5, "accounted_usd": 0, "api_calls": 0},
                },
            }
        )
        self.assertIn("in 120 / out 30 / total 150", screen.status)
        self.assertIn("CLI quota unknown", screen.status)
        self.assertNotIn("$", screen.stream.getvalue())
        self.assertEqual(screen.display.context[1], "CLI · 150 token")

    def test_cli_only_startup_and_sidebar_hide_api_budget(self):
        screen = self.screen()
        settings = Settings(
            connections=[
                Connection("fixture", "codex"),
                Connection("disabled-api", "openai", enabled=False),
            ]
        )
        screen.configure_connections(settings, "general")
        text = screen.t("general_header", resources=screen.resources)
        self.assertIn("CLI subscription", text)
        self.assertNotIn("$", text)
        self.assertNotIn("$", screen.display.context[1])
        settings.connections[1].enabled = True
        screen.configure_connections(settings, "general")
        self.assertIn("$5", screen.resources)
        screen.configure_connections(Settings(), "general")
        self.assertNotIn("$", screen.resources)

    def test_usage_cli_view_preserves_machine_budget_and_reports_missing_counts(self):
        result = {
            "usage": {"budget_usd": 5, "accounted_usd": 0, "api_calls": 0, "remaining_usd": 5},
            "events": [usage_event(counts={})],
        }
        original = copy.deepcopy(result)
        text = present(result, "tr")
        self.assertNotIn("$", text)
        self.assertIn("giriş ? / çıkış ? / toplam ?", text)
        self.assertIn("CLI kotası bilinmiyor", text)
        self.assertEqual(result, original)

    def test_api_and_mixed_usage_keep_separate_counts_and_estimates(self):
        api = usage_event(
            "api", {"input_tokens": 60, "output_tokens": 10}, estimated_cost_usd=0.012
        )
        result = {
            "usage": {"budget_usd": 5, "accounted_usd": 0.012, "api_calls": 1},
            "events": [usage_event(), api],
        }
        text = present(result, "en")
        self.assertIn("CLI · tokens in 120 / out 30 / total 150", text)
        self.assertIn("API · tokens in 60 / out 10 / total 70", text)
        self.assertIn("$0.0120", text)
        screen = self.screen()
        screen.transport = "cli"
        screen.event(usage_event())
        screen.event(
            {
                "type": "status",
                "data": {
                    "status": "completed",
                    "usage": result["usage"],
                },
            }
        )
        self.assertIn("CLI", screen.status)
        self.assertIn("$0.0120", screen.status)
        self.assertIn("API · tokens in ?", screen.status)

    def test_budget_reservation_without_token_report_still_shows_api_evidence(self):
        text = present(
            {"usage": {"budget_usd": 5, "api_calls": 0, "pending_reserved_usd": 0.3}}, "en"
        )
        self.assertIn("$0.3000", text)
        self.assertIn("in ? / out ? / total ?", text)
        self.assertIn("Not the final invoice", text)

    def test_cli_model_catalog_hides_api_profile_prices(self):
        text = present(
            {
                "providers": [{"id": "fixture", "kind": "codex", "available": True}],
                "profiles": {
                    "fixture": [{"id": "small", "level": 1, "input_price": 1, "output_price": 2}]
                },
            },
            "en",
        )
        self.assertNotIn("$", text)
        self.assertIn("CLI subscription", text)

    def test_each_turn_resets_usage_while_resume_keeps_api_accounting(self):
        class Engine:
            import threading

            stopped = threading.Event()
            record = {"usage": {"api_calls": 1, "accounted_usd": 0.4}}

            def execute(self, task, emit, resume=False):
                return {"status": "completed"}

            def cancel(self):
                self.stopped.set()

        screen = self.screen()
        screen.usage_events = [usage_event()]
        screen.transport = "cli"
        screen.tokens = 150
        with patch.object(screen, "refresh"):
            execute_task(Engine(), "fixture", screen)
            self.assertEqual(screen.usage_events, [])
            self.assertEqual(screen.tokens, 0)
            self.assertEqual(screen.usage, {})
            execute_task(Engine(), "fixture", screen, resume=True)
            self.assertEqual(screen.usage["accounted_usd"], 0.4)

    def test_windows_title_restored_after_normal_exit_or_worker_error(self):
        def read_title(buffer, size):
            buffer.value = "claude"
            return 6

        for failure in (False, True):
            kernel = Mock()
            kernel.GetConsoleTitleW.side_effect = read_title
            kernel.SetConsoleTitleW.return_value = 1
            with patch.object(ctypes, "WinDLL", return_value=kernel, create=True):
                try:
                    with windows_console_title() as changed:
                        self.assertTrue(changed)
                        if failure:
                            raise RuntimeError("worker stopped")
                except RuntimeError:
                    self.assertTrue(failure)
            self.assertEqual(kernel.SetConsoleTitleW.call_args_list, [call("EROL"), call("claude")])

    def test_resumed_api_stream_preserves_previously_accounted_cost(self):
        class Engine:
            import threading

            stopped = threading.Event()
            record = {
                "usage": {"api_calls": 1, "accounted_usd": 2.0, "unreported_reserved_usd": 0.3}
            }

            def execute(self, task, emit, resume=False):
                emit(usage_event("api", estimated_cost_usd=0.5))
                return {"status": "completed"}

            def cancel(self):
                self.stopped.set()

        screen = self.screen()
        execute_task(Engine(), "fixture", screen, resume=True)
        self.assertEqual(screen.usage["accounted_usd"], 2.5)
        self.assertEqual(screen.usage["unreported_reserved_usd"], 0.3)
        self.assertIn("$2.5000", screen.display.context[1])

    def test_unreported_api_tokens_account_for_reserved_estimate_during_stream(self):
        screen = self.screen()
        screen.transport = "api"
        screen.event(
            usage_event(
                "api",
                counts={},
                estimated_cost_usd=None,
                unreported_reserved_usd=0.3,
                billing_evidence="reserved_estimate_only",
            )
        )
        self.assertEqual(screen.usage["accounted_usd"], 0.3)
        self.assertEqual(screen.usage["unreported_reserved_usd"], 0.3)
        screen.event({"type": "status", "data": {"status": "completed", "usage": screen.usage}})
        self.assertIn("reserved estimate $0.3000", screen.status)
        self.assertIn("in ? / out ? / total ?", screen.status)

    def test_windows_title_failure_keeps_terminal_usable(self):
        with patch.object(ctypes, "WinDLL", side_effect=OSError("unavailable"), create=True):
            with windows_console_title() as changed:
                self.assertFalse(changed)
        kernel = Mock()
        kernel.GetConsoleTitleW.return_value = 0
        with patch.object(ctypes, "WinDLL", return_value=kernel, create=True):
            with windows_console_title() as changed:
                self.assertFalse(changed)
        kernel.SetConsoleTitleW.assert_not_called()

    def test_windows_repaint_reasserts_owned_title_after_provider_events(self):
        screen = self.screen()
        screen.rich, screen.active, screen.owns_windows_title = True, True, True
        for item in (
            {
                "type": "routing",
                "data": {
                    "role": "assistant",
                    "connection": "fixture",
                    "model": "small",
                    "effort": "low",
                    "reason": "fixture",
                    "transport": "cli",
                },
            },
            {"type": "status", "data": {"status": "completed", "usage": {}}},
            {"type": "text_delta", "data": {"text": "\x1b]2;claude\x07answer"}},
        ):
            screen.stream.seek(0)
            screen.stream.truncate()
            screen.event(item)
            self.assertIn("\x1b]2;EROL\x07", screen.stream.getvalue())
            self.assertNotIn("\x1b]2;claude\x07", screen.stream.getvalue())
        screen.stream.seek(0)
        screen.stream.truncate()
        screen.refresh()
        self.assertEqual(screen.stream.getvalue().count("\x1b]2;EROL\x07"), 1)
        screen.close()
        screen.stream.seek(0)
        screen.stream.truncate()
        screen.refresh()
        self.assertEqual(screen.stream.getvalue(), "")

    def test_title_reassertion_is_absent_in_plain_or_unowned_posix_views(self):
        for rich, active, owned in ((False, False, True), (True, True, False)):
            screen = self.screen()
            screen.rich, screen.active, screen.owns_windows_title = rich, active, owned
            screen.refresh()
            screen.write("plain fixture")
            self.assertNotIn("\x1b]2;", screen.stream.getvalue())

    def test_failed_native_title_capture_does_not_take_unrestorable_ownership(self):
        screen = self.screen()
        screen.rich = True
        with (
            patch("erol.console.os", SimpleNamespace(name="nt")),
            patch("erol.console.windows_console_title", return_value=contextlib.nullcontext(False)),
        ):
            try:
                screen.setup()
                self.assertFalse(screen.owns_windows_title)
                screen.refresh()
            finally:
                screen.close()
        self.assertNotIn("\x1b]2;", screen.stream.getvalue())
