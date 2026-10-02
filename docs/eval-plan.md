# Behavioral evaluation plan

Defined on 2026-10-02 before the learning implementation. These are acceptance contracts, not measured performance claims. ECC `eval-harness` informed the deterministic graders; ECC `security-review` informed persistence and input boundaries.

The release gate is every deterministic acceptance test passing. A passing test proves the exercised fixture, not agent reliability, universal secret detection, or operating-system containment. Record failures and repairs; do not invent `pass@k`, token savings, or time-equivalent reasoning.

| ID | Scenario | Required behavior |
| --- | --- | --- |
| MEM-01 | Same repository, different harness | Both adapters resolve one canonical external project state. |
| MEM-02 | Equal folder names, different roots/remotes | Stable IDs remain distinct; credential-bearing remotes leave no credential in persisted identity. |
| MEM-03 | Relevant and unrelated memories | Query retrieves relevant incidents/facts within its budget; stale entries are excluded by default. |
| MEM-04 | Secret-like text in any persisted input | Write fails before content reaches SQLite, Markdown, generated skills, or diagnostic output. |
| MEM-05 | Reopened store | Incident evidence and lifecycle state persist and can be retrieved. |
| LEARN-01 | Timeout with changing timestamp/request ID | Same component/exception yields same fingerprint; different exception or component remains distinct. |
| LEARN-02 | Three independent verified occurrences | Creates a repeated pattern and at most one candidate; unverified outcomes do not qualify. |
| LEARN-03 | Replaying a task/event | Does not increase independent occurrence or successful-use counts. |
| LEARN-04 | Existing equivalent skill | Duplicate detection prevents another generated candidate for the same scope/workflow. |
| LEARN-05 | Draft activation request | Refused without passing evaluation bound to the current artifact and evidence. |
| LEARN-06 | Positive and negative trigger fixtures | All expected activations and exclusions pass; unrelated tasks never activate the generated project skill. |
| LEARN-07 | Missing or failing behavior evidence | Candidate remains inactive; a caller's unchecked `passed=true` is insufficient. |
| LEARN-08 | Unsafe/generated command or injected instruction | Security gate blocks candidate; scanning never grants tool permissions or runs candidate scripts. |
| LEARN-09 | Candidate with excessive context | Context gate fails before activation. Character-based estimates are labelled estimates. |
| LEARN-10 | Passing local candidate | Activation writes a versioned project-local skill, linked to its incidents and eval; other projects cannot select it. |
| LEARN-11 | Real use in distinct tasks | Success/false-activation/regression observations reference the active revision and actual supplied test/review evidence. Fixtures are labelled fixtures. |
| LEARN-12 | Successful local usage | Creates a promotion candidate; no global registry mutation occurs automatically. |
| LEARN-13 | Explicit generalization approval | Requires approved current revision and reviewed cross-project evidence; remains `approved_for_generalization` and leaves the global registry unchanged. A portable globally installed revision is a later gate. |
| LEARN-14 | Revision changes after eval | Old evaluation and usage evidence cannot qualify the new revision for activation/promotion. |
| LEARN-15 | Failed revision or false activation | Skill can be disabled/revised; rollback restores a previously validated revision without transferring its trust to edited bytes. |
| LEARN-16 | Repeated failed strategy | Reports bounded escalation/replan guidance; never executes an unlimited retry loop. |

End-to-end golden sequence: record three independent, evidence-backed pagination failures; match the second to the first; detect a pattern; draft one project skill; run positive/negative routing, behavior-evidence, context, and security gates; activate locally; select it on a new matching task; record distinct successful uses; request a promotion candidate; prove the global registry remains unchanged. A failed-use variant must disable or revise the skill. Store all fixture data in temporary directories.

Behavior evaluation checks that evidence is provided and bound to the draft. A local deterministic engine cannot establish that an arbitrary external test genuinely repaired a production bug. Human review and future trusted harness receipts are separate evidence layers.

## Implemented evaluation scope

