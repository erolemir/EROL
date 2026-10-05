"""Check or regenerate committed static harness bridge snapshots.

This compares renderer output to fixture bytes. It does not establish that either
harness has loaded the adapter or successfully executed a task.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from erol.adapters import (  # noqa: E402
    HARNESSES,
    generated_files,
    instruction_path,
    managed_instruction_block,
)
from erol.common import reject_links  # noqa: E402
from erol.plugin import plugin_files  # noqa: E402


def expected_snapshots() -> dict[Path, str | bytes]:
    result = {}
    for harness in HARNESSES:
        base = ROOT / "adapters" / harness
        result[base / instruction_path(harness)] = managed_instruction_block(harness)
        native_root = Path(".agents" if harness == "codex" else ".claude")
        for native_path, content in generated_files(harness).items():
            # Fixtures share a normalized directory layout; runtime installation
            # still uses the native path provided by generated_files().
            relative = Path(native_path).relative_to(native_root)
            result[base / relative] = content
    result.update({ROOT / path: content for path, content in plugin_files(ROOT).items()})
    return result


def unexpected_bundle_files(expected: dict[Path, str | bytes]) -> list[Path]:
    extras = []
    for directory in (ROOT / "plugins/erol/runtime", ROOT / "plugins/erol/scripts"):
        reject_links(directory)
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            reject_links(path)
            if not path.is_file() or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            if path not in expected:
                extras.append(path)
    return extras


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Read-only byte comparison (default).")
    action.add_argument("--write", action="store_true", help="Regenerate known fixture snapshots.")
    options = parser.parse_args(argv)
    failures = []
    snapshots = expected_snapshots()
    # Validate the complete batch before any mutation; never write through links.
    for path in snapshots:
        reject_links(path)
        if not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("Generated snapshot escapes repository")
    extras = unexpected_bundle_files(snapshots)
    for path, content in snapshots.items():
        expected = content.encode("utf-8") if isinstance(content, str) else content
        if options.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(expected)
        elif not path.is_file() or path.read_bytes() != expected:
            failures.append(str(path.relative_to(ROOT)))
    if failures or extras:
        for path in failures:
            print(f"Adapter fixture drift: {path}")
        for path in extras:
            print(f"Unexpected bundled file: {path.relative_to(ROOT)}; review before removing")
        print("Run python scripts/check_adapter_drift.py --write to regenerate snapshots.")
        return 1
    print(
        "Static adapter snapshots generated."
        if options.write
        else "Static adapter snapshots match renderers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
