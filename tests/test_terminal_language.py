"""Language boundaries, Windows record input and task-relative binary snapshots."""

import contextlib
import ctypes
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from erol.chat import ChatEngine
from erol.common import ErolError
from erol.connections import ConnectionStore, Settings
from erol.console import (
    Editor,
    Screen,
    WindowsKeys,
    command,
    execute_task,
    key_windows,
    launch,
    read_prompt,
)
from erol.console_input import InputRecord, decode_record
from erol.i18n import HELP_EN, MESSAGES, message, os_language
from erol.workspace import Fingerprint, changes, file_names, snapshot


class LanguageTests(unittest.TestCase):
    def test_os_ui_language_wins_over_regional_environment(self):
        function = Mock(return_value=0x041F)
        kernel = Mock(GetUserDefaultUILanguage=function)
        with (
            patch("erol.i18n.os.name", "nt"),
            patch.object(ctypes, "WinDLL", return_value=kernel, create=True),
            patch.dict(os.environ, {"LANG": "en_US.UTF-8"}),
        ):
            self.assertEqual(os_language(), "tr")
            function.return_value = 0x0409
            self.assertEqual(os_language(), "en")
            function.return_value = 0x0411
            self.assertEqual(os_language(), "en")

    def test_posix_environment_and_fallback(self):
        with patch("erol.i18n.os.name", "posix"):
            for value, expected in (("tr_TR.UTF-8", "tr"), ("tr:en", "tr"), ("de_DE", "en")):
                with patch.dict(os.environ, {"LC_ALL": value, "LANG": "en_US"}, clear=True):
                    self.assertEqual(os_language(), expected)
            with (
                patch.dict(os.environ, {}, clear=True),
                patch("erol.i18n.locale.getlocale", side_effect=ValueError),
            ):
                self.assertEqual(os_language(), "en")

    def test_settings_compatibility_validation_and_persistence(self):
        self.assertEqual(Settings.load({}).language, "auto")
        for invalid in (None, [], "fr", True):
            with self.assertRaises(ErolError):
                Settings.load({"language": invalid})
        with tempfile.TemporaryDirectory() as temporary:
            root, home = Path(temporary) / "project", Path(temporary) / "home"
            root.mkdir()
            engine = ChatEngine(root, home)
            command(engine, "/settings api_budget_usd 7")
            for preference in ("en", "tr", "auto"):
                with patch("erol.i18n.os_language", return_value="en"):
                    response = command(engine, "/language " + preference)
                self.assertEqual(response["preference"], preference)
                reloaded = ConnectionStore(home, root).settings
                self.assertEqual(reloaded.language, preference)
                self.assertEqual(reloaded.api_budget_usd, 7)
            before = (home / "connections.json").read_bytes()
            with self.assertRaises(ErolError):
                command(engine, "/language fr")
            self.assertEqual((home / "connections.json").read_bytes(), before)
            engine.connections.settings.language = "en"
            self.assertEqual(command(engine, "/help")["commands"]["/exit"], "Exit the terminal")
            engine.connections.settings.language = "tr"
            self.assertEqual(command(engine, "/help")["commands"]["/exit"], "Terminalden çık")
            self.assertEqual(command(engine, "/status")["status"], "ready")

    def test_catalogs_have_matching_commands_placeholders_and_fallback(self):
        import string

        from erol.console import COMMANDS

        self.assertEqual(set(COMMANDS), set(HELP_EN))
        formatter = string.Formatter()
        for en, tr in MESSAGES.values():
            self.assertEqual(
                {name for _, name, _, _ in formatter.parse(en) if name},
                {name for _, name, _, _ in formatter.parse(tr) if name},
            )
        self.assertEqual(message("unsupported", "ready"), "Ready")
        screen = Screen(io.StringIO())
        screen.set_language("en")
        self.assertIn("Ready", screen.status)
        screen.set_language("tr")
        self.assertIn("Hazır", screen.status)

    def start(self, root, home, inputs):
        output = io.StringIO()
        screen = Screen(output)
        with (
            patch("erol.console.Screen", return_value=screen),
            patch("erol.console.read_prompt", side_effect=inputs),
            patch.object(__import__("sys").stdin, "isatty", return_value=True),
            patch.object(__import__("sys").stdout, "isatty", return_value=True),
            patch("erol.console.shutil.which", return_value=None),
            patch("erol.chat.adapter") as provider,
        ):
            result = launch(root, home)
        provider.assert_not_called()
        return result, output.getvalue()

    def test_projectless_language_persists_only_global_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            home = base / ".erol"
            project = base / "workspace"
            project.mkdir()
            _, output = self.start(base, home, ["/language en", "/help", "/exit"])
            self.assertIn("UI language: en", output)
            self.assertEqual(
                json.loads((home / "connections.json").read_text("utf-8"))["language"], "en"
            )
            self.assertFalse((home / "state").exists())
            self.assertFalse((home / "global").exists())
            _, output = self.start(base, home, ["/language tr", "/project workspace", ",", "/exit"])
            self.assertIn("Arayüz dili: tr", output)
            self.assertIn("Bir görev yaz", output)
            self.assertEqual(
                json.loads((home / "connections.json").read_text("utf-8"))["language"], "tr"
            )
            _, output = self.start(base, home, ["/help", "/exit"])
            self.assertIn("Proje seçilmedi", output)

    def test_interactive_connect_is_short_headless_contract_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, home = Path(temporary) / "project", Path(temporary) / "home"
            root.mkdir()
            _, output = self.start(root, home, ["/connect codex", "/exit"])
            self.assertNotIn('"input_price"', output)
            self.assertIn("/providers", output)
            result = command(ChatEngine(root, home), "/connect codex")
            self.assertTrue(result["connection"]["models"])


