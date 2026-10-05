# Local autonomous execution

`plan` and `explain` remain advisory. `run` explicitly opts into native model
execution and the reviewed check commands supplied by the caller. The canonical
Python runtime remains standard-library-only; Codex or Claude must already be
installed and authenticated. EROL does not install a harness or change saved
settings, plugins, hooks, authentication or permissions.

## Commands

Pass `--project` and `--home` before the subcommand. Start from a clean local Git
checkout with a committed HEAD and an external EROL home:

```console
erol --project /path/to/project --home /external/erol checks show --file /path/to/reviewed-checks.json
erol --project /path/to/project --home /external/erol checks trust --file /path/to/reviewed-checks.json
erol --project /path/to/project --home /external/erol run --task "Repair the failing import" --harness codex --checks /path/to/reviewed-checks.json
erol --project /path/to/project --home /external/erol run --task "Repair the failing import" --harness claude --review-harness codex --checks /path/to/reviewed-checks.json --task-id unique-repair-42
erol --project /path/to/project --home /external/erol runs list
erol --project /path/to/project --home /external/erol runs show --id <RUN_ID>
erol --project /path/to/project --home /external/erol runs resume --id <RUN_ID>
erol --project /path/to/project --home /external/erol runs cancel --id <RUN_ID>
```

The default reviewer uses the selected harness in a distinct native session. EROL
does not substitute another harness if authentication or capabilities fail. The
harness uses its configured default model. `run` and `runs resume` exit 0 only
when completed, 1 when incomplete/cancelled, and 2 for rejected input or unavailable
resources. Inspection/cancellation commands use ordinary 0/2 exit statuses.

The [manifest schema](../schemas/checks.schema.json) and
[example](../examples/checks.json) define literal argv arrays, unique check names,
`acceptance`/`static` kinds and timeouts of 1–300 seconds. At least one acceptance
check is mandatory. Select checks that exercise the requested behavior: marking
a no-op command `acceptance` does not make it behavioral evidence. Checks execute
without an assembled shell string, with the caller's permissions. Review the
manifest and invoked code before granting check authorization. Windows `.cmd`, `.bat` and `.ps1` executable
wrappers are rejected; use native executables or Node script entry points.
Ignored local dependencies and environment files are not copied to the worktree.

## Check authorization and command environment

Repository manifests never grant their own execution authority. `checks trust`
stores a schema-versioned receipt outside the project, scoped to the normalized
original root and canonical manifest SHA-256. Another checkout, even with the
same remote/project ID, cannot borrow it. Identical manifest content within the
same root shares authorization; this is content authorization, not path approval.
Changes need another reviewed approval. `checks revoke --file PATH` removes that
content's receipt. Keep the same project and external home across these commands.
Isolated runners, discovery, direct terminal checks and API check tools require
the receipt before execution; saved-run continuation revalidates it before native
preflight and each phase. Revocation prevents subsequent starts; it does not kill
a command already running. Model-owned native tools retain the native CLI policy.

Commands inherit only PATH, PATHEXT, SYSTEMROOT, WINDIR, COMSPEC, temporary-directory,
locale, timezone, terminal/color and Python encoding settings, plus EROL_RUN_ACTIVE.
Credentials, HOME and arbitrary interpreter startup variables are omitted.
Reviewed public variable names can be added with repeated `--env NAME`; actual
values are secret-screened at execution time. Startup injection variables remain
forbidden even when requested. Use absolute trusted executable paths if PATH is
not trustworthy. Native CLI account/login environments are separate from checks.

An optional literal executor prefix is applied to every approved check, including
matching API `run_command` tools. For example, after provisioning a restricted
OS account or sandbox wrapper that accepts an executable and its arguments:

```console
erol checks trust --file /path/to/reviewed-checks.json --prefix '["/absolute/restricted-check-executor","--"]'
```

The wrapper must understand the appended argv, provide its own project/dependency
mounts and enforce isolation. EROL does not assemble a shell or install/validate
this OS containment (`sandbox_verified` is false). Default checks still run with
the caller's permissions. Manifest approval does not attest invoked scripts,
dependencies, executable replacement or later source edits. Inspect these before
approving; use an independently configured sandbox/separate account for hostile
projects. Environment minimization is defense in depth, not filesystem isolation.

