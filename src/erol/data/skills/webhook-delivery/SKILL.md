---
name: webhook-delivery
description: "Implement inbound or outbound webhook delivery with verification, durable acknowledgement and replay handling."
metadata:
  version: "1.0.0"
---
# Webhook Delivery

Implement inbound or outbound webhook delivery with verification, durable acknowledgement and replay handling.

## Workflow

1. Distinguish receiving from sending; use the provider's exact signature bytes, timestamp rules and secret rotation behavior.
2. Acknowledge only after durable acceptance. Deduplicate immutable event identifiers within the correct tenant and event scope.
3. Separate delivery success from business processing success. Persist outbound attempts and apply bounded backoff, jitter and terminal failure handling.
4. Validate callback destinations to prevent arbitrary internal-network requests; preserve ordering only where the contract requires it.

## Verification

Test modified bodies, expired signatures, duplicate events, crash after persistence, reordered events and a receiver recovering after failure.

## Deliverable

Delivery state machine, signature fixtures and operational retry/dead-letter visibility.
