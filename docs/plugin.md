# Native EROL plugin

EROL's native plugin includes one entry skill, its launcher, the Python core and the
canonical skill catalogue. Install the plugin once and invoke **@EROL** in Codex
desktop or **/erol** in Claude Code. Node.js 18+ and Python 3.11+ are required on the
execution host; no separate `pip install` or global `erol` executable is needed.

Install the tested GitHub release channel:

```console
codex plugin marketplace add erolemir/EROL --ref stable
codex plugin add erol@erol
```

```console
claude plugin marketplace add https://github.com/erolemir/EROL.git#stable
claude plugin install erol@erol
```

These commands register the Git marketplace and install its bundled plugin.
For local development use `codex plugin marketplace add .` or
`claude plugin marketplace add ./` from your checkout instead.
See [releases and updates](releases.md) and [the acceptance record](installation-check.md).
Start a new session after installation.
Official sources document [Codex plugin packaging](https://developers.openai.com/plugins/build/plugins)
and [Claude marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).

| Surface | Entry point | Qualification |
| --- | --- | --- |
| Codex desktop | Type `@`, then choose **EROL** | Desired displayed plugin entry; live picker and model execution remain untested |
| Codex CLI/IDE | `$erol` or the skill selector | Uses the skill entry rather than desktop mention syntax |
| Claude Code | `/erol` | Current documentation supports a plugin's bare skill name if no command collides |
| Claude collision/older client fallback | `/erol:erol` | Unambiguous native plugin namespace |
| Standalone Claude project bridge | `/erol` | Project skill outside the native plugin namespace |

The [Claude command-name rules](https://code.claude.com/docs/en/skills#how-a-skill-gets-its-command-name)
document the bare alias. Local Claude Code **2.1.92** passed manifest validation;
the alias has not been exercised in that older installed build. Local Codex
**0.159.0-alpha.12.1** exposes `plugin add` and `plugin marketplace add` in CLI help,
but provides no `plugin validate` subcommand. Neither check proves model invocation.

The entry skill resolves `../../scripts/erol.mjs` relative to its loaded
`skills/erol/SKILL.md`, then passes the actual working repository as `--project`.
The launcher forwards arguments to its sibling `runtime/erol` package, preserving
the caller's working directory and stream input/output. It isolates Python imports
from the caller's project and ambient module paths. Both harnesses use the same
external EROL home, normally `~/.erol`; plugin updates or removal do not own that memory.

On Windows, a host sandbox can allow Python while rejecting Node's child-process
creation with `EPERM`. The entry skill then resolves sibling `scripts/erol.py` and
invokes it directly with Python's `-I -S -X utf8` options, retaining all project,
home and CLI arguments. This uses the same bundled core and current host permissions.
It does not retry denied Node launches indefinitely or request broader sandbox access.

EROL returns focused context and advisory roles. The assistant performs implementation,
tests and review using its normal tools. A distinct `plan --task-id` receipt binds
real-use evidence to the selected revision. Incident learning, eval and project skill
activation require explicit evidence. The plugin installs no automatic lifecycle hooks,
permission overrides, MCP server or model configuration.

The package has `plugins/erol/plugin.json` for portable OpenAI packaging,
`plugins/erol/.claude-plugin/plugin.json` for Claude, and native marketplaces in
`.agents/plugins/marketplace.json` and `.claude-plugin/marketplace.json`. Both
marketplaces are named `erol`, making the installation identifier `erol@erol`.

`src/erol`, its data files and `bin/erol.mjs` remain canonical. Regenerate the bundled
copies and bridge snapshots with:

```console
python scripts/check_adapter_drift.py --write
python scripts/check_adapter_drift.py --check
claude plugin validate ./plugins/erol
claude plugin validate .
```

The read-only drift check compares runtime, launcher, manifests and skill bytes and
flags unexpected files in generated runtime/scripts directories. It ignores Python
bytecode caches. Regeneration does not delete unexpected or obsolete files; review
them before removal. Copied-plugin tests run the bundled core in an unrelated temporary
project, but full desktop selection and native model-driven use remain acceptance work.
