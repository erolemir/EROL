---
name: background-job-reliability
description: "Make queued work recoverable through acknowledgements, leases, bounded retries and safe replay."
metadata:
  version: "1.0.0"
---
# Background Job Reliability

Make queued work recoverable through acknowledgements, leases, bounded retries and safe replay.

## Workflow

1. Identify acknowledgement timing, visibility timeout or lease, worker shutdown behavior, and the real queue delivery guarantee.
2. Make effect completion replay-safe and persist progress at meaningful boundaries; a retry counter alone is not deduplication.
3. Differentiate poison payloads from transient failures. Bound attempts, retain sanitized failure evidence and provide a replay path.
4. Handle cancellation and graceful drain without acknowledging unfinished work; measure oldest-item age as well as queue depth.

## Verification

Kill a worker before and after a durable effect, expire a lease, deliver twice and exhaust retries. Check recovered effects and retained failures.

## Deliverable

Worker lifecycle changes, replay tests and queue health signals.
