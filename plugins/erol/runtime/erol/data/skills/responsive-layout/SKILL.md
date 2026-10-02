---
name: responsive-layout
description: "Build layouts that remain usable across viewport sizes, zoom and variable content."
metadata:
  version: "1.0.0"
---
# Responsive Layout

Build layouts that remain usable across viewport sizes, zoom and variable content.

## Workflow

1. Inspect existing layout primitives and the actual content extremes before choosing breakpoints; prioritize reading and action order.
2. Use intrinsic sizing, wrapping and bounded overflow instead of hardcoded device widths. Avoid hiding required actions to make a screenshot fit.
3. Preserve keyboard order, focus visibility and touch usability as components rearrange; account for zoom and localization.
4. Test representative narrow, wide and intermediate widths with long labels, empty states and loading content.

## Verification

Capture viewport/zoom checks and keyboard paths; verify no inaccessible clipped content or horizontal overflow in supported flows.

## Deliverable

Layout changes and an evidence-backed viewport matrix.
