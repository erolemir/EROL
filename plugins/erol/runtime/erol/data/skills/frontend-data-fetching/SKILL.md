---
name: frontend-data-fetching
description: "Manage remote UI data through cache keys, cancellation and consistent loading/error states."
metadata:
  version: "1.0.0"
---
# Frontend Data Fetching

Manage remote UI data through cache keys, cancellation and consistent loading/error states.

## Workflow

1. Read the framework's current data layer and existing cache conventions; identify which inputs determine resource identity.
2. Include filters, pagination and authenticated scope in keys. Cancel or disregard obsolete responses when the selected identity changes.
3. Define initial load, background refresh, error, empty and stale states; keep retry policy bounded and appropriate to request semantics.
4. Reconcile mutations through authoritative responses or controlled optimistic updates, including rollback when an update fails.

## Verification

Simulate out-of-order responses, tenant changes, rapid filter updates, failed mutation and refetch. Verify visible data corresponds to the active key.

## Deliverable

Query-key/state changes and asynchronous race fixtures.
