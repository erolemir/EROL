---
name: configuration-management
description: "Make configuration explicit, validated and environment-consistent without exposing secrets."
metadata:
  version: "1.0.0"
---
# Configuration Management

Make configuration explicit, validated and environment-consistent without exposing secrets.

## Workflow

1. Inventory configuration sources and precedence; identify runtime versus build-time settings and environment-specific ownership.
2. Validate types, ranges and required relationships at the correct boundary. Fail with actionable key names without echoing secret values.
3. Use safe documented defaults only where omission has a well-defined meaning; avoid silent production fallback to a test environment.
4. Separate secrets from shareable examples and define reload behavior so partial configuration does not create mixed states.

## Verification

Test missing/invalid values, precedence, environment selection and redacted failure output; ensure example config matches supported behavior.

## Deliverable

Validated configuration contract and reproducible environment examples.
