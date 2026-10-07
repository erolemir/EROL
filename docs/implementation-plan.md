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

The explicit `logo` command renders the user supplied green mantis reference
through standard-library decompression, area resampling and Unicode half blocks.
It runs before project detection/state initialization, preserves other commands'
JSON contracts, respects terminal width and automatic color opt-outs, and adds
no runtime dependency. Source artwork is a compressed single-channel package
asset, with near-black background noise removed and a reference image digest.
Rendering assumes approximately 1:2 monospace character cells; terminal fonts
and 24-bit color support affect visual fidelity. Local validation is pending.

Release preparation exposed a POSIX false positive in run metadata: joined
filesystem components containing a run UUID were scanned as one entropy token.
RunStore now applies the existing absolute-path/component scanner only to its six
explicit filesystem fields. Model text, nested fields, credential patterns and
random secret components retain rejection. Two cross-platform regression tests
cover both acceptance and rejection; release still requires the complete CI matrix.
Linux CI also showed that a killed orphan can remain a zombie until init reaps it.
The descendant-cleanup test now verifies Linux terminal state when a PID remains;
the conservative production duplicate-worker guard continues to reject uncertain
process state. This changes the test's evidence interpretation, not cancellation.
Darwin can return EPERM on a second SIGKILL of a zombie-only process group.
Cleanup accepts that case only after the owned leader exited and a bounded ps
group/state query proves no executing group member remains. Living, malformed,
unavailable or denied observations continue to fail; no saved PID is signalled.
Windows job close dispatches termination asynchronously, so descendant evidence
waits at most five seconds for observed death and still fails for a living PID.

The public README now provides Turkish end-to-end onboarding with an English
summary. It distinguishes native plugins from the standalone CLI, gives a
versioned/checksummed Windows user install and macOS/Linux virtualenv path,
documents exact project/home ordering, meaningful check manifests and research
scope grading, recovery/queues/memory, updates/removal and troubleshooting.
Commands are grounded in current CLI contracts; desktop/live-model limitations
remain explicit. v0.1.6 main/release links document the observed remote matrix.
Local validation passed the 183-test Python suite (one POSIX test skipped on
Windows), 12 Node tests, Ruff lint/format, Mypy, adapter drift, pack/context
evaluation and both package build/smoke paths. Documentation checks verified
54 CLI examples, 12 PowerShell blocks, local links/anchors, both check manifests,
positive/negative research scope fixtures and read-only commands in Turkish-path
projects with external temporary homes. The Windows hash snippet matched the
release wheel; macOS/Linux shell installs and live harness tasks were not rerun.


## EROL terminal milestone (0.2.0 local, unpublished)

Implemented adapter/event contracts first, followed by independent external CLI/API
connections, budget/tool execution, plan-aware routing, direct workspace diffs,
portable console input, and packaged original PNG branding. Existing dirty logo
work and JSON/isolated-run commands were retained. Runtime dependencies remain
empty. Full delivery validation and independent review are complete as recorded below.

The EROL skill and six loaded builtin workflows were used: api-contract-design,
configuration-management, llm-feature-evaluation, repository-change-planning,
requirements-acceptance, tool-capability-selection. No learned project skill was
available. Existing memory was checked against current implementation; it was
not used as authority. A separate read-only review identified Gemini schema,
model escalation, single-writer process tracking, input redraw and fatal cleanup
issues; fixes and focused regression tests were added.

Limits: capability/latency priors are not empirical success rates; Luna API price
is unset. agy is excluded from read-only roles because its native workspace write
policy does not enforce that role. Sessions preserve diffs per continuation step,
not a synthesized whole-session patch. Terminal usage does not automatically
award learning-use receipts or global promotions. Observed live/platform checks
and final test/build counts will be recorded below after execution.


Measured final local delivery: README dependency install, full Python suite
221 tests (219 pass, two POSIX-specific skips), then the final expanded terminal
suite 37/37 including Windows buffer/key and queued-command regressions; 12 Node tests;
Ruff lint/format and Mypy; adapter drift; 96 pack workflows, 289 routing fixtures,
context and learning evals; Python sdist/wheel build and clean wheel smoke; npm
pack and four-launcher smoke all passed on Windows / Python 3.14.2. The package
smokes verify original PNG bytes and terminal commands/data. Initial full-suite
failure was a stale generated plugin snapshot while source was still changing;
regeneration resolved it. Independent review resolved all reported code findings; its current targeted
results are recorded separately from the full-suite run.

Actual Windows PTY trials exercised plain/rich startup, /help, Tab completion,
raw console restoration, multi-line bracketed paste, cancellation and re-entry.
Saved external settings values contained both pasted lines, including a 142-character
submission crossing native read buffers, proving a single multi-line submission. Physical keyboard Ctrl+J and mouse/resize visual fidelity
were not independently observed; key state/decoding is deterministic-test covered.
The PTY translated directly injected LF to Enter, so this is not claimed as a
physical Ctrl+J acceptance test.

Live Codex CLI 0.159.0-alpha.12.1 account/model calls and exact-session retry ran,
but native Windows sandbox returned Access denied on both OS-temp and user-profile
trial projects. No files were changed and no live task success was credited.
The schema guard now correctly reports needs_attention instead of confusing
turn.completed with implementation. Claude native auth status reported loggedIn=false;
no Claude model turn was attempted. agy is not installed (the IDE launcher exists).
No paid API model call, macOS or Linux terminal trial was made. API protocol/real
loopback streaming/tool tests are separate evidence from live account compatibility.

