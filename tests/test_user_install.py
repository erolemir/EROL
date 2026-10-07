"""Installer integrity, reversible command updates and isolated shell profiles."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import install


class UserInstallTests(unittest.TestCase):
    def test_release_rejects_wrong_bytes_before_any_installation(self):
        metadata = json.dumps(
            {
                "version": "0.2.5",
                "repository": install.REPOSITORY,
                "channel": "stable",
                "source_commit": "a" * 40,
            }
        ).encode()
        sums = ("0" * 64 + "  erol_ai-0.2.5-py3-none-any.whl\n").encode()
        with patch.object(install, "download", side_effect=[metadata, sums, b"wrong wheel"]):
            with self.assertRaisesRegex(ValueError, "checksum does not match"):
                install.release_payload()

    def test_release_binds_wheel_to_exact_stable_version_and_repository(self):
        payload = b"verified wheel fixture"
        metadata = {
            "version": "0.2.5",
            "repository": install.REPOSITORY,
            "channel": "stable",
            "source_commit": "a" * 40,
        }
        sums = (hashlib.sha256(payload).hexdigest() + "  erol_ai-0.2.5-py3-none-any.whl\n").encode()
        with patch.object(
            install, "download", side_effect=[json.dumps(metadata).encode(), sums, payload]
        ) as download:
            self.assertEqual(
                install.release_payload(), ("0.2.5", "erol_ai-0.2.5-py3-none-any.whl", payload)
            )
            self.assertIn(
                "/releases/download/v0.2.5/SHA256SUMS", download.call_args_list[1].args[0]
            )
        for field, value in [
            ("version", "../other"),
            ("repository", "other/repo"),
            ("source_commit", "unknown"),
        ]:
            record = {**metadata, field: value}
            with (
                self.subTest(field=field),
                patch.object(install, "download", return_value=json.dumps(record).encode()),
            ):
                with self.assertRaisesRegex(ValueError, "metadata"):
                    install.release_payload()

    def test_missing_duplicate_checksum_and_non_object_metadata_are_rejected(self):
        metadata = json.dumps(
            {
                "version": "0.2.5",
                "repository": install.REPOSITORY,
                "channel": "stable",
                "source_commit": "a" * 40,
            }
        ).encode()
        line = b"0" * 64 + b"  erol_ai-0.2.5-py3-none-any.whl\n"
        for sums in [b"", line * 2]:
            with (
                self.subTest(sums=sums),
                patch.object(install, "download", side_effect=[metadata, sums]),
            ):
                with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
                    install.release_payload()
        with patch.object(install, "download", return_value=b"[]"):
            with self.assertRaisesRegex(ValueError, "metadata"):
                install.release_payload()

    def test_zsh_profile_preserves_user_content_and_is_idempotent(self):
        with tempfile.TemporaryDirectory(prefix="erol-install-test-") as temporary:
            root = Path(temporary)
            profile = root / ".zshrc"
            profile.write_text("export CUSTOM=keep\n", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                for _ in range(2):
                    self.assertEqual(
                        install.configure_posix_path(root, root / "space bin", "/bin/zsh"),
                        [profile],
                    )
            content = profile.read_text()
            self.assertTrue(content.startswith("export CUSTOM=keep\n"))
            self.assertEqual(content.count("# EROL user CLI"), 1)
            self.assertIn("'", content)
            self.assertIn(':"$PATH"', content)

    def test_bash_login_and_interactive_shells_and_zdotdir_are_supported(self):
        with tempfile.TemporaryDirectory(prefix="erol-install-test-") as temporary:
            root = Path(temporary)
            (root / ".bash_profile").write_text("# custom login\n")
            with patch.dict(os.environ, {}, clear=True):
                paths = install.configure_posix_path(root, root / "bin", "/bin/bash")
            self.assertEqual(paths, [root / ".bashrc", root / ".bash_profile"])
            self.assertFalse((root / ".profile").exists())
            zdotdir = root / "zsh config"
            with patch.dict(os.environ, {"ZDOTDIR": str(zdotdir)}, clear=True):
                self.assertEqual(
                    install.configure_posix_path(root, root / "bin", "/bin/zsh"),
                    [zdotdir / ".zshrc"],
                )

    def test_unknown_shell_does_not_edit_an_unread_profile(self):
        with tempfile.TemporaryDirectory(prefix="erol-install-test-") as temporary:
            root = Path(temporary)
            self.assertEqual(install.configure_posix_path(root, root / "bin", "/bin/fish"), [])
            self.assertEqual(list(root.iterdir()), [])

    def test_bash_login_precedes_profile_when_no_bash_profile_exists(self):
        with tempfile.TemporaryDirectory(prefix="erol-install-test-") as temporary:
            root = Path(temporary)
            login = root / ".bash_login"
            login.write_text("# existing login\n")
            paths = install.configure_posix_path(root, root / "bin", "/bin/bash")
            self.assertEqual(paths, [root / ".bashrc", login])
            self.assertIn("# EROL user CLI", login.read_text())
            self.assertFalse((root / ".profile").exists())

    def test_failure_before_environment_creation_preserves_original_error(self):
        with tempfile.TemporaryDirectory(prefix="erol-install-test-") as temporary:
            root = Path(temporary)
            with patch.object(
                install.venv.EnvBuilder, "create", side_effect=OSError("venv unavailable")
            ):
                with self.assertRaisesRegex(OSError, "venv unavailable"):
                    install.install_cli(
                        root / "home",
                        root / "bin",
                        "0.2.5",
                        "erol_ai-0.2.5-py3-none-any.whl",
                        b"wheel",
                    )

    def test_atomic_reservation_never_removes_a_concurrent_environment(self):
        with tempfile.TemporaryDirectory(prefix="erol-install-test-") as temporary:
            root = Path(temporary)
            environment = root / "home/cli/0.2.5"
            mkdir = Path.mkdir

            def concurrent(path, *args, **kwargs):
                if path == environment:
                    mkdir(path)
                    (path / "other-installer").write_bytes(b"preserve")
                    raise FileExistsError("another installer reserved the directory")
                return mkdir(path, *args, **kwargs)

            with patch.object(Path, "mkdir", new=concurrent):
                with self.assertRaises(FileExistsError):
                    install.install_cli(
                        root / "home",
                        root / "bin",
                        "0.2.5",
                        "erol_ai-0.2.5-py3-none-any.whl",
                        b"wheel",
                    )
            self.assertEqual((environment / "other-installer").read_bytes(), b"preserve")

    def test_windows_path_precedes_old_npm_wrapper_without_duplicates(self):
        class Key:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        registry = types.SimpleNamespace(
            HKEY_CURRENT_USER=1,
            HKEY_LOCAL_MACHINE=2,
            REG_EXPAND_SZ=2,
            CreateKey=lambda *args: Key(),
            QueryValueEx=lambda *args: (r"C:\npm;C:\USER\BIN;C:\tools", 2),
            OpenKey=lambda *args: Key(),
        )
        calls = []
        registry.SetValueEx = lambda *args: calls.append(args)
        windll = types.SimpleNamespace(
            user32=types.SimpleNamespace(SendMessageTimeoutW=lambda *args: 1)
        )
        with (
            patch.dict("sys.modules", {"winreg": registry}),
            patch("ctypes.windll", windll, create=True),
            patch.object(install.shutil, "which", return_value=None),
        ):
            install.configure_windows_path(Path(r"C:\user\bin"))
        self.assertEqual(calls[0][-1], r"C:\user\bin;C:\npm;C:\tools")

    def test_existing_incomplete_environment_and_invalid_version_remain_intact(self):
        with tempfile.TemporaryDirectory(prefix="erol-install-test-") as temporary:
            root = Path(temporary)
            environment = root / "home/cli/0.2.5"
            environment.mkdir(parents=True)
            sentinel = environment / "existing"
            sentinel.write_bytes(b"keep")
            with self.assertRaisesRegex(ValueError, "incomplete"):
                install.install_cli(
                    root / "home", root / "bin", "0.2.5", "erol_ai-0.2.5-py3-none-any.whl", b"wheel"
                )
            self.assertEqual(sentinel.read_bytes(), b"keep")
            with self.assertRaisesRegex(ValueError, "version"):
                install.install_cli(root / "home", root / "bin", "../escape", "other.whl", b"wheel")

    def test_venv_failure_removes_only_new_environment(self):
        with tempfile.TemporaryDirectory(prefix="erol-install-test-") as temporary:
            root = Path(temporary)
            old = root / "home/cli/0.2.4"
            old.mkdir(parents=True)
            (old / "keep").write_bytes(b"old CLI")

            def fail(environment):
                environment.mkdir(exist_ok=True)
                raise OSError("missing venv support")

            with patch.object(install.venv.EnvBuilder, "create", side_effect=fail):
                with self.assertRaisesRegex(OSError, "venv support"):
                    install.install_cli(
                        root / "home",
                        root / "bin",
                        "0.2.5",
                        "erol_ai-0.2.5-py3-none-any.whl",
                        b"wheel",
                    )
            self.assertEqual((old / "keep").read_bytes(), b"old CLI")
            self.assertFalse((root / "home/cli/0.2.5").exists())


if __name__ == "__main__":
    unittest.main()
