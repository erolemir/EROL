---
name: observability-design
description: "Design logs, metrics and traces that explain user-visible failures without excessive cardinality or sensitive payloads."
metadata:
  version: "1.0.0"
---
# Observability Design

Design logs, metrics and traces that explain user-visible failures without excessive cardinality or sensitive payloads.

## Workflow

1. Start from user outcomes and failure questions; define success/latency denominators and the boundaries instrumentation must explain.
2. Propagate correlation across requests and jobs using supported context; choose bounded labels and avoid user IDs as unbounded metric dimensions.
3. Log state transitions and causes with redaction, not full sensitive requests; distinguish application rejection from infrastructure failure.
4. Set alerts on actionable symptoms with ownership and investigation paths; manage sampling, retention and ingestion cost.

## Verification

Inject a known failure and trace it end-to-end; verify metric counts against sample events, label bounds and secret redaction.

## Deliverable

Signal definitions, instrumentation and failure-investigation evidence.
