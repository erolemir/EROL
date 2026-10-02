---
name: distributed-workflow
description: "Coordinate multi-service effects using durable states, reconciliation and explicit compensation limits."
metadata:
  version: "1.0.0"
---
# Distributed Workflow

Coordinate multi-service effects using durable states, reconciliation and explicit compensation limits.

## Workflow

1. Map every durable transition, owner and irreversible effect; identify the business invariant rather than assuming cross-service atomicity.
2. Attach stable operation IDs and persist intent before sending effects. Model timeouts as uncertain states that need reconciliation.
3. Specify compensations as real business actions with their own failures; a refund does not erase history or always reverse a shipment.
4. Provide operator recovery and audit trails for stuck states; bound automatic retries and preserve duplicate-event tolerance.

## Verification

Inject failure between each effect and state update, replay messages and simulate compensation failure. Check final invariants and manual recovery paths.

## Deliverable

State/transition diagram, compensation matrix and fault-injection plan.
