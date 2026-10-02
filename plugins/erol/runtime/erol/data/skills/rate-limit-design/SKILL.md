---
name: rate-limit-design
description: "Design bounded request quotas with explicit identities, burst behavior and fair failure responses."
metadata:
  version: "1.0.0"
---
# Rate Limit Design

Design bounded request quotas with explicit identities, burst behavior and fair failure responses.

## Workflow

1. Define the limiting subject, protected resource, time window, burst allowance and desired response before selecting an algorithm.
2. Resolve client identity from trusted authentication or proxy configuration; raw caller headers must not let clients evade quotas.
3. Use atomic shared accounting when limits span replicas. Specify failure-open or failure-closed behavior per resource rather than accidentally choosing it.
4. Expose retry timing and operational metrics without leaking another user's usage; distinguish overload protection from billing entitlements.

## Verification

Test bursts, sustained load, multiple replicas, window edges, identity spoofing and limiter-store failure with deterministic time.

## Deliverable

Quota policy, atomic implementation and fairness/load fixtures.
