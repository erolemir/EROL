---
name: test-fixture-design
description: "Build deterministic fixtures that expose behavioral failures without reproducing implementation details."
metadata:
  version: "1.0.0"
---
# Test Fixture Design

Build deterministic fixtures that expose behavioral failures without reproducing implementation details.

## Workflow

1. Identify the observable invariant and smallest data set that distinguishes correct from faulty behavior.
2. Control time, identifiers, randomness and external effects at explicit interfaces; keep setup isolated from test ordering and user configuration.
3. Use realistic boundary values and independent expected outcomes, avoiding assertions copied from the same algorithm under test.
4. Clean up owned resources and retain sanitized diagnostics when a fixture fails; do not substitute a mock for the boundary being evaluated.

## Verification

Run alone and with neighboring tests, repeat deterministically, and confirm a targeted faulty implementation fails for the intended reason.

## Deliverable

Minimal fixture, independent assertions and repeatability evidence.
