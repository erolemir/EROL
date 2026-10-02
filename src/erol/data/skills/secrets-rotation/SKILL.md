---
name: secrets-rotation
description: "Plan and verify credential rotation with overlap, revocation and recoverable dependent-service updates."
metadata:
  version: "1.0.0"
---
# Secrets Rotation

Plan and verify credential rotation with overlap, revocation and recoverable dependent-service updates.

## Workflow

1. Inventory credential owners, consumers and exposure evidence without printing values; classify emergency versus routine rotation.
2. Define issuance, rollout, validation and revocation order. Use overlapping acceptance only where the provider and threat model allow it.
3. Update consumers through supported secret stores and deployment paths; avoid committing replacements into source or logs.
4. Verify dependent jobs, caches and long-lived sessions; state the rollback boundary once the old credential is revoked.

## Verification

Check new credentials through permitted calls, prove revoked credentials fail, and retain redacted evidence of consumer health.

## Deliverable

Rotation sequence, dependency checklist and revocation evidence; execute live changes only within task authorization.
