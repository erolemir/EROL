"""A deterministic, trusted fixture runner for the learning loop, not an LLM benchmark."""

from __future__ import annotations

import tempfile
from pathlib import Path

from erol.common import digest
from erol.identity import detect_project
from erol.learning import LearningEngine
from erol.registry import Skill
from erol.store import Store

REMEDY = "Use a stable composite Version and ID cursor"
Row = tuple[int, int]


def paginate(rows: list[Row], *, composite: bool, batch_size: int = 2) -> list[Row]:
    """Known trusted implementation fixture; never evaluates generated code."""
    remaining = sorted(rows)
    cursor: Row | None = None
    result: list[Row] = []
    while True:
        available = [
            row
            for row in remaining
            if cursor is None or (row > cursor if composite else row[0] > cursor[0])
        ]
        batch = available[:batch_size]
        if not batch:
            return result
        result.extend(batch)
        cursor = batch[-1]


def check_remedy(skill: Skill | None, rows: list[Row]) -> dict:
    """A narrow fixture interpreter maps a reviewed remedy to the trusted cursor implementation."""
    if skill is not None and REMEDY not in skill.body:
        raise ValueError("Fixture interpreter supports only the reviewed composite-cursor remedy")
    expected = sorted(rows)
    actual = paginate(rows, composite=True)
    if actual != expected or len(set(actual)) != len(actual):
        raise ValueError("Composite cursor failed the data-integrity fixture")
    return {
        "name": "heldout-composite-cursor-data-integrity",
        "passed": True,
        "reference": "fixture-sha256-" + digest({"input": rows, "output": actual}),
    }


def report(check: dict) -> dict:
    return {
        "implementer": "trusted-fixture-runner",
        "reviewer": "independent-fixture-assertions",
        "tests": [check],
        "findings": [],
    }


def learning_demo() -> dict:
    """Run actual deterministic regressions and local lifecycle transitions in an isolated home."""
    datasets = [
        [(1, j) for j in range(1, 6)],
        [(1, j) for j in range(1, 4)] + [(2, 4), (2, 5), (2, 6)],
        [(2, j) for j in range(1, 8)],
    ]
    with tempfile.TemporaryDirectory(prefix="erol-demo-") as temporary:
        base = Path(temporary)
        project_root = base / "project"
        project_root.mkdir()
        with Store(base / "home", detect_project(project_root)) as store:
            engine = LearningEngine(store)
            repeated = []
            candidate = None
            for index, rows in enumerate(datasets, 1):
                if paginate(rows, composite=False) == sorted(rows):
                    raise ValueError("Bug fixture no longer reproduces")
                check = check_remedy(None, rows)
                result = engine.record_incident(
                    {
                        "id": f"incident-{index}",
                        "task_id": f"repair-{index}",
                        "symptom": "Import skips rows at equal-version batch boundaries",
                        "error": (
                            f"ImportCursorError skipped rows request=run{index} at 14:3{index}"
                        ),
                        "component": "contact-import",
                        "exception": "ImportCursorError",
                        "root_category": "nonunique-cursor",
                        "root_cause": "Version alone is not a unique pagination key",
                        "solution": REMEDY,
                        "confidence": 0.95,
                        "verification": report(check),
                    }
                )
                repeated.append(len(result["repeat_matches"]))
                candidate = result["candidate"]
            if candidate is None:
                raise ValueError("Expected a draft after three distinct repairs")
            skill = Skill.from_dict(candidate["skill"])
            heldout = [(3, j) for j in range(1, 7)] + [(4, 7), (4, 8)]
            behavior = check_remedy(skill, heldout)
            evaluation = engine.evaluate(
                candidate["id"],
                {
                    "positive_tasks": [skill.triggers[0] + " please investigate"],
                    "negative_tasks": ["CSS spacing", skill.triggers[0] + " different root cause"],
                    "behavior": report(behavior),
                },
            )
            active = engine.activate(candidate["id"])
            admitted = []
            for index in range(3):
                receipt = engine.begin_task(f"usage-{index}", skill.triggers[0])
                admitted.append(skill.name in receipt["plan"]["context"]["selected_skills"])
                checks = check_remedy(skill, [(5 + index, j) for j in range(1, 6)])
                engine.complete_task(f"usage-{index}", report(checks))
            promotion = engine.promotion_candidate(skill.name)
            export = engine.export_skill(skill.name)
            if not Path(export["path"]).is_file():
                raise ValueError("Project export missing")
            return {
                "passed": evaluation["passed"] and all(admitted),
                "kind": "deterministic_learning_and_pagination_fixture",
                "bug_reproductions": 3,
                "historical_matches_per_encounter": repeated,
                "candidate_count": len(store.list("candidates")),
                "active_version": active["version"],
                "heldout_behavior_passed": behavior["passed"],
                "successful_real_fixture_uses": engine.metrics(skill.name)["successful_tasks"],
                "promotion_status": promotion["status"],
                "global_registry_modified": False,
                "limitations": [
                    "Trusted deterministic fixture interpreter, not an autonomous harness trial",
                    "Reviewer is a separate assertion role, not a human security audit",
                    "No measured LLM success, resolution-time or actual token savings",
                ],
            }
