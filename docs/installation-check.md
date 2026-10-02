# Installation acceptance — 2026-10-02

## GitHub distribution acceptance

The first public release, [0.1.2](https://github.com/erolemir/EROL/releases/tag/v0.1.2),
was generated automatically after all six OS/Python jobs passed. Both clients
were migrated from the local marketplace to the GitHub `stable` ref, installed
and enabled `erol@erol` 0.1.2, and exposed AGPL-3.0-only manifests.
The installed Codex bundled launcher returned version 0.1.2 and the existing
project's external memory counts. No database was copied into the plugin.

A Windows Task Scheduler run actually refreshed both native clients successfully
with exit code 0. Updater files live in `~/.erol/updater`: files first placed in
application-private AppData were invisible to the scheduled process. The task
uses the OS shell, ordinary user permissions and saved CLI paths where needed.
See [release and update instructions](releases.md).

These are native installation, runtime and updater checks. The earlier model
trial below used 0.1.1. Desktop picker invocation and an authenticated Claude
model session remain unverified; no new model trial is claimed here.

## Earlier local development acceptance

Installed at the user's request on their Windows computer. At that stage no
public packages or marketplaces had been published.

| Host | Plugin | Status |
| --- | --- | --- |
| Codex 0.159.0-alpha.12.1 | erol@erol 0.1.1 | Installed and enabled; live CLI trial passed |
| Claude Code 2.1.92 | erol@erol 0.1.1 | Installed and enabled; model trial blocked by missing login |

Both hosts retain their existing plugins. Their native installation commands
register the local marketplace and enable EROL in the user's harness configuration.
The project bridge installer is a separate optional setup path.

## Codex trial

A fresh ephemeral Codex CLI session read the installed
`~/.codex/plugins/cache/erol/erol/0.1.1/skills/erol/SKILL.md`, invoked the bundled core
and completed `status` plus `plan` for:

```text
RabbitMQ duplicate consumer at least once delivery
```

The context admitted `message-idempotency` version 1.0.0. The unique task receipt
was independently checked in the actual project database under
`~/.erol/state/erol-3184064b80f55cea/memory.db`; its status is `started`. This verifies
planning and persistence, without inventing a completed repair, project skill use,
incident or promotion evidence. No source edits or delegated agents occurred.

The initial 0.1.0 Node entry failed inside Codex's Windows sandbox because spawning
Python returned EPERM, although direct Python 3.14.2 ran. Version 0.1.1 adds an
isolated direct Python entry. The updated entry skill used that fallback successfully
under the same workspace-write sandbox with the EROL memory home as an explicitly
writable directory. No sandbox bypass or permission-policy change was used.

Desktop `@EROL` picker selection remains a separate manual acceptance step. Start a
new chat and select EROL from the `@` menu; restart the app if it does not refresh.

## Claude trial

The native plugin is installed and enabled. Its copied runtime executes the same
plan locally. The `/erol` model invocation returned `Not logged in · Please run
/login`, without an API call or charge. Complete `/login` in Claude Code before
trying `/erol`; use `/erol:erol` if the older client does not resolve the short name.

## Release checks

112 Python tests ran: 110 passed and two platform-dependent checks skipped. All ten
Node tests passed. Ruff lint/formatting and mypy for 19 canonical source files pass.
Generated bundle drift checks pass. The local npm archive executes both Node and
direct Python entries, at the package root and inside the plugin, against all 32
routing fixtures. Wheel installation and learning checks run in an isolated home.

Detailed logs remain ignored under `.validation/`; they are not distributed in the
packages. The checked behavior does not establish a live Claude session, desktop
picker behavior, real defect resolution, promotion or cross-platform compatibility.
