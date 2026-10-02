---
name: data-pipeline-integrity
description: "Build batch or streaming pipelines with explicit schemas, reconciliation and recoverable checkpoints."
metadata:
  version: "1.0.0"
---
# Data Pipeline Integrity

Build batch or streaming pipelines with explicit schemas, reconciliation and recoverable checkpoints.

## Workflow

1. Define source/destination grain, schema and ownership; identify authoritative totals and permissible transformations.
2. Use durable checkpoints and stable record identities; specify replay, late-arriving updates and schema evolution behavior.
3. Quarantine malformed data with bounded diagnostics rather than silently dropping it or blocking all valid records forever.
4. Reconcile completeness and business totals across stages; separate ingestion success from downstream correctness.

## Verification

Replay batches, interrupt after a checkpoint, inject duplicate/late/malformed records and verify counts, totals and corrected outputs.

## Deliverable

Pipeline contract, reconciliation report and recovery fixtures.
