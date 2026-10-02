---
name: frontend-e2e-testing
description: "Test critical browser journeys with stable state setup, meaningful assertions and controlled dependencies."
metadata:
  version: "1.0.0"
---
# Frontend E2E Testing

Test critical browser journeys with stable state setup, meaningful assertions and controlled dependencies.

## Workflow

1. Select the smallest user journey that detects a meaningful regression; reuse repository fixtures and supported browser tooling.
2. Set up isolated users and data without relying on ordering between tests. Control time and remote services where deterministic behavior is required.
3. Assert visible outcomes and durable effects using resilient locators, not arbitrary sleeps or implementation-only CSS selectors.
4. Preserve traces/screenshots for failures and distinguish mocked provider checks from a real end-to-end environment.

## Verification

Run the journey and its failure/recovery variant; demonstrate the target regression fails before the fix when feasible and report skipped services.

## Deliverable

Browser test, deterministic fixtures and reproducible failure evidence.
