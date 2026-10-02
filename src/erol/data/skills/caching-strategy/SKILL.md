---
name: caching-strategy
description: "Design cache keys, invalidation and freshness policies from measured read behavior and correctness requirements."
metadata:
  version: "1.0.0"
---
# Caching Strategy

Design cache keys, invalidation and freshness policies from measured read behavior and correctness requirements.

## Workflow

1. Measure repeated reads and state freshness requirements before introducing caching; identify the authoritative data owner.
2. Include tenant, authorization-sensitive scope and version in keys. Do not share personalized responses through a public key.
3. Choose TTL and invalidation together; define stale reads, negative caching and read-after-write behavior explicitly.
4. Bound memory and stampede coordination; make cache failure degrade to controlled origin load rather than an unbounded retry storm.

## Verification

Test concurrent misses, expiry, tenant separation, source changes and cache outage. Compare origin load and stale-read behavior to the baseline.

## Deliverable

Key/freshness policy, cache-failure tests and measured load change.

## Current reference

Verify platform-specific details against [official documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching) for the deployed version.
