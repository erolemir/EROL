"""Exercise the real user installer against the built wheel in an external home."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path
from unittest.mock import patch

from scripts import install


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))["project"]["version"]
    name = f"erol_ai-{version}-py3-none-any.whl"
    payload = (root / "dist" / name).read_bytes()
    record = {
        "version": version,
        "repository": install.REPOSITORY,
        "channel": "stable",
        "source_commit": "a" * 40,
    }
    sums = (hashlib.sha256(payload).hexdigest() + "  " + name + "\n").encode()
    with tempfile.TemporaryDirectory(prefix="erol-user-install-smoke-") as temporary:
        base = Path(temporary)
        home, bin_dir = base / "external home", base / "user bin"
        blocked = base / "global npm prefix"
        blocked.mkdir()
        sentinel = blocked / "unchanged"
        sentinel.write_text("global directory must not be used")
        blocked.chmod(0o555)
        try:
            with patch.dict(os.environ, {"npm_config_prefix": str(blocked)}):
                with patch.object(
                    install, "download", side_effect=[json.dumps(record).encode(), sums, payload]
                ):
                    if install.main(["--home", str(home), "--bin-dir", str(bin_dir), "--no-path"]):
                        raise RuntimeError("Isolated installer failed")
                command = bin_dir / ("erol.exe" if os.name == "nt" else "erol")
                project = base / "explicit project"
                project.mkdir()
                before = command.read_bytes()
                command.write_bytes(b"previous launcher fixture")
                second = install.install_cli(home, bin_dir, version, name, payload)
                backups = list((home / "install-backups").iterdir())
                if (
                    second != command
                    or not backups
                    or backups[0].read_bytes() != b"previous launcher fixture"
                ):
                    raise RuntimeError("Reinstallation failed to preserve the existing command")
                install.install_cli(home, bin_dir, version, name, payload)
                if (
                    command.read_bytes() != before
                    or list((home / "install-backups").iterdir()) != backups
                ):
                    raise RuntimeError(
                        "Same-version reinstallation changed the command or added backups"
                    )
                for arguments in [
                    ["--version"],
                    [
                        "--project",
                        str(project),
                        "--home",
                        str(home),
                        "terminal",
                        "--command",
                        "/menu",
                    ],
                ]:
                    result = subprocess.run(
                        [str(command), *arguments],
                        cwd=project,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        check=True,
                        timeout=30,
                    )
                    if arguments == ["--version"] and result.stdout.strip() != version:
                        raise RuntimeError("Installed version mismatch")
                    if arguments != ["--version"]:
                        choices = json.loads(result.stdout).get("menu_choices", [])
                        if not {"/model", "/files", "/diff"}.issubset(
                            {item["value"] for item in choices}
                        ):
                            raise RuntimeError("Installed menu failed")
                if (
                    sentinel.read_text() != "global directory must not be used"
                    or len(list(blocked.iterdir())) != 1
                ):
                    raise RuntimeError("Global npm prefix was changed")
        finally:
            blocked.chmod(0o755)
        native_shells = []
        if os.name != "nt":
            for name in ("bash", "zsh"):
                shell = shutil.which(name)
                if shell is None:
                    continue
                profiles = base / (name + " profiles")
                profiles.mkdir()
                env = {**os.environ, "HOME": str(profiles), "ZDOTDIR": str(profiles)}
                env.pop("BASH_ENV", None)
                env.pop("ENV", None)
                with patch.dict(os.environ, {"ZDOTDIR": str(profiles)}):
                    install.configure_posix_path(profiles, bin_dir, shell)
                argv = (
                    [shell, "--noprofile", "--rcfile", str(profiles / ".bashrc"), "-ic"]
                    if name == "bash"
                    else [shell, "-d", "-ic"]
                )
                result = subprocess.run(
                    [*argv, "command -v erol"],
                    env=env,
                    cwd=project,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30,
                )
                if Path(result.stdout.strip()).resolve() != command.resolve():
                    raise RuntimeError(f"{name} startup did not discover the installed CLI")
                native_shells.append(name)
        print(
            json.dumps(
                {
                    "passed": True,
                    "platform": os.name,
                    "version": version,
                    "installation": "real wheel, isolated home and bin",
                    "reinstall_backup": True,
                    "global_npm_prefix_unchanged": True,
                    "real_user_path_changed": False,
                    "native_shell_profile_checks": native_shells,
                }
            )
        )


if __name__ == "__main__":
    main()
