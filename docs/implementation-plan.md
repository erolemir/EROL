# Living implementation plan

Current milestone: bounded autonomous work, parallel review and evidence-linked research.

Implemented user-authorized follow-up areas: bounded Git/TODO/check/issue discovery;
external durable queue with
explicit project-bound policy, dependencies, unique tasks, cancellation/recovery and
no automatic merge/push; paired behavioral benchmarks on identical controlled fixtures;
public-source access receipts distinct from model interpretation; indexed hybrid
memory retrieval with revision/freshness gates; parallel read-only specialist reviews
while retaining a single writer; and a loopback-only read-only interactive panel.
Windows deterministic/native tests are local evidence. Linux/macOS runtime results
must be measured separately, not inferred from typing or the old CI matrix. The
user explicitly waived live Claude tests after the expired-OAuth result; its adapter
contract remains deterministic-tested. Limits and unsupported cases will be recorded.

Architecture decisions:

- Python >=3.11 standard library for a dependency-free runtime and built-in SQLite.
  A dependency-free Node launcher provides the local npx entry point and plugin
  runtime discovery without introducing a second implementation of storage or learning.
- One canonical core, external memory.db and separately versioned runs.db per project identity.
- Generated skills start project scoped. Immutable revision digests bind evals and uses.
- Static routing/workflow lint is distinct from independently reviewed behavioral evidence.
- No automatic execution of imported skill scripts, remote telemetry or privileged agent launch.
  This milestone does not publish, merge or push changes. Earlier distribution work
  was separately authorized; npm/PyPI publication remains separate.

Implemented: CLI, shared external memory, project identity, incident normalization,
evidence-gated learning, immutable skill revisions, registry/router, bounded context,
advisory role plans, safe project bridge setup, generated native plugin bundles,
local Node entry point, deterministic evals and isolated package checks.

Turkish routing now includes explicit task aliases across the builtin pack,
dotted-capital/ASCII normalization, and screen/date-filter regression fixtures.
Bridges distinguish admitted builtin workflows from learned project revisions.
Negative precedence, lazy body loading, and the four-skill context cap remain in force.

The curated builtin catalog now has 96 workflows across nine domains and 18
advisory roles, including operations, SEO, marketing and growth. Category discovery,
common API/test phrase coverage and adjacent-domain negative fixtures support the
larger catalog. Independent review and two limited drafting trials supplement
static/routing checks; live outcome improvement for the full pack remains unproven.

Acceptance criteria are defined in eval-plan.md before implementation. Test fixtures
use temporary homes outside their projects. Native installations change user
configuration only at the user's explicit request.

An installed Codex CLI session verified skill loading, direct Python fallback,
planning and durable task receipts. Both native plugins are installed on the user's
computer at their request; the current Claude live trial returned an expired OAuth error.

Public GitHub distribution now includes a tested `stable` channel, automatic
versioned release workflow, owner-reviewed main protection and optional Windows
native-client refreshes. npm/PyPI registry publication is not implemented.

Implemented in this checkout: capability-checked Codex/Claude CLI adapters,
baseline/acceptance checks, independent review, exact source/check digests,
bounded retries/replanning, native-session resume, cooperative cancellation,
Windows Job/POSIX process-group cleanup, retained patches and crash-idempotent
revision-bound usage. Runtime dependencies remain empty. Git identity detection
now explicitly decodes UTF-8 paths, including Turkish names.

Execution is opt-in, separate from advisory plans, and uses detached worktrees,
external versioned runs.db and an OS-held project lease. One unfinished task per
project is supported across different homes through a Git metadata lease/marker;
retained worktrees are not automatically deleted. Check
manifests are executable caller inputs, not a sandbox. Deterministic and live-trial
results are recorded separately in validation.md.

The user's research follow-up prioritizes technical, product and competitor
analysis. Implemented `--mode research` adds native web access, dated primary and
secondary sources, exact report citations, claim/source references, uncertainty
and conflicts, and a separate source-review contract. Missing/contradicted source
review blocks completion. The structural gate is explicitly static; source checks
are model review assertions. Native provider/network policy can restrict access.
Broad comparative accuracy or product/competitor outcome improvements are unmeasured.

Earlier core validation: 158 Python tests (157 pass, one POSIX-only skip), ten
Node tests, 289 routing fixtures, Ruff lint/format, Mypy, adapter drift, pack/context
and learning evals, Python build/wheel smoke and npm pack/smoke pass on Windows
Python 3.12.4 / Node 20.15.0. Codex 0.159.2 passed repair, checkpoint resume and
independent review, plus a narrow official-source technical research trial.
Claude 2.1.92 native execution returned expired-OAuth HTTP 401; its live repair,
resume and source-retrieval acceptance remain blocked pending native reauthentication.
The user waived further live Claude trials; the Claude adapter remains covered by
fake-process protocol, permission, timeout, cancellation and resume tests.
No live compatibility claim is made for Linux/macOS or broad product/competitor tasks.

The follow-up adds work.db schema 1 and rebuildable search.db schema 2 without
changing memory.db. Policies bind project/source/check definitions and resource
limits. Queue claims survive interrupted checkpoints; duplicate task IDs and
uncertain workers do not relaunch. Acyclic dependencies compose verified ancestor
delta patches once, without commits, merges or publication. Up to three read-only
specialists review concurrently; one implementer writes per project. Full revision
and optional current-file bindings gate indexed BM25/bilingual memory retrieval.
Public HTTPS access receipts are independent of model source interpretation.
Paired context-ablation suites compare identical fixtures and persist native usage,
outcomes and duration. The loopback panel exposes selected read-only evidence.
See autonomous-work.md for exact CLI contracts and bounds.

New live Codex trials passed a policy-queued repair with two concurrent reviewers
and checkpoint resume, official-source research with three observed HTTPS receipts,
and one behavioral pair. Both pair arms passed in one attempt; this sample does
not show a speed or usage advantage. New deterministic coverage includes queue
recovery, dependencies, cancellation races, peer IDs/resume/cancellation, indexed
freshness/project guards, source access boundaries and read-only panel behavior.
Final delivery commands and measured counts are recorded in validation.md.
The final full suite has 180 tests (179 pass, one POSIX-only skip), twelve Node
tests and 289 routing cases. Ruff/Mypy, adapter drift, pack/context/learning evals,
Python build/wheel smoke and npm pack/smoke all passed. Browser bridge availability
prevented a visual panel check; HTTP and JavaScript behavior were tested separately.

Pending: neural embedding retrieval, concurrent writers, multi-project worker pools,
desktop plugin selection, authenticated test evidence, verified automatic native event
ingestion, global revision creation/installation, provider-backed scheduling
and contained execution of third-party candidates.

See validation.md for measured local results and delivery-report.md for the full
implementation report. The current milestone does not claim completion of the
entire long-term architecture or tested compatibility across the CI matrix.

Release preparation exposed a POSIX false positive in run metadata: joined
filesystem components containing a run UUID were scanned as one entropy token.
RunStore now applies the existing absolute-path/component scanner only to its six
explicit filesystem fields. Model text, nested fields, credential patterns and
random secret components retain rejection. Two cross-platform regression tests
cover both acceptance and rejection; release still requires the complete CI matrix.
