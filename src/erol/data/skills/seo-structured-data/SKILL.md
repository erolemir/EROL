---
name: seo-structured-data
description: "Implement structured data that reflects visible page content and the current supported search feature."
metadata:
  version: "1.0.0"
---
# Seo Structured Data

Implement structured data that reflects visible page content and the current supported search feature.

## Workflow

1. Choose a currently supported feature matching the page purpose; check official required fields and content policies at implementation time.
2. Map markup to visible authoritative content; avoid fake ratings, hidden claims or invented availability.
3. Generate escaped valid JSON and consistent canonical identifiers; prevent duplicate or contradictory entities across templates.
4. Make updates follow page data ownership so markup does not silently become stale.

## Verification

Validate syntax and eligible fields with current official tooling, compare rendered page/markup values and monitor reports; eligibility does not guarantee display.

## Deliverable

Markup changes, content mapping and validation evidence.

## Current reference

Verify platform-specific details against [official documentation](https://developers.google.com/search/docs/appearance/structured-data/sd-policies) for the deployed version.
