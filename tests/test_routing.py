import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from erol.common import digest
from erol.orchestration import routing_eval
from erol.registry import Registry, Skill, evaluate_skill, matches


class FakeStore:
    project_id = "project-a"

    def __init__(self, records):
        self.records = records

    def list(self, kind):
        assert kind == "skills"
        return copy.deepcopy(self.records)


def project_skill():
    return Skill(
        "custom-import-debug",
        "Debug project-specific contact import.",
        ["contact import"],
        ["marketing contacts"],
        "# Contact import\n\n## Workflow\n"
        "1. Inspect the import cursor and reproduce boundary ties.\n"
        "2. Use a stable unique cursor.\n3. Verify regression tests and evidence.\n",
        scope="project",
        project_id="project-a",
    )


class RoutingTests(unittest.TestCase):
    def test_builtin_discovery_does_not_read_bodies(self):
        original = Path.read_text
        reads = []

        def guarded(path, *args, **kwargs):
            reads.append(path.name)
            if path.name == "SKILL.md":
                self.fail("discovery loaded body")
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", guarded):
            registry = Registry()
            self.assertEqual(24, len(registry.list()))
            registry.explain("pagination")
        self.assertEqual(["registry.json"], reads)

    def test_route_loads_only_selected_bodies(self):
        registry = Registry()
        original = Path.read_text
        reads = []

        def observed(path, *args, **kwargs):
            reads.append(path.parent.name)
            return original(path, *args, **kwargs)

        with patch.object(Path, "read_text", observed):
            skills = registry.route("pagination", limit=1)
        self.assertEqual(["stable-pagination"], reads)
        self.assertEqual("stable-pagination", skills[0].name)
        self.assertIn("## Workflow", skills[0].body)

    def test_golden_positive_negative_routing(self):
        report = routing_eval()
        self.assertTrue(report["passed"], [c for c in report["cases"] if not c["passed"]])
        self.assertEqual(32, report["total"])
        self.assertFalse(report["behavior_verified"])

    def test_whole_word_and_negative_precedence(self):
        skill = project_skill()
        self.assertFalse(matches(skill, "contact imports"))
        self.assertTrue(matches(skill, "CONTACT IMPORT"))
        self.assertFalse(matches(skill, "contact import marketing contacts"))
        self.assertFalse(Registry().explain("metadata duplication"))

    def test_project_scope_status_and_integrity(self):
        skill = project_skill()
        active = {
            **skill.to_dict(),
            "id": "skill-1",
            "status": "project_active",
            "digest": digest(skill.to_dict()),
        }
        disabled = {**active, "name": "disabled-skill", "status": "needs_revision"}
        foreign = {**active, "name": "foreign-skill", "project_id": "other-project"}
        registry = Registry(project_store=FakeStore([active, disabled, foreign]))
        self.assertEqual([skill.name], [s.name for s in registry.route("contact import")])
        returned = registry.get(skill.name)
        returned.triggers.append("mutated")
        self.assertEqual(["contact import"], registry.get(skill.name).triggers)
        tampered = {**active, "triggers": ["any task"]}
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            Registry(project_store=FakeStore([tampered]))

    def test_builtin_body_integrity_and_path_containment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entry = {
                "name": "example",
                "description": "Example",
                "triggers": ["example"],
                "avoid_when": [],
                "path": "../escaped.md",
            }
            (root / "registry.json").write_text(json.dumps({"skills": [entry]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escapes"):
                Registry(root)
            entry.update(path="SKILL.md", digest="bad")
            (root / "registry.json").write_text(json.dumps({"skills": [entry]}), encoding="utf-8")
            (root / "SKILL.md").write_text("changed body", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                Registry(root).get("example")

    def test_static_eval_labels_and_empty_fixtures(self):
        skill = project_skill()
        report = evaluate_skill(skill)
        self.assertTrue(report["passed"], report)
        self.assertFalse(report["behavior_verified"])
        self.assertFalse(report["security_verified"])
        self.assertTrue(report["synthetic_trigger_cases"])
        self.assertEqual(digest(skill.to_dict()), report["skill_digest"])
        self.assertFalse(evaluate_skill(skill, cases=[])["passed"])
        positive_only = [{"task": "contact import", "should_trigger": True}]
        self.assertFalse(evaluate_skill(skill, positive_only)["passed"])
        with self.assertRaises(ValueError):
            evaluate_skill(skill, [{"task": "contact import", "should_trigger": "yes"}])

    def test_explicit_eval_negatives_and_secret_rejection(self):
        skill = project_skill()
        cases = [
            {"task": "contact import", "should_trigger": True},
            {"task": "contact import marketing contacts", "should_trigger": False},
        ]
        self.assertTrue(evaluate_skill(skill, cases)["passed"])
        skill.body += "\napi_key=unredacted-demo-key\n"
        self.assertFalse(evaluate_skill(skill, cases)["passed"])

    def test_duplicate_workflow_and_metadata_copy(self):
        registry = Registry()
        original = registry.get("stable-pagination")
        clone = Skill.from_dict({**original.to_dict(), "name": "other-pagination"})
        duplicates = registry.duplicates(clone)
        self.assertIn("stable-pagination", [item["name"] for item in duplicates])
        metadata = registry.list()
        metadata[0]["triggers"].append("modified")
        self.assertNotIn("modified", registry.list()[0]["triggers"])

    def test_builtin_skills_pass_static_lint(self):
        registry = Registry()
        for metadata in registry.list():
            with self.subTest(skill=metadata["name"]):
                report = evaluate_skill(registry.get(metadata["name"]))
                self.assertTrue(report["passed"], report)

    def test_limit_validation(self):
        registry = Registry()
        self.assertEqual([], registry.route("pagination", 0))
        for limit in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                registry.route("pagination", limit)


if __name__ == "__main__":
    unittest.main()
