"""Install a built wheel offline into a clean environment and run its bundled data."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import textwrap
import tomllib
import venv
from pathlib import Path


def smoke() -> int:
    root = Path(__file__).resolve().parents[1]
    version = tomllib.loads((root / "pyproject.toml").read_text("utf-8"))["project"]["version"]
    expected_pack = len(
        json.loads((root / "src/erol/data/registry.json").read_text("utf-8"))["skills"]
    )
    expected_data = {
        name: hashlib.sha256((root / "src/erol/data" / name).read_bytes()).hexdigest()
        for name in ("registry.json", "agents.json")
    }
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
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if install.returncode:
            print(install.stderr)
            return install.returncode
        code = textwrap.dedent(
            """
            import hashlib, json
            from pathlib import Path
            import erol
            from erol.cli import qualify_pack
            from erol.registry import Registry
            from erol.orchestration import Orchestrator, routing_eval
            from erol.demo import learning_demo
            registry = Registry()
            metadata = registry.list()
            plans = [Orchestrator(registry).plan(item['triggers'][0]) for item in metadata]
            data = Path(erol.__file__).parent / 'data'
            print(json.dumps({
                'module': erol.__file__, 'version': erol.__version__,
                'pack_count': len(metadata), 'pack_passed': qualify_pack(registry)['passed'],
                'plans_checked': len(plans), 'routing_passed': routing_eval()['passed'],
                'learning_passed': learning_demo()['passed'],
                'data_digests': {name: hashlib.sha256((data / name).read_bytes()).hexdigest()
                                 for name in ('registry.json', 'agents.json')}
            }))
            """
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
            if result["pack_count"] == expected_pack
            and result["plans_checked"] == expected_pack
            and result["pack_passed"]
            and result["data_digests"] == expected_data
            and result["routing_passed"]
            and result["learning_passed"]
            else 1
        )


if __name__ == "__main__":
    raise SystemExit(smoke())
