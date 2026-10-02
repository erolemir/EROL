---
name: container-runtime-hardening
description: "Reduce container privileges and image exposure while preserving required runtime behavior."
metadata:
  version: "1.0.0"
---
# Container Runtime Hardening

Reduce container privileges and image exposure while preserving required runtime behavior.

## Workflow

1. Inventory image provenance, runtime user, capabilities, mounts, network and secrets; identify what the application actually needs.
2. Prefer an unprivileged user and narrow capabilities; treat daemon access and host mounts as high-impact privileges.
3. Limit writable paths and resource use, preserve diagnostic needs and use supported sandbox options for the host/runtime.
4. Keep build-time credentials and unnecessary tooling out of the final image; verify changes against the installed runtime rather than copying flags blindly.

## Verification

Run application health, file-write and shutdown checks under the restricted configuration; test expected denial without claiming complete isolation.

## Deliverable

Privilege/mount diff and compatibility evidence.

## Current reference

Verify platform-specific details against [official documentation](https://docs.docker.com/engine/security/) for the deployed version.
