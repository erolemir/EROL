---
name: threat-modeling
description: "Model assets, trust boundaries and concrete abuse paths before choosing security controls."
metadata:
  version: "1.0.0"
---
# Threat Modeling

Model assets, trust boundaries and concrete abuse paths before choosing security controls.

## Workflow

1. List valuable assets, actors and entry points; draw where data crosses a trust or privilege boundary.
2. Trace concrete misuse paths with attacker influence, preconditions and affected assets rather than collecting generic vulnerability names.
3. Prioritize by exploitability and consequence in this system; map existing controls and meaningful gaps.
4. Assign bounded mitigations and residual risks to owners; choose relevant versioned verification requirements when a standard is used.

## Verification

Exercise representative abuse cases against the design or permitted test environment and distinguish modeled risk from demonstrated exploitability.

## Deliverable

Boundary diagram, prioritized abuse cases and evidence-linked controls.

## Current reference

Verify platform-specific details against [official documentation](https://owasp.org/projects/asvs) for the deployed version.