The local standalone CLI was staged under external EROL home cli/0.2.0 with the
previous cli/0.1.7 preserved; the owned global launcher is switched only after
clean package smoke. No external publication, push, tag, commit or marketplace
installation is part of this delivery. Existing desktop plugin caches are not
silently replaced; the repository plugin bundle is synchronized.

## Terminal startup repair (2026-10-05)

Launching `erol` from `C:\Users\emirh` previously constructed a project engine
before choosing a workspace, rejecting the nested default `~/.erol` home. The
interactive path now displays the branded project picker first. `/help`, `/logo`
and `/exit` are available before `/project PATH`; invalid/overlapping directories
cannot start engines or provider calls. Normal projects still open directly.
Project switching creates a fresh session and clears input history. Headless
commands retain the existing external-home invariant; no credentials or state
were moved and no guard was relaxed.

The EROL plan `startup-workspace-fix-20261005` admitted regression-test-design;
that workflow was applied. No learned project skill was selected. An earlier
ambiguous routing probe also admitted performance-profiling, but that workflow
was not applied or credited. Four startup regression tests were added; two
failed with the reported containment error before the fix, then all 41 chat
tests passed. An independent read-only review reran all 41 and found no new
issues. Windows PTY trials confirmed startup from the actual user directory,
picker help, overlap rejection and clean exit, plus selection of a quoted
absolute Windows path with spaces into the normal terminal using a temporary
external home. No model task was submitted in these trials.

The README validation sequence passed on Windows / Python 3.14.2: dependency
installation; 228 Python tests (226 passed, two POSIX-specific skips); 12 Node
tests; Ruff lint/format; Mypy; adapter drift; 96 pack workflows, 289 routing
fixtures, context and learning evals; sdist/wheel build and clean wheel smoke;
npm pack and clean four-launcher smoke. Logs are external under
`erol-startup-validation-owq1ubid` in OS temp. The verified incident was recorded
under the existing external EROL home; a single occurrence did not create or
promote a learned skill. macOS/Linux and live model execution were not rerun for
this startup repair.

## Animated terminal sidebar (2026-10-05)

The reported oversized left logo and old shell text behind it were reproduced
as a missing owned-screen boundary. The rich terminal now enters a cleared
alternate buffer and renders transcript, right brand panel, editor and status
as separate cell regions. Cached reference-derived poses gently move antennae
and forelegs; the original PNG and default standalone logo output are unchanged.
The sidebar adapts to width/height; `/logo` changes its width, and PgUp/PgDn
read bounded transcript history. Narrow/NO_COLOR/dumb terminals fall back to
text or static output. Runtime dependencies remain empty.

The actual EROL plan `terminal-sidebar-20261005` admitted evidence-code-review
and regression-test-design; no learned skill was selected. The owned-screen
regression failed before implementation. New tests cover Unicode wrapping,
animation/input separation, resizing down to tiny windows, history, no-color,
shell restoration and cleanup exceptions. A separate reviewer found input-mode
cleanup could be skipped by a redraw failure and a delayed refresh could repaint
the shell after close; both were repaired and regression tests added. Windows
PTY trials exercised animated right panel, picker help, logo width toggle,
Ctrl+C input recovery and exit; no model task was submitted. Physical resize,
macOS/Linux UI, mouse interaction and live provider execution were not observed.

A normal-chat Windows PTY trial also submitted bracketed-paste multiline JSON
while animation was active, then exercised PgUp/PgDn after `/help`. The temporary
external settings retained both pasted argv entries, confirming one intact
multiline submission. Direct injection is not a physical Ctrl+J or mouse test.

Final README sequence passed on Windows / Python 3.14.2: dependency installs,
235 Python tests (233 pass, two POSIX-specific skips), 12 Node tests, Ruff
lint/format, Mypy, adapter drift, 96 pack workflows / 289 routing fixtures,
context/learning evals, sdist/wheel build and clean wheel smoke, npm pack and
four-launcher smoke. External logs are `erol-sidebar-validation-vbfygp4e` under
OS temp. Independent review reran 11 terminal and 41 chat tests after the two
cleanup fixes, with no remaining blocking findings. The verified display
incident was recorded externally; no candidate or global promotion was created.

## Terminal language, input and source snapshot repair (2026-10-05)

The EROL plan `terminal-language-20261005` admitted internationalization,
regression-test-design and evidence-code-review, all applied. No learned project
skill was selected. UI catalogs now support persisted auto/en/tr selection;
Windows reads the user's UI language independently of regional locale. POSIX
uses locale environment fallback. Startup reads settings without creating state;
picker language changes persist only after a valid project is selected. Command
names, JSON fields, statuses and USD arithmetic remain canonical; native/provider
diagnostics and model output retain their original language.