class InputTests(unittest.TestCase):
    def test_input_and_redraw_failures_cancel_and_join_worker_before_return(self):
        import threading

        for failure in ("input", "redraw"):

            class Engine:
                def __init__(self):
                    self.stopped = threading.Event()
                    self.ended = threading.Event()

                def cancel(self):
                    self.stopped.set()

                def execute(self, task, emit, resume=False):
                    self.stopped.wait(2)
                    self.ended.set()
                    return {"status": "cancelled"}

            engine = Engine()
            screen = Screen(io.StringIO())
            with patch.object(
                screen,
                "refresh",
                side_effect=OSError("redraw failed") if failure == "redraw" else None,
            ):
                poll = (
                    Mock(side_effect=ErolError("input unavailable"))
                    if failure == "input"
                    else lambda: None
                )
                with self.assertRaises((ErolError, OSError)):
                    execute_task(engine, "test", screen, poll=poll)
            self.assertTrue(engine.stopped.is_set())
            self.assertTrue(engine.ended.is_set())
            self.assertFalse(screen.running)

    def test_streaming_at_retention_limit_preserves_surviving_viewport_anchor(self):
        from erol.display import Display

        display = Display()
        display.append("\n".join(f"line {n:04d} " + "x" * 39 for n in range(4100)))
        display.frame(110, 30, "Ready")
        display.scroll = 100
        before = display.frame(110, 30, "Ready").lines[0].partition(" │ ")[0]
        display.append("\n" + "\n".join(f"new {n:04d} " + "x" * 40 for n in range(20)))
        after = display.frame(110, 30, "Ready").lines[0].partition(" │ ")[0]
        self.assertEqual(before, after)
        self.assertLessEqual(len(display.text), 200000)

    class Keys:
        def __init__(self, text):
            self.buffer = text

        def getwch(self):
            char, self.buffer = self.buffer[0], self.buffer[1:]
            return char

        def kbhit(self):
            return bool(self.buffer)

    def test_sgr_wheel_long_coordinates_and_clicks_do_not_pollute_editor(self):
        for text, expected in (
            ("\x1b[<64;1234;5678M", "wheel_up"),
            ("\x1b[<65;123;56M", "wheel_down"),
            ("\x1b[<0;42;24M", "unknown"),
            ("\x1b[<0;42;24m", "unknown"),
        ):
            reader = self.Keys(text + "z")
            self.assertEqual(key_windows(reader), expected)
            self.assertEqual(key_windows(reader), "z")
        editor = Editor([], [])
        editor.insert("input")
        editor.key("clear_input")
        self.assertEqual(editor.key("enter"), "")
        self.assertEqual(editor.text, "")

    def test_native_keyboard_repeat_and_mouse_wheel_events(self):
        record = InputRecord()
        record.type = 1
        record.data.key.down, record.data.key.repeat, record.data.key.char = True, 2, "ş"
        self.assertEqual(decode_record(record), "şş")
        record.data.key.down = False
        self.assertEqual(decode_record(record), "")
        record.type = 2
        record.data.mouse.flags, record.data.mouse.buttons = 4, 120 << 16
        self.assertEqual(decode_record(record), "\x1b[<64;1;1M")
        record.data.mouse.buttons = (-120 & 0xFFFF) << 16
        self.assertEqual(decode_record(record), "\x1b[<65;1;1M")
        record.data.mouse.flags = 1
        self.assertEqual(decode_record(record), "")

    def test_conpty_unicode_alt_key_up_records_form_one_character(self):
        records = []
        for unit in ("\ud83d", "\ude80"):
            alt_down, alt_up = InputRecord(), InputRecord()
            alt_down.type = alt_up.type = 1
            alt_down.data.key.down, alt_down.data.key.key = True, 18
            alt_up.data.key.down, alt_up.data.key.key, alt_up.data.key.char = False, 18, unit
            records.extend([alt_down, alt_up])
        raw = "".join(decode_record(record) for record in records)
        reader = WindowsKeys.__new__(WindowsKeys)
        reader.buffer = raw
        editor = Editor([], [])
        editor.insert("tr")
        editor.key(reader.getwch())
        self.assertEqual(editor.text, "tr🚀")
        editor.key("backspace")
        self.assertEqual(editor.key("enter"), "tr")

    def test_native_key_up_does_not_block_escape_timeout_or_lose_queued_input(self):
        from ctypes import wintypes

        class Kernel:
            def __init__(self):
                self.events = []
                for down, char in ((False, "x"), (True, "a"), (True, "b")):
                    record = InputRecord()
                    record.type = 1
                    record.data.key.down, record.data.key.char = down, char
                    self.events.append(record)

            def ReadConsoleInputW(self, handle, pointer, maximum, count):
                record = self.events.pop(0)
                ctypes.memmove(pointer, ctypes.byref(record), ctypes.sizeof(record))
                count._obj.value = 1
                return True

            def GetNumberOfConsoleInputEvents(self, handle, count):
                count._obj.value = len(self.events)
                return True

        reader = WindowsKeys.__new__(WindowsKeys)
        reader.kernel, reader.ctypes, reader.wintypes = Kernel(), ctypes, wintypes
        reader.handle, reader.buffer, reader.records = 0, "", True
        self.assertTrue(reader.kbhit())
        self.assertEqual(reader.getwch(), "a")
        self.assertEqual(reader.getwch(), "b")
        self.assertFalse(reader.kbhit())

    def test_native_surrogate_pair_split_across_reads_survives_paste(self):
        reader = WindowsKeys.__new__(WindowsKeys)
        with patch.object(reader, "raw_char", side_effect=["\ud83d", "\ude80", "ş"]):
            editor = Editor([], [])
            editor.key("paste_start")
            editor.key(reader.getwch())
            editor.key(reader.getwch())
            editor.key("paste_end")
            self.assertEqual(editor.key("enter"), "🚀ş")
        reader.buffer = ""
        with patch.object(reader, "raw_char", side_effect=["\ud83d", "x"]):
            self.assertEqual(reader.getwch(), "\ufffd")
            self.assertEqual(reader.buffer, "x")

    def test_running_task_handles_scroll_cancel_and_queues_next_draft(self):
        import threading

        class Engine:
            stopped = threading.Event()

            def cancel(self):
                self.stopped.set()

            def execute(self, task, emit, resume=False):
                while not self.stopped.wait(0.02):
                    pass
                return {"status": "cancelled"}

        screen = Screen(io.StringIO())
        screen.rich, screen.active = True, True
        screen.display.append("\n".join(f"line {n}" for n in range(100)))
        screen.display.frame(110, 30, screen.status)
        keys = iter(["wheel_up", "x", "cancel"])
        with patch.object(screen, "refresh"):
            result = execute_task(Engine(), "test", screen, poll=lambda: next(keys, None))
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(screen.pending_keys, ["x"])
        self.assertGreater(screen.display.scroll, 0)

    def test_wheel_scroll_preserves_draft_and_backspace_then_submit(self):
        screen = Screen(io.StringIO())
        screen.rich = True
        screen.active = True
        screen.display.append("\n".join(str(n) for n in range(100)))
        keys = self.Keys("abc\x7f\x1b[<64;1;1M\r")
        host_platform = os.name
        with (
            patch("erol.console.os", SimpleNamespace(name="nt")),
            patch("erol.console.windows_console_mode", return_value=contextlib.nullcontext(True)),
            patch("erol.console.WindowsKeys", return_value=keys),
            patch("erol.console.sys.stdin.fileno", return_value=0),
        ):
            self.assertEqual(os.name, host_platform)
            self.assertEqual(read_prompt(screen, [], []), "ab")
        # Submission follows the new output; wheel did not enter the draft or history.
        self.assertIn("erol › ab\n", screen.display.text)


