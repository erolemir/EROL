# Local validation

Release preparation: the first PR #6 Linux run rejected legitimate slash-joined
execution metadata as high entropy. The correction reuses component-aware scanning
for six explicit RunStore path fields; arbitrary text and credential components
remain rejected. Two added regression tests pass locally, alongside Ruff and Mypy.
The prior 180-test delivery record below predates these two tests. Remote platform
results must be read from the PR/main validation runs, not inferred from this fix.
The subsequent Linux run passed 181 tests and exposed a cleanup assertion that
confused an orphan zombie PID with a running descendant. The assertion now accepts
only a reaped PID or observed Linux zombie state; an executing child still fails.
Production unknown-process handling remains conservative.
Both Linux jobs then passed. macOS exposed EPERM on repeated zombie-group cleanup;
the runtime now requires observed terminal group states before accepting that
case. A regression covers terminal/live/mixed/unknown groups and a living leader.
The next matrix passed all four Linux/macOS jobs. Windows 3.14 found that an
immediate PID assertion raced asynchronous Job Object termination. The cleanup
test now observes up to five seconds of kernel completion; living PIDs still fail.
The local full run passed 183 tests (182 passed, one POSIX-only skip), and all
distribution/eval checks passed after the runtime corrections.

## Autonomous work follow-up: 2026-10-03 (Istanbul)

Windows / Python 3.12.4 / Node 20.15.0. The final full unittest command ran
**180 tests: 179 passed and one POSIX permission check skipped on Windows**, in
208.547 seconds. Ruff lint/format passed (148 files); Mypy passed for 30 canonical
source files and the additional Linux/Darwin static platform checks. All twelve
Node tests passed, including panel filtering, literal rendering of untrusted text
and endpoint failure. Adapter drift and the 96-skill / 289-case pack/context/learning
validation passed. Development requirements installed successfully in the ignored
venv. These results supersede the 158-test core record below.

The remaining exact README delivery commands also passed: `python -m build`
produced the wheel and source distribution; `python scripts/package_smoke.py`
passed a clean offline wheel installation and routing/learning/data checks;
`npm pack --pack-destination dist` produced a local 308-file archive; and
`python scripts/npm_package_smoke.py` passed all four isolated Node/Python
CLI/plugin launchers with 289 routing cases and private artifact exclusion.
No package was uploaded to a registry. `git diff --check` passed.

New deterministic cases cover actual overlapping native-process fixtures,
distinct peer IDs, completed-peer resume without relaunch, cancellation of both
owned peers, queue deduplication/recovery and late cancellation checkpoints,
source/check/policy changes, dependency cycles and transitive verified deltas,
Turkish/spaced public policy paths, index project/revision/file freshness,
public/private/mixed DNS, redirect revalidation, body limits and read-only HTTP
responses. A Windows reset while rejecting an unread POST body was reproduced
in the full suite, fixed with bounded body draining and verified in the final suite.
The in-app browser bridge was unavailable; no visual browser verification is claimed.

### New live Codex trials

- `scripts/advancement_trial.py`: passed policy discovery/enqueue, three failing
  arithmetic tests becoming three passes, two concurrent distinct read-only native
  reviewers, and checkpoint interruption/resume using the same peer session IDs.
  Run `run-0cb91d3213644e348b7912889c9536e0`, retained fixture
  `erol-live-queue-d1ymcuiy`. Both reviewers inspected the supplied/source evidence;
  Git metadata was inaccessible under their native policy. The exact tested and
  reviewed source digest matched. This does not test mid-tool native interruption.
- `scripts/research_trial.py`: passed the SQLite/PostgreSQL requirements and a
  distinct source review. EROL directly observed HTTP 200 for all three official
  cited pages, retaining time, byte count and SHA-256 digests without body archives.
  Run `run-f9cb770b90424ce9a6e7f1a3c7172743`, fixture
  `erol-live-research-v0tz30eq`. The reviewer reported opening each source, but direct
  file inspection was denied; its source assessment remains a model assertion.
- `benchmark --suite examples/behavior-suite.json --harness codex`: one controlled
  pair passed both arms in one attempt, with no check regressions. EROL took
  190.109 seconds and reported 408,343 input / 2,671 output tokens; control took
  189.187 seconds and reported 379,607 input / 2,468 output tokens. Both costs were
  null because Codex did not report prices. Cached-input counts are reported
  separately and must not be added to input totals. This sample shows no speed or
  usage advantage. Native user/plugin instructions remained active in both arms;
  the comparison varies injected context, not the entire harness environment.

These trials used Codex 0.159.2 and separate external temporary homes/Git projects.
Selected reports are under ignored `.validation`, not raw native streams. The user
waived further Claude live trials after the earlier OAuth failure. Claude's
deterministic CLI contract tests remain enabled; live Claude success is unverified.
This host has no general Linux WSL distribution and its Docker daemon was not
running. New Linux/macOS runtime behavior was not tested; the historical CI matrix
below predates these changes. No release, merge, push or external publication occurred.

