"""Guided navigation must be reversible and must never start model work."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from erol.choices import Choice
from erol.connections import Model
from erol.console import (
    Editor,
    Screen,
    command,
    escape_key,
    interactive_command,
    read_choice,
    read_prompt,
    run_task,
)
from erol.display import SGR, Display, cells
from erol.general import GeneralEngine
from erol.terminal import render_logo


class ChoiceTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{"label": f"Model {i}", "value": str(i)} for i in range(1, 61)]

    def test_arrows_current_choice_and_numbered_selection(self):
        choice = Choice(self.rows, "12")
        self.assertEqual(choice.key("enter"), "12")
        choice.key("down")
        self.assertEqual(choice.key("enter"), "13")
        for key in ("end", "down"):
            choice.key(key)
        self.assertEqual(choice.key("enter"), "60")
        choice.key("home")
        choice.key("up")
        self.assertEqual(choice.key("enter"), "1")
        for key in "29":
            choice.key(key)
        self.assertEqual(choice.key("enter"), "29")

    def test_invalid_numbers_do_not_choose_or_overflow(self):
        choice = Choice(self.rows)
        for key in "999999999999":
            choice.key(key)
        self.assertEqual(len(choice.number), 6)
        self.assertIsNone(choice.key("enter"))
        choice.key("down")
        self.assertEqual(choice.key("enter"), "2")

    def test_paste_cannot_select_or_move_menu(self):
        choice = Choice(self.rows)
        for key in ("paste_start", "2", "down", "enter", "paste_end"):
            self.assertIsNone(choice.key(key))
        self.assertEqual(choice.key("enter"), "1")

    def test_scrolling_menu_keeps_selected_row_visible(self):
        choice = Choice(self.rows)
        choice.key("end")
        lines = choice.lines("Models", "Enter / Esc", 10)
        self.assertEqual(len(lines), 10)
        self.assertIn("› 60. Model 60", lines)
        choice.key("page_up")
        self.assertEqual(choice.key("enter"), "55")
        self.assertIn("55. Model 55", choice.lines("Models", "Esc", 2)[0])

    def test_completion_cycles_without_sending_commands(self):
        editor = Editor([], ["/model", "/models", "/motion"])
        editor.insert("/mo")
        editor.key("tab")
        self.assertEqual(editor.text, "/model")
        editor.key("tab")
        self.assertEqual(editor.text, "/models")
        editor.key("tab")
        self.assertEqual(editor.text, "/motion")
        editor.key("escape")
        self.assertEqual(editor.text, "")
        self.assertEqual(escape_key("\x1b"), "escape")

    def test_search_preserves_values_and_handles_turkish_and_model_digits(self):
        choice = Choice(
            [
                {"label": "İstanbul uygulaması", "value": "/my-projects 8"},
                {"label": "gpt-6.1-sol", "value": "/model codex:gpt-6.1-sol"},
            ]
        )
        for key in "istanbul":
            choice.key(key)
        self.assertEqual(choice.key("enter"), "/my-projects 8")
        for _ in "istanbul":
            choice.key("backspace")
        for key in "gpt-6.1":
            choice.key(key)
        self.assertEqual(choice.key("enter"), "/model codex:gpt-6.1-sol")

    def test_search_empty_results_cannot_select_and_recovers(self):
        choice = Choice(self.rows)
        choice.key("z")
        self.assertIsNone(choice.key("enter"))
        choice.key("end")
        self.assertTrue(choice.lines("Models", "Search", 10))
        choice.key("backspace")
        self.assertEqual(choice.key("enter"), "1")


class SetupTests(unittest.TestCase):
    def test_pasted_controls_cannot_escape_form_into_next_prompt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            engine = GeneralEngine(root, Path(temporary) / "external-home")
            for field in ("/project", "/rename"):
                for control in ("cancel", "escape"):
                    screen = Screen(io.StringIO())
                    screen.rich = True
                    screen.pending_keys = [
                        "paste_start",
                        control,
                        "/",
                        "e",
                        "x",
                        "i",
                        "t",
                        "enter",
                        "paste_end",
                        "escape",
                    ]
                    with (
                        patch(
                            "erol.console.input_session",
                            return_value=contextlib.nullcontext((0, None)),
                        ),
                        patch.object(screen, "refresh"),
                    ):
                        self.assertEqual(interactive_command(engine, field, screen), {})
                    self.assertEqual(screen.pending_keys, [])

    def test_cancel_connection_keeps_task_without_running_or_creating_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            home = Path(temporary) / "external-home"
            engine, screen = GeneralEngine(root, home), Screen(io.StringIO())
            with (
                patch("erol.console.read_choice", return_value=None),
                patch.object(engine, "execute") as execute,
            ):
                self.assertEqual(run_task(engine, "Fix pagination", screen), {})
            execute.assert_not_called()
            self.assertEqual(screen.draft, "Fix pagination")
            self.assertFalse(home.exists())

    def test_task_draft_is_restored_in_editor_and_empty_enter_opens_navigation(self):
        screen = Screen(io.StringIO())
        screen.rich, screen.draft = True, "Fix pagination"
        screen.pending_keys = ["enter"]
        with (
            patch("erol.console.input_session", return_value=contextlib.nullcontext((0, None))),
            patch.object(screen, "refresh"),
        ):
            self.assertEqual(read_prompt(screen, [], []), "Fix pagination")
        self.assertEqual(screen.draft, "")
        self.assertEqual(Editor([], []).key("enter"), "")

    def test_plain_picker_search_and_cancelled_forms_are_reversible(self):
        screen = Screen(io.StringIO())
        with patch("builtins.input", side_effect=["istanbul", "1"]):
            self.assertEqual(
                read_choice(
                    screen,
                    "Projects",
                    [
                        {"label": "İstanbul", "value": "/my-projects 8"},
                        {"label": "Ankara", "value": "/my-projects 2"},
                    ],
                ),
                "/my-projects 8",
            )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            home = Path(temporary) / "external-home"
            engine = GeneralEngine(root, home)
            for text in ("/project", "/rename"):
                with patch("erol.console.read_prompt", return_value=""):
                    self.assertEqual(interactive_command(engine, text, screen), {})
            self.assertFalse(home.exists())

    def test_start_and_connection_choices_do_not_probe_or_create_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            home = Path(temporary) / "external-home"
            engine = GeneralEngine(root, home)
            with patch.object(engine, "providers", side_effect=AssertionError("no probes")):
                self.assertIn(
                    "/connect", {r["value"] for r in command(engine, "/start")["menu_choices"]}
                )
                self.assertTrue(command(engine, "/connect")["connection_choices"])
            self.assertFalse(home.exists())

    def test_connection_selection_preserves_profiles_and_manual_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            engine = GeneralEngine(root, Path(temporary) / "external-home")
            engine.connections.connect("codex", "work")
            connection = engine.connections.get("work")
            connection.models = [Model.load({"id": "custom", "level": 3})]
            engine.connections.save()
            engine.selected_model = "work:custom"
            with patch.object(engine, "providers", side_effect=AssertionError("no probes")):
                rows = command(engine, "/connect")["connection_choices"]
                selected = next(row["value"] for row in rows if row["value"] == "/connect use work")
                command(engine, selected)
            self.assertEqual(engine.connections.settings.preferred_connection, "work")
            self.assertEqual(engine.selected_model, "work:custom")
            self.assertEqual(engine.connections.get("work").models[0].id, "custom")


class PickerTests(unittest.TestCase):
    def test_pasted_cancel_cannot_escape_payload_into_next_prompt(self):
        for control in ("cancel", "escape"):
            screen = Screen(io.StringIO())
            screen.rich = True
            screen.pending_keys = [
                "paste_start",
                control,
                "/",
                "e",
                "x",
                "i",
                "t",
                "enter",
                "paste_end",
                "escape",
            ]
            with (
                patch("erol.console.input_session", return_value=contextlib.nullcontext((0, None))),
                patch.object(screen, "refresh"),
                patch(
                    "erol.console.key_windows", side_effect=AssertionError("payload not consumed")
                ),
            ):
                self.assertIsNone(read_choice(screen, "Pick", [{"label": "One", "value": "1"}]))
            self.assertEqual(screen.pending_keys, [])
            self.assertIsNone(screen.display.overlay)

    def test_cancel_and_eof_restore_transcript_and_overlay(self):
        for key in ("escape", "cancel", "eof"):
            screen = Screen(io.StringIO())
            screen.rich = True
            screen.display.text = "\n".join(str(i) for i in range(100))
            screen.display.scroll = 4
            with (
                patch("erol.console.input_session", return_value=contextlib.nullcontext((0, None))),
                patch("erol.console.os.name", "nt"),
                patch("erol.console.key_windows", return_value=key),
                patch.object(screen, "refresh"),
            ):
                if key == "eof":
                    with self.assertRaises(EOFError):
                        read_choice(screen, "Pick", [{"label": "One", "value": "1"}])
                else:
                    self.assertIsNone(read_choice(screen, "Pick", [{"label": "One", "value": "1"}]))
            self.assertIsNone(screen.display.overlay)
            self.assertEqual(screen.display.scroll, 4)
            self.assertTrue(screen.display.text.endswith("99"))

    def test_plain_picker_selects_or_returns_without_control_sequences(self):
        for value, expected in (("2", "b"), ("", None), ("99", None), ("/exit", None)):
            output = io.StringIO()
            screen = Screen(output)
            with patch("builtins.input", return_value=value):
                self.assertEqual(
                    read_choice(
                        screen,
                        "Pick",
                        [{"value": "a", "label": "First"}, {"value": "b", "label": "Second"}],
                    ),
                    expected,
                )
            self.assertNotIn("\x1b", output.getvalue())

    def test_untrusted_choice_labels_cannot_inject_terminal_controls(self):
        screen = Screen(io.StringIO())
        screen.rich = True
        overlays = []
        with (
            patch("erol.console.input_session", return_value=contextlib.nullcontext((0, None))),
            patch("erol.console.os.name", "nt"),
            patch("erol.console.key_windows", return_value="escape"),
            patch.object(
                screen, "refresh", side_effect=lambda: overlays.append(screen.display.overlay)
            ),
        ):
            read_choice(screen, "Pick", [{"label": "name\x1b[2J\nnext", "value": "1"}])
        self.assertNotIn("\x1b", "\n".join(overlays[0]))
        self.assertIn("next", "\n".join(overlays[0]))


class InteractiveNavigationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.engine = GeneralEngine(self.root, self.root / "external")
        self.screen = Screen(io.StringIO())
        self.screen.rich = True

    def test_headless_menu_is_data_only_and_creates_no_state(self):
        with patch.object(self.engine, "providers") as providers:
            result = command(self.engine, "/menu")
        providers.assert_not_called()
        self.assertIn("/model", [r["value"] for r in result["menu_choices"]])
        self.assertFalse(self.engine.home.exists())

    def test_menu_to_model_picker_uses_current_inventory_and_no_turn(self):
        self.engine.connections.connect("codex")
        profiles = [Model("test-small"), Model("test-large")]
        with (
            patch.object(
                self.engine,
                "providers",
                return_value=(
                    [{"id": "codex", "kind": "codex", "available": True}],
                    {"codex": profiles},
                ),
            ),
            patch(
                "erol.console.read_choice", side_effect=["/model", "/model codex:test-large"]
            ) as picker,
            patch.object(self.engine, "execute") as execute,
        ):
            result = interactive_command(self.engine, "/menu", self.screen)
        execute.assert_not_called()
        self.assertEqual(result["model"], "codex:test-large")
        self.assertEqual(picker.call_args_list[1].args[2][0]["value"], "/model auto")
        self.assertFalse((self.engine.home / "global/chat").exists())

    def test_model_picker_cancel_preserves_manual_preference(self):
        self.engine.selected_model = "codex:test"
        with (
            patch.object(
                self.engine,
                "providers",
                return_value=(
                    [{"id": "codex", "kind": "codex", "available": True}],
                    {"codex": [Model("test")]},
                ),
            ),
            patch("erol.console.read_choice", return_value=None),
        ):
            self.assertEqual(interactive_command(self.engine, "/model", self.screen), {})
        self.assertEqual(self.engine.selected_model, "codex:test")

    def test_view_menu_restores_full_layout(self):
        self.screen.display.compact = True
        with patch("erol.console.read_choice", return_value="/view full") as picker:
            self.assertEqual(
                interactive_command(self.engine, "/menu", self.screen), {"view": "full"}
            )
        self.assertIn("/view full", [r["value"] for r in picker.call_args.args[2]])

    def test_old_chat_pagination_keeps_number_bound_to_displayed_page(self):
        rows = [{"id": f"session-{i}", "title": f"Chat {i}"} for i in range(50)]
        with (
            patch.object(self.engine.sessions, "list", return_value=rows),
            patch("erol.console.read_choice", side_effect=["/chats page 2", None]) as picker,
        ):
            self.assertEqual(interactive_command(self.engine, "/chats", self.screen), {})
        next_page = picker.call_args_list[0].args[2][-1]
        self.assertEqual(next_page["value"], "/chats page 2")
        second = picker.call_args_list[1].args[2]
        self.assertEqual(second[0]["value"], "/chats 1")
        self.assertEqual(second[-2]["value"], "/chats page 1")

    def test_preferences_are_visible_in_narrow_and_wide_frames(self):
        self.engine.selected_model, self.engine.selected_effort = "codex:test", "high"
        self.screen.configure_connections(self.engine.connections.settings, "my-project")
        self.screen.configure_selection(self.engine)
        for width in (50, 110):
            frame = self.screen.display.frame(width, 30, "Ready")
            self.assertIn("codex:test · high", SGR.sub("", frame.lines[-3]))


class MantisTests(unittest.TestCase):
    def test_all_phases_preserve_silhouette_and_static_original(self):
        for width in (8, 18, 24, 44):
            original = render_logo(width, bright=True)
            occupancy = SGR.sub("", original)
            for phase in range(24):
                self.assertEqual(
                    SGR.sub("", render_logo(width, bright=True, pose=phase)), occupancy
                )
                self.assertEqual(
                    render_logo(width, color=False, pose=phase), render_logo(width, color=False)
                )
            self.assertEqual(original, render_logo(width, bright=True, pose=24))
            self.assertNotEqual(original, render_logo(width, bright=True, pose=12))

    def test_motion_off_and_reading_editor_stay_still(self):
        display = Display()
        display.editor = ("hello", 5)
        display.append("response\n")
        display.motion = False
        first = display.frame(110, 30, "Ready", 1)
        second = display.frame(110, 30, "Ready", 12)
        self.assertEqual(first, second)

    def test_overlay_resize_is_bounded_without_destroying_conversation(self):
        display = Display()
        display.append("saved response")
        display.overlay = ["Choose", "› model 漢字 " * 40] * 20
        for columns, rows in ((110, 30), (45, 14), (80, 18), (20, 6)):
            frame = display.frame(columns, rows, "Ready")
            self.assertEqual(len(frame.lines), rows)
            self.assertTrue(all(cells(line) < columns for line in frame.lines))
        display.overlay = None
        self.assertIn("saved response", SGR.sub("", display.frame(110, 30, "Ready").lines[0]))

    def test_worker_protocol_is_quiet_but_answers_and_errors_are_visible(self):
        output = io.StringIO()
        screen = Screen(output)
        screen.event({"type": "text_delta", "role": "implementer", "data": {"text": '{"summary":'}})
        screen.event({"type": "text_delta", "role": "reviewer", "data": {"text": '{"approved":'}})
        self.assertEqual(output.getvalue(), "")
        screen.event({"type": "text_delta", "role": "assistant", "data": {"text": "Useful answer"}})
        screen.event({"type": "error", "role": "implementer", "data": {"message": "check failed"}})
        self.assertIn("Useful answer", output.getvalue())
        self.assertIn("check failed", output.getvalue())


if __name__ == "__main__":
    unittest.main()
