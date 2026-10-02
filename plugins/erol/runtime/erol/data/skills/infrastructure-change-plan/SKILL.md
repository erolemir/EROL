---
name: infrastructure-change-plan
description: "Review infrastructure changes for drift, state ownership, blast radius and recoverable application impact."
metadata:
  version: "1.0.0"
---
# Infrastructure Change Plan

Review infrastructure changes for drift, state ownership, blast radius and recoverable application impact.

## Workflow

1. Confirm environment, account, workspace and state ownership; compare proposed changes with current managed and unmanaged resources.
2. Inspect replacements, destructive operations, dependency order and secrets in generated plans rather than relying only on a change count.
3. Keep state locking, backups and drift reconciliation explicit; avoid importing or overwriting resources without verifying ownership.
4. Produce the reviewed plan before any authorized apply and define application-level checks and recovery boundaries.

## Verification

Validate configuration, inspect the exact plan revision and verify resource/application health after any permitted apply; report unapplied plans honestly.

## Deliverable

Reviewed plan, blast-radius summary and recovery/check sequence.
