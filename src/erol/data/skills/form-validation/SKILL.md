---
name: form-validation
description: "Implement form validation, submission and recovery without losing user input or trusting client checks alone."
metadata:
  version: "1.0.0"
---
# Form Validation

Implement form validation, submission and recovery without losing user input or trusting client checks alone.

## Workflow

1. Map required, conditional and server-owned fields to the actual server contract. Client validation improves feedback but never replaces server checks.
2. Choose when to validate without disrupting composition or typing. Associate messages with fields and move focus deliberately after failed submission.
3. Preserve edits through failed requests; prevent duplicate submission and distinguish pending, accepted and uncertain outcomes.
4. Handle stale server errors, dependent fields and navigation protection according to the product flow, not a universal blocking rule.

## Verification

Test keyboard submission, invalid/valid transitions, server field errors, repeated clicks, latency and recovery with entered data intact.

## Deliverable

Validation/submission state model and user-path tests.