The pasted connection report was a full model-profile JSON, followed by a
punctuation-only task that failed before model execution. Interactive /connect
now reports registration and directs the user to /providers for login/access;
headless connection JSON is unchanged. Punctuation-only prompts are rejected
before task dispatch. The user's selected non-Git directory contained generated
Flutter, Gradle and Next caches plus legitimate large DOCX/SQLite assets. Caches
are excluded; large binary snapshots retain streaming SHA256 and size. Source
text/tool limits and the aggregate 64 MiB scan cap remain. Read-only verification
of that directory succeeded with 2,468 files and two binary fingerprints, without
writing project files or submitting a model task.

A Windows DEL Backspace regression failed before the fix and passes afterward.
Native console records preserve wheel and Unicode input; SGR reports are also
decoded. Backspace BS/DEL, Delete and Ctrl+U edit input. Task-time raw input polls
scroll and Ctrl+C while queueing other keys for the next editor. Mode restoration
and worker cancellation/join are guaranteed on input/redraw exceptions. Streaming
preserves the viewed history anchor, including when the 200,000-character
retention cap trims old content. Independent review identified surrogate loss,
retention-cap viewport movement and poll/render worker cleanup gaps; all were
fixed with regression coverage. Final independent rerun passed 17 language/input/
snapshot, 12 terminal and 41 chat tests (70 total), with no remaining blocker.

Windows PTY tests used temporary external homes and confirmed tr OS detection,
persisted en/tr switching, localized help, short connection output, DEL Backspace
in a settings command, SGR wheel reports and PgUp/PgDn. A local streaming fixture
confirmed task-time scroll (maximum observed offset 96), Ctrl+C cancellation,
worker completion and a usable next editor. No paid provider task was submitted.
These are native Windows console/PTY and injected-sequence checks, not a physical
mouse/keyboard or resize trial. macOS/Linux UI and live provider execution remain
untested for this repair. POSIX locale/input logic has deterministic coverage.

A further live Unicode probe exposed ConPTY characters carried on VK_MENU
key-up, which ordinary key-up filtering had discarded. Only nonempty Alt Unicode
key-up records are now accepted; ordinary key releases still cannot duplicate
input. Captured synthetic rocket input now yields one U+1F680 codepoint followed
by Backspace. A new regression reproduces the exact native event shape; the
independent reviewer reran all 18 language/input/snapshot tests successfully.
An intermediate full run overlapped this final source change and failed only the
generated-runtime byte comparison. Canonical/plugin sources were regenerated
and the complete frozen-source sequence was restarted; that intermediate run
is not counted as final passing evidence.

Final frozen-source validation passed on Windows / Python 3.14.2: 254 Python
tests (252 pass, two POSIX-specific skips), 12 Node tests, Ruff lint/format,
Mypy over 39 source files, adapter drift, 96 pack workflows / 289 routing
fixtures, context/learning evals, sdist/wheel build and clean wheel smoke, npm
pack and four-launcher smoke. Dependency installs passed in the initial sequence;
all subsequent checks were repeated after the source freeze. External final logs
are `erol-language-verified-w24t8uk6` in OS temp. The native-input incident was
recorded in external EROL storage with local test/review attestations; it created
no learned candidate or promotion. Documentation and local packages are updated;
no external publication was performed.

## Explicit check trust, panel access and credential labels (2026-10-05)

The EROL plan `security-boundaries-20261005` admitted security-boundary-review,
evidence-code-review, regression-test-design and documentation-maintenance; all
were read and applied. No learned project skill was selected. The supplied review
findings were verified against local code, with synthetic credential values and
harmless marker commands rather than external host actions.

Checks now need an external schema-versioned receipt bound to the normalized
original project root and canonical manifest digest. `checks show/trust/revoke`
inspect/manage authorization without executing the manifest. Isolated run start,
resume and every phase, discovery checks, terminal checks and matching API command
tools revalidate that receipt. Saved-manifest digest tampering and another clone
cannot borrow it. A reviewed optional executor argv prefix supports independently
configured sandbox/separate-account execution; the same prefix reaches API check
tools. Behavioral suites need prior per-case manifest approval before fixtures are
created and propagate only the caller's approved policy to generated roots.
Owned opt-in live trial scripts explicitly approve their fixed generated fixtures.

Check commands use a small system/path/temp/locale/encoding environment allowlist.
Credentials and arbitrary account/startup environment variables are removed.
Explicit additional public names are checked, with interpreter injection names
still forbidden. These measures establish authorization and minimized inheritance,
not OS containment: default approved commands retain caller permissions, invoked
code/dependencies can change independently of the manifest, and native model tools
retain their own provider policy. Revocation blocks subsequent starts, not a
command already running. README/execution/terminal/discovery docs state these limits.

The loopback evidence API requires a new random 256-bit bearer token per server
and authenticates before storage access. Static assets contain no evidence/token;
the private bootstrap URL uses a fragment removed with history.replaceState.
The browser retains it only in memory and sends the bearer header to same-origin
API calls. Host/Origin checks, no-store/no-referrer headers, CSP and disabled
request logging remain. Reopening the bootstrap link is necessary after refresh;
same-account process/browser access is not an OS isolation guarantee.

Secret scanning now recognizes provider-prefixed credential labels, including
short/numeric/bool/list AWS and Stripe values, before memory writes and raw-log
persistence. Safe key_env references and native worker session identifiers remain
valid. An intermediate execution run exposed the latter false positive; its
label rule was corrected and the full 35-test execution suite passed afterward.
Scanning remains heuristic and is not a replacement for secret-safe storage and
restricted command environments.

