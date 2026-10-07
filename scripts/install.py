"""Install the verified stable CLI into the user's home; Python 3.11+, stdlib only."""

from __future__ import annotations

import argparse
import hashlib
import json
import ntpath
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid
import venv
from pathlib import Path

REPOSITORY = "erolemir/EROL"
STABLE = f"https://raw.githubusercontent.com/{REPOSITORY}/stable/RELEASE.json"
VERSION = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")


def download(url: str, limit: int) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Release download exceeds the expected size")
    return data


def release_payload() -> tuple[str, str, bytes]:
    record = json.loads(download(STABLE, 4096))
    if not isinstance(record, dict):
        raise ValueError("Invalid stable release metadata")
    version = record.get("version", "")
    if (
        not isinstance(version, str)
        or VERSION.fullmatch(version) is None
        or record.get("repository") != REPOSITORY
        or record.get("channel") != "stable"
        or re.fullmatch(r"[0-9a-f]{40}", str(record.get("source_commit", ""))) is None
    ):
        raise ValueError("Invalid stable release metadata")
    name = f"erol_ai-{version}-py3-none-any.whl"
    base = f"https://github.com/{REPOSITORY}/releases/download/v{version}"
    sums = download(f"{base}/SHA256SUMS", 65536).decode("ascii")
    matches = [line.split("  ") for line in sums.splitlines() if line.endswith("  " + name)]
    if len(matches) != 1 or len(matches[0]) != 2:
        raise ValueError("Release wheel checksum is missing or ambiguous")
    digest = matches[0][0]
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise ValueError("Invalid release checksum")
    payload = download(f"{base}/{name}", 20 * 1024 * 1024)
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError("Release wheel checksum does not match; nothing installed")
    return version, name, payload


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=120)
    if result.returncode:
        raise ValueError(result.stderr.strip() or f"Installation command failed: {args[0]}")
    return result.stdout.strip()


def install_cli(home: Path, bin_dir: Path, version: str, name: str, payload: bytes) -> Path:
    if VERSION.fullmatch(version) is None or name != f"erol_ai-{version}-py3-none-any.whl":
        raise ValueError("Invalid installation version or filename")
    home = home.expanduser().resolve()
    environment = home / "cli" / version
    if not environment.resolve().is_relative_to(home):
        raise ValueError("CLI environment resolves outside the selected EROL home")
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    source = scripts / ("erol.exe" if os.name == "nt" else "erol")
    if environment.exists():
        print("[2/4] Checking the existing installation...", flush=True)
        if not source.is_file() or run(str(source), "--version") != version:
            raise ValueError(f"Existing CLI environment is incomplete: {environment}")
    else:
        print("[2/4] Creating your isolated Python environment...", flush=True)
        environment.parent.mkdir(parents=True, exist_ok=True)
        # Reserve the final venv path atomically before cleanup ownership begins.
        environment.mkdir()
        try:
            venv.EnvBuilder(with_pip=True).create(environment)
            print("[3/4] Installing the verified package...", flush=True)
            with tempfile.TemporaryDirectory(prefix="erol-install-wheel-") as directory:
                wheel = Path(directory) / name
                wheel.write_bytes(payload)
                run(
                    str(python), "-I", "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)
                )
            if run(str(source), "--version") != version:
                raise ValueError("Installed CLI version differs from the verified wheel")
        except Exception:
            # Only this newly-created, explicitly bound environment may be removed.
            if (
                environment.exists()
                and environment.resolve().is_relative_to(home)
                and not environment.is_symlink()
            ):
                shutil.rmtree(environment, ignore_errors=True)
            raise
    bin_dir = bin_dir.expanduser().absolute()
    bin_dir.mkdir(parents=True, exist_ok=True)
    target = bin_dir / source.name
    if target.is_dir():
        raise ValueError(f"Command destination is a directory: {target}")
    if target.is_file() and not target.is_symlink() and target.read_bytes() == source.read_bytes():
        shutil.copymode(source, target)
        print(f"Already up to date: EROL {version}", flush=True)
        return target
    if target.exists() or target.is_symlink():
        backups = home / "install-backups"
        backups.mkdir(parents=True, exist_ok=True)
        backup = backups / (target.name + "." + uuid.uuid4().hex)
        if target.is_symlink():
            backup.symlink_to(os.readlink(target))
        else:
            shutil.copy2(target, backup)
        print(f"Previous command backed up: {backup}")
    temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def configure_posix_path(user_home: Path, bin_dir: Path, shell: str) -> list[Path]:
    kind = Path(shell).name
    if kind == "zsh":
        # zsh reads .zshrc from ZDOTDIR when it is configured.
        profiles = [Path(os.environ.get("ZDOTDIR", str(user_home))) / ".zshrc"]
    elif kind == "bash":
        login = next(
            (
                name
                for name in (".bash_profile", ".bash_login", ".profile")
                if (user_home / name).exists()
            ),
            ".profile",
        )
        profiles = [user_home / ".bashrc", user_home / login]
    elif kind in {"sh", "dash", "ksh", ""}:
        profiles = [user_home / ".profile"]
    else:
        print(f"Add this directory to your shell PATH: {bin_dir}")
        return []
    path = shlex.quote(str(bin_dir))
    block = f'\n# EROL user CLI\nexport PATH={path}:"$PATH"\n# End EROL user CLI\n'
    for profile in profiles:
        existing = (
            profile.read_text(encoding="utf-8", errors="surrogateescape")
            if profile.exists()
            else ""
        )
        if block in existing:
            continue
        profile.parent.mkdir(parents=True, exist_ok=True)
        with profile.open("a", encoding="utf-8", errors="surrogateescape") as stream:
            stream.write(block)
    return profiles