class SnapshotTests(unittest.TestCase):
    def test_generated_caches_ignored_and_binary_digests_detect_same_size_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in (".dart_tool", ".next", ".gradle"):
                directory = root / "app" / name
                directory.mkdir(parents=True)
                (directory / "cache").write_bytes(b"x" * 200)
            (root / "source.py").write_text("print(1)")
            file = root / "asset.docx"
            file.write_bytes(b"PK\x03\x04" + b"a" * 100)
            with patch("erol.workspace.MAX_FILE", 64):
                before = snapshot(root)
                self.assertEqual(set(before), {"source.py", "asset.docx"})
                self.assertIsInstance(before["asset.docx"], Fingerprint)
                file.write_bytes(b"PK\x03\x04" + b"b" * 100)
                after = snapshot(root)
                delta = changes(before, after)[0]
                self.assertTrue(delta["binary"])
                self.assertNotEqual(delta["before_sha256"], delta["after_sha256"])
                file.unlink()
                self.assertEqual(changes(after, snapshot(root))[0]["status"], "deleted")
                file.write_bytes(b"\0new")
                self.assertTrue(changes({}, snapshot(root))[0]["binary"])

    def test_oversized_text_names_the_file_and_aggregate_remains_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "big.py").write_text("x" * 100)
            with patch("erol.workspace.MAX_FILE", 64):
                with self.assertRaisesRegex(ErolError, "big.py"):
                    snapshot(root)
            (root / "big.py").write_bytes(b"\0" * 100)
            with patch("erol.workspace.MAX_FILE", 64), patch("erol.workspace.MAX_TOTAL", 80):
                with self.assertRaisesRegex(ErolError, "snapshot exceeds"):
                    snapshot(root)

    def test_git_tracked_generated_files_are_filtered(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = Mock(
                returncode=0, stdout=b"app/.next/cache\0app/.gradle/a\0app/.dart_tool/a\0src/a.py\0"
            )
            with patch("erol.workspace.subprocess.run", return_value=result):
                self.assertEqual(file_names(Path(temporary)), ["src/a.py"])
