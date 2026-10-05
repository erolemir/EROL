# Discovery, bounded work and evidence

The next delivery adds six connected capabilities: work discovery, policy-driven
queue execution, paired behavioral measurements, parallel read-only reviewers,
indexed bilingual retrieval with source freshness checks, and a local evidence
panel. Research additionally records EROL-observed source access independently
from a model's assessment of claims.

## Discover and authorize work

```console
erol checks show --file /absolute/reviewed-checks.json
erol checks trust --file /absolute/reviewed-checks.json
erol scan --checks /absolute/reviewed-checks.json
erol scan --issues /absolute/reviewed-issues.json
erol queue policy --harness codex --checks /absolute/reviewed-checks.json --output /absolute/policy.json --max-tasks 2 --reviewers 2
erol queue enqueue --policy /absolute/policy.json
erol queue list
erol queue work --policy /absolute/policy.json
erol queue resume --id JOB_ID --policy /absolute/policy.json
erol queue cancel --id JOB_ID
```

Scanning alone does not run models. Supplying `scan --checks` explicitly runs the
reviewed literal check commands in the source project, without shell expansion.
Source mutation discards the scan. Git-tracked and nonignored files are bounded
to 10,000 files, four MiB per file and 64 MiB total; TODO extraction skips binary
and oversized text files and keeps at most 200 TODO candidates. Imported issues
use the [reviewed JSON format](../examples/issues.json), with at most 50 entries.
Secrets in candidate text are omitted. Repository notes are untrusted references.

Priority uses observed acceptance failures, static failures, imported issues and
TODOs in that order. Effort stays unknown; this heuristic does not predict cost.
`queue policy` creates a project-bound check-repair policy without executing it.
Review the generated JSON before running `queue work`. Its rules explicitly name
kinds, path globs, harnesses, mode and absolute check paths. The limits bound tasks
per invocation, total time, per-task/session/check time and reviewer count.
The maxima are 20 tasks, four hours total, one hour per task, 15 minutes per model
session, five minutes per check and three reviewers. The default generated policy
permits one task and one hour total. There is no background daemon or automatic
publication.

`queue work --scan` discovers TODOs and enqueues matching rules first. To discover
check failures, use the explicit `scan --checks` command beforehand. Default
generated rules match check failures only. Source, policy and check digests bind
the queue entry. A changed source or definition requires rescan/enqueue; the queue
does not silently widen authorization. Candidate/policy duplicates are ignored.
Every job has its own unique task ID; work.db is separate from memory.db/runs.db.

## Dependencies and recovery

```console
erol queue depend --id CHILD_JOB --on PARENT_JOB
erol queue depend --id FINAL_JOB --on PARENT_JOB --on OTHER_PARENT_JOB
```

Dependencies form an acyclic graph. Completed parents must still match their
tested/reviewed source digest. EROL composes each ancestor's verified delta patch
once into a new detached worktree before baseline checks. Temporary Git indexes
write tree objects without staging the user's index or creating commits. Conflicts
stop for attention; there is no automatic resolution, merge, push or publication.
Legacy runs without delta packages support direct parents only.
Composition permits at most 20 packages, 20 dependency levels and 128,000 patch
bytes. Readiness is ordered by dependency depth. Stale queued entries must be
cancelled or handled explicitly before processing a changed policy/source.

The queue claims a job before launch and locates interrupted runs by its task ID,
including a crash before the run ID was saved. An uncertain claim without a run
receipt refuses duplicate launch. Explicit `queue resume` reuses native sessions
and reconciles a run already finalized before the queue checkpoint. Cancellation
is a separate durable flag so a late worker payload cannot erase it. The Git and
external-home OS leases preserve one writing worker per source project across
different EROL homes.

## Parallel independent review

```console
erol run --task "Repair the boundary case" --harness codex --checks /absolute/checks.json --reviewers 3
```

