"""Bounded native discovery fixtures; no account or model calls."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from erol.common import ErolError
from erol.connections import Connection
from erol.harness import command_prefix, windows_codex_executable
from erol.providers import CLIAdapter


class HarnessDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.local = Path(self.temporary.name)
        self.directory = self.local / "OpenAI" / "Codex" / "bin"
        self.directory.mkdir(parents=True)
        # Replace this module's os reference, not global os.name/Path semantics.
        self.windows = SimpleNamespace(
            name="nt", environ={"LOCALAPPDATA": str(self.local)}, scandir=os.scandir
        )

    def native(self, relative, modified):
        path = self.directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic native discovery fixture")
        os.utime(path, ns=(modified, modified))
        return path

    def test_missing_path_finds_newest_real_native_file_not_newest_directory(self):
        self.native("codex.exe", 1_000_000_000)
        newest = self.native("0000000000000001/codex.exe", 3_000_000_000)
        self.native("0000000000000002/codex.exe", 2_000_000_000)
        empty = self.directory / "ffffffffffffffff"
        empty.mkdir()
        os.utime(empty, ns=(9_000_000_000, 9_000_000_000))
        with (
            patch("erol.harness.os", self.windows),
            patch("erol.harness.shutil.which", return_value=None),
        ):
            self.assertEqual(command_prefix("codex"), [str(newest)])

    def test_native_ties_have_deterministic_path_order(self):
        self.native("0000000000000001/codex.exe", 2_000_000_000)
        second = self.native("0000000000000002/codex.exe", 2_000_000_000)
        with patch("erol.harness.os", self.windows):
            self.assertEqual(windows_codex_executable(), str(second))

    def test_path_precedence_does_not_inspect_desktop_install(self):
        preferred = str(self.local / "preferred.exe")
        with (
            patch("erol.harness.os", self.windows),
            patch("erol.harness.shutil.which", return_value=preferred),
            patch("erol.harness.windows_codex_executable") as fallback,
        ):
            self.assertEqual(command_prefix("codex"), [preferred])
            fallback.assert_not_called()

    def test_explicit_connection_executable_bypasses_automatic_discovery(self):
        executable = str(self.local / "explicit.exe")
        with patch("erol.providers.command_prefix") as automatic:
            adapter = CLIAdapter(Connection("fixture", "codex", executable=executable), self.local)
        self.assertEqual(adapter.prefix, [executable])
        automatic.assert_not_called()

    def test_discovery_is_single_level_and_ignores_other_names_and_wrappers(self):
        self.native("unrelated/codex.exe", 8_000_000_000)
        self.native("0000000000000001/nested/codex.exe", 8_000_000_000)
        self.native("0000000000000002/codex.cmd", 8_000_000_000)
        with patch("erol.harness.os", self.windows):
            self.assertIsNone(windows_codex_executable())

    def test_directory_inventory_is_bounded_and_linked_install_fails_closed(self):
        for index in range(65):
            (self.directory / f"entry-{index}").mkdir()
        with patch("erol.harness.os", self.windows):
            self.assertIsNone(windows_codex_executable())
        with (
            patch("erol.harness.os", self.windows),
            patch("erol.harness.reject_links", side_effect=ErolError("linked fixture")),
        ):
            self.assertIsNone(windows_codex_executable())

    def test_missing_or_relative_local_appdata_never_scans_and_other_clis_do_not_fallback(self):
        for value in (None, "relative"):
            windows = SimpleNamespace(
                name="nt", environ={} if value is None else {"LOCALAPPDATA": value}
            )
            with patch("erol.harness.os", windows):
                self.assertIsNone(windows_codex_executable())
        with (
            patch("erol.harness.os", self.windows),
            patch("erol.harness.shutil.which", return_value=None),
            patch("erol.harness.windows_codex_executable") as fallback,
        ):
            with self.assertRaisesRegex(ErolError, "PATH.*absolute native executable"):
                command_prefix("claude")
            fallback.assert_not_called()

    def test_windows_shell_wrapper_uses_native_node_and_never_silently_falls_back(self):
        wrapper = self.local / "codex.cmd"
        entry = self.local / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        entry.parent.mkdir(parents=True)
        entry.write_text("// synthetic entry fixture", "utf-8")
        node = str(self.local / "node.exe")
        with (
            patch("erol.harness.os", self.windows),
            patch("erol.harness.shutil.which", side_effect=[str(wrapper), node]),
            patch("erol.harness.windows_codex_executable") as fallback,
        ):
            self.assertEqual(command_prefix("codex"), [node, str(entry)])
            fallback.assert_not_called()
        with (
            patch("erol.harness.os", self.windows),
            patch(
                "erol.harness.shutil.which",
                side_effect=[str(wrapper), str(self.local / "node.cmd")],
            ),
            patch("erol.harness.windows_codex_executable") as fallback,
        ):
            with self.assertRaisesRegex(ErolError, "no supported native or Node"):
                command_prefix("codex")
            fallback.assert_not_called()

    def test_non_windows_hosts_never_scan_desktop_install(self):
        with (
            patch("erol.harness.os", SimpleNamespace(name="posix")),
            patch("erol.harness.shutil.which", return_value=None),
            patch("erol.harness.windows_codex_executable") as fallback,
        ):
            with self.assertRaisesRegex(ErolError, "unavailable"):
                command_prefix("codex")
            fallback.assert_not_called()

    def test_other_windows_wrappers_cannot_select_the_claude_package(self):
        entry = self.local / "node_modules" / "@anthropic-ai" / "claude-code" / "cli.js"
        entry.parent.mkdir(parents=True)
        entry.write_text("// synthetic unrelated CLI fixture", "utf-8")
        with (
            patch("erol.harness.os", self.windows),
            patch("erol.harness.shutil.which", return_value=str(self.local / "agy.cmd")) as which,
        ):
            with self.assertRaisesRegex(ErolError, "Unsupported CLI shell wrapper"):
                command_prefix("agy")
            which.assert_called_once_with("agy")


if __name__ == "__main__":
    unittest.main()
