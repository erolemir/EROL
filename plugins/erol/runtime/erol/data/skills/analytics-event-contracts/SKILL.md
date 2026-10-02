---
name: analytics-event-contracts
description: "Define analytics events with stable identities, semantics and privacy-aware verification."
metadata:
  version: "1.0.0"
---
# Analytics Event Contracts

Define analytics events with stable identities, semantics and privacy-aware verification.

## Workflow

1. Define event meaning, trigger point, entity identity and allowed properties; separate attempted, completed and confirmed outcomes.
2. Specify ownership, versioning and deduplication across browser/server producers so one business effect is not counted twice.
3. Minimize sensitive properties and honor applicable consent/retention requirements; avoid putting free-form private payloads into analytics.
4. Document downstream metric consumers and changes that require coordinated migration rather than silently renaming events.

## Verification

Trace representative user paths to captured events, test replay and missing properties, and reconcile counts against authoritative effects.

## Deliverable

Event dictionary, versioned payload rules and tracking verification.
