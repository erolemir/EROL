---
name: privacy-data-retention
description: "Map sensitive data collection, retention and deletion to concrete systems and stated policy requirements."
metadata:
  version: "1.0.0"
---
# Privacy Data Retention

Map sensitive data collection, retention and deletion to concrete systems and stated policy requirements.

## Workflow

1. Inventory data types, purposes, access and copies across logs, databases, exports, queues and vendors; distinguish direct identifiers from derived data.
2. Use applicable verified policy/legal requirements as inputs rather than inventing universal retention periods or compliance guarantees.
3. Define deletion, anonymization, legal-hold and backup expiration behavior with explicit owners and observable completion states.
4. Prevent old jobs or restores from resurrecting deleted data and keep audit evidence minimal and appropriately protected.

## Verification

Exercise a synthetic subject through collection, expiry, deletion and permitted restoration; report vendor/backup limits and unresolved policy questions.

## Deliverable

Data/purpose map, retention/deletion design and synthetic verification; this is implementation evidence, not legal certification.
