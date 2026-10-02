---
name: design-system-components
description: "Create reusable UI components with explicit variants, interaction contracts and consistent tokens."
metadata:
  version: "1.0.0"
---
# Design System Components

Create reusable UI components with explicit variants, interaction contracts and consistent tokens.

## Workflow

1. Inventory repeated UI behavior and existing tokens; choose an API from real call sites rather than speculative universal variants.
2. Separate semantic intent from visual style. Define focus, disabled, loading, error and composition behavior where applicable.
3. Keep accessibility properties available to callers and prevent incompatible props or broken native semantics.
4. Document a few representative uses, migration impact and extension points; avoid exporting implementation details as permanent public contracts.

## Verification

Exercise interaction and accessibility states, theme/contrast variations and at least two actual consumers. Snapshot similarity alone is insufficient.

## Deliverable

Component contract, representative examples and interaction tests.
