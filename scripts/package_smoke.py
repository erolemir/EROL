"""Install a built wheel offline into a clean environment and run its bundled data."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import tomllib
import venv
from pathlib import Path


def smoke() -> int:
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))["project"]["version"]
    wheels = list((root / "dist").glob(f"erol_ai-{version}-*.whl"))
    if len(wheels) != 1:
        raise ValueError("Expected exactly one EROL wheel; build the current version first")
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    with tempfile.TemporaryDirectory(prefix="erol-wheel-") as temporary:
        base = Path(temporary)
        runtime = base / "runtime"
        venv.EnvBuilder(with_pip=True).create(runtime)
        executable = runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        install = subprocess.run(
            [str(executable), "-m", "pip", "install", "--no-index", "--no-deps", str(wheels[0])],
            cwd=base,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if install.returncode:
            print(install.stderr)
            return install.returncode
        code = (
            "import json; import erol; "
            "from erol.registry import Registry; from erol.orchestration import routing_eval; "
            "from erol.demo import learning_demo; "
            "print(json.dumps({'module':erol.__file__,'version':erol.__version__,"
            "'pack_count':len(Registry().list()),'routing_passed':routing_eval()['passed'],"
            "'learning_passed':learning_demo()['passed']}))"
        )
        check = subprocess.run(
            [str(executable), "-c", code],
            cwd=base,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        result = json.loads(check.stdout)
        if not Path(result["module"]).is_relative_to(runtime):
            raise ValueError("Smoke test accidentally loaded repository sources")
        result.pop("module")
        print(json.dumps({"wheel": wheels[0].name, "clean_install": True, **result}, indent=2))
        return (
            0
            if result["pack_count"] == 24 and result["routing_passed"] and result["learning_passed"]
            else 1
        )


if __name__ == "__main__":
    raise SystemExit(smoke())
