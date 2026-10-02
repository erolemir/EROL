# Harness capabilities

Checked against official documentation on **2026-10-02**. Documentation-supported
features and EROL's implementation are separate facts. A local installed Codex CLI
trial verified skill loading, status, planning and a persisted task receipt.
Codex desktop selection remains unverified. Live Codex execution has a narrow
repair/resume trial; Claude's live execution was blocked by expired OAuth despite
its local login probe. Local file generation, ownership, rollback, and shared-home
integration are covered by automated tests. See [installation acceptance](installation-check.md).

| Capability | Codex documented native surface | Claude Code documented native surface | EROL implementation |
| --- | --- | --- | --- |
| Project instructions | Root/nested `AGENTS.md`, override discovery and context limit [source](https://developers.openai.com/codex/guides/agents-md) | `CLAUDE.md`; newer releases also support `AGENTS.md` [source](https://code.claude.com/docs/en/memory) | Appends a small owned block to `AGENTS.md` or `CLAUDE.md`; preserves existing bytes |
| Lazy skills | Repo `.agents/skills/<name>/SKILL.md`; metadata precedes full body [source](https://developers.openai.com/codex/skills) | Repo `.claude/skills/<name>/SKILL.md`; manual and model-selected invocation [source](https://code.claude.com/docs/en/skills) | One bridge skill per harness; CLI routes canonical skills with a context budget |
| Native plugins | Local marketplace and portable plugin manifest [source](https://developers.openai.com/plugins/build/plugins) | Local marketplace and `.claude-plugin/plugin.json` [source](https://code.claude.com/docs/en/plugin-marketplaces) | Generated manifests, bundled core, Node and direct Python entries; installed Codex CLI trial passed |
| Subagents | Custom `.codex/agents/*.toml`; native delegation subject to client availability [source](https://developers.openai.com/codex/subagents) | Custom `.claude/agents/*.md` with frontmatter [source](https://code.claude.com/docs/en/sub-agents) | Plan role specifications only; harness executes delegation; no agent definitions installed |
| Lifecycle hooks | `hooks.json` or inline TOML hooks; non-managed hooks require trust [source](https://developers.openai.com/codex/hooks) | Lifecycle hooks configured through settings [source](https://code.claude.com/docs/en/hooks) | No hooks installed; no automatic transcript ingestion or command execution |
| Configuration | `.codex/config.toml` [source](https://developers.openai.com/codex/config-reference) | `.claude/settings.json`, local and user layers [source](https://code.claude.com/docs/en/settings) | Project bridge setup leaves configs untouched; native plugin commands register/enable the plugin through the harness. Permission policies stay unchanged |
| Durable learning | Harness-specific memory behavior is not EROL's shared storage | Native auto memory is independent of EROL [source](https://code.claude.com/docs/en/memory) | Both bridges call the same canonical external home and project identity |

The inspected OpenAI URLs currently redirect to `learn.chatgpt.com`; source links
above retain the official documented entry points. Codex's repository skill location
is `.agents/skills`, rather than assuming older `.codex/skills` layouts.

Start a new harness session after installation and verify that the bridge is listed.
In Claude Code, `/erol` can explicitly invoke the bridge; for a plugin skill,
`/erol:erol` is the full name and `/erol` is available when its short name does not
conflict. See the [current command-name rules](https://code.claude.com/docs/en/skills#how-a-skill-gets-its-command-name).
The intended Codex desktop plugin selector displays EROL through `@`; a live
installed test remains pending. Codex CLI/IDE skills use `$erol` or `/skills`
per the [official skills guide](https://learn.chatgpt.com/docs/build-skills).
Normal substantive tasks with project setup are directed to the
bridge by the root instruction block; model compliance is not a deterministic hook.
If project skills or instruction discovery are disabled, the bridge cannot force
them on. Codex `AGENTS.override.md` can supersede the installed root `AGENTS.md`.
Claude's newer `AGENTS.md` support may make both instruction files visible; they
point to the same home and should lead to one plan per task.

The default bridge returns plans, memories and skill references; plans launch no
models or tests. The separate opt-in `run` command launches native CLI sessions,
executes supplied check argv, and records independent review with revision-bound
outcomes. It does not execute stored skill snippets or certify reviewer correctness.
See [execution](execution.md) for restrictions, capability probes and live evidence.

Research mode explicitly uses Codex live `--search`, checked in installed help,
or Claude `WebSearch`/`WebFetch` with existing tool/permission restrictions.
The report/source contract and separate source review target technical, product
and competitor decisions. Structural validity and native model source-review
assertions are different evidence layers; see [research](research-execution.md).
Execution/resume use documented [Codex CLI](https://learn.chatgpt.com/docs/non-interactive-mode)
and [Claude CLI](https://code.claude.com/docs/en/headless) surfaces; tool restrictions
use [Claude permissions](https://code.claude.com/docs/en/permissions).
Remote/cloud clients need their own installed CLI and accessible home;
local cross-harness storage does not imply cloud synchronization.

The canonical core now also supports bounded work discovery and explicit
project-policy queue execution, verified dependency delta composition, two/three
parallel read-only specialist reviewers, indexed bilingual BM25 retrieval with
freshness checks, paired native context-ablation suites, public HTTPS access
receipts and a loopback-only evidence panel. These do not change native model
defaults or saved user configuration. See [autonomous work](autonomous-work.md).
One implementer writes per project. Native plugin/user instructions remain active
in benchmark arms; only injected EROL context varies. Neural embeddings and
simultaneous writing agents are not implemented. The user waived further Claude
live trials; protocol tests remain active and no live Claude success is claimed.
