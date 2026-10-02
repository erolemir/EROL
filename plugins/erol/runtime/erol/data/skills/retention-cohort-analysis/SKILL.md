---
name: retention-cohort-analysis
description: "Measure retention using comparable cohorts, meaningful activity definitions and censoring-aware windows."
metadata:
  version: "1.0.0"
---
# Retention Cohort Analysis

Measure retention using comparable cohorts, meaningful activity definitions and censoring-aware windows.

## Workflow

1. Define the entity, cohort entry event, meaningful return activity and churn rule; distinguish subscription status from actual product use.
2. Align observation windows and handle incomplete cohorts, reactivation and data gaps explicitly.
3. Segment by entry context or customer need without changing definitions mid-comparison; reconcile counts to source records.
4. Form product/lifecycle hypotheses from observed patterns and separate correlation from causal explanation.

## Verification

Validate sample entity histories, cohort denominators and censoring logic; disclose tracking changes and uncertainty in small cohorts.

## Deliverable

Retention matrix, definition dictionary and testable intervention hypotheses.
