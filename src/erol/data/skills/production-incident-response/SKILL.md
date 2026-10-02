---
name: production-incident-response
description: "Respond to production incidents with evidence preservation, scoped mitigation and recovery verification."
metadata:
  version: "1.0.0"
---
# Production Incident Response

Respond to production incidents with evidence preservation, scoped mitigation and recovery verification.

## Workflow

1. Establish affected services/users, start time and recent changes; separate observed facts from causal hypotheses.
2. Preserve bounded logs and state before mitigation. Prefer reversible changes with a clearly authorized operational scope.
3. Track one mitigation at a time with its expected signal and stop condition; avoid repeated blind restarts or speculative destructive repairs.
4. Verify sustained recovery at the user boundary and retain a timeline, follow-up owners and sanitized learning evidence.

## Verification

Compare error/latency and successful user paths before/after mitigation; document residual risk and tests that prevent recurrence.

## Deliverable

Incident timeline, demonstrated cause or uncertainty, mitigation and recovery evidence.
