---
name: transaction-boundaries
description: "Define database transaction ownership and concurrency invariants for multi-step writes."
metadata:
  version: "1.0.0"
---
# Transaction Boundaries

Define database transaction ownership and concurrency invariants for multi-step writes.

## Workflow

1. Name the invariant and the database isolation level actually in use; map who begins, commits and rolls back each unit of work.
2. Use constraints or guarded updates for facts that must hold under concurrent requests; avoid read-then-write assumptions without protection.
3. Keep remote calls out of long-held transactions; define reconciliation or an outbox where database and remote side effects cannot commit atomically.
4. Bound lock waits and retry only recognized transient conflicts with a fresh transaction and preserved idempotency key.

## Verification

Execute two competing writes on the supported database, rollback after partial work, and retry after conflict. A SQLite-only test does not prove another engine's locking behavior.

## Deliverable

Invariant table, transaction ownership changes and concurrency evidence.
