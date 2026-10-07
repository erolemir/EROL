"""The logo is a visual command, with no project state or JSON side effects."""

import contextlib
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from erol.cli import main
from erol.console import Screen, key_windows, read_prompt
from erol.display import SGR, Display, cells
from erol.terminal import render_logo


class ScreenIsolationTests(unittest.TestCase):
    def test_windows_vt_backspace_erases_typed_text(self):
        from erol.console import Editor

        reader = unittest.mock.Mock()
        reader.getwch.return_value = "\x7f"
        editor = Editor([], [])
        editor.insert("abc")
        self.assertEqual(key_windows(reader), "backspace")
        editor.key(key_windows(reader))
        self.assertEqual(editor.text, "ab")

    def test_owned_screen_is_cleared_and_shell_restored(self):
        output = io.StringIO()
        screen = Screen(output)
        screen.rich = True
        screen.active = True
        with patch(
            "erol.console.shutil.get_terminal_size", return_value=os.terminal_size((110, 30))
        ):
            try:
                screen.setup()
                self.assertIn("\x1b[?1049h\x1b[2J", output.getvalue())
            finally:
                screen.close()
        self.assertIn("\x1b[?1049l", output.getvalue())
        self.assertFalse(screen.animation.is_alive())

        before = output.getvalue()
        screen.refresh()
        self.assertEqual(output.getvalue(), before)

    def test_resize_clears_old_sidebar_and_restores_input(self):
        output = io.StringIO()
        screen = Screen(output)
        screen.rich = True
        screen.active = True
        screen.display.append("a long response " * 20)
        screen.display.editor = ("/help", 5)
        with patch(
            "erol.console.shutil.get_terminal_size", return_value=os.terminal_size((110, 30))
        ):
            screen.refresh()
        self.assertIn("│", output.getvalue())
        output.seek(0)
        output.truncate()
        with patch(
            "erol.console.shutil.get_terminal_size", return_value=os.terminal_size((45, 14))
        ):
            screen.refresh()
        self.assertIn("\x1b[2J", output.getvalue())
        self.assertNotIn("│", output.getvalue())
        self.assertIn("erol › /help", output.getvalue())

    def test_no_color_keeps_plain_output_without_animation(self):
        output = io.StringIO()
        with (
            patch.object(output, "isatty", return_value=True),
            patch.dict(os.environ, {"NO_COLOR": "1"}),
        ):
            screen = Screen(output)
            screen.setup()
            screen.write("plain\n")
            screen.close()
        self.assertEqual(output.getvalue(), "plain\n")
        self.assertIsNone(screen.animation)

    def test_input_mode_restored_when_cleanup_redraw_fails(self):
        screen = Screen(io.StringIO())
        screen.rich = True
        mode = unittest.mock.MagicMock()
        with (
            patch("erol.console.os.name", "nt"),
            patch("erol.console.windows_console_mode", return_value=mode),
            patch("erol.console.WindowsKeys"),
            patch("erol.console.sys.stdin.fileno", return_value=0),
            patch.object(screen, "edit", side_effect=OSError("closed output")),
        ):
            with self.assertRaisesRegex(OSError, "closed output"):
                read_prompt(screen, [], [])
        mode.__exit__.assert_called_once()


