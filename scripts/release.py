"""Version tested main code on stable; never commit or push back to main.

Only the trusted release workflow publishes. Local callers can run prepare on a
clean disposable checkout to inspect the same deterministic version changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "erolemir/EROL"
SEMVER = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z")


def command(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, encoding="utf-8").strip()


def version_tuple(value: str) -> tuple[int, int, int]:
    match = SEMVER.fullmatch(value)
    if match is None:
        raise ValueError("Release versions must be three numeric components")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def next_version(base: str, tags: list[str]) -> str:
    floor = version_tuple(base)
    released = [
        version_tuple(tag[1:]) for tag in tags if tag.startswith("v") and SEMVER.fullmatch(tag[1:])
    ]
    if released:
        latest = max(released)
        floor = max(floor, (latest[0], latest[1], latest[2] + 1))
    return ".".join(map(str, floor))


def stable_record() -> dict[str, str] | None:
    probe = subprocess.run(
        ["git", "show", "refs/remotes/origin/stable:RELEASE.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return json.loads(probe.stdout) if probe.returncode == 0 else None


def prepare(source_sha: str) -> str:
    if (
        not re.fullmatch(r"[0-9a-f]{40}", source_sha)
        or command("git", "rev-parse", "HEAD") != source_sha
    ):
        raise ValueError("Prepare requires the exact validated source commit")
    if command("git", "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Prepare requires a clean tracked source tree")
    base = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))["project"]["version"]
    previous = stable_record()
    version = (
        previous["version"]
        if previous and previous["source_commit"] == source_sha
        else next_version(base, command("git", "tag", "--list", "v*").splitlines())
    )
    version_tuple(version)
    for name in ("package.json", "package-lock.json"):
        path = ROOT / name
        data = json.loads(path.read_text("utf-8"))
        data["version"] = version
        if name == "package-lock.json":
            data["packages"][""]["version"] = version
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", "utf-8")
    path = ROOT / "pyproject.toml"
    text = path.read_text("utf-8")
    text, count = re.subn(
        r'^version = "[^"]+"$', f'version = "{version}"', text, count=1, flags=re.M
    )
    if count != 1:
        raise ValueError("Missing canonical package version")
    path.write_text(text, "utf-8")
    (ROOT / "src/erol/__init__.py").write_text(
        f'"""EROL canonical core."""\n\n__version__ = "{version}"\n', "utf-8"
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_adapter_drift.py"), "--write"],
        check=True,
        cwd=ROOT,
    )
    (ROOT / "RELEASE.json").write_text(
        json.dumps(
            {
                "version": version,
                "source_commit": source_sha,
                "repository": REPOSITORY,
                "channel": "stable",
                "license": "AGPL-3.0-only",
            },
            indent=2,
        )
        + "\n",
        "utf-8",
    )
    print(f"Prepared {version} from {source_sha}; main unchanged")
    return version


def publish() -> None:
    record = json.loads((ROOT / "RELEASE.json").read_text("utf-8"))
    version = record["version"]
    version_tuple(version)
    source = record["source_commit"]
    if command("git", "rev-parse", "HEAD") != source:
        raise ValueError("Publish must start from the validated source checkout")
    if record["repository"] != REPOSITORY:
        raise ValueError("Unexpected release repository")
    # Recheck immediately before publishing. A newer main commit needs its own CI.
    if command("git", "ls-remote", "origin", "refs/heads/main").split()[0] != source:
        raise ValueError("Main advanced; wait for the newer commit's validation")
    assets = sorted((ROOT / "dist").glob("*"))
    expected = {
        f"erol_ai-{version}-py3-none-any.whl",
        f"erol_ai-{version}.tar.gz",
        f"erol-{version}.tgz",
    }
    if {path.name for path in assets if path.is_file()} != expected:
        raise ValueError("Release requires exactly the current wheel, sdist and npm package")
    sums = ROOT / "dist/SHA256SUMS"
    sums.write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in assets
        ),
        "utf-8",
    )
    subprocess.run(["git", "add", "--all"], cwd=ROOT, check=True)
    tree = command("git", "write-tree")
    previous = stable_record()
    if previous and previous["source_commit"] == source:
        commit = command("git", "rev-parse", "refs/remotes/origin/stable")
        if command("git", "rev-parse", f"{commit}^{{tree}}") != tree:
            raise ValueError("Retry would change an existing immutable release")
    else:
        parents = ["-p", source]
        if previous:
            parents = ["-p", command("git", "rev-parse", "refs/remotes/origin/stable"), *parents]
        commit = command(
            "git", "commit-tree", tree, *parents, "-m", f"release: v{version} from {source}"
        )
    tag = f"v{version}"
    subprocess.run(
        [
            "git",
            "push",
            "--atomic",
            "origin",
            f"{commit}:refs/heads/stable",
            f"{commit}:refs/tags/{tag}",
        ],
        cwd=ROOT,
        check=True,
    )
    notes = ROOT / ".validation/release-notes.md"
    notes.parent.mkdir(exist_ok=True)
    notes.write_text(
        f"EROL {version}, automatically built after validation on Linux, macOS and Windows.\n\n"
        f"Source: https://github.com/{REPOSITORY}/commit/{source}\n\n"
        "Install the native marketplace from `erolemir/EROL` at ref `stable`. "
        "See README for Codex and Claude instructions. "
        "Local project memory stays outside the plugin.\n\n"
        "Packages are GitHub release assets; no npm or PyPI registry publication is implied. "
        "Licensed AGPL-3.0-only. SHA256SUMS covers the three package archives.\n",
        "utf-8",
    )
    existing = subprocess.run(
        ["gh", "release", "view", tag, "--repo", REPOSITORY], capture_output=True, check=False
    )
    action = "upload" if existing.returncode == 0 else "create"
    args = [
        "gh",
        "release",
        action,
        tag,
        *(str(path) for path in [*assets, sums, ROOT / "RELEASE.json"]),
        "--repo",
        REPOSITORY,
    ]
    if action == "upload":
        print(f"Release {tag} already exists; existing assets retained")
        return
    args += ["--title", f"EROL {version}", "--notes-file", str(notes)]
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("prepare").add_argument("--source-sha", required=True)
    sub.add_parser("publish")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.source_sha)
    else:
        publish()


if __name__ == "__main__":
    main()
