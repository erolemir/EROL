# EROL implementation report

This is the first usable local learning milestone, not completion of every feature
in the long-term specification. Public GitHub distribution and release rules are
documented in releases.md; runtime limitations remain explicit.

## ARCHITECTURE

One standard-library Python core owns SQLite memory, project identity, routing and
learning. A dependency-free Node launcher provides the npx and plugin entry points.
Generated plugin copies are checked against canonical code. See architecture.md.

## IMPLEMENTED

JSON CLI; configuration validation; safe project setup/update/uninstall; external
project memory and readable exports; incident fingerprinting; repeated pattern
detection; draft candidates; evidence-gated activation; immutable revisions;
usage receipts and metrics; failure recovery, revision and rollback; controlled
promotion candidates; metadata-first registry; bounded context; advisory role
plans; generated native bundles; original foundation workflows; deterministic evals.

## CODEX

The local marketplace and plugin have the display name EROL. The intended desktop
entry point is `@EROL`; CLI/IDE skills use `$erol` or `/skills`. Project setup adds
one `.agents/skills/erol` bridge and a small owned AGENTS.md block. File-level
integration and an installed Codex CLI planning/persistence trial pass. Desktop
picker invocation remains pending. See installation-check.md for the actual result.

## CLAUDE

Native marketplace and plugin manifests are included. `/erol` is the desired short
command, supported by current Claude Code when it does not conflict; `/erol:erol`
is the full plugin command. Project setup installs a standalone `/erol` bridge and
owned CLAUDE.md block. The local native plugin is installed and enabled; live
session behavior remains pending because this host requires Claude login.

## MEMORY

Canonical state is outside the repository under `~/.erol/state/<project-id>`.
Credential-free remote identity falls back to the canonical project path. Shared
identity and home give both harnesses access to the same evidence. Facts keep old
revisions stale; retrieval excludes stale facts. Compaction marks exact duplicates
stale without deleting incident history. There is no cloud sync or transcript upload.

## LEARNING

Distinct verified incidents with consistent error family, cause and remedy produce
a pattern and candidate by default after three tasks with adequate confidence.
Replay, conflicting remedies, duplicates and weak evidence cannot inflate that
threshold. Positive and negative trigger checks, reviewed behavior evidence,
workflow, security and budget checks gate activation. Repeated failed strategy
attempts recommend escalation after the configured threshold.

## SELF-GENERATED SKILLS

Generated skills remain project-scoped. Eval and real-use evidence bind the full
skill digest and version. Only context-admitted skills receive use credit. Failed
use and false activation remove the revision from routing. New revisions require
new evidence; rollback cannot silently restore a failed revision. Successful
distinct uses qualify a promotion candidate. Approval records generalization
permission, without installing a global skill.

## TOKEN STRATEGY

Metadata discovery precedes body loading. Context admits a small bounded set of
skills and relevant memory, reporting omitted oversized items. The default is four
skills and a character-based 4,000-token estimate. Actual model token counts and
task-quality savings are unmeasured.

## AGENTS

Fourteen original role specifications guide specialist selection. Plans bound the
recommended roles and separate implementation, testing and review when the role
budget permits. Roles and FAST/BALANCED/REASONING/REVIEW tiers are advisory; EROL
does not launch workers, select a provider or fabricate review evidence.

## SECURITY

Parameter-bound SQLite, serialized lifecycle transitions, secret-shaped input
rejection, schema and evidence validation, link/reparse-point rejection, ownership
checks, atomic file replacement and rollback protect the implemented paths.
The launcher passes argv without a shell and isolates bundled imports. No generated
script execution, elevated worker launch or permission-policy modifications exist.
External reports remain trusted local attestations, not authenticated facts.

## EVAL RESULTS

Static checks pass for all 24 original foundation skills and 32 routing fixtures.
The pagination fixture reproduces three errors, retrieves increasing historical
matches, activates one candidate, records three successful fixture uses and produces
a promotion candidate without changing a global registry. Unit/integration and
adversarial checks, lint, types and isolated packaging checks are documented in
validation.md. No live LLM behavior score is claimed.

## BENCHMARKS

A local 500-iteration sample averaged 4.32 ms for routing/rendering, admitting one
skill into a 1,865-character context packet. Catalogue bodies total 28,023 characters.
These are local proxies, without a vanilla assistant comparison or measured model
cost, repair-time or task-success improvement.

## KNOWN LIMITATIONS

Lexical retrieval scans memory records. Runtime authenticity of reviewed reports,
automatic native event ingestion, provider-backed scheduling, contained third-party
execution, live harness trials, cross-project behavior trials, global revision
generation/installation remain pending. GitHub source distribution and automated
release packaging are documented in releases.md. Local Windows
checks do not establish that the declared CI matrix has passed.

## NEXT HIGH-VALUE WORK

1. Load the generated plugins in live Codex and Claude sessions; verify invocation,
   actual repository selection, cross-session retrieval and receipts for completed work.
2. Add native event adapters with sanitized evidence capture and authentic test
   execution receipts, preserving the distinction between observations and authority.
3. Trial project-generated workflows on held-out real tasks and additional projects.
4. Add indexed retrieval with measured relevance and bounded memory growth.
5. Implement portable global revisions with independent eval and explicit approval,
   preserving reviewed approval gates for global installation.
