---
name: dependency-supply-chain-review
description: "Review dependency provenance, build scripts and artifact integrity for supply-chain exposure."
metadata:
  version: "1.0.0"
---
# Dependency Supply Chain Review

Review dependency provenance, build scripts and artifact integrity for supply-chain exposure.

## Workflow

1. Resolve the exact package/version and trusted source; inspect lockfiles, integrity metadata and maintainership evidence instead of relying on name popularity.
2. Review lifecycle scripts, transitive changes and build/network behavior in a suitable isolated environment.
3. Distinguish known advisory findings from reachable application exposure; use current primary advisory records and installed-version evidence.
4. Preserve reproducibility and document provenance gaps before recommending adoption or replacement.

## Verification

Compare expected and produced artifacts, verify lockfile integrity and exercise the application behavior affected by the dependency change.

## Deliverable

Provenance assessment, script/permission findings and adoption criteria.