## Autonomous core and research: 2026-10-02

Current checkout tested locally on **Windows, Python 3.12.4, Node.js 20.15.0**.
Runtime dependencies remain empty. Dev tooling ran in an ignored local venv.
This is a new local record; the historical remote CI matrix below predates these
changes. No new CI matrix or live Linux/macOS execution is claimed.

| README command | Observed result |
| --- | --- |
| `python -m pip install -e . -r requirements-dev.txt` | Passed in the development venv. |
| `python -m unittest discover -s tests -v` | 158 tests: 157 passed, one POSIX permissions check skipped on Windows. |
| `ruff check src tests scripts bin` | Passed. |
| `ruff format --check src tests scripts bin` | Passed. |
| `mypy --explicit-package-bases src/erol bin/erol.py` | Passed for 25 canonical source files. |
| `npm test` | Ten launcher tests passed. |
| `python scripts/check_adapter_drift.py --check` | Passed after regeneration from canonical sources. |
| `python scripts/validate.py` | 96 skill bodies, 289/289 routing cases, context lint and deterministic learning fixture passed. |
| `python -m build` | Wheel and source distribution built. |
| `python scripts/package_smoke.py` | Clean offline wheel install, 96 skill plans, canonical data digests, routing and learning fixture passed. |
| `npm pack --pack-destination dist` | Local archive built; no registry publication. |
| `python scripts/npm_package_smoke.py` | Four isolated CLI/plugin Node/Python launchers passed 289 routing cases; private artifacts excluded. |

Additional Linux/Darwin Mypy platform checks passed. These are static typing checks,
not runtime platform evidence. Fake CLI subprocesses cover both event protocols,
cross-harness review, acceptance/review failure, malformed/truncated/secret streams,
timeouts, cancellation and descendant cleanup. Real temporary Git repos with
Turkish/spaced paths exercise identity, patches, source mutation, replay refusal,
exact native-session resume, missing-ack/live-process refusal and different-home
project locks. Revision changes, omitted context and finalization checkpoint replay
cannot produce invalid or duplicate learned-skill credit. Existing memory schema
and learning regressions pass. Research fixtures separately reject malformed dates,
URLs, unknown claims/citations and incomplete/unavailable/contradicted source review.

### Native trials, separate from deterministic tests

`python scripts/execution_trial.py --harness codex --report .validation/execution-codex.json`
passed with **Codex 0.159.2**. Three arithmetic tests failed at baseline and passed
after the repair. Runner interruption was injected after the native worker finished
but before its checkpoint; resume used the exact acknowledged worker session.
A distinct reviewer inspected source/tests, returned no blocking findings and
shared the same tested/reviewed digest. The root fixture remained unchanged and
the patch/worktree were retained. This is one narrow repair, not a general task
success benchmark or a mid-tool native interruption test. Git metadata was
inaccessible to the reviewer; EROL supplied its observed patch/check evidence.

`python scripts/research_trial.py --harness codex --report .validation/research-codex.json`
passed with Codex 0.159.2 live search. It produced a SQLite/PostgreSQL comparison,
six claims, three official source pages, recommendation and limitations.
The independent reviewer reported opening all three sources and checking their
claims. Report coverage and structural integrity are runner-observed; source
verification is labelled **model_review_assertion**. Source accuracy is not
cryptographically authenticated, and broad product/competitor quality is unmeasured.

`python scripts/execution_trial.py --harness claude --report .validation/execution-claude.json`
was attempted with **Claude 2.1.92** and ended `needs_attention`, exit 1.
Local `auth status` reported logged in, but actual execution returned HTTP 401:
OAuth had expired and native reauthentication was required. No post-repair check,
review, resume-success or skill credit was reported. The bounded native diagnostic
is retained; no credentials or raw transcript was copied. Live Claude repair/resume
and research retrieval remain unverified pending native login. The adapter was not
silently replaced and no saved config/permission/hook settings were changed.

Trial JSON files live under ignored `.validation`; temporary fixtures and run DBs
remain outside the repo. These receipts are local observations and model assertions,
not externally signed evidence. Worktrees and permission/tool policies are not
an OS sandbox. This earlier core record predates the policy queue, parallel
read-only reviews, indexed retrieval and panel described above. Neural embeddings
and simultaneous writing agents remain unsupported.

## Earlier catalog and release records

