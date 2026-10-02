---
name: realtime-service
description: "Design authenticated realtime connections with bounded delivery, reconnect and backpressure behavior."
metadata:
  version: "1.0.0"
---
# Realtime Service

Design authenticated realtime connections with bounded delivery, reconnect and backpressure behavior.

## Workflow

1. Choose streaming direction and delivery semantics from the use case; map authentication, channel membership and token expiry.
2. Bound per-connection buffers and define what happens to slow consumers. Do not let one client exhaust worker memory.
3. Use event identifiers or a cursor when replay is required; define gaps and resynchronization instead of promising lossless reconnect implicitly.
4. Handle disconnect cleanup, heartbeats and replica routing; verify proxy timeouts against the chosen transport.

## Verification

Exercise slow clients, reconnect after a gap, revoked membership, expired authentication and a rolling server restart.

## Deliverable

Connection lifecycle, delivery contract and bounded-buffer tests.
