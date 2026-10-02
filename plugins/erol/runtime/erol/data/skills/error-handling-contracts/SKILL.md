---
name: error-handling-contracts
description: "Design errors that preserve causality, stable caller behavior and safe operational diagnostics."
metadata:
  version: "1.0.0"
---
# Error Handling Contracts

Design errors that preserve causality, stable caller behavior and safe operational diagnostics.

## Workflow

1. Classify validation, authorization, transient infrastructure and unexpected failures by caller-visible meaning.
2. Preserve stable codes and useful causal context across layers; avoid swallowing unknown failures or converting them into success.
3. Separate safe client messages from internal diagnostics. Attach correlation identifiers without exposing credentials or raw sensitive payloads.
4. Define retryability from effect semantics and evidence; a network exception may mean a write outcome is unknown.

## Verification

Test each public error class, nested causes, redacted logs and failure after a partial side effect; verify existing clients keep their contract.

## Deliverable

Error mapping, propagation changes and failure-path fixtures.
