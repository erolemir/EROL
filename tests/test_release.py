"""Verify monotonic versions and coherent releases without modifying main."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.release import next_version, version_tuple

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_versions_are_monotonic_and_respect_series_floor(self):
        self.assertEqual(next_version("0.1.1", []), "0.1.1")
        tags = ["v0.1.9", "v0.1.10", "v0.1.2", "unrelated", "v0.1.30-rc.1"]
        self.assertEqual(next_version("0.1.1", tags), "0.1.11")
        self.assertEqual(next_version("0.2.0", tags), "0.2.0")
        self.assertEqual(next_version("0.1.1", ["v1.0.0"]), "1.0.1")

    def test_version_rejects_tags_and_injection(self):
        for value in ("v0.1.1", "01.2.3", "0.1.1;whoami", "0.1.1\n", "0.1", "-1.2.3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                version_tuple(value)

    def test_prepare_keeps_main_and_synchronizes_all_versions(self):
        with tempfile.TemporaryDirectory(prefix="erol-release-test-") as temporary:
            root = Path(temporary)
            for directory in ("src", "bin", "scripts"):
                shutil.copytree(
                    ROOT / directory,
                    root / directory,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"),
                )
            for name in (
                "package.json",
                "package-lock.json",
                "pyproject.toml",
                ".gitignore",
                "LICENSE",
                "COPYRIGHT",
            ):
                shutil.copy2(ROOT / name, root / name)

            def git(*args: str) -> str:
                return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

            git("init", "-b", "main")
            git("config", "core.autocrlf", "false")
            git("config", "user.name", "EROL release fixture")
            git("config", "user.email", "fixture@example.invalid")
            git("add", "--all")
            git("commit", "-m", "fixture source")
            source = git("rev-parse", "HEAD")
            source_version = json.loads((root / "package.json").read_text("utf-8"))["version"]
            major, minor, _ = version_tuple(source_version)
            expected = f"{major + 1}.{minor}.11"
            git("tag", f"v{major + 1}.{minor}.10")
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts/release.py"),
                    "prepare",
                    "--source-sha",
                    source,
                ],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True,
            )
            self.assertIn(expected, result.stdout)
            self.assertEqual(git("rev-parse", "refs/heads/main"), source)
            for name in (
                "package.json",
                "package-lock.json",
                "plugins/erol/plugin.json",
                "plugins/erol/.claude-plugin/plugin.json",
            ):
                self.assertEqual(json.loads((root / name).read_text("utf-8"))["version"], expected)
            record = json.loads((root / "RELEASE.json").read_text("utf-8"))
            self.assertEqual(record["source_commit"], source)
            self.assertEqual(record["license"], "AGPL-3.0-only")
            for name in (
                "src/erol/__init__.py",
                "plugins/erol/runtime/erol/__init__.py",
                "pyproject.toml",
            ):
                self.assertIn(f'"{expected}"', (root / name).read_text("utf-8"))
            changed = subprocess.run(
                [
                    sys.executable,
                    str(root / "scripts/release.py"),
                    "prepare",
                    "--source-sha",
                    source,
                ],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertNotEqual(changed.returncode, 0, "Dirty release preparation must be rejected")


if __name__ == "__main__":
    unittest.main()
