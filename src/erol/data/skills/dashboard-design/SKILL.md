---
name: dashboard-design
description: "Design operational dashboards around decisions, metric definitions and comparable data states."
metadata:
  version: "1.0.0"
---
# Dashboard Design

Design operational dashboards around decisions, metric definitions and comparable data states.

## Workflow

1. Identify the decisions and actions the dashboard supports; define each metric's grain, denominator, timezone and refresh latency.
2. Separate current state from trends and comparisons. Avoid mixing totals with incompatible filters or time windows.
3. Choose chart/table forms for the comparison; show units, missing data, empty states and drill-down paths without implying false precision.
4. Keep filters and export definitions consistent; provide keyboard access and text alternatives for critical visual information.

## Verification

Reconcile sample displayed totals to source rows, test filter combinations and stale/partial data, and review representative user decisions.

## Deliverable

Dashboard layout, metric dictionary and reconciliation checks.
