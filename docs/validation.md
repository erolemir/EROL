# Local validation

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