Recorded on 2026-10-02 on Windows with Python 3.14 and Node.js 24.13.0.
This local record precedes publication. The later
[remote validation run](https://github.com/erolemir/EROL/actions/runs/37011560028)
passed all six Windows/macOS/Linux and Python 3.11/3.14 jobs, including 117 Python
tests, ten Node tests, lint, types, builds, isolated package checks and EROL evals.
Windows skips two unsupported platform checks; other platform results are visible
in their CI jobs. This is package and deterministic behavior evidence, not a live
model-success benchmark.

## Evidence

The curated-catalog expansion passes 126 Python tests (two Windows platform skips),
ten Node tests and 289 routing fixtures across 96 builtin skills. English, Turkish
and ASCII Turkish cases exercise all skills; adjacent-domain negatives cover SEO
versus ingestion and frontend query caches versus backend Redis. Ruff, formatting,
mypy, adapter drift, static pack qualification and context lint pass.

An independent review agent inspected all 72 new skill bodies and the changed
runtime. Findings about missing advisory roles, ambiguous phrases and installed
wheel validation were corrected. Its old/new router comparison covered 294 tasks
against 97 builtin/project metadata entries with identical scores. Two limited
forward trials produced a hypothetical paid-search draft and a PostgreSQL recovery
runbook using the selected skill bodies. They distinguished assumptions from
evidence and identified budget/recovery prerequisites. Neither trial launched ads,
spent money or restored a database; these are not measured outcome improvements.

Fresh wheel installation qualifies all 96 bodies, checks canonical registry and
role digests, creates 96 advisory plans, and runs routing and learning fixtures.
The npm archive runs the 289-case eval through all four isolated launchers.

Earlier validation records follow for comparison.

The Turkish-routing follow-up passes 121 Python tests (two Windows platform skips),
ten Node tests, and 68 routing fixtures. New cases cover all 24 builtin skills,
the Tahakkuk screen/date-filter request, uppercase dotted İ, ASCII typing, and
unrelated holiday/photo/physical-filter requests. A copied native plugin selects
`frontend-state-correctness` from an unrelated project with empty learned skills.
The original regression failed before the fix. This verifies deterministic routing
and packaged execution, not a live model's ability to repair that application's code.

- Python unit, integration and adversarial lifecycle checks pass. Two checks are
  skipped locally: a Windows real-symlink case unavailable to the process and a
  POSIX-only permission check.
- Ruff lint, Ruff formatting and mypy pass on canonical sources.
- The launchers have executable tests for interpreter discovery, argument
  boundaries, inherited-environment isolation, exit codes and safe temporary setup.
  Direct Python fallback tests exclude Node entirely and require isolated startup.
- In the original baseline, all 24 built-in skills pass static quality checks. All 32 golden routing
  fixtures pass, including negative triggers.
- Context lint passes: four active skills maximum and a default budget estimated
  at 4,000 tokens using characters/4. This is not a tokenizer measurement.
- Generated adapter and plugin snapshots are compared to canonical sources.
- Python wheel and source distribution are built; an isolated offline wheel
  installation checks registry discovery, routing and the learning fixture.
- A local npm archive is unpacked into a temporary directory. Both its CLI and
  native plugin launchers, including direct Python entries, execute the bundled routing eval from an unrelated
  project, with ambient import shadowing rejected. Private databases, virtual
  environments, caches and validation artifacts are excluded.

Run the commands in README to reproduce the checks. Test counts are deliberately
not a compatibility guarantee; the assertions and tested environment define their scope.

## Learning fixture

The deterministic demo reproduces a pagination bug three times: a nonunique
version-only cursor skips equal-version rows across batch boundaries. Composite
version/ID pagination fixes the fixture and passes held-out rows.

Historical match counts across the three encounters are 0, 1 and 2. One candidate
passes reviewed fixture evidence, becomes a project skill, is admitted to three
distinct fixture tasks and qualifies as a promotion candidate. The global registry
is unchanged. This executes a trusted fixture interpreter, not a live autonomous
agent or a human review. It cannot establish better model performance.

## Local benchmark

One 500-iteration sample on this host, with an empty temporary memory and the task
`RabbitMQ duplicate consumer at least once delivery`, produced:

| Measurement | Result |
| --- | ---: |
| Mean routing and plan render time | 4.32 ms |
| Selected skill bodies | 1 |
| Rendered context packet | 1,865 characters |
| All catalogue bodies combined | 28,023 characters |

These are local routing and rendered-context proxies. Comparing the packet with all
catalogue bodies does not model a baseline coding assistant. There is no measured
task success rate, repair time, provider cost or actual LLM token reduction.

## Native integration limits

Generating valid manifests, validating them with available CLI tools and invoking
the copied runtime are separate from loading a plugin in a live assistant session.
Codex desktop `@EROL` selection, Claude `/erol` invocation, model compliance with
the bridge and cross-harness task completion still require live acceptance tests.
During initial development no plugins were installed into user settings. At the
user's subsequent request, local EROL 0.1.1 was installed and enabled in Codex and
Claude Code. See installation-check.md for that machine's acceptance results.
GitHub releases now distribute the native plugins and archives. No npm or PyPI
registry publication is claimed here.

## Security scope

Adversarial checks cover replay, scope isolation, revision drift, stale promotion
evidence, false/failed use, conflicting installer ownership, path links/reparse
points, secret-shaped input, raw argument boundaries and Python import shadowing.
The core never executes generated workflow commands. Reviewed behavior evidence is
a caller-provided attestation: EROL cannot authenticate identities or prove that
external tests ran. Conservative scanners do not replace an execution sandbox.
