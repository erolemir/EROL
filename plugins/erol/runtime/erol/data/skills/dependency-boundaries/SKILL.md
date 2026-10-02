---
name: dependency-boundaries
description: "Restructure modules around dependency direction, ownership and testable interfaces."
metadata:
  version: "1.0.0"
---
# Dependency Boundaries

Restructure modules around dependency direction, ownership and testable interfaces.

## Workflow

1. Map real dependency edges and identify the responsibility causing the cycle; preserve existing behavior before moving code.
2. Place stable contracts at the boundary owned by the consuming domain; do not replace one cycle with a generic shared-module dumping ground.
3. Inject effects where it makes testing or ownership clearer, using repository conventions rather than mandatory abstractions everywhere.
4. Migrate callers incrementally and preserve public import paths where compatibility requires them.

## Verification

Import representative entry points in a clean process and run behavior tests across both sides of the new boundary.

## Deliverable

Dependency map, scoped module changes and compatibility checks.
