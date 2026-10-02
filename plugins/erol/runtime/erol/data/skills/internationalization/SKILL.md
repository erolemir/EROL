---
name: internationalization
description: "Implement locale-aware UI strings, formats and directionality without changing canonical stored values."
metadata:
  version: "1.0.0"
---
# Internationalization

Implement locale-aware UI strings, formats and directionality without changing canonical stored values.

## Workflow

1. Inventory locale-sensitive display and message composition; separate locale, timezone and stored canonical value.
2. Use established locale APIs and message catalogs for pluralization and formatting; avoid concatenating translated fragments.
3. Preserve precision for money and explicit timezone boundaries for dates. Parse user input using a defined contract rather than reversing display strings.
4. Exercise long translations, right-to-left layout and fallback messages while retaining accessible labels and consistent direction.

## Verification

Test at least contrasting locales, missing translations, plural boundaries, timezone edges and format/parse round trips where parsing is supported.

## Deliverable

Message/format changes and a locale boundary matrix.