## Execution and evidence

OS-held leases permit one unfinished run per project, including callers using
different homes for the same Git checkout. A small Git metadata marker references
the retained external run record; missing/unknown referenced state fails closed.
Use the original home to resume or cancel its run. The runner creates
a detached worktree from HEAD beneath external state and retains the original
project identity and exact admitted skill revisions. Git worktree registration
changes local Git metadata; the main checkout stays intact. No automatic commit,
merge, push or publication is performed. A worktree is not an OS sandbox.

The loop records baseline checks, invokes an implementer, observes checks directly,
and launches a separate reviewer. Codex uses workspace-write for implementation
and read-only for review with approval requests disabled; denied operations stay
denied. Claude uses `dontAsk`, an explicit read/edit tool set for implementation,
read-only tools for review, and an empty strict MCP configuration. EROL runs the
checks; Claude workers have no Bash tool. Native and managed settings can further
restrict these operations. This does not establish OS containment, universal
prompt-injection protection or reviewer correctness.

Completion requires all checks and no unresolved high/critical findings on the
same source digest. Digests cover tracked/staged changes and nonignored new files,
including contents; ignored caches/build outputs are excluded. Changing source
during checks/review invalidates the evidence. Changed HEAD, linked source files,
files larger than 4 MiB and patches above 128,000 bytes require attention.
Successful runs return an applicable `changes.patch`, retained worktree, observed
checks and review.

Check records contain exit codes and bounded, secret-screened diagnostic excerpts.
Native streams are parsed in memory; only session IDs, numeric usage, structured
outcomes and bounded native errors are retained. Raw conversations, reasoning and
tool payloads are not copied into EROL storage or the repo. Native clients retain
their own sessions under their own policies. Secret screening is best effort.
Usage fields are native provider reports, not billing totals. An interrupted
checkpoint may lack a finished invocation's usage measurements.

`runs.db` has a separate schema version and project binding, beside `memory.db`.
Successful completion uses existing revision-bound learning gates and is labelled
`runner_observed`, not cryptographically authenticated. Omitted skills and replayed
task IDs receive no credit; incomplete runs receive no success credit. Incident
drafting, skill activation and promotion remain separate workflows.

## Interruption and limits

At most three implementation attempts are allowed, including two correction turns.
Two matching strategy/failure observations require causal replanning. Defaults are
60 minutes from creation (including downtime), 15 minutes per model invocation
and at most 5 minutes per check. Limits preserve work and return `needs_attention`;
resume does not reset them.

Resume verifies project/root, registered worktree, HEAD, manifest/source digests
and process state. Changed manifests require a new task. Changed source invalidates
checks/review. Native sessions resume by exact ID, never `--last`. An interrupted
launch without an acknowledged session, or an alive/unknown previous child,
prevents a second worker. Finalization is idempotent across execution and learning
databases, so checkpoint interruption cannot double-credit usage.

Cancellation is durable and observed by the active owner. The cancelling CLI never
kills an arbitrary saved PID. Windows children start suspended, join a kill-on-close
Job Object and then resume; POSIX children use owned process groups. Windows owner
exit terminates its job. Abrupt POSIX owner death may leave children alive; resume
refuses duplicate workers. Unknown/reused PID state is handled conservatively.
Completed/cancelled runs cannot resume. Worktrees are retained, not auto-deleted.

## Explicit live acceptance

These development commands invoke real models in external temporary Git fixtures:

```console
python scripts/execution_trial.py --harness codex --report .validation/execution-codex.json
python scripts/execution_trial.py --harness claude --report .validation/execution-claude.json
```

The trial fixes an arithmetic error, injects runner interruption after native worker
completion but before checkpointing, resumes that session and requires passing tests
plus review. This differs from interrupting a native tool mid-execution. Fake-process
tests cover timeouts, malformed events, output limits and descendant cleanup. Trial
directories remain available for inspection. See validation.md for measured results.

`--mode research` enables native web tools and additional report/source gates.
See [research](research-execution.md); it uses the same retained worktree, checks and resume
protocol. It does not require a provider SDK or add runtime dependencies.

Scanning, rule-based automatic starts, parallel workers, semantic retrieval and a
dashboard remain subsequent milestones.