`tests/test_memory.py` exercises external state, credential-free identity, relevance/budgets, stale history, transactional rollback, secret rejection, repeated contradiction revisions, and error-family normalization. `tests/test_learning.py` exercises incident repetition, independent-task deduplication, conflicting remedies, duplicate suppression, eval/context/security gates, project isolation, revision-bound task usage, failure disabling, rollback, and controlled generalization approval. `tests/test_cli.py` repeats the full persisted lifecycle through separate CLI subprocesses, including paths containing spaces, error exit statuses, rejected draft activation, replay refusal, and sanitized error output. All evidence in these tests is explicitly synthetic local attestation.

Actual global skill installation is deliberately absent. Approval produces review
material for a future portable revision; it does not install the project-specific
body into a global registry. No global auto-promotion is claimed. The advisory CLI
bridge still depends on the calling harness to execute repairs/tests and supply
their evidence. Opt-in `run` observes its own check processes separately.

## Execution and research acceptance

Follow-up gates: discovery must not persist secret lines or execute repository
instructions; changed source/checks/policy must prevent queue launch; duplicate and
cyclic dependencies must be rejected; dependent work may consume only completed,
unchanged predecessor patches; interruption cannot launch a duplicate model session.
Parallel reviewer IDs must be distinct, results bound to one digest, and any failure
or high finding blocks success. Search indexes must reject stale/withdrawn revisions,
preserve budgets and project isolation. Source receipts must reject private addresses,
unsafe redirects and oversized content; a fetched page does not establish factual
truth. Benchmark fixtures/checks must be identical across paired arms; incomplete
native usage cannot become invented cost/savings. Panel endpoints are read-only,
loopback-bound, escaped and omit raw prompts/conversations.

| ID | Trigger | Required result |
| --- | --- | --- |
| RUN-01 | Clean Git source, both fake CLI protocols | Baseline fails, repaired acceptance passes, distinct review session passes, same source/check digests and retained applicable patch. |
| RUN-02 | Failing acceptance or high review finding | At most three implementer attempts, two matching failures request replan, no success credit. |
| RUN-03 | Malformed/truncated/secret event stream | Bounded sanitized record, attention state, no raw conversation or credential persistence. |
| RUN-04 | Native timeout, cancellation or checkpoint interruption | Owned process cleanup, durable state, exact acknowledged session resume; no second worker for unknown/alive state. |
| RUN-05 | Competing caller or different external home | OS lease and shared Git marker reject duplicate/unfinished project workers without claiming a second task ID. |
| RUN-06 | Changed checks, source or skill revision | Old evidence cannot establish completion; checks/review invalidate and revision gates revalidate. |
| RUN-07 | Replayed task ID or context-omitted skill | Refuse replay; no omitted skill usage; atomic finalization cannot double-credit. |
| RUN-08 | Turkish/spaced paths and public CLI lifecycle | Preserve source project identity and UTF-8 JSON; memory schema and existing learning commands remain compatible. |
| RES-01 | Research mode | Explicit native web capability/tool policy; no editing tools on reviewer; default model/config remains native. |
| RES-02 | Invalid dates, URLs, citations or claim references | Static artifact failure; cannot substitute it for mandatory acceptance behavior. |
| RES-03 | Missing/unavailable/contradicted source review | High finding blocks completion despite passing local checks; model source assertions labelled separately. |
| RES-04 | Edited research artifact after verification | Same source digest rules invalidate old acceptance and source review. |

Fake CLI and ledger fixtures are deterministic contract evidence, not retrieval or
model-accuracy evidence. Explicit live scripts use external temporary Git projects;
their outcomes and auth/platform limits appear separately in validation.md.

## Measurement protocol

Run `python -m unittest discover -s tests -v` and `python -m erol eval` from the same checked-out revision. Save command, exit status, fixture count, and named checks. Built-in evals can demonstrate routing, persistence, and lifecycle policy without invoking a model. They do not demonstrate live Codex/Claude task execution.

For a future vanilla-versus-EROL comparison, use identical repository snapshots, tasks, model/version, tool policy, retry budget, and graders. Collect actual input/output tokens where the harness supplies them, selected-skill counts, relevant memory bytes, retries, wall time, regressions, and reviewer findings. Separate first encounter, retrieval encounter, and activated-skill encounter. Publish raw provenance and limitations before any improvement percentage.

The broader attachment's backend, SQL, cache, messaging, frontend, creative, and marketing golden tasks require live domain fixtures and harness execution. Metadata-routing examples alone must not be reported as successful completion of those tasks.
