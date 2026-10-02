"""Research structure fixtures do not claim real web retrieval or source accuracy."""

import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from erol.common import ErolError
from erol.harness import validate_result
from erol.research import load_research, review_gaps


class ResearchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="erol-research-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "research").mkdir()
        self.ledger = {
            "schema_version": 1,
            "question": "Which fixture?",
            "scope": "Technical comparison",
            "sources": [
                {
                    "id": "S1",
                    "url": "https://example.test/docs",
                    "title": "Fixture docs",
                    "publisher": "Fixture",
                    "accessed_on": date.today().isoformat(),
                    "published_on": None,
                    "kind": "primary",
                }
            ],
            "claims": [
                {
                    "id": "C1",
                    "statement": "Synthetic fact",
                    "source_ids": ["S1"],
                    "kind": "fact",
                    "confidence": "low",
                }
            ],
            "conflicts": [],
            "limitations": ["No external source in this test"],
        }
        self.report = "Synthetic fact. [S1](https://example.test/docs)"

    def save(self, ledger=None):
        (self.root / "research/sources.json").write_text(
            json.dumps(ledger or self.ledger), encoding="utf-8"
        )
        (self.root / "research/report.md").write_text(self.report, encoding="utf-8")

    def test_valid_contract_and_independent_review_gaps(self):
        self.save()
        ledger = load_research(self.root)
        self.assertTrue(review_gaps(ledger, {"source_checks": []}))
        review = {
            "summary": "Synthetic review",
            "findings": [],
            "source_checks": [
                {"source_id": "S1", "status": "verified", "reason": "Synthetic assertion"}
            ],
        }
        self.assertEqual([], review_gaps(ledger, validate_result(review, "research_reviewer")))
        for status in ("unavailable", "contradicted"):
            review["source_checks"][0]["status"] = status
            self.assertEqual("high", review_gaps(ledger, review)[0]["severity"])
        review["source_checks"][0]["status"] = "invented"
        with self.assertRaises(ErolError):
            validate_result(review, "research_reviewer")

    def test_invalid_dates_urls_references_and_missing_citations(self):
        for source_field, value in (
            ("url", "file:///private"),
            ("url", "https://user:pass@example.test/docs"),
            ("accessed_on", "2026-02-30"),
            ("accessed_on", "9999-01-01"),
        ):
            with self.subTest(source_field=source_field, value=value):
                ledger = copy.deepcopy(self.ledger)
                ledger["sources"][0][source_field] = value
                self.save(ledger)
                with self.assertRaises(ErolError):
                    load_research(self.root)
        self.ledger["claims"][0]["source_ids"] = ["unknown"]
        self.save()
        with self.assertRaises(ErolError):
            load_research(self.root)
        self.ledger["claims"][0]["source_ids"] = ["S1"]
        self.report = "Unsupported citation"
        self.save()
        with self.assertRaises(ErolError):
            load_research(self.root)