Focused Windows checks passed 11 security-boundary tests, 35 execution tests,
22 advancement tests and two panel JavaScript tests. These cover denied unreviewed
host commands, revoked resume before preflight, actual harmless child environment
observations, malformed/root-mismatched receipts, executor prefix propagation,
token rotation/Host/Origin/auth rejection and no credential persistence. The
prefix fixture proves argv dispatch, not sandbox containment. Final independent
review and the frozen-source README validation results are recorded below.

The separate `/root/terminal_review` agent completed source/bypass review and
independently passed 120 Python tests plus two Node tests, with one POSIX permission
test skipped on Windows. Its Node VM fixture finding was fixed with browser globals,
fragment removal and bearer/no-store assertions, then independently rerun. No
remaining concrete finding was reported. Canonical/plugin runtime source equality
was verified after regeneration. No live provider, new OS containment or Linux/macOS
runtime trial was performed for this security repair.

The complete frozen-code README sequence passed on Windows / Python 3.14.2:
267 Python tests (265 passed, two POSIX-specific skips), 12 Node tests, Ruff
lint/format, Mypy over 40 source files, adapter drift, 96 workflows / 289 routing
fixtures, context/learning evals, sdist/wheel and clean wheel smoke, npm pack and
four-launcher smoke. Dependency installs also passed. External logs are
`erol-security-validation-2qovn00b` under OS temp. Documentation-only result/security
policy updates were followed by another package build and both package smokes.
These measurements do not establish OS sandbox containment or live provider
success. No external publication was performed.

## Projectless conversation and terminal usability (2026-10-05)

The user expanded projectless settings to general conversation and research,
then requested better EROL terminal readability and interaction. Actual EROL
plans `projectless-settings-20261005` and `terminal-usability-20261005` were
created and applied. Loaded builtin workflows were evidence-code-review,
regression-test-design, documentation-maintenance, memory-hygiene,
configuration-management, internationalization, and accessibility-audit.
The last three supplemented scope missed by initial routing. The ECC
make-interfaces-feel-better skill supplied relevant wrapping, hierarchy and
interaction-feedback guidance. No learned project skill was selected. Old
terminal/install memory was revalidated against current source; no plan was
credited as execution or model success.

Shared ConnectionContext handles external settings without project identity;
GeneralEngine provides neutral-directory conversation with no project Store,
Workspace, snapshots, commands or memory. API research exposes bounded public
HTTPS source reading only; native Codex/Claude use verified tool restrictions.
agy remains project-implementer-only. Global session records preserve bounded
user intent and cumulative API accounting, not answer/source-body transcripts.
Native session ids are not reused across scopes. Per-session OS leases,
in-process mutation locks and live-owner/uncertain-cleanup guards protect
continuation. A general completed answer remains verified=false.

Interactive results now use grouped help and readable provider/model/setting/
status/usage/test/session/plan summaries, while headless JSON stays structured.
Word wrapping, semantic colors after layout, command/argument suggestions,
Ctrl+W/Ctrl+K, multiline arrow navigation, /clear, /view compact|full and
/motion on|off improve the existing fixed editor/status and bounded transcript.
Failures are visible; successful tool-result echoes are quiet. Test evidence is
shown from observed check records, never inferred from model prose.

Separate `/root/terminal_review` independently passed 53 focused tests and
closed concrete headless-auto parity, hidden tool failure, live API session
concurrency, lock cleanup and mutation-race findings with reproducible fixtures.
Two later parent regressions additionally exercise cross-process lease release
on owner exit and unconditional descriptor closure on native unlock failure.
No remaining review blocker was reported. Native/model restrictions reference
current official Codex configuration and Claude CLI documentation.

A real Windows ConPTY trial used the actual Screen/read_prompt/worker loop:
Tab completed /connect, Backspace removed a trailing character, bracketed
multiline paste plus Ctrl+W returned the expected two-line input, PgUp scrolled
during streaming (maximum offset 26), Ctrl+C stopped and joined the worker,
and the next editor accepted /exit. Compact layout and disabled motion were
active; screen and console modes were restored. The worker was a local synthetic
fixture, not a live provider turn. Ctrl+J and additional resize/edit paths have
deterministic coverage; no new physical keyboard or screen-reader trial is claimed.
External receipt: `erol-usability-live-probe-result.json` under OS temp.

Full README validation and clean packaging results are recorded below after the
frozen-code run. No paid API, live web source, macOS/Linux terminal or new
OS containment trial is credited for this change; API research has no search
index and does not extract PDF text. No external publication is authorized.

The user then requested automatic relevant skill use for ordinary prompts.
Project mode's existing project Registry/context integration was made explicit
in model guidance and visible skills events. General mode now uses the builtin
Orchestrator with empty memory, sends admitted bodies to the model, accounts
for context bytes during model eligibility and reports/persists only admitted
names. Two added regressions verify a real builtin market-research body reaches
the synthetic model without Store/Workspace/tools, no stale skill appears on
the next unrelated task, and a context-omitted skill is neither sent nor reported.
This tests context delivery, not paid-model compliance or learned skill success.
The first full README run passed 292 tests with two POSIX skips and all remaining
checks/build/smokes before this additive skill change; final validation is rerun
against the frozen final source.

