---
name: repository-change-planning
description: "Plan a scoped code change from affected callers, compatibility constraints and verifiable milestones."
metadata:
  version: "1.0.0"
---
# Repository Change Planning

Plan a scoped code change from affected callers, compatibility constraints and verifiable milestones.

## Workflow

1. Find the current entry points, data ownership and affected callers; ground the plan in actual files and tests.
2. Separate contract changes from internal implementation. Include data, rollout and backward compatibility where they materially affect acceptance.
3. Order small reviewable changes by dependency and identify what can proceed independently without conflicting ownership.
4. State evidence needed to finish each milestone and the conditions that require revising the plan.

## Verification

Trace a representative request through the planned boundaries and ensure each milestone has a testable completion condition.

## Deliverable

File-backed plan, compatibility risks and focused checks.
