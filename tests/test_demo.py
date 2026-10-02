"""A real deterministic fixture exercise, distinct from caller evidence schemas."""

import unittest

from erol.demo import learning_demo, paginate
from erol.registry import Skill, matches


class DemoTests(unittest.TestCase):
    def test_learned_error_trigger_handles_new_request_ids_and_timestamps(self):
        skill = Skill(
            name="learned-cursor",
            description="Investigate import errors",
            triggers=["contact import importcursorerror skipped rows"],
            avoid_when=["different root cause"],
            body="Fixture only",
            scope="project",
            project_id="test-project",
        )
        self.assertTrue(
            matches(skill, "contact-import ImportCursorError skipped rows request=new456 at 21:45")
        )
        self.assertFalse(matches(skill, "frontend ImportCursorError skipped rows request=new456"))
        self.assertFalse(
            matches(
                skill,
                "contact-import ImportCursorError skipped rows "
                "request=new456 at 21:45 different root cause",
            )
        )

    def test_cursor_bug_and_fixed_data_integrity(self):
        rows = [(1, i) for i in range(1, 8)] + [(2, 8), (2, 9)]
        self.assertNotEqual(paginate(rows, composite=False), rows)
        for size in (1, 2, 3, 4, 10):
            self.assertEqual(paginate(rows, composite=True, batch_size=size), rows)

    def test_fixture_learning_loop_reuses_incidents_and_limits_promotion(self):
        report = learning_demo()
        self.assertTrue(report["passed"])
        self.assertEqual(report["historical_matches_per_encounter"], [0, 1, 2])
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["successful_real_fixture_uses"], 3)
        self.assertEqual(report["promotion_status"], "promotion_candidate")
        self.assertFalse(report["global_registry_modified"])
