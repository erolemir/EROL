# Living implementation plan

Current milestone: usable local learning core and versioned GitHub plugin distribution.

Architecture decisions:

- Python >=3.11 standard library for a dependency-free runtime and built-in SQLite.
  A dependency-free Node launcher provides the local npx entry point and plugin
  runtime discovery without introducing a second implementation of storage or learning.
- One canonical core, one SQLite database per credential-free project identity.
- Generated skills start project scoped. Immutable revision digests bind evals and uses.
- Static routing/workflow lint is distinct from independently reviewed behavioral evidence.
- No generated script execution, remote telemetry or privileged agent launch.
  GitHub publication is explicitly authorized; npm/PyPI publication remains separate.

Implemented: CLI, shared external memory, project identity, incident normalization,
evidence-gated learning, immutable skill revisions, registry/router, bounded context,
advisory role plans, safe project bridge setup, generated native plugin bundles,
local Node entry point, deterministic evals and isolated package checks.

Turkish routing now includes explicit task aliases across the builtin pack,
dotted-capital/ASCII normalization, and screen/date-filter regression fixtures.
Bridges distinguish admitted builtin workflows from learned project revisions.
Negative precedence, lazy body loading, and the four-skill context cap remain in force.

Acceptance criteria are defined in eval-plan.md before implementation. Test fixtures
use temporary homes outside their projects. Native installations change user
configuration only at the user's explicit request.

An installed Codex CLI session verified skill loading, direct Python fallback,
planning and durable task receipts. Both native plugins are installed on the user's
computer at their request; Claude model execution requires login.

Public GitHub distribution now includes a tested `stable` channel, automatic
versioned release workflow, owner-reviewed main protection and optional Windows
native-client refreshes. npm/PyPI registry publication is not implemented.

Pending: live Codex desktop and Claude Code session trials,
authenticated test evidence, verified native event
ingestion, indexed and semantic retrieval, global revision creation/installation,
provider-backed scheduling and contained execution of third-party candidates.

See validation.md for measured local results and delivery-report.md for the full
implementation report. The current milestone does not claim completion of the
entire long-term architecture or tested compatibility across the CI matrix.
