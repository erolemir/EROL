"""Execute an unpacked local npm archive without network or user installation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path


def smoke(archive: Path) -> None:
    canonical_root = Path(__file__).resolve().parents[1]
    fixtures = json.loads(
        (canonical_root / "src/erol/data/routing_cases.json").read_text(encoding="utf-8")
    )["cases"]
    expected_count = len(fixtures)
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required for npm archive validation")
    with tempfile.TemporaryDirectory(prefix="erol-npm-smoke-") as temporary:
        root = Path(temporary)
        with tarfile.open(archive, "r:gz") as package:
            for member in package.getmembers():
                target = (root / member.name).resolve()
                if not target.is_relative_to(root) or not member.isfile():
                    raise ValueError("Archive contains a path escape or non-file member")
                if any(part in {".venv", "__pycache__", "node_modules"} for part in target.parts):
                    raise ValueError("Private build artifacts entered the npm archive")
                if target.suffix in {".db", ".pyc"}:
                    raise ValueError("Private runtime artifacts entered the npm archive")
                stream = package.extractfile(member)
                if stream is None:
                    raise ValueError("Archive file is unreadable")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(stream.read())
        project = root / "unrelated project"
        project.mkdir()
        env = {**os.environ, "EROL_PYTHON": sys.executable, "PYTHONPATH": "."}
        (project / "json.py").write_text("raise RuntimeError('import shadow executed')", "utf-8")
        launchers = [
            "bin/erol.mjs",
            "plugins/erol/scripts/erol.mjs",
            "bin/erol.py",
            "plugins/erol/scripts/erol.py",
        ]
        for launcher in launchers:
            command = [
                *(
                    [node]
                    if launcher.endswith(".mjs")
                    else [sys.executable, "-I", "-S", "-X", "utf8"]
                ),
                str(root / "package" / launcher),
                "--project",
                str(project),
                "--home",
                str(root / "home"),
                "eval",
            ]
            result = subprocess.run(
                command,
                cwd=project,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Packaged launcher failed: {launcher}")
            report = json.loads(result.stdout)
            if (
                not report["passed"]
                or report["routing"]["total"] != expected_count
                or report["routing"]["passed_count"] != expected_count
            ):
                raise RuntimeError("Packaged runtime routing failed")
        print(
            json.dumps({"passed": True, "launchers": launchers, "routing_fixtures": expected_count})
        )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))["project"]["version"]
    smoke(
        Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "dist" / f"erol-{version}.tgz"
    )