After final source freeze, the actual global launch flow was exercised in a
Windows ConPTY from the user home using an external temporary EROL home. Grouped
help, /clear, compact view, motion off, language change, human status/settings and
exit worked; only connections.json was created, no global task/project state.
The local Codex 0.159.0-alpha.12.1 reported available and recognized projectless
research controls. Claude login was missing and agy was unavailable.
A real subscription Codex general-mode turn with an explicitly selected
gpt-6.1-sol returned the exact requested EROL_OK response, with project_id=null,
verified=false and no project state created. Native usage reported 21,052 input
and 40 output tokens; CLI remaining quota was unknown. API calls/accounting were
zero, so the $5 API guard was untouched. This verifies one projectless native
turn, not live web research, learned skill use or project sandbox access.
Sanitized external receipts: `erol-general-native-capabilities.json` and
`erol-general-native-turn-result.json` under OS temp.

Final frozen-source README sequence passed on Windows / Python 3.14.2:
294 Python tests (292 passed, two POSIX-specific skips), 12 Node tests, Ruff
lint/format, Mypy over 42 source files, adapter drift, 96 workflows / 289 routing
fixtures, context/learning evals, sdist/wheel build, clean wheel smoke, npm pack
and four-launcher npm smoke. Dependency installs passed. Logs:
`erol-general-validation-0s1pf753` under OS temp. Separate additive-skill review
independently reran 68 tests with no new concrete blocker.

The local 0.2.0 CLI environment was reinstalled from the verified wheel. An
isolated installed-Python smoke matched all 41 canonical Python module hashes,
registered three CLI connections plus OpenAI without project state, and executed
a synthetic projectless prompt with the actual packaged market-research body.
The response remained verified=false; no paid API or fake learned-use receipt
was awarded. Receipt: `erol-usability-installed-smoke-result.json` under OS temp.
Documentation-only final-result additions are followed by another build and
both package smokes. These checks preceded external publication.

### 0.2.0 publication

The user explicitly requested publication to main and a release on 2026-10-05.
The release-verification workflow is admitted in EROL task
`terminal-release-20261005`. The existing main rules require a pull request and
the six-platform/Python Quality gate; the owner's review bypass applies only
through a pull request. After merge, successful latest-main validation triggers
the existing stable/tag/GitHub-asset release workflow. No npm or PyPI registry
upload is part of this request. Release assets must match the validated source
through RELEASE.json and SHA256SUMS.

A prepublication portability check corrected the native-unlock test fixture to
use integer flock flags instead of Mock attributes; Windows does not exercise
their bitwise composition. Real Linux/macOS behavior is checked by the CI matrix,
not claimed from local Windows tests.

The user's standalone-terminal screenshot also exposed a missing Codex PATH
entry: desktop-host PATH found the CLI, ordinary Windows Terminal did not.
Bounded native desktop discovery now preserves PATH/explicit override precedence
and rejects links. A real Windows probe with PATH restricted to System32 found
Codex 0.159.0-alpha.12.1 and passed the native login/capability check. This probe
made no model call and does not verify other providers or platforms.

Initial PR #8 CI passed both Linux versions, then macOS 3.11 exposed two
portability issues. A Windows-keyboard fixture mutated global os.name and made
resource loading instantiate WindowsPath on POSIX; it now replaces only the
console module's os reference and asserts host identity stays unchanged.
Darwin may return EPERM while an exited group leader is not yet reaped. Cleanup
now gives the owned leader a bounded 250 ms wait, then still requires observed
leader exit and the existing numeric process-group zombie/absence proof. Live
or unknown groups and non-Darwin permission errors remain failures. A native
Darwin repeated-output regression exercises 25 cleanup attempts in CI; local
Windows deterministic fixtures do not establish native Darwin containment.

The user subsequently requested economic greetings, CLI token-only display and
correct terminal tab branding. Explicit complete greetings now classify small
and use low effort; attached technical/risky work stays conservative. A live
subscription Codex turn with automatic routing and System32-only PATH selected
gpt-6-luna/low and answered the Turkish greeting: 20,214 input and 14 output tokens,
API calls zero, verified=false, no project state. This is actual provider usage,
not a measured general token-saving claim. External receipt:
`erol-economic-native-turn-result.json` under OS temp.
Interactive CLI accounting hides USD when no API call/accounting is observed;
API and mixed-role tasks retain token/cost estimates. Windows console title is
set to EROL and restored on exit; OS/profile settings may suppress app titles.

The user's fresh-session screenshot confirmed Luna/token presentation but showed
the tab title returning to Claude after a provider turn. Native provider probes
can rename the shared console after EROL's initial title assignment. Active
Windows repaints now reassert a fixed, documented OSC 2 EROL title; plain/POSIX
and closed views emit no title control. A real ConPTY trial seeded Claude,
initialized Screen, simulated a provider overwriting the title, then repainted:
native title became EROL and close restored Claude. External receipt:
`erol-title-live-probe-result.json`. This tests the Windows terminal transport;
manually pinned/profile-suppressed tab names remain terminal policy.

Before this additive title repair, the complete local README sequence passed
324 Python tests (321 passed, three platform skips), 12 Node tests, Ruff/Mypy,
adapter drift, pack/context eval and both package builds/smokes. PR CI run
37319948984 passed all six OS/Python jobs, including the native Darwin repeat
cleanup regression. The title addition receives focused tests/review and a new
complete CI run before merging; that previous run is not credited to the new head.

