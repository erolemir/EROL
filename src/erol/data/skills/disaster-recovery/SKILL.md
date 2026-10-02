---
name: disaster-recovery
description: "Plan disaster recovery across infrastructure, data, credentials and routing with a tested failback boundary."
metadata:
  version: "1.0.0"
---
# Disaster Recovery

Plan disaster recovery across infrastructure, data, credentials and routing with a tested failback boundary.

## Workflow

1. Define what failure the plan covers and agreed recovery objectives; inventory dependencies beyond the application binary.
2. Map restore/failover order for data, credentials, network and workers; prevent old and new writers from producing split-brain effects.
3. Use a rehearsal environment or an explicitly authorized window; record assumptions about external providers and unavailable dependencies.
4. Specify failback, reconciled data ownership and the point after which automatic rollback is unsafe.

## Verification

Measure end-to-end recovery and data gaps, exercise one missing dependency, and verify user paths and duplicate-effect prevention.

## Deliverable

Recovery/failback runbook and measured rehearsal limits.
