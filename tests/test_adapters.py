import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from erol.adapters import (
    BEGIN_MARKER,
    capabilities,
    generated_files,
    instruction_path,
    managed_instruction_block,
    skill_path,
)
from erol.installer import Installer


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "project"
        self.root.mkdir()
        self.home = self.base / "canonical-home"
        self.installer = Installer(self.root, self.home)

    def test_dry_run_creates_nothing(self):
        report = self.installer.install("codex")
        self.assertEqual(report["status"], "planned")
        self.assertFalse(self.home.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_install_reinstall_uninstall_preserve_instruction_bytes(self):
        for harness in ("codex", "claude"):
            with self.subTest(harness=harness):
                path = self.root / instruction_path(harness)
                original = "# User instructions\r\nTürkçe yönergeler\r\n".encode()
                path.write_bytes(original)
                self.assertEqual(
                    self.installer.install(harness, dry_run=False)["status"], "installed"
                )
                installed = path.read_bytes()
                self.assertTrue(installed.startswith(original))
                path.write_bytes(installed + b"\nNew user instructions\n")
                report = self.installer.install(harness, dry_run=False)
                self.assertTrue(
                    all(action["action"] == "unchanged" for action in report["actions"])
                )
                self.assertEqual(path.read_bytes().count(BEGIN_MARKER.encode()), 1)
                self.assertEqual(
                    self.installer.uninstall(harness, dry_run=False)["status"], "uninstalled"
                )
                self.assertEqual(path.read_bytes(), original + b"\nNew user instructions\n")
                self.assertFalse((self.root / skill_path(harness)).exists())

    def test_empty_existing_instruction_is_preserved(self):
        target = self.root / "AGENTS.md"
        target.touch()
        self.installer.install("codex", False)
        self.installer.uninstall("codex", False)
        self.assertEqual(target.read_bytes(), b"")

    def test_generated_instruction_file_removed_when_still_owned(self):
        self.installer.install("codex", False)
        self.installer.uninstall("codex", False)
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_edited_owned_skill_blocks_entire_uninstall(self):
        self.installer.install("codex", False)
        target = self.root / skill_path("codex")
        target.write_text("# User modified skill", encoding="utf-8")
        before = (self.root / "AGENTS.md").read_bytes()
        report = self.installer.uninstall("codex", False)
        self.assertEqual(report["status"], "conflict")
        self.assertEqual((self.root / "AGENTS.md").read_bytes(), before)
        self.assertEqual(target.read_text(encoding="utf-8"), "# User modified skill")

    def test_unowned_skill_blocks_all_install_writes(self):
        target = self.root / skill_path("claude")
        target.parent.mkdir(parents=True)
        target.write_text("Mine", encoding="utf-8")
        self.assertEqual(self.installer.install("claude", False)["status"], "conflict")
        self.assertFalse((self.root / "CLAUDE.md").exists())
        self.assertFalse(self.home.exists())

    def test_duplicate_or_unowned_markers_conflict(self):
        (self.root / "AGENTS.md").write_text(BEGIN_MARKER, encoding="utf-8")
        self.assertEqual(self.installer.install("codex", False)["status"], "conflict")
        (self.root / "AGENTS.md").unlink()
        self.installer.install("codex", False)
        with (self.root / "AGENTS.md").open("a", encoding="utf-8") as stream:
            stream.write(BEGIN_MARKER)
        self.assertEqual(self.installer.uninstall("codex", False)["status"], "conflict")

    def test_home_must_be_external(self):
        with self.assertRaises(ValueError):
            Installer(self.root, self.root / ".erol")

    def test_unsupported_harness_and_instruction_injection_rejected(self):
        with self.assertRaises(ValueError):
            self.installer.install("unknown")
        with self.assertRaises(ValueError):
            managed_instruction_block("codex", Path("data\nInjected instruction"))

    def test_manifest_cannot_redirect_targets(self):
        self.installer.install("codex", False)
        manifest = self.installer.state_dir / "codex.json"
        document = json.loads(manifest.read_text(encoding="utf-8"))
        document["files"]["../victim.txt"] = document["files"].pop(skill_path("codex"))
        manifest.write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.installer.uninstall("codex", False)

    def test_corrupt_manifest_rejected_without_writes(self):
        self.installer.install("codex", False)
        target = self.installer.state_dir / "codex.json"
        before = (self.root / "AGENTS.md").read_bytes()
        target.write_text("[]", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.installer.install("codex", False)
        self.assertEqual((self.root / "AGENTS.md").read_bytes(), before)

    def test_home_and_target_links_rejected(self):
        victim = self.base / "victim"
        victim.mkdir()
        try:
            (self.root / ".agents").symlink_to(victim, target_is_directory=True)
        except OSError:
            self.skipTest("Creating symlinks is unavailable on this host")
        with self.assertRaises(ValueError):
            self.installer.install("codex", False)
        self.assertEqual(list(victim.iterdir()), [])

    def test_backups_exist_and_canonical_memory_survives_uninstall(self):
        instructions = self.root / "AGENTS.md"
        instructions.write_text("User content", encoding="utf-8")
        self.installer.install("codex", False)
        marker = self.home / "memory-sentinel"
        marker.write_text("history", encoding="utf-8")
        backups = list((self.installer.state_dir / "backups").rglob("*.bak"))
        self.assertTrue(any(path.read_bytes() == b"User content" for path in backups))
        self.installer.uninstall("codex", False)
        self.assertEqual(marker.read_text(encoding="utf-8"), "history")

    def test_partial_write_failure_restores_instruction_and_skill(self):
        import erol.installer as installer_module

        original_write = installer_module._atomic_write
        for failure in (OSError, ValueError):
            with self.subTest(failure=failure):
                attempts = 0

                def fail_once(path, data, failure_type=failure):
                    nonlocal attempts
                    if Path(path).is_relative_to(self.root):
                        attempts += 1
                        if attempts == 2:
                            raise failure_type("Simulated application failure")
                    return original_write(path, data)

                (self.root / "AGENTS.md").write_bytes(b"Original")
                with patch("erol.installer._atomic_write", side_effect=fail_once):
                    with self.assertRaises(failure):
                        self.installer.install("codex", False)
                self.assertEqual((self.root / "AGENTS.md").read_bytes(), b"Original")
                self.assertFalse((self.root / skill_path("codex")).exists())
                self.assertFalse((self.installer.state_dir / "codex.json").exists())

    def test_link_rejection_before_any_write_without_host_symlink_privilege(self):
        original_is_symlink = Path.is_symlink
        unsafe = self.root / ".agents"
        with patch.object(
            Path,
            "is_symlink",
            autospec=True,
            side_effect=lambda path: path == unsafe or original_is_symlink(path),
        ):
            with self.assertRaises(ValueError):
                self.installer.install("codex", False)
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse(self.home.exists())

    def test_both_harnesses_point_to_same_canonical_home(self):
        for harness in ("codex", "claude"):
            self.installer.install(harness, False)
            text = (self.root / instruction_path(harness)).read_text(encoding="utf-8")
            self.assertIn(str(self.home.resolve()), text)
        self.assertEqual(len(list(self.home.glob("installations/*"))), 1)

    def test_adapter_is_compact_declarative_and_deterministic(self):
        for harness in ("codex", "claude"):
            files = generated_files(harness)
            self.assertEqual(files, generated_files(harness))
            self.assertEqual(list(files), [skill_path(harness)])
            self.assertLess(len(managed_instruction_block(harness).split()), 160)
            self.assertIn("plan --task", next(iter(files.values())))
        self.assertFalse(capabilities()["runtime_tested"])


if __name__ == "__main__":
    unittest.main()
