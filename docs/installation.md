# Installation and removal

The native plugin is the primary setup path. It bundles EROL's runtime; you need
Node.js 18+ and Python 3.11+ on the assistant's execution host. EROL has no third-party
Python or npm runtime dependencies. The canonical memory home defaults to `~/.erol`
and stays outside the project and plugin cache. Both harnesses must use the same
home to share project learning.

Install the GitHub release channel into your chosen harness:

```console
codex plugin marketplace add erolemir/EROL --ref stable
codex plugin add erol@erol
```

```console
claude plugin marketplace add https://github.com/erolemir/EROL.git#stable
claude plugin install erol@erol
```

Start a new session in your working project. Use `@EROL` in Codex desktop's plugin
picker or `/erol` in Claude Code. Use `/erol:erol` if a name collision or older
client prevents the short form. Codex CLI/IDE uses `$erol` or its skill selector.
See [native plugin details and validation limits](plugin.md).
See [releases and updates](releases.md) for automatic refresh, fixed versions and
switching an existing local marketplace to GitHub. Developers can instead add a
local checkout with `codex plugin marketplace add .` or `claude plugin marketplace add ./`.

For development or standalone project setup, link the local Node CLI from this checkout:

```console
npm install --ignore-scripts --no-audit --no-fund
npx --no-install erol --version
npx --no-install erol --project /path/to/project setup --harness codex
npx --no-install erol --project /path/to/project setup --harness codex --apply
npx --no-install erol --project /path/to/project setup --harness claude --apply
```

Use `--no-install` to resolve the checkout's local command without downloading an
unrelated registry package. Set `EROL_PYTHON` to the executable path when needed.
Node setup supplies its own canonical launcher path to the installer. The resulting
skill stores `node` plus that absolute path with literal argument quoting, so later
sessions do not depend on `npx` temporarily adding `erol` to PATH. Keep the installed
checkout/package at that path, or rerun setup from its new location. An unrelated
`EROL_LAUNCHER` environment path is rejected before writes.

The bundled plugin and Node-installed project bridge also document a direct Python
entry when a Windows sandbox denies Node child-process creation. It runs sibling
`erol.py` with `-I -S -X utf8` and the same CLI arguments, without relaxing the host's
permissions. Always keep both launcher files together with the installed core.

Python-only users can install the core in their selected environment:

```console
python -m pip install -e .
erol --project /path/to/project setup --harness codex --apply
```

The Python-only bridge uses the environment's `erol` executable, which must remain
available to the harness. Native plugins use their own bundled launcher. Run the CLI
with `--project` and optional `--home` before the subcommand in every setup path.

Standalone setup defaults to a read-only preview. It installs one bridge at
`.agents/skills/erol/SKILL.md` for Codex or `.claude/skills/erol/SKILL.md` for Claude,
plus a bounded block in root `AGENTS.md` or `CLAUDE.md`. It never installs hooks or
changes harness permissions. The bridge starts task receipts and records reviewed
outcomes only after the assistant actually performs the work.

Preview and apply standalone removal with:

```console
npx --no-install erol --project /path/to/project uninstall --harness codex
npx --no-install erol --project /path/to/project uninstall --harness codex --apply
```

For a native plugin, use the harness's plugin removal command or interface. The
standalone `uninstall` command removes only its project bridge and managed block;
canonical memory remains in the external home in both installation modes.

Standalone ownership, checksums and backups live under
`~/.erol/installations/<path-hash>/`. Reinstall preserves content outside the managed
block; modified owned content, an unowned existing bridge, duplicate markers or a
malformed manifest stop the whole operation. Original affected files are backed up
before changes. Atomic replacements and rollback handle ordinary application errors;
multiple installer processes and power loss are not a multi-file filesystem transaction.

The installer validates targets, rejects symbolic links and Windows reparse points,
and rejects overlapping memory/project paths. New POSIX state directories request
private permissions; Windows relies on inherited user-directory ACLs. Backups can
contain existing instruction content and stay local. No force-overwrite shortcut exists.
Moving a project changes its installation ownership path; an old manifest does not
automatically own the copied bridge in a new checkout.
