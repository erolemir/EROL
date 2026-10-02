---
name: secure-file-handling
description: "Review untrusted file parsing, paths and storage boundaries for traversal and resource exhaustion."
metadata:
  version: "1.0.0"
---
# Secure File Handling

Review untrusted file parsing, paths and storage boundaries for traversal and resource exhaustion.

## Workflow

1. Map attacker-controlled filenames, content, archive entries and destinations; distinguish lexical checks from resolved filesystem paths.
2. Reject path escape and unsupported links/reparse targets before mutation. Use generated storage identifiers and bounded extraction.
3. Constrain file size, decompressed size, nesting and parser resources; validate actual content rather than relying only on extension or MIME headers.
4. Keep temporary and quarantined content away from executable or public paths; clean up owned artifacts without following untrusted links.

## Verification

Test absolute/parent paths, link escapes, duplicate archive entries, malformed content and decompression limits using local fixtures.

## Deliverable

Boundary fixes, adversarial fixtures and parser/resource limits.