class SidebarLayoutTests(unittest.TestCase):
    def test_long_unicode_output_and_input_never_enter_logo_cells(self):
        display = Display()
        display.append(("漢字\tuzun metin e\u0301 " * 40) + "\nlast line")
        text = "第一 satır\n" + "x" * 160 + "\nüçüncü"
        display.editor = (text, len(text))
        frame = display.frame(110, 30, "Hazır")
        self.assertEqual(len(frame.lines), 30)
        self.assertTrue(all(cells(line) <= 109 for line in frame.lines))
        for line in frame.lines[:23]:
            left, _, _ = SGR.sub("", line).partition(" │ ")
            self.assertEqual(cells(left), 84)
        row, col = frame.cursor
        self.assertTrue(25 <= row <= 27)
        self.assertTrue(1 <= col < 110)

    def test_animation_moves_only_the_sidebar_while_preserving_cursor(self):
        display = Display()
        display.append("response\n")
        display.editor = ("/project", 4)
        first = display.frame(110, 30, "Hazır", pose=1)
        second = display.frame(110, 30, "Hazır", pose=4)
        self.assertNotEqual(first.lines, second.lines)
        self.assertEqual(first.cursor, second.cursor)
        self.assertEqual(first.lines[23:], second.lines[23:])
        self.assertEqual(
            [line.partition(" │ ")[0] for line in first.lines[:23]],
            [line.partition(" │ ")[0] for line in second.lines[:23]],
        )
        self.assertEqual(
            len(render_logo(24, pose=1).splitlines()), len(render_logo(24, pose=4).splitlines())
        )

    def test_resize_and_history_remain_bounded(self):
        display = Display()
        display.append("\n".join(f"line {i}" for i in range(100)))
        display.editor = ("abc\n" + "漢" * 60, 124)
        wide = display.frame(110, 30, "Hazır")
        display.scroll = 500
        old = display.frame(110, 30, "Hazır")
        self.assertNotEqual(wide.lines[0], old.lines[0])
        self.assertIn("line 0", old.lines[0])
        for columns, rows in ((45, 14), (12, 6), (8, 1), (80, 24)):
            frame = display.frame(columns, rows, "Hazır")
            self.assertEqual(len(frame.lines), rows)
            self.assertTrue(all(cells(line) < columns for line in frame.lines))
            row, col = frame.cursor
            self.assertTrue(1 <= row <= rows)
            self.assertTrue(1 <= col < columns)
        previous = display.frame(80, 24, "Hazır").lines[0]
        display.append("\nnew result")
        self.assertEqual(display.frame(80, 24, "Hazır").lines[0], previous)


class TerminalLogoTests(unittest.TestCase):
    def invoke(self, *args, tty=False, environment=None):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / "unused project"
            home = Path(temporary) / "external home"
            output, errors = io.StringIO(), io.StringIO()
            with (
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(errors),
                patch.object(output, "isatty", return_value=tty),
                patch.dict(
                    os.environ,
                    {"USERPROFILE": temporary, "HOME": temporary, **(environment or {})},
                    clear=True,
                ),
            ):
                code = main(["--project", str(project), "--home", str(home), "logo", *args])
            self.assertFalse(project.exists())
            self.assertFalse(home.exists())
            return code, output.getvalue(), errors.getvalue()

    def test_pipe_is_plain_art_and_width_is_respected(self):
        code, output, errors = self.invoke("--width", "80")
        self.assertEqual(code, 0, errors)
        self.assertNotIn("\x1b", output)
        lines = output.splitlines()
        self.assertTrue(all(len(line) == 80 for line in lines))
        self.assertGreater(len(lines), 40)
        self.assertIn("▀", output)
        self.assertIn("▄", output)

    def test_terminal_color_and_opt_out(self):
        code, output, errors = self.invoke("--width", "48", tty=True)
        self.assertEqual(code, 0, errors)
        self.assertIn("\x1b[38;2;0;", output)
        self.assertIn("\x1b[48;2;0;", output)
        self.assertTrue(output.endswith("\x1b[0m\n"))
        plain = re.sub(r"\x1b\[[0-9;]*m", "", output)
        self.assertTrue(all(len(line) == 48 for line in plain.splitlines()))
        for environment in ({"NO_COLOR": ""}, {"TERM": "dumb"}):
            code, output, errors = self.invoke(tty=True, environment=environment)
            self.assertEqual(code, 0, errors)
            self.assertNotIn("\x1b", output)

    def test_explicit_color_overrides_auto_and_never_is_plain(self):
        code, output, errors = self.invoke("--color", "always", environment={"NO_COLOR": "1"})
        self.assertEqual(code, 0, errors)
        self.assertIn("\x1b[38;2;0;", output)
        code, output, errors = self.invoke("--color", "never", tty=True)
        self.assertEqual(code, 0, errors)
        self.assertNotIn("\x1b", output)

    def test_invalid_width_fails_without_art_or_state(self):
        for width in ("0", "7", "161"):
            code, output, errors = self.invoke("--width", width)
            self.assertEqual(code, 2)
            self.assertEqual(output, "")
            self.assertIn("width", json.loads(errors)["error"])
