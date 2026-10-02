---
name: reverse-proxy-tls
description: "Configure proxy routing and TLS while preserving trusted client identity and upstream request semantics."
metadata:
  version: "1.0.0"
---
# Reverse Proxy Tls

Configure proxy routing and TLS while preserving trusted client identity and upstream request semantics.

## Workflow

1. Read the active proxy/server version and route chain; distinguish TLS termination, certificate issuance and upstream transport.
2. Align timeouts, body limits and streaming behavior with application needs; do not solve slow writes by making all limits unlimited.
3. Trust forwarded client/host headers only from configured proxy hops; verify redirect, cookie and absolute-URL behavior.
4. Validate configuration before an authorized reload and retain a known-good route/certificate rollback path.

## Verification

Test certificate chain/hostname, redirects, expected upstream headers, large/slow requests and renewal rehearsal on a permitted endpoint.

## Deliverable

Validated proxy config and request/TLS evidence.
