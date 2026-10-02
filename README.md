# EROL

**Extensible Reasoning & Orchestration Layer**

One entry point for project memory, specialist workflows and evidence-based learning.

EROL helps a coding assistant remember verified fixes, select relevant skills and
develop expertise specific to your project. Codex and Claude Code share the same
local memory. Only a small selection of relevant workflows enters each task's context.

```text
error → incident memory → repetition → pattern → skill candidate
      → eval → project skill → verified use → promotion candidate
```

Project learning is enabled by default. Global promotion requires reviewed evidence
and explicit approval. EROL never fills a global registry with automatically generated skills.

**Status:** early development. Source and native plugins are available from
[GitHub](https://github.com/erolemir/EROL). Tested releases are distributed through
the `stable` branch and [release assets](https://github.com/erolemir/EROL/releases).
The project is not published to npm or PyPI.

## Quick start

Node.js 18+ and Python 3.11+ are required
for the plugin and Node CLI. The Python core has no third-party runtime dependencies.

### Codex plugin

Register the tested release channel, then install:

```console
codex plugin marketplace add erolemir/EROL --ref stable
codex plugin add erol@erol
```

Start a new Codex desktop chat, type `@`, and select **EROL** from the plugin menu:

```text
@EROL Investigate duplicate message processing and use this project's previous fixes.
```

`@EROL` describes the desktop plugin entry point. The plugin's display name is EROL;
the installed desktop selection still needs a live acceptance test. Codex CLI and
IDE skill invocation uses `$erol` or `/skills` instead of the desktop mention syntax.

### Claude Code plugin

Register the tested release channel, then install:

```console
claude plugin marketplace add https://github.com/erolemir/EROL.git#stable
claude plugin install erol@erol
```

Start a new Claude Code session in your project:

```text
/erol Investigate duplicate message processing and use this project's previous fixes.
```

Current Claude Code supports a plugin skill's short name when no command conflicts.
If `/erol` is unavailable or resolves to another skill, use the full name
`/erol:erol`. A standalone project installation uses `/erol` directly.
See the [official command-name rules](https://code.claude.com/docs/en/skills#how-a-skill-gets-its-command-name).

Native plugin installation includes the EROL core and launcher. It does not require
a separate `pip install`. It does require Node and Python on the host running the assistant.
If the host blocks Node's child-process creation, the entry skill uses its bundled
direct Python launcher with the same permissions and isolated imports.
See [installation](docs/installation.md) for prerequisites, project setup and removal.

### Updates

Approved `main` changes pass the complete CI matrix before the release workflow
automatically versions and publishes the `stable` channel. It never pushes code
back to `main`. Outside contributions require the repository owner's approval.

Claude's marketplace auto-update can be enabled in `/plugin` → Marketplaces → erol.
For Windows, enable scheduled native refreshes from a checkout on each computer:

```powershell
./scripts/update-plugins.ps1 -Harness Both -Register
```

Updates run at login and every six hours while signed in. Start a new/reloaded
session to use an updated plugin. Fixed version refs and local-path marketplaces
stay pinned/local. See [releases and updates](docs/releases.md) for manual refresh,
removal and platform limits.

### Local CLI and project setup

From the EROL checkout, install the local command link and run it without downloading
an unrelated registry package:

```console
npm install --ignore-scripts --no-audit --no-fund
npx --no-install erol --version
npx --no-install erol --project /path/to/project status
npx --no-install erol --project /path/to/project setup --harness codex
npx --no-install erol --project /path/to/project setup --harness codex --apply
npx --no-install erol --project /path/to/project setup --harness claude --apply
npx --no-install erol eval
```

Project setup previews changes by default; `--apply` writes one bridge skill and
one owned instruction block. It backs up managed changes, preserves existing
instructions, refuses ownership conflicts and retains memory on uninstall.
Node-based setup records the launcher's absolute path so later sessions can invoke
it; keep this checkout at that location or rerun setup after moving it.

The CLI passes arguments to the bundled Python core. It has no npm runtime
dependencies or installation hooks. Set `EROL_PYTHON` to a Python executable path
if your system's default Python is older than 3.11.

Python-only use is also available:

```console
python -m pip install -e .
erol --project /path/to/project status
```

Use a virtual environment if preferred. Pass `--project` and optional `--home`
before the subcommand. Subsequent examples use `erol`; the same commands work
with the local `npx --no-install erol` prefix from this checkout.

## What happens during a task

1. EROL retrieves relevant project evidence and identifies useful workflows.
2. It returns a bounded context packet and an advisory plan for implementation,
   testing and independent review.
3. The host assistant performs the work and supplies verified outcomes.
4. Recurring incidents become candidates; evaluated candidates become project skills.
5. Successful use of the same evaluated revision qualifies it for promotion review.

EROL supplies plans and durable evidence. The host assistant runs agents, edits,
tests and reviews. A local installed Codex CLI trial passed skill loading, planning
and receipt persistence. Desktop selection, live Claude use and complete real
repair execution remain pending; see [installation acceptance](docs/installation-check.md).

## Learning from recurring errors

For example, an import can skip rows when its pagination cursor uses a nonunique
version number. After a tested repair and independent review, record sanitized
evidence following [the incident format](examples/incident.json):

```console
erol incident record --input examples/incident.json
erol incident match --component contact-import --exception ImportCursorError --error "ImportCursorError skipped rows request=next at 18:35"
erol learning candidates
```

By default, three distinct verified tasks with a consistent error family, cause
and solution create a project candidate. Replaying an incident does not increase
its evidence count. Low confidence, conflicting remedies and duplicate workflows
do not qualify a new active skill.

```console
erol learning eval --id <CANDIDATE_ID> --input <REVIEWED_BEHAVIOR_EVAL_JSON>
erol learning activate --id <CANDIDATE_ID>
erol plan --task-id <UNIQUE_TASK_ID> --task <CURRENT_TASK>
erol skill usage --task-id <UNIQUE_TASK_ID> --input <REVIEWED_COMPLETION_JSON>
erol skill metrics --name <SKILL_NAME>
erol learning promotion --name <SKILL_NAME>
```

Activation requires positive and negative trigger fixtures, reviewed behavior
evidence, workflow checks and security and context-budget gates. Usage credit
requires that the exact evaluated revision was actually admitted to a new task's
context. Failed use or a false activation removes that revision from routing until
it is repaired and evaluated again.

Example JSON files are synthetic formats, not evidence of real project repairs.
EROL checks supplied reports but cannot authenticate the reviewer or certify that
reported tests ran. Global approval records permission for generalization;
producing, evaluating and installing a global revision remains future work.

## Memory and context

Memory lives outside your repository at
`~/.erol/state/<normalized-project-name>-<hash>/memory.db`. Project identity uses a
credential-free Git remote, with canonical root path as the fallback. Codex and
Claude share memory when they use the same project identity and EROL home.

SQLite is canonical; Markdown exports provide readable views of decisions,
learnings, incidents, patterns, tasks and handoffs. No transcript upload or
telemetry is implemented. POSIX state directories request private permissions;
Windows state inherits the user's directory permissions.

The built-in pack contains 24 original foundation skills and 14 advisory roles.
Discovery reads metadata; selected skill bodies load on demand. Negative triggers
override positive matches. Oversized context items are reported as omitted.
Token budgets use character estimates, not measured model token counts.

## Development and validation

```console
python -m pip install -e . -r requirements-dev.txt
python -m unittest discover -s tests -v
ruff check src tests scripts bin
ruff format --check src tests scripts bin
mypy --explicit-package-bases src/erol bin/erol.py
npm test
python scripts/check_adapter_drift.py --check
python scripts/validate.py
python -m build
python scripts/package_smoke.py
npm pack --pack-destination dist
python scripts/npm_package_smoke.py
```

See [validation results](docs/validation.md) for the tested environment and
limitations. CI declares Windows, macOS and Linux with Python 3.11 and 3.14;
local results do not establish that the remote CI matrix has passed.

Read more: [architecture](docs/architecture.md), [learning lifecycle](docs/learning.md),
[plugin usage](docs/plugin.md), [capabilities](docs/capabilities.md),
[eval contracts](docs/eval-plan.md) and [routing](docs/routing.md).

## Current limits

- Routing and memory retrieval are lexical; semantic retrieval and indexed search are pending.
- Role plans and model tiers are advisory; EROL has no model provider or worker scheduler.
- Learning relies on explicit sanitized evidence; automatic native event ingestion is pending.
- Security heuristics do not provide complete secret detection or an execution sandbox.
- Live harness trials, cross-project behavior trials and global skill installation are pending.
- Local benchmarks measure routing and rendered context, without claiming better task
  success, real token savings or faster repairs.

AGPL-3.0-only licensed. You may use, modify and redistribute EROL under the
[license](LICENSE), preserving required notices and sharing source as required.
See [contributing](CONTRIBUTING.md) and [security](SECURITY.md).