Two or three native reviewer sessions run concurrently with acceptance/regression,
security/permission and domain focuses. They receive the same patch and observed
checks, use read-only tool policies and must acknowledge distinct session IDs.
All blocking findings apply to completion. Any source mutation invalidates their
evidence. A resume reuses finished peers and resumes acknowledged unfinished peers;
unknown or live peers prevent a second launch. This is parallel review with one
implementer, not simultaneous writing agents. Worktree separation is not an OS
sandbox. Native CLI containment and Windows/POSIX process cleanup retain the
[execution platform limits](execution.md).

## Indexed memory and research access

```console
erol memory index
erol memory search "veritabanı zaman aşımı" --mode hybrid --max-chars 6000
erol memory search "database timeout" --mode lexical
```

The separate rebuildable search.db schema 2 contains a SQLite inverted term
index. BM25 combines literal normalized tokens with explicit lower-weight Turkish
and English concept aliases. Plans and task context use hybrid retrieval by
default; lexical search remains available. This is deterministic concept
expansion, not neural embedding search. Search revalidates full record revisions,
withdrawals and optional `source_revisions: [{path, sha256}]` bindings against
current project files. Unbound memories stay explicitly untrusted. Skills still
enter through the existing revision/context gates; indexed memory cannot grant
skill usage credit.

Research mode retrieves public HTTPS sources itself after report/ledger checks.
Each source gets a timestamp, HTTP result, final URL, byte count and SHA-256 content
digest; source bodies are not archived. Private/mixed DNS, credentials, non-443
ports, HTTP downgrades, unsupported content types, more than three redirects and
bodies over one MiB are blocked. DNS uses a time-bounded isolated process; TLS
connects to a resolved public IP while validating the original hostname. Total
source access has a 60-second budget within the task deadline. No auth/cookie or
user proxy configuration is used. An unavailable source blocks completion and may
be replaced during a repair round. Receipts establish local access, not truth,
authority or externally signed evidence. Independent claim/source review remains
required and separately labeled `model_review_assertion`.

## Paired behavior measurements and panel

```console
erol benchmark --suite examples/behavior-suite.json --harness codex --report /absolute/behavior-report.json --repeat 1
erol panel --port 8765 --open
```

Behavioral suites use explicit synthetic fixture files, seed memory and acceptance
commands. Each pair uses byte-identical committed seed files and the same grader,
harness/default model, permission policy, retries and independent review. Separate
external homes prevent arm contamination. The control omits EROL context and
receives no skill-use credit. Both arms retain runner checks and review: this is a
context ablation, not a vanilla CLI comparison.
Native user/plugin instructions remain active in both arms; only the context
injected by the runner varies. Reports contain completion,
regressed checks, attempts, duration and native-reported usage/cost; unavailable
costs are null. One pair cannot establish a general improvement. Up to ten cases
and three repeats are allowed; results persist after every arm. Fixture homes and
worktrees remain outside the repository for inspection.

Before a benchmark, extract each case's `checks` object to a manifest JSON file,
inspect both commands and fixture source/dependencies, and explicitly approve it
with `checks trust` under the invoking project/home. Unapproved cases stop before
fixture creation or native calls. The approved policy is propagated to the
externally generated fixture roots; suite files cannot grant this authority.

The read-only Turkish panel binds 127.0.0.1, polls selected evidence metadata,
filters status/IDs and expands check/review receipts. It excludes task prompts,
context packets, raw streams and credentials. It has no mutation API, external
assets or CORS. Every server generates a random 256-bit bearer token; `/api/state`
authenticates before opening evidence storage. Use the ephemeral fragment link
printed by `panel` or `--open`. JavaScript removes the fragment from browser
history and keeps the token in memory, not local/session storage. Refreshing
requires reopening the original link. Static assets contain no token/evidence.
Host and supplied Origin must match loopback; responses disable caching and
referrers and use a restrictive CSP. Server logs omit requests, and tokens rotate
on restart. Keep the bootstrap link private. This prevents unauthenticated local
HTTP reads; it does not isolate browser/process memory from the same OS account.

Windows deterministic and live Codex results are documented separately in
[validation](validation.md). Claude live trials are skipped at the user's request
after the earlier expired-OAuth result; fake-process contract tests still cover
Claude. New Linux/macOS runtime behavior remains untested locally.
