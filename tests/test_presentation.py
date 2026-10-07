"""Human views and editing must preserve machine contracts and layout boundaries."""

import copy
import io
import unittest
from unittest.mock import Mock

from erol.console import Editor, Screen, key_windows
from erol.display import Display, cells, wrap
from erol.presentation import present


class PresentationTests(unittest.TestCase):
    def test_human_views_preserve_structured_data_and_report_observed_failure(self):
        samples = [
            {
                "project": None,
                "mode": "research",
                "session": "session-fixture",
                "status": "waiting_budget",
            },
            {
                "providers": [
                    {"id": "fixture", "kind": "openai", "available": False, "reason": "Missing key"}
                ]
            },
            {"model": "fixture:small"},
            {"settings": {"api_budget_usd": 5, "policy": "balanced", "connections": []}},
            {
                "tests": [
                    {
                        "name": "acceptance",
                        "argv": ["python", "check.py"],
                        "passed": False,
                        "exit_code": 1,
                        "output": "observed failure",
                    }
                ]
            },
            {"usage": {"budget_usd": 5, "accounted_usd": 1, "api_calls": 1, "remaining_usd": 4}},
        ]
        for sample in samples:
            original = copy.deepcopy(sample)
            text = present(sample, "en")
            self.assertNotIn('"project":', text)
            self.assertEqual(sample, original)
        tests = present(samples[4], "tr")
        self.assertIn("BAŞARISIZ", tests)
        self.assertIn("observed failure", tests)
        self.assertNotIn("GEÇTİ", tests)
        self.assertIn("unverified", present({"tests": []}, "en"))
        self.assertIn("$5.0000", present(samples[5], "en"))

    def test_failed_tool_is_visible_while_success_results_are_quiet(self):
        output = io.StringIO()
        screen = Screen(output)
        screen.set_language("en")
        screen.event(
            {
                "type": "tool_result",
                "data": {"tool": "read_source", "summary": "Source unavailable", "is_error": True},
            }
        )
        self.assertIn("Error", output.getvalue())
        self.assertIn("Source unavailable", output.getvalue())
        before = output.getvalue()
        screen.event({"type": "tool_result", "data": {"tool": "read_source", "is_error": False}})
        self.assertEqual(before, output.getvalue())

    def test_editing_words_lines_and_draft_history(self):
        editor = Editor(["older prompt"], ["/help", "/connect codex", "/connect claude"])
        editor.insert("first line\nsecond word")
        editor.key("erase_word")
        self.assertEqual(editor.text, "first line\nsecond ")
        editor.key("up")
        self.assertEqual(editor.cursor, 7)
        editor.key("erase_end")
        self.assertEqual(editor.text, "first l\nsecond ")
        editor.key("down")
        self.assertEqual(editor.cursor, 15)
        editor.key("clear_input")
        editor.insert("draft")
        editor.key("up")
        self.assertEqual(editor.text, "older prompt")
        editor.key("down")
        self.assertEqual(editor.text, "draft")
        editor.key("clear_input")
        editor.insert("/connect c")
        self.assertEqual(editor.suggestions(), ["/connect codex", "/connect claude"])
        editor.key("tab")
        self.assertEqual(editor.text, "/connect codex")
        editor.key("tab")
        self.assertEqual(editor.text, "/connect claude")
        reader = Mock()
        for key, action in (("\x17", "erase_word"), ("\x0b", "erase_end")):
            reader.getwch.return_value = key
            self.assertEqual(key_windows(reader), action)

    def test_compact_word_wrap_suggestions_and_resize_are_bounded(self):
        self.assertEqual(wrap("one two three", 8), ["one two", "three"])
        self.assertEqual(wrap("    abcdefghijk", 8), ["    abcd", "efghijk"])
        display = Display()
        display.append("EROL · fixture\n" + "one two three " * 25)
        display.editor = ("/con", 4)
        display.suggestions = ["/connect codex", "/connect claude"]
        full = display.frame(110, 30, "Ready")
        display.compact = True
        compact = display.frame(110, 30, "Ready")
        self.assertIn(" │ ", full.lines[0])
        self.assertNotIn(" │ ", compact.lines[0])
        self.assertIn("Tab › /connect", compact.lines[-2])
        self.assertEqual(full.cursor, compact.cursor)
        for columns, rows in ((110, 30), (45, 14), (12, 6), (8, 1)):
            frame = display.frame(columns, rows, "Ready")
            self.assertEqual(len(frame.lines), rows)
            self.assertTrue(all(cells(line) < columns for line in frame.lines))
