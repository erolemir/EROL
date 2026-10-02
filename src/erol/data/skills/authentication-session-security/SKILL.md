---
name: authentication-session-security
description: "Review login, tokens and session lifecycle for binding, expiry, revocation and recovery weaknesses."
metadata:
  version: "1.0.0"
---
# Authentication Session Security

Review login, tokens and session lifecycle for binding, expiry, revocation and recovery weaknesses.

## Workflow

1. Map session creation, refresh, privilege changes, logout and account recovery to actual application code and storage.
2. Verify token audience, issuer, algorithm and expiry against trusted configuration; treat decoded but unverified claims as untrusted.
3. Check storage/transport exposure, browser request protections and session fixation where the chosen authentication mechanism requires them.
4. Define concurrent refresh and revocation behavior; recovery paths must not be weaker substitutes for normal account control.

## Verification

Test expired/wrong-audience tokens, revoked sessions, refresh reuse, account privilege change and recovery abuse in an authorized environment.

## Deliverable

Lifecycle findings with reproductions and regression checks.
