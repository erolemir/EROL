import json
import tempfile
import unittest
from pathlib import Path

from erol.common import ErolError
from erol.config import Config


class ConfigTests(unittest.TestCase):
    def test_project_override_and_global_default(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            home, project = base / "home", base / "project"
            home.mkdir()
            project.mkdir()
            (home / "config.json").write_text('{"context_tokens":2000}', encoding="utf-8")
            (project / ".erol.json").write_text('{"context_tokens":1000}', encoding="utf-8")
            config = Config.load(home, project)
            self.assertEqual(config.context_tokens, 1000)
            self.assertFalse(config.global_auto_promotion)

    def test_bad_configuration_does_not_silently_relax_safety(self):
        rejected = [
            {"schema_version": True},
            {"learning_enabled": "yes"},
            {"global_auto_promotion": True},
            {"minimum_pattern_occurrences": 1},
            {"minimum_confidence": float("nan")},
            {"max_active_skills": 7},
            {"context_tokens": 0},
            {"unknown_policy": True},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for fields in rejected:
                (base / ".erol.json").write_text(json.dumps(fields), encoding="utf-8")
                with self.subTest(fields=list(fields)), self.assertRaises(ErolError):
                    Config.load(base / "home", base)

    def test_schema_defaults_match_runtime_configuration(self):
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / "schemas/config.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(Config().to_dict()), set(schema["properties"]))
        for field, value in Config().to_dict().items():
            if "default" in schema["properties"][field]:
                self.assertEqual(value, schema["properties"][field]["default"])
