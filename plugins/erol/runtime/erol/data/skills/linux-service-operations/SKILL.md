---
name: linux-service-operations
description: "Diagnose Linux service health from process ownership, logs, resources and configuration before changing service state."
metadata:
  version: "1.0.0"
---
# Linux Service Operations

Diagnose Linux service health from process ownership, logs, resources and configuration before changing service state.

## Workflow

1. Identify the exact host, unit, process owner and recent change; collect status, bounded logs and dependency failures using read-only diagnostics first.
2. Check resource exhaustion, permissions, listening sockets and configuration validity against the installed service version.
3. Choose a scoped reversible correction; explain effects of reload versus restart and preserve evidence before clearing state.
4. Apply service mutations only within the authorized host/task scope, with a health check and recovery path.

## Verification

Verify startup, readiness, expected ports and repeated healthy requests; report which host actions were actually executed.

## Deliverable

Root-cause evidence, scoped repair and post-change health checks.
