"""Canonical, lazy skill registry and honest deterministic qualification checks."""

from __future__ import annotations

import builtins
import hashlib
import json
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from .common import canonical, digest
from .router import normalize, rank, score
from .security import scan_instructions


@dataclass
class Skill:
    name: str
    description: str
    triggers: list[str]
    avoid_when: list[str]
    body: str
    version: str = "1.0.0"
    scope: str = "builtin"
    project_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Skill:
        return cls(
            **json.loads(
                json.dumps(
                    {field.name: value[field.name] for field in fields(cls) if field.name in value}
                )
            )
        )

    def metadata(self) -> dict[str, Any]:
        value = self.to_dict()
        del value["body"]
        return value


def body_digest(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class Registry:
    """Read metadata at discovery and verify/read bodies only on selection.

    Project store must provide ``list('skills')`` and ``project_id``. Only active
    skills belonging to that store enter routing; candidates never enter it.
    """

    def __init__(self, builtin_root: Path | None = None, project_store: Any = None):
        self.root = (builtin_root or Path(__file__).parent / "data").resolve()
        self.project_store = project_store
        self._metadata: dict[str, dict[str, Any]] = {}
        self._paths: dict[str, Path] = {}
        self._project: dict[str, dict[str, Any]] = {}
        manifest = json.loads((self.root / "registry.json").read_text(encoding="utf-8"))
        for entry in manifest["skills"]:
            entry = dict(entry)
            name = entry["name"]
            if name in self._metadata:
                raise ValueError(f"duplicate skill name: {name}")
            path = (self.root / entry.pop("path")).resolve()
            if not path.is_relative_to(self.root) or path == self.root:
                raise ValueError("skill path escapes canonical data root")
            self._metadata[name] = entry
            self._paths[name] = path
        self.refresh_project()

    def refresh_project(self) -> None:
        self._project.clear()
        if self.project_store is None:
            return
        project_id = getattr(self.project_store, "project_id", None)
        if not project_id:
            raise ValueError("project store must expose project_id")
        for record in self.project_store.list("skills"):
            if record.get("status") != "project_active":
                continue
            if record.get("project_id") != project_id or record.get("scope") != "project":
                continue
            skill = Skill.from_dict(record)
            if skill.name in self._metadata:
                raise ValueError(f"project skill shadows builtin: {skill.name}")
            if record.get("digest") != digest(skill.to_dict()):
                raise ValueError(f"project skill digest mismatch: {skill.name}")
            self._project[skill.name] = dict(record)

    def list(self) -> builtins.list[dict[str, Any]]:
        """Return independent metadata copies without loading builtin bodies."""
        metadata = list(self._metadata.values())
        metadata += [Skill.from_dict(record).metadata() for record in self._project.values()]
        return json.loads(json.dumps(sorted(metadata, key=lambda item: item["name"])))

    def get(self, name: str) -> Skill:
        if name in self._project:
            return Skill.from_dict(self._project[name])
        if name not in self._metadata:
            raise KeyError(f"unknown skill: {name}")
        entry = dict(self._metadata[name])
        path = self._paths[name].resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("skill path escapes canonical data root")
        content = path.read_text(encoding="utf-8")
        # Canonical files have JSON-compatible YAML scalar frontmatter. Core
        # metadata lives in the manifest; adapters export standard SKILL.md.
        if content.startswith("---\n"):
            _, _, content = content.split("---\n", 2)
        body = content.strip() + "\n"
        expected = entry.pop("digest", None)
        if expected and expected != body_digest(body):
            raise ValueError(f"builtin skill digest mismatch: {name}")
        return Skill.from_dict({**entry, "body": body})

    def explain(self, task: str, limit: int = 4) -> builtins.list[dict[str, Any]]:
        return rank(task, self.list(), limit)

    def route(self, task: str, limit: int = 4) -> builtins.list[Skill]:
        return [self.get(result["name"]) for result in self.explain(task, limit)]

    def duplicates(self, skill: Skill) -> builtins.list[dict[str, Any]]:
        """Explicitly requested duplicate checking loads bodies; discovery does not."""
        result = []
        wanted = {normalize(trigger) for trigger in skill.triggers}
        for metadata in self.list():
            other = self.get(metadata["name"])
            existing = {normalize(trigger) for trigger in other.triggers}
            overlap = len(wanted & existing) / max(1, len(wanted | existing))
            same_body = normalize(skill.body) == normalize(other.body)
            if other.name == skill.name or same_body or overlap >= 0.75:
                result.append(
                    {"name": other.name, "same_body": same_body, "trigger_overlap": overlap}
                )
        return result

    find_duplicates = duplicates


def evaluate_skill(skill: Skill, cases: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Lint and route fixtures; does NOT execute an agent or prove task success.

    Fixture form: {task: str, should_trigger: bool}. Default positive fixtures
    are synthetic copies of trigger phrases, and are labelled as such.
    """
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check(
        "name",
        bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill.name)) and len(skill.name) <= 64,
        "lowercase kebab name, at most 64 characters",
    )
    check(
        "description",
        0 < len(skill.description.strip()) <= 1024,
        "nonempty, at most 1024 characters",
    )
    check(
        "version", bool(re.fullmatch(r"\d+\.\d+\.\d+", skill.version)), "semantic numeric version"
    )
    check(
        "scope",
        skill.scope in {"builtin", "project", "global"}
        and (skill.scope != "project" or bool(skill.project_id)),
        "project skills need a project identity",
    )
    valid_triggers = (
        isinstance(skill.triggers, list)
        and bool(skill.triggers)
        and all(isinstance(p, str) and normalize(p) for p in skill.triggers)
    )
    check("triggers", valid_triggers, "at least one explicit nonempty phrase")
    valid_avoids = (
        isinstance(skill.avoid_when, list)
        and bool(skill.avoid_when)
        and all(isinstance(p, str) and normalize(p) for p in skill.avoid_when)
    )
    check("negative_triggers", valid_avoids, "at least one explicit exclusion phrase")
    check(
        "context_budget",
        80 <= len(skill.body.strip()) <= 16000 and len(skill.body.splitlines()) <= 500,
        "80..16000 characters; at most 500 lines; character estimate only",
    )
    check(
        "workflow",
        any(marker in skill.body.casefold() for marker in ("workflow", "1.", "steps")),
        "ordered workflow present",
    )
    check(
        "verification",
        any(
            marker in skill.body.casefold()
            for marker in ("verify", "verification", "test", "evidence")
        ),
        "verification guidance present",
    )
    check(
        "no_instruction_override",
        not bool(
            re.search(
                r"ignore (?:all |previous |system )?instructions|"
                r"disable (?:the )?(?:sandbox|security)|exfiltrat",
                skill.body,
                re.I,
            )
        ),
        "limited suspicious-instruction lint; not a complete security review",
    )
    check(
        "secret_and_instruction_scan",
        not (scan_instructions(skill.body) + scan_instructions(canonical(skill.to_dict()))),
        "conservative local scanner; not an independent security review",
    )
    synthetic = cases is None
    fixtures = (
        cases
        if cases is not None
        else (
            [{"task": trigger, "should_trigger": True} for trigger in skill.triggers]
            + [
                {"task": f"{skill.triggers[0]} {avoid}", "should_trigger": False}
                for avoid in skill.avoid_when
            ]
            if valid_triggers and valid_avoids
            else []
        )
    )
    if not isinstance(fixtures, list) or any(
        not isinstance(case, dict)
        or not isinstance(case.get("task"), str)
        or not isinstance(case.get("should_trigger"), bool)
        for case in fixtures
    ):
        raise ValueError("cases must contain task text and boolean should_trigger")
    check(
        "fixture_coverage",
        any(case.get("should_trigger") is True for case in fixtures)
        and any(case.get("should_trigger") is False for case in fixtures),
        "at least one positive and one negative case required",
    )
    for index, case in enumerate(fixtures):
        actual = (
            score(case["task"], skill.metadata())["score"] > 0
            if valid_triggers and valid_avoids
            else False
        )
        check(f"trigger_case_{index}", actual == case["should_trigger"], case["task"])
    return {
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "body_digest": body_digest(skill.body),
        "skill_digest": digest(skill.to_dict()),
        "kind": "static_workflow_and_trigger_lint",
        "synthetic_trigger_cases": synthetic,
        "behavior_verified": False,
        "security_verified": False,
        "estimated_tokens": (len(skill.body) + 3) // 4,
    }


def matches(skill: Skill, task: str) -> bool:
    return score(task, skill.metadata())["score"] > 0