def configure_windows_path(bin_dir: Path) -> None:
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        try:
            value, kind = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            value, kind = "", winreg.REG_EXPAND_SZ

        def normalize(value: str) -> str:
            return ntpath.normcase(ntpath.expandvars(value).rstrip("\\/"))

        parts = [
            part for part in value.split(";") if part and normalize(part) != normalize(str(bin_dir))
        ]
        updated = ";".join([str(bin_dir), *parts])
        if updated != value:
            winreg.SetValueEx(key, "Path", 0, kind, updated)
    # Explorer must learn the changed user PATH before launching a fresh terminal.
    import ctypes

    ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x0002, 1000, None)
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ) as key:
            system_path, _ = winreg.QueryValueEx(key, "Path")
        conflict = shutil.which("erol", path=ntpath.expandvars(system_path))
        target = bin_dir / "erol.exe"
        if conflict and normalize(conflict) != normalize(str(target)):
            print(
                f"Another EROL command precedes user PATH: {conflict}. Use the full command below."
            )
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home() / ".erol")
    parser.add_argument("--bin-dir", type=Path, default=Path.home() / ".local" / "bin")
    parser.add_argument("--no-path", action="store_true", help="Do not change shell/user PATH")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):  # noqa: UP036 - bootstrap runs before any installation
        print("EROL needs Python 3.11+. Install it, then run this command again.", file=sys.stderr)
        return 1
    try:
        stage = "download"
        print("[1/4] Downloading and verifying the stable EROL release...", flush=True)
        version, name, payload = release_payload()
        stage = "installation"
        target = install_cli(args.home, args.bin_dir, version, name, payload)
        print(f"Installed EROL {version}: {target}")
        print("[4/4] Making the command available...", flush=True)
        if not args.no_path:
            try:
                if os.name == "nt":
                    configure_windows_path(target.parent)
                    configured = True
                else:
                    configured = bool(
                        configure_posix_path(
                            Path.home(), target.parent, os.environ.get("SHELL", "")
                        )
                    )
                if configured:
                    print("Close and reopen the terminal, then type: erol")
            except OSError as error:
                print(f"CLI installed, but PATH setup failed: {error}", file=sys.stderr)
                print(f"Add this directory to your user PATH: {target.parent}", file=sys.stderr)
        immediate = (
            "& '" + str(target).replace("'", "''") + "'"
            if os.name == "nt"
            else shlex.quote(str(target))
        )
        print("Run now: " + immediate)
        print("In EROL: press Enter for the menu, or type /start to choose a connection.")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"EROL {stage} failed: {error}", file=sys.stderr)
        if isinstance(error, PermissionError):
            print(
                "Use a writable --home and --bin-dir in your own account, "
                "then rerun the installer.",
                file=sys.stderr,
            )
        elif stage == "download":
            print(
                "Check your internet/proxy connection to GitHub, "
                "then run the same installation command again.",
                file=sys.stderr,
            )
        elif "Existing CLI environment is incomplete" in str(error):
            print(
                "Preserve or rename the incomplete folder shown above, "
                "then rerun the installer. It was not removed.",
                file=sys.stderr,
            )
        else:
            print(
                "Check Python 3.11+ and venv/pip support. Rerun the same command; "
                "your previous launcher is preserved until replacement succeeds.",
                file=sys.stderr,
            )
        print(
            "No administrator/sudo is needed. Check Python venv support, network "
            "and home-directory write access.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