## English README maintenance (2026-10-06)

The GitHub-facing README is translated into English, including installation
instructions, terminal usage, task/research examples, troubleshooting, learning
gates, and limitations. Command names, configuration keys, manifests, pinned
release examples, evidence links, and runtime behavior are preserved. English
contents links target the translated headings; explicit legacy heading aliases
preserve existing Turkish section links. Personal example paths are replaced
with neutral placeholders. The original brand PNG is unchanged.

This is a documentation-only change. Validation results are recorded below
only after the corresponding checks have actually completed. No live provider
calls or learned-skill qualification are part of this task.

Local validation on Windows / Python 3.14.2 passed: 327 Python tests (324
passed, three platform-specific skips), 12 Node tests, Ruff lint/format, Mypy
across 42 source files, adapter drift, 96-workflow / 289-fixture pack evaluation,
context/learning evaluation, sdist/wheel build, and wheel/npm package smokes.
The documentation check preserved all 39 fenced blocks, both JSON manifests,
CLI option names, external URLs, and legacy level-two section anchors. It
resolved 59 Markdown link targets and ran nine non-provider CLI examples using
an explicit project and a temporary external home. GitHub's Markdown API also
rendered the English document successfully.

Independent read-only review found one scope-check example had lost its Turkish
keyword alternatives. The exact original bilingual acceptance expression was
restored, and the reviewer confirmed the finding was resolved with no new
concrete blocker. No live provider calls, account login changes, runtime edits,
learned project-skill use receipts, or global promotion were performed.


## Three-stage reliability, efficiency and usability upgrade (2026-10-06)

The user approved implementation in accuracy → local efficiency → usability order,
then requested all generated reports under the external EROL home and automatic
subagent model/effort selection in native AI hosts. Team features and publication
remain outside scope. The runtime remains dependency-free and harness-independent.

Implemented software:

- Fifty additive Turkish/English acceptance fixtures (339 total), natural inspection
  and prioritization triggers, clause-scoped operation negation, bounded followup
  task context, explicit replacement/project resets and routing diagnostics.
- Repeated plan/explain/chat `--skill`, terminal `/skills use` and `/skills auto`,
  project/revision validation, actual context admission and no omitted-skill roles.
- Shared terminal/runner observed completion, distinct native/API review sessions,
  source/check/report digest binding and transactionally idempotent revision credit.
- Phase/model/tool/check/review accounting, full prepared prompt/tool/summary context
  proxies, independent retry escalation, provider discovery shared within a task,
  committed revision-based incremental indexing with a full legacy bootstrap.
