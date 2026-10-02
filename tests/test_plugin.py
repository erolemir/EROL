import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from erol import __version__
from erol.adapters import generated_files, launcher_command, skill_path
from erol.installer import Installer
from erol.plugin import plugin_files

ROOT = Path(__file__).resolve().parents[1]


class PluginTests(unittest.TestCase):
    def test_native_manifests_and_both_marketplaces_share_identity(self):
        files = plugin_files()
        portable = json.loads(files["plugins/erol/plugin.json"])
        claude = json.loads(files["plugins/erol/.claude-plugin/plugin.json"])
        codex_marketplace = json.loads(files[".agents/plugins/marketplace.json"])
        claude_marketplace = json.loads(files[".claude-plugin/marketplace.json"])
        for document in (portable, claude, codex_marketplace, claude_marketplace):
            self.assertEqual(document["name"], "erol")
        self.assertEqual(portable["version"], __version__)
        self.assertEqual(claude["version"], __version__)
        self.assertEqual(
            json.loads((ROOT / "package.json").read_text("utf-8"))["version"], __version__
        )
        self.assertEqual(portable["extensions"]["com.openai"]["interface"]["displayName"], "EROL")
        self.assertEqual(codex_marketplace["plugins"][0]["source"]["path"], "./plugins/erol")
        self.assertEqual(claude_marketplace["plugins"][0]["source"], "./plugins/erol")
        self.assertNotIn("hooks", portable["extensions"]["com.openai"])
        self.assertNotIn("apps", portable["extensions"]["com.openai"])
        self.assertNotIn("hooks", claude)

    def test_plugin_is_generated_and_bundles_runtime_without_global_cli(self):
        files = plugin_files()
        for relative, content in files.items():
            self.assertEqual((ROOT / relative).read_bytes(), content.encode("utf-8"))
        body = files["plugins/erol/skills/erol/SKILL.md"]
        self.assertIn("../../scripts/erol.mjs", body)
        self.assertIn("node <EROL_LAUNCHER>", body)
        self.assertIn("--project <PROJECT_ROOT>", body)
        self.assertIn("--task-id", body)
        self.assertNotIn("`erol ", body)
        self.assertIn("no pip install or global erol command", body)
        self.assertEqual(
            files["plugins/erol/scripts/erol.mjs"], (ROOT / "bin/erol.mjs").read_text("utf-8")
        )
        for source in (ROOT / "src/erol").glob("*.py"):
            relative = f"plugins/erol/runtime/erol/{source.name}"
            self.assertEqual(files[relative], source.read_text("utf-8"))
        self.assertIn("plugins/erol/runtime/erol/data/registry.json", files)
        self.assertFalse(any("__pycache__" in path for path in files))

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable")
    def test_copied_plugin_runs_bundled_core_from_another_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            package = base / "native plugin with spaces"
            for relative, content in plugin_files().items():
                if relative.startswith("plugins/erol/"):
                    path = package / relative.removeprefix("plugins/erol/")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content.encode("utf-8"))
            project = base / "working project ü"
            project.mkdir()
            # A caller package must not shadow the shipped runtime.
            (project / "erol.py").write_text(
                "raise RuntimeError('caller package executed')", "utf-8"
            )
            env = {**os.environ, "EROL_PYTHON": sys.executable}
            result = subprocess.run(
                [
                    shutil.which("node"),
                    str(package / "scripts/erol.mjs"),
                    "--project",
                    str(project),
                    "--home",
                    str(base / "memory"),
                    "plan",
                    "--task",
                    "SCRUM-17 Tahakkuk Gönderilenler ekranında filtreyi ve tarih aralığını düzelt",
                    "--task-id",
                    "plugin-task",
                ],
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(output["task_id"], "plugin-task")
            self.assertEqual(
                ["frontend-state-correctness"], output["plan"]["context"]["selected_skills"]
            )
            self.assertEqual([], output["selected_skills"])
            self.assertTrue(any((base / "memory/state").glob("*/memory.db")))
            self.assertFalse((package / "state").exists())

    def test_direct_python_entry_uses_copied_runtime_without_node_and_blocks_shadowing(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            package = base / "native package ü"
            for relative, content in plugin_files().items():
                if relative.startswith("plugins/erol/") and not relative.endswith(".mjs"):
                    path = package / relative.removeprefix("plugins/erol/")
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content.encode("utf-8"))
            project = base / "unrelated project"
            project.mkdir()
            for module in ("json", "erol", "sitecustomize"):
                (project / f"{module}.py").write_text(
                    "raise RuntimeError('shadow executed')", "utf-8"
                )
            task = 'RabbitMQ duplicate consumer at least once delivery "Türkçe"'
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    "-X",
                    "utf8",
                    str(package / "scripts/erol.py"),
                    "--project",
                    str(project),
                    "--home",
                    str(base / "state"),
                    "plan",
                    "--task",
                    task,
                    "--task-id",
                    "direct-python-task",
                ],
                cwd=project,
                env={**os.environ, "PYTHONPATH": ".", "PYTHONHOME": str(project)},
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["task_id"], "direct-python-task")
            self.assertEqual(report["plan"]["task"], task)
            self.assertIn("message-idempotency", report["plan"]["context"]["selected_skills"])
            self.assertFalse((package / "scripts/erol.mjs").exists())
            self.assertTrue(any((base / "state/state").glob("*/memory.db")))

    def test_direct_python_entry_rejects_nonisolated_start_before_importing_project_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / "pathlib.py").write_text("raise RuntimeError('shadow executed')", "utf-8")
            result = subprocess.run(
                [sys.executable, "-S", str(ROOT / "bin/erol.py"), "--version"],
                cwd=project,
                env={**os.environ, "PYTHONPATH": str(project)},
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=15,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("python -I -S", result.stderr)
            self.assertNotIn("shadow executed", result.stderr)

    def test_npx_bridge_persists_trusted_absolute_launcher_and_updates_ownership(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            project = base / "work"
            project.mkdir()
            installed = base / "installed runtime with spaces"
            module = installed / "src/erol/installer.py"
            module.parent.mkdir(parents=True)
            module.touch()
            launcher = installed / "bin/erol.mjs"
            launcher.parent.mkdir()
            launcher.write_text("// fixture launcher", encoding="utf-8")
            home = base / "memory"
            Installer(project, home).install("claude", False)
            with (
                patch("erol.installer.__file__", str(module)),
                patch.dict(os.environ, {"EROL_LAUNCHER": str(launcher)}, clear=False),
            ):
                installer = Installer(project, home)
                self.assertEqual(installer.install("claude", False)["status"], "installed")
            text = (project / skill_path("claude")).read_text("utf-8")
            self.assertIn(launcher_command(launcher), text)
            self.assertNotIn("`erol ", text)
            # Receipt commands stay usable after the setup process environment ends.
            self.assertIn("Runtime argv", (project / "CLAUDE.md").read_text("utf-8"))
            self.assertEqual(
                Installer(project, home).uninstall("claude", False)["status"], "uninstalled"
            )

    def test_untrusted_environment_launcher_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            project = base / "work"
            project.mkdir()
            malicious = base / "erol.mjs"
            malicious.write_text("// unrelated executable", encoding="utf-8")
            with patch.dict(os.environ, {"EROL_LAUNCHER": str(malicious)}, clear=False):
                with self.assertRaises(ValueError):
                    Installer(project, base / "memory")
            self.assertEqual(list(project.iterdir()), [])
            self.assertFalse((base / "memory").exists())

    def test_renderer_quotes_paths_without_interpreting_command_substitution(self):
        prefix = Path(tempfile.gettempdir()).resolve()
        path = prefix / "runtime with space and ' quote $()" / "erol.mjs"
        command = launcher_command(path)
        if os.name == "nt":
            self.assertEqual(command, "node '" + str(path).replace("'", "''") + "'")
        else:
            import shlex

            self.assertEqual(shlex.split(command), ["node", str(path)])
        body = generated_files("codex", path)[skill_path("codex")]
        self.assertIn(command, body)
        with self.assertRaises(ValueError):
            generated_files("codex", prefix / "bad\npath" / "erol.mjs")

    def test_drift_checker_detects_unexpected_runtime_without_deleting_it(self):
        spec = importlib.util.spec_from_file_location(
            "plugin_drift", ROOT / "scripts/check_adapter_drift.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unexpected = root / "plugins/erol/runtime/erol/unexpected.py"
            unexpected.parent.mkdir(parents=True)
            unexpected.write_text("# unowned fixture", encoding="utf-8")
            with patch.object(module, "ROOT", root):
                self.assertEqual(module.unexpected_bundle_files({}), [unexpected])
            self.assertEqual(unexpected.read_text("utf-8"), "# unowned fixture")


if __name__ == "__main__":
    unittest.main()
