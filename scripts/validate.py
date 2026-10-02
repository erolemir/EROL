"""Release checks in temporary external homes; no real user configuration mutations."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from erol.cli import parser, run
from erol.demo import learning_demo
from erol.registry import Registry


def validate() -> int:
    with tempfile.TemporaryDirectory(prefix="erol-validation-") as temporary:
        base = Path(temporary)
        repo = base / "project"
        repo.mkdir()
        argv = ["--project", str(repo), "--home", str(base / "home")]
        for command in (["eval"], ["lint", "context"]):
            result = run(parser().parse_args(argv + command))
            summary = {"command": command, "passed": result["passed"]}
            if command == ["eval"]:
                summary.update(
                    {
                        "pack_count": len(result["pack"]["skills"]),
                        "routing_passed": result["routing"]["passed_count"],
                        "routing_total": result["routing"]["total"],
                    }
                )
            else:
                summary.update(result)
            print(json.dumps(summary, indent=2))
            if not result["passed"]:
                return 1
        report = learning_demo()
        print(json.dumps(report, indent=2))
        if not report["passed"]:
            return 1
        if len(Registry().list()) != 24:
            raise ValueError("Pack metadata mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(validate())
