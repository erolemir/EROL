---
name: web-performance-budget
description: "Measure web loading and interaction bottlenecks with repeatable budgets and representative users."
metadata:
  version: "1.0.0"
---
# Web Performance Budget

Measure web loading and interaction bottlenecks with repeatable budgets and representative users.

## Workflow

1. Establish page, device/network and interaction baselines; separate laboratory measurements from real-user distributions.
2. Attribute delay to rendering, network, JavaScript execution or third parties before optimizing. Track resource ownership and critical dependencies.
3. Choose bounded changes such as asset sizing, loading priority or reduced work; avoid hiding useful content just to improve a synthetic score.
4. Set regression budgets for the routes that matter and document measurement variability and accessibility tradeoffs.

## Verification

Repeat the same traces before/after and test real interactions. Report sample, configuration and which field metrics remain unmeasured.

## Deliverable

Measured bottleneck, scoped change and repeatable performance budget.
