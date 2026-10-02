"""Direct isolated entry for hosts that deny Node child-process creation.

Run: python -I -S -X utf8 /absolute/path/to/erol.py <CLI arguments>
"""

import sys


def main() -> int:
    if not sys.flags.isolated or not sys.flags.no_site:
        print(
            "Run this launcher with Python 3.11+: python -I -S -X utf8 <erol.py> ...",
            file=sys.stderr,
        )
        return 1
    if sys.version_info < (3, 11):  # noqa: UP036 - standalone entry can run under an older interpreter
        print("EROL requires Python 3.11 or newer.", file=sys.stderr)
        return 1
    from pathlib import Path

    parent = Path(__file__).resolve().parents[1]
    for root in (parent / "src", parent / "runtime"):
        if (root / "erol" / "__main__.py").is_file():
            sys.path.insert(0, str(root))
            from erol.cli import main as core_main

            return core_main()
    print("EROL could not find its bundled runtime.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
