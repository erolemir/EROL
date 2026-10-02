---
name: database-backup-restore
description: "Design backup and restore procedures around recoverable data, dependencies and measured recovery objectives."
metadata:
  version: "1.0.0"
---
# Database Backup Restore

Design backup and restore procedures around recoverable data, dependencies and measured recovery objectives.

## Workflow

1. Define recovery point/time objectives and inventory database, keys, configuration and external objects needed for a usable restoration.
2. Choose a backup method supported by the exact engine/version and consistency requirements; copying live files is not automatically a consistent backup.
3. Protect backup access and retention; monitor completion, available capacity and the age of the last recoverable backup.
4. Restore into an isolated target first, validate identity and forbid overwriting live data without explicit task authorization.

## Verification

Measure restore duration and recoverable point; verify representative records, constraints and application reads, including missing-key/dependency failures.

## Deliverable

Backup/restore runbook and measured rehearsal evidence.

## Current reference

Verify platform-specific details against [official documentation](https://www.postgresql.org/docs/current/backup.html) for the deployed version.
