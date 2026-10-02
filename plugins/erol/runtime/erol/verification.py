"""Validate explicit local evidence attestations. This does not execute tests."""

from __future__ import annotations

from erol.common import ErolError, required_text
from erol.security import assert_secret_safe


def verify_report(report: object) -> dict:
    if not isinstance(report, dict):
        raise ErolError("Verification report must be an object")
    assert_secret_safe(report)
    implementer = required_text(report.get("implementer"), "implementer", 120)
    reviewer = required_text(report.get("reviewer"), "independent reviewer", 120)
    if reviewer.casefold() == implementer.casefold():
        raise ErolError("Independent reviewer must differ from implementer")
    tests = report.get("tests")
    if not isinstance(tests, list) or not tests:
        raise ErolError("At least one evidence-linked check is required")
    normalized = []
    for item in tests:
        if not isinstance(item, dict) or item.get("passed") is not True:
            raise ErolError("All reported checks must pass before learning")
        normalized.append(
            {
                "name": required_text(item.get("name"), "check name", 200),
                "passed": True,
                "reference": required_text(item.get("reference"), "evidence reference", 1000),
            }
        )
    findings = report.get("findings", [])
    if not isinstance(findings, list):
        raise ErolError("Reviewer findings must be a list")
    for finding in findings:
        if not isinstance(finding, dict) or finding.get("severity") not in {
            "critical",
            "high",
            "medium",
            "low",
        }:
            raise ErolError("Invalid finding severity")
        if type(finding.get("resolved")) is not bool:
            raise ErolError("Findings require explicit resolution status")
        if finding["severity"] in {"critical", "high"} and not finding["resolved"]:
            raise ErolError("Unresolved critical/high findings prevent completion")
    return {
        "implementer": implementer,
        "reviewer": reviewer,
        "tests": normalized,
        "findings": findings,
        "evidence_type": "local_attestation",
        "checks_executed_by_erol": False,
    }
