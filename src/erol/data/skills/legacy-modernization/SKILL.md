---
name: legacy-modernization
description: "Modernize legacy code incrementally with characterization, compatibility seams and recoverable rollout."
metadata:
  version: "1.0.0"
---
# Legacy Modernization

Modernize legacy code incrementally with characterization, compatibility seams and recoverable rollout.

## Workflow

1. Characterize current behavior, known defects and contracts that consumers actually depend on; avoid treating undocumented behavior as irrelevant.
2. Choose a narrow seam and migrate one capability at a time. Preserve data ownership and prevent concurrent old/new writers from disagreeing.
3. Use comparison or shadow reads where safe; do not double-execute irreversible side effects to compare implementations.
4. Define rollback and retirement criteria before removing compatibility paths; keep improvements separate from unexplained behavior changes.

## Verification

Run characterization tests and representative parity checks, including failure paths and migration interruption.

## Deliverable

Incremental migration plan, compatibility checks and rollback boundary.
