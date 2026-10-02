---
name: git-branch-integration
description: "Synchronize and integrate Git branches while preserving local work and divergent history."
metadata:
  version: "1.0.0"
---
# Git Branch Integration

Synchronize and integrate Git branches while preserving local work and divergent history.

## Workflow

1. Inspect status, upstreams, worktree ownership and uncommitted files before changing refs. Fetch and compare ancestry and ahead/behind counts.
2. Fast-forward branches where possible; when histories diverge, preserve both sides through the user-authorized merge or rebase strategy.
3. Resolve conflicts by intended behavior and surrounding tests, not wholesale acceptance of one side. Keep conflict repair separate from unrelated feature changes.
4. Verify the resulting history and working tree. Push only within task authorization; never infer permission for a destructive reset or force push from the word sync.

## Verification

Check ancestry, retained commits, unresolved markers and relevant tests; document conflict decisions and any work that remains uncommitted.

## Deliverable

Integrated branch, preserved-work evidence and conflict-resolution summary.
