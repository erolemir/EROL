---
name: authorized-security-testing
description: "Plan and execute bounded security tests on explicitly authorized targets with reproducible findings."
metadata:
  version: "1.0.0"
---
# Authorized Security Testing

Plan and execute bounded security tests on explicitly authorized targets with reproducible findings.

## Workflow

1. Confirm the owner-authorized target, accounts, allowed techniques, test window and stop conditions before interacting with a target.
2. Start from application boundaries and meaningful abuse hypotheses; prefer isolated fixtures when they can verify the same control.
3. Bound rate and effects, use test data and avoid unnecessary access to real user data or disruptive persistence.
4. Record minimal reproducible evidence, impact and remediation; distinguish unsuccessful probes from verified vulnerabilities.

## Verification

Check findings against the authorized scope and retest repaired controls. Report untested boundaries and limitations without claiming full security assurance.

## Deliverable

Scoped test plan and sanitized reproducible findings, with no activity outside authorization.
