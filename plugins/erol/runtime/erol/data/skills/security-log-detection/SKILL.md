---
name: security-log-detection
description: "Design actionable security detections from reliable event semantics and tested false-positive controls."
metadata:
  version: "1.0.0"
---
# Security Log Detection

Design actionable security detections from reliable event semantics and tested false-positive controls.

## Workflow

1. Define the behavior, event source, identity fields and timestamp reliability; confirm the needed data exists before writing a rule.
2. Correlate events within a bounded window and include legitimate administration paths as contrast cases.
3. Set severity and escalation from consequence and confidence; avoid alerting on every failed login as if it were confirmed compromise.
4. Protect sensitive logs, document retention and assign an owner and investigation runbook for each actionable alert.

## Verification

Replay sanitized positive and negative event sequences, missing fields and clock disorder; report coverage and known false positives.

## Deliverable

Detection rule, replay fixtures and triage runbook.