- `/models compare`, native plan host detection/selection, manual model/effort
  precedence and per-role alternatives. Effort-only selection filters eligible
  profiles before choosing a model. Unknown native capabilities inherit current
  settings. Bridges use supported delegation parameters and never write agent
  Markdown/config/hooks. Official native capability references:
  [Codex subagents](https://developers.openai.com/codex/subagents) and
  [Claude subagents](https://code.claude.com/docs/en/sub-agents), checked 2026-10-06.
- Preview-first onboarding with exact-manifest trust, digest-bound wizard approval,
  automatic-connection reset, separate package/login/model/check doctor diagnostics,
  consolidated task result and read-only local panel terminal records.
- External task reports at `<EROL_HOME>/reports/<project-id>/<task-id>/`. API workers
  can discover/read/write only their exact report subtree; reviewers read it, and
  report changes invalidate evidence. Source docs and native discovery paths remain.
- Six controlled paired cases for pagination, message idempotency, filter state,
  migration rollback, authorization and sourced research, repeat/fixed-model/effort
  options and a repaired external-artifact live research trial. README packages
  three usage examples, with deterministic versus live verification distinguished.

Seven repeated local-work measurements preserved search results for 1,000 records.
Forced full reconciliation examined 1,000 records; unchanged incremental sync
examined zero. Median durations were 11.512 ms and 2.711 ms respectively. Five
native provider discovery/login/profile probes per task versus one shared probe
measured median 0.717 s and 0.141 s. These measurements cover local work only,
not model quality, charged model calls or overall task savings.

The requested six-case × three-repeat live behavioral gate remains **pending**.
A fixed Codex gpt-6.1-sol/medium attempt completed one failed pair: both arms
returned native filesystem denial before repair/check/review. The next owned run
was interrupted and durably cancelled after observing child exit. The partial
report explicitly records the blocker and is not a successful comparison. Profiles
were not calibrated from these failures, and no general success/token-saving claim
is made. Linux/macOS and live Claude/API/native delegation need separate trials.

External evidence is retained under the task report directory for
`erol-upgrade-20261006-implementation`: `behavior.json`, `local-work.json`,
`cli-smoke.json` and validation logs. Four CLI/deterministic research-trial smoke
cases passed without model calls. The source ledger smoke does not verify factual
accuracy. Independent read-only review found and resolved negation boundaries,
index commit provenance, retry context/escalation, report scope/digest/discovery,
queue digest compatibility, onboarding approval/automatic reset, effort-only
selection and general followup model-risk issues. The final reviewer found no new
concrete blocker and made no file changes or live model calls.

Final local validation on Windows / Python 3.12.10: 349 Python tests
(346 passed, three platform skips), 12 Node tests, Ruff lint/format, Mypy across
46 source files, adapter drift, 96-skill / 339-case routing and context/learning
evaluation passed. Build/package smoke outcomes and the final validation summary
are retained alongside the external task logs. Four CLI/trial smoke cases passed.
These results do not replace the pending live behavioral gate.

## Native Windows access diagnosis and follow-up (2026-10-06)

A fresh shell read/write/Python-test canary passed with the existing native
sandbox. A real paired runner trial reproduced PowerShell Get-Content and
Set-Location denial in both arms. Comparing directory ACLs exposed owner-only
ancestors installed by Windows `mkdir(mode=0700)` under the private memory/run
tree. This is an observed filesystem denial, not an automatic approval rejection.

New source worktrees are separate at `home/workspaces/<project-id>/<run-id>/worktree`.
Memory, run records, schemas and patches remain in private state. Windows home
and source containers inherit default ACLs without changing existing ACLs; POSIX
privacy is preserved. Resume validates exact new or legacy locations. Controlled
benchmark fixtures now use inherited Windows ACLs under `home/benchmarks/`, which
also avoids the long Git metadata path encountered with deeply nested reports.

The fresh pagination pair passed implementation, both acceptance checks and
separate native review in both arms (Codex 0.160.0, requested gpt-6.1-sol/medium).
Independent read-only code review found no new blocker. Complete validation then
found stale Queue worktree identity checks and a long-path fixture setup failure.
Queue now accepts only exact new or legacy identities; exclusive short benchmark
roots avoid that failure. The reviewer independently ran all three affected
regression tests, which passed, and found no additional blocker.

Final Windows validation passed: 351 Python tests (348 passed, three platform
skips), 12 Node tests, Ruff lint/format, Mypy across 46 source files, adapter drift,
339 routing fixtures, pack/context/learning eval, build and wheel/npm smokes.
The full six-case, three-repeat live trial is running with fixed requested
gpt-6.1-sol/medium. These comparisons vary injected context; native user/plugin
instructions remain active in both arms. Cross-model/effort ranking cannot be
calibrated from this single requested configuration.
External evidence is under `reports/erol-dc3958ee207243b6/erol-live-access-20261006/`.
No general savings, untested model calibration or learned-use credit is claimed.

## Review gate and terminal project/chat navigation (2026-10-06)

The live evidence audit found four legacy completed migration outcomes with
unresolved medium findings, plus a high finding that already required attention.
All unresolved findings now block runner completion and learning credit, at every
severity. Benchmark metrics recompute this gate for legacy runs. Learning metrics,
rollback and qualification revalidate historical attestations; stored records are
retained rather than silently rewritten. New regressions cover medium/low review,
legacy use credit, legacy qualification and fake-engine evidence qualification.
Independent review found and resolved the legacy metrics issue. Pre-navigation
validation passed 356 Python tests (353 passed, three skips), 12 Node tests,
Ruff/Mypy, 339 routing cases, adapter drift, pack/context/learning eval and build
with wheel/npm package smokes. This is local code validation, not live gate success.

The user's terminal navigation request adds `/my-projects` with visited checkouts,
read-only discovery of old memory metadata, displayed-number selection and fresh
project identity validation. `/chats` lists scoped records with pagination;
`/chats show` shows retained summary/change/check evidence and `/chats continue`
explicitly starts work. `/rename` and `/chats rename` preserve evidence and persist
names across reopen/continuation. The user chose existing summaries and records;
full transcript retention is not added. Catalog and chat state stay external.

Independent review reproduced and resolved two issues: long display names rejected
by ID validation, and switching sessions during preflight planning. Display names
are bounded printable text; whole-task busy/lock guards include planning and all
exception exits. The reviewer independently passed all 14 navigation regressions
with fake providers and found no remaining actionable issue. Complete validation
passed on Windows / Python 3.12.10: 371 Python tests (368 passed, three platform
skips), 12 Node tests, Ruff lint/format, Mypy across 47 source files, adapter drift,
96-skill / 339-case routing and pack/context/learning evaluation, build and wheel/npm
package smokes. The reviewer also independently passed the updated two startup
tests and all fifteen navigation tests: 17/17. No live provider calls were made by
the reviewer. Current evidence is external under
`reports/erol-dc3958ee207243b6/erol-terminal-projects-20261006/`.

The fixed requested Codex gpt-6.1-sol/medium matrix finished all 36 arms (six cases,
three repeats, context enabled/disabled). Strict success was 16/18 with injected
context and 14/18 without it: 30/36 overall. Five migration outcomes retained open
review findings (four had legacy completed status); one control research arm
timed out. The source access denial did not recur. The observer then failed on its
null worker logging; the timeout was recovered from the retained run without
replay, and only the remaining three research arms were launched. Those final
arms used the corrected review gate; all original run evidence remains retained.
This change in gate version is an explicit experimental limitation.

Median elapsed seconds, including failed outcomes, with / without injected context:
pagination 124.266 / 129.516; idempotency 113.110 / 138.266; filter state
116.921 / 135.046; migration rollback 527.360 / 523.671; authorization
120.656 / 129.203; sourced research 369.656 / 301.125. The recovered timeout
duration is a phase-sum estimate. Reported usage/cached usage is distinct from
cost; CLI cost remained unknown. Native user/plugin instructions were active in
both arms and local validation overlapped part of the timings. The full live
quality gate **did not pass**; three samples and one requested model/effort cannot
calibrate cross-model rankings or justify a general savings claim. No profile
rank update or learned-use credit was applied. Final calibration and strict
evidence audit are in the external access task's `calibration.json` and
`evidence-audit.json`; successful sourced reports remain in their task report
directories, with model-asserted independent source reviews explicitly labeled.

The user explicitly authorized pushing the completed source to `main` and creating
a release. Publication follows the existing validate → automatically versioned
stable release workflow, with exact source provenance and wheel/sdist/npm assets.
The live behavioral quality failure remains documented; passing static/package CI
must not be presented as broad model success. Publication status and remote CI
evidence are retained in the external task report after the workflows finish.

The first PR CI run exposed POSIX-only false secret detection for the newly
generated top-level `artifact_directory` field. Run-store validation now applies
the existing absolute-path, full credential-pattern and per-component entropy
checks to that exact field. Arbitrary task/context strings keep full-value scans.
The two path regressions now cover report persistence and credential, relative,
non-string and nested-field rejection. This is a narrow metadata fix, not a
general relaxation of secret detection. The failed initial CI evidence is retained
externally; the corrected source must pass the complete matrix before merge.

## Terminal output and model selection usability — 2026-10-07

The user reported missing generated paths, unclear edits and inaccessible manual
model selection. Five regressions failed against the old behavior before repair.
Results now show absolute source/report paths, change kinds, line counts and short
patches. `/files` exposes observed report metadata; `/diff NUMBER [PAGE]` pages
retained patches, including historical continuation steps. Legacy inventories and
truncated/binary evidence remain explicit. No full conversations are retained.

`/model` now opens a numbered inventory; `/model NUMBER`, unambiguous raw IDs and
fully qualified names work. Snapshot/config guards prevent stale-number replacement,
and unavailable connections are rejected. `/effort` validates supported profiles;
manual preferences apply only to implementer/assistant, remain process-local and
cannot change during active execution. Reviewers/planners retain separate routing.

Independent review reproduced full-name/raw-ID collisions, numeric filename/index
collisions, missing legacy absolute paths, inaccessible historical diffs and C++
increment/decrement line-count errors. All were repaired with targeted regressions.
The local global launcher points to `~/.erol/cli/0.2.0`, independently of installed
plugins; it must be updated to the validated distribution to expose these changes.
Final validation/review/installation evidence is kept outside the repository in
`reports/erol-dc3958ee207243b6/erol-terminal-ux-20261007/`.

## Guided terminal and mantis follow-up — 2026-10-07

The user requested improvements across command discovery, project/model selection
and reading, and reported unnatural mantis animation. Startup now points to common
actions and `/menu`. Rich model, effort, project and saved-chat pickers support
arrows, numeric selection, paging and cancellation without starting model work.
Headless JSON and plain numbered views keep their existing contracts. Preferences
remain visible, Tab cycles ambiguous completions, and the narrower brand sidebar
leaves more room for answers. Worker/reviewer protocol JSON is kept out of the
conversation; validated results and observed errors/checks remain visible.

Animation no longer shifts disconnected horizontal strips. A slow light cycle
preserves the original silhouette at every phase; monochrome and motion-off stay
static. The original brand asset is unchanged. Nineteen focused acceptance tests
cover menu input/paste/cancel, inventory selection, chat paging, reading boundaries
and silhouette stability. Actual generated terminal frames were rasterized and
visually inspected; this is synthetic frame inspection, not universal live UI
coverage. Full gates and independent review evidence are retained externally in
`reports/erol-dc3958ee207243b6/erol-terminal-guidance-mantis-20261007/`.

Independent review identified a paste-cancellation boundary that could expose the
remaining pasted text to the next prompt. The picker now consumes the complete
bracketed payload before accepting cancellation; an outer-loop regression covers
both pasted Ctrl+C and Esc, rather than only the choice-state component.

The initial remote matrix found omitted generated plugin runtime copies and a
legacy Tab expectation. Runtime snapshots were regenerated through the canonical
drift script, and the existing editor test now asserts the requested completion
cycling. The failed CI log is retained externally; the corrected distribution
must pass the complete matrix and local gates before publication.

## Simple README installation — 2026-10-07

The README now starts with a short terminal/Codex/Claude setup and first use.
Windows terminal setup uses three pipx commands; the stable GitHub source archive
keeps the command independent of changing wheel filenames and needs no Git/Node
installation. macOS/Linux has a separate folded setup with official pipx package
guidance. The original detailed guide and exact development validation sequence
remain in a collapsed section, preserving existing anchors and manual options.
The manual wheel example now targets the validated v0.2.4 release. pipx update
and removal are documented alongside existing standalone installation options.

Installation verification uses external temporary pipx home/bin directories and
an isolated bootstrap, never the user's existing EROL executable or user PATH.
The stable archive install, version and headless help/menu are exercised;
ensurepath is checked in dry-run mode. macOS/Linux package-manager setup and
native plugin installation are documented paths, not new live acceptance claims.
Evidence remains external under
`reports/erol-dc3958ee207243b6/erol-simple-readme-install-20261007/`.
