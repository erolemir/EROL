---
name: multi-tenant-isolation
description: "Verify tenant scoping across queries, jobs, caches and object references."
metadata:
  version: "1.0.0"
---
# Multi Tenant Isolation

Verify tenant scoping across queries, jobs, caches and object references.

## Workflow

1. Trace trusted tenant identity from authentication to every query and side effect; distinguish platform operators from tenant administrators.
2. Scope lookups by both tenant and object identity. Review relationships, joins, exports, cache keys and job payloads, not just top-level routes.
3. Prevent caller-selected tenant IDs from replacing verified scope. Preserve legitimate administrative paths with explicit checks.
4. Use least-privilege data access and inspect shared uniqueness constraints for cross-tenant information leakage.

## Verification

Create two tenants with overlapping local identifiers and exercise reads, updates, exports, jobs and cached responses across both scopes.

## Deliverable

Boundary inventory and executable cross-tenant denial tests.
