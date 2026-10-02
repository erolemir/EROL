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

Actual global skill installation is deliberately absent. Approval produces review material for a future portable revision; it does not install the project-specific body into a global registry. No global auto-promotion is claimed. The CLI bridge still depends on the calling harness to execute repairs/tests and supply their evidence.

## Measurement protocol

Run `python -m unittest discover -s tests -v` and `python -m erol eval` from the same checked-out revision. Save command, exit status, fixture count, and named checks. Built-in evals can demonstrate routing, persistence, and lifecycle policy without invoking a model. They do not demonstrate live Codex/Claude task execution.

For a future vanilla-versus-EROL comparison, use identical repository snapshots, tasks, model/version, tool policy, retry budget, and graders. Collect actual input/output tokens where the harness supplies them, selected-skill counts, relevant memory bytes, retries, wall time, regressions, and reviewer findings. Separate first encounter, retrieval encounter, and activated-skill encounter. Publish raw provenance and limitations before any improvement percentage.

The broader attachment's backend, SQL, cache, messaging, frontend, creative, and marketing golden tasks require live domain fixtures and harness execution. Metadata-routing examples alone must not be reported as successful completion of those tasks.
