# EROL

<p align="center"><img src="src/erol/data/brand/erol.png" alt="EROL green praying mantis logo" width="240"></p>

**Extensible Reasoning & Orchestration Layer**

A shared terminal, economical model routing, project memory, and controlled
task execution for Codex, Claude Code, Antigravity, and API connections.

EROL helps your development assistant reuse previously verified solutions,
choose relevant workflows, and evaluate results through tests and a separate
review. It also supports technical, product, market, and competitor research.
The Python core has no third-party runtime dependencies.

**Distribution:** Tested packages are available through
[GitHub Releases](https://github.com/erolemir/EROL/releases) and the `stable`
branch. `main` is the development source; its version may differ from `stable`.
EROL is not currently published to the npm or PyPI registries. Use the GitHub
installation instructions below instead of `npm install -g erol` or
`pip install erol-ai`.

<a id="içindekiler"></a>

## Contents

- [Which installation should I choose?](#which-installation-should-i-choose)
- [Requirements](#requirements)
- [Codex plugin](#codex-plugin)
- [Claude Code plugin](#claude-code-plugin)
- [Windows: make erol available across your account](#windows-make-erol-available-across-your-account)
- [macOS and Linux: Python CLI](#macos-and-linux-python-cli)
- [Run from source and set up a project](#run-from-source-and-set-up-a-project)
- [EROL terminal](#erol-terminal)
- [Everyday use](#everyday-use)
- [Autonomous development task](#autonomous-development-task)
- [Technical, product, and competitor research](#technical-product-and-competitor-research)
- [Task discovery, queue, and parallel review](#task-discovery-queue-and-parallel-review)
- [Memory and learning](#memory-and-learning)
- [Update and uninstall](#update-and-uninstall)
- [Troubleshooting](#troubleshooting)
- [Validation and development](#validation-and-development)
- [Capabilities and limitations](#capabilities-and-limitations)
- [License and contributions](#license-and-contributions)

<a id="hangi-kurulumu-seçmeliyim"></a>

## Which installation should I choose?

| Need | Installation | Usage |
| --- | --- | --- |
| Use EROL in Codex chats | Codex plugin | Select EROL in Desktop; use `$erol` in CLI/IDE |
| Use it in Claude Code sessions | Claude plugin | `/erol:erol` |
| Run plans, tasks, research, and the panel from a terminal | Python CLI | `erol ...` |
| Develop EROL or install a project-specific bridge | Source checkout | `npx --no-install erol ...` or an editable Python installation |

You can combine these options. The plugin bundles its own runtime, so a separate
Python package installation is not required. **Installing the plugin does not
add a global `erol` command to your terminal.** Follow the CLI section for that.

The plugin and `plan` command provide context and recommendations; the assistant
in your chat performs the work. `run` and `queue work` with an explicit policy
start EROL's task executor.

<a id="gereksinimler"></a>

## Requirements

| Component | Requirement |
| --- | --- |
| Python | 3.11 or later on the machine running the CLI or plugin |
| Node.js | 18 or later for the plugin's Node launcher and the Node CLI |
| Git | For Git marketplace installation and autonomous tasks using worktrees |
| Codex / Claude Code | The CLI for your chosen harness and valid login/access |
| Internet | For the initial download, model calls, and web research |

The Python-only CLI does not require Node. Test tools and project dependencies
used by your check commands must also be available in your project's environment.

Preflight checks in Windows PowerShell:

```powershell
py -3 --version
node --version
git --version
codex --version
claude --version
```

You do not need to run checks for a harness you will not use. On macOS/Linux,
use `python3 --version` to check Python. Official installation instructions:
[Python](https://www.python.org/downloads/), [Node.js](https://nodejs.org/en/download),
[Git](https://git-scm.com/downloads), [Codex](https://developers.openai.com/codex/cli),
[Claude Code](https://code.claude.com/docs/en/setup).

<a id="codex-eklentisi"></a>

## Codex plugin

Register the tested release channel and install the plugin in your terminal:

```console
codex plugin marketplace add erolemir/EROL --ref stable
codex plugin add erol@erol
codex plugin list --marketplace erol --json
```

The list should show `installed: true`, `enabled: true`, and the installed
version. Then open a **new Codex chat** in your project. In Desktop, select EROL
from the `@` menu; restart the app if it does not appear. Example task:

```text
@EROL Inspect this project, consider previous decisions, fix the bug, and test the result.
```

In Codex CLI/IDE, select the skill with `$erol` or `/skills`:

```text
$erol Investigate the API bug, choose the appropriate workflow, and verify the result with tests.
```

Desktop picker behavior depends on the client version. Plugin installation and
enablement are separate from live picker/model acceptance checks.
[Official marketplace documentation](https://developers.openai.com/plugins/build/plugins)
and [EROL plugin details](docs/plugin.md).

<a id="claude-code-eklentisi"></a>

## Claude Code plugin

A user-scoped installation is available across your local projects:

```console
claude plugin marketplace add https://github.com/erolemir/EROL.git#stable
claude plugin install erol@erol --scope user
claude plugin list
```

Check that the list shows `erol@erol`, its version, and `enabled` status. Open a
new Claude Code session in your project and invoke the full skill name:

```text
/erol:erol Evaluate this product for small businesses in Turkey; research the market and competitors, and cite current sources.
```

The shorter `/erol` name may work if the client supports it and it does not
conflict with another skill. For login errors, refresh your login with `/login`
inside Claude Code. Installing the plugin does not create a model account or
subscription. [Official installation documentation](https://code.claude.com/docs/en/plugins/install)
and [skill naming rules](https://code.claude.com/docs/en/skills#how-a-skill-gets-its-command-name).

<a id="windows-bilgisayar-genelinde-erol-komutu"></a>

## Windows: make erol available across your account

This option creates a separate Python environment without changing packages in
other projects. Run the steps in order in PowerShell. `0.1.6` is a reproducible
example version; adjust `$erolVersion` to your chosen version from the
[Releases page](https://github.com/erolemir/EROL/releases).

### 1. Download the package and verify its SHA256 hash

```powershell
$erolVersion = '0.1.6'
$erolDownloadDir = Join-Path $env:USERPROFILE ".erol\downloads\$erolVersion"
$erolWheelName = "erol_ai-$erolVersion-py3-none-any.whl"
$erolReleaseUrl = "https://github.com/erolemir/EROL/releases/download/v$erolVersion"
New-Item -ItemType Directory -Path $erolDownloadDir -Force | Out-Null
Invoke-WebRequest "$erolReleaseUrl/$erolWheelName" -OutFile (Join-Path $erolDownloadDir $erolWheelName)
Invoke-WebRequest "$erolReleaseUrl/SHA256SUMS" -OutFile (Join-Path $erolDownloadDir 'SHA256SUMS')
$erolHashLine = (Select-String -LiteralPath (Join-Path $erolDownloadDir 'SHA256SUMS') -SimpleMatch "  $erolWheelName").Line
if (-not $erolHashLine) { throw 'Wheel entry not found in SHA256SUMS' }
$erolExpectedHash = ($erolHashLine -split '\s+')[0]
$erolActualHash = (Get-FileHash -LiteralPath (Join-Path $erolDownloadDir $erolWheelName) -Algorithm SHA256).Hash.ToLowerInvariant()
if ($erolActualHash -ne $erolExpectedHash) { throw 'EROL package SHA256 hash does not match' }
```

### 2. Install into a separate Python environment

```powershell
$erolCliDir = Join-Path $env:USERPROFILE ".erol\cli\$erolVersion"
py -3 -m venv $erolCliDir
& (Join-Path $erolCliDir 'Scripts\python.exe') -m pip install --no-index --no-deps (Join-Path $erolDownloadDir $erolWheelName)
& (Join-Path $erolCliDir 'Scripts\erol.exe') --version
```

The last command should print your chosen version. You do not need to activate
the environment or change PowerShell execution policy. `py -3` must select
Python 3.11+; if you have multiple versions installed, you can create the
environment with a specific version such as `py -3.12`.

### 3. Use erol from any folder

Copy Python's native launcher into your user command directory:

```powershell
$erolUserBin = Join-Path $env:USERPROFILE '.local\bin'
New-Item -ItemType Directory -Path $erolUserBin -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $erolCliDir 'Scripts\erol.exe') -Destination (Join-Path $erolUserBin 'erol.exe') -Force
$erolUserPath = [string][Environment]::GetEnvironmentVariable('Path', 'User')
if ($erolUserPath.Split(';') -notcontains $erolUserBin) {
    [Environment]::SetEnvironmentVariable('Path', "$erolUserPath;$erolUserBin", 'User')
}
if ($env:Path.Split(';') -notcontains $erolUserBin) { $env:Path += ";$erolUserBin" }
erol --version
```

The copied launcher remains bound to this Python environment. Do not move or
delete `$erolCliDir`. To update, install the new version and copy its launcher
again. You may need to open a new terminal or restart an app for it to see the
PATH change. Installation is scoped to your user account; administrator access
and system PATH changes are not required. If another `erol.exe` already exists,
check its ownership before copying over it.

<a id="macos-ve-linux-python-cli"></a>

## macOS and Linux: Python CLI

Create a separate environment with Python 3.11+. Adapt the `0.1.6` example to
your chosen release:

```sh
python3 -m venv "$HOME/.local/share/erol/venv"
"$HOME/.local/share/erol/venv/bin/python" -m pip install --no-deps \
  https://github.com/erolemir/EROL/releases/download/v0.1.6/erol_ai-0.1.6-py3-none-any.whl
"$HOME/.local/share/erol/venv/bin/erol" --version
```

Compare the package hash with the release's `SHA256SUMS` file, using
`shasum -a 256` on macOS or `sha256sum` on Linux. You can use the full launcher
path from any project, or activate the environment in the current terminal:

```sh
. "$HOME/.local/share/erol/venv/bin/activate"
erol --version
```

Activation applies to that terminal session. Keep EROL separate from the target
project's virtual environment.

<a id="kaynak-koddan-kullanım-ve-proje-kurulumu"></a>

## Run from source and set up a project

Check out the tested channel:

```console
git clone --branch stable https://github.com/erolemir/EROL.git
cd EROL
npm install --ignore-scripts --no-audit --no-fund
npx --no-install erol --version
npx --no-install erol --project /path/to/project status
```

On Windows, use a project path such as `"C:\Projects\MyProject"`.
`npx --no-install` uses the command in your checkout instead of downloading an
unrelated package with the same name from a registry. The Node CLI has no
runtime dependencies or install hooks. If Node selects the wrong Python,
specify its executable path; for example, on Windows:

```powershell
$env:EROL_PYTHON = 'C:\Program Files\Python312\python.exe'
```

For Python development, run `python -m pip install -e .` inside your chosen
virtual environment. An editable installation depends on the checkout; it is
not a wheel installation.

### Optional project-specific bridge

A bridge is not required when you use the native plugin. Preview it first:

```console
erol --project /path/to/project setup --harness codex
erol --project /path/to/project setup --harness codex --apply
erol --project /path/to/project setup --harness claude --apply
```

`--apply` manages `.agents/skills/erol/SKILL.md` and the owned block in `AGENTS.md`
for Codex, or `.claude/skills/erol/SKILL.md` and the owned block in `CLAUDE.md`
for Claude. Existing instructions are preserved, changes are backed up, and
ownership conflicts are rejected. Review the normal diff before using it with
your team. The Node bridge records the launcher's absolute path; rerun setup if
you move the checkout. The Python bridge requires `erol` to be available in the
harness environment. [Installation and ownership details](docs/installation.md).

<a id="erol-terminali"></a>

## EROL terminal

In version 0.2.0 of this checkout, typing `erol` in a project folder starts the
EROL terminal. Startup shows the green brand logo, project path, connection
status, and task budget. `erol chat` opens the same interface. Enter sends the
message, Ctrl+J adds a line, Tab completes commands, and arrow keys navigate
session history. Ctrl+C cancels the task and preserves its changes. Small
screens, `NO_COLOR`, or unsupported terminals use plain input. Multiline paste
is supported in terminals that emit bracketed-paste markers.

Connections, models, settings, status, usage, and test results appear as short,
human-readable summaries in the interactive screen; the headless JSON contract
is preserved. `/help` groups commands by conversation, connections, validation,
and display. Tab suggestions appear while you type. Ctrl+W removes the previous
word and Ctrl+K clears to the end of the line; up/down move between lines in
multiline input. `/clear` clears only the visible conversation. `/view compact`
hides the logo panel to widen the response area, and `/view full` restores it.
`/motion off` stops the animation; `/motion on` restores it. These display
preferences apply to the current session.

On supported terminals, EROL opens a clean alternate screen, keeping previous
shell output out of the background. Responses appear on the left, with a gently
animated brand logo on the right. Input and status stay at the bottom. `/logo`
expands or contracts the right panel. The mouse wheel or PgUp/PgDn scrolls
response history; your scroll position is preserved while a task runs.
Backspace/Delete remove text, and Ctrl+U clears the input. In terminals using
mouse reporting, Shift+click can be used for text selection. The logo panel
appears at a minimum of 72 columns / 18 rows; smaller screens preserve the text
and input area. Exiting restores the previous terminal screen. `NO_COLOR` uses
a plain, static display.

The initial interface language follows your computer's settings: Turkish for a
Turkish Windows UI, English for other languages. POSIX uses locale environment
variables. Change it with `/language tr`, `/language en`, or `/language auto`.
The preference is saved in external settings even without a selected project.
Command names and JSON fields stay unchanged; provider errors and model
responses appear in their original languages.

If started from your user folder, such as `C:\Users\YourName`, EROL opens
projectless general conversation when the EROL home is contained in that
folder. Connection, model, language, and settings commands do not require a
project. Type a question for general conversation, use `/research QUESTION or
URL` for research, or `/general` to disable web tools and return to general
conversation. Select a project for file operations with
`/project "C:\Projects\MyProject"`. Starting from a normal project folder keeps
project mode; `erol chat --mode general` opens projectless mode from any folder.
Changing scope creates a separate session while preserving the selected model
and external connection, language, and budget settings.

Projectless mode does not create project memory, snapshots, check commands, or
file tools. Native CLIs run in fresh temporary working directories. Codex's
shell tool is disabled; Claude has no tools in general conversation and uses
WebSearch/WebFetch for research. Native configuration/plugin policies still
apply; this is not universal OS isolation. `agy` is ineligible for the read-only
role and is not selected in projectless mode; its connection remains available
for project implementation tasks.

API research can read public HTTPS HTML/text URLs, but does not provide a search
index. You may need to supply a relevant URL. Private/local addresses and URLs
containing credentials are rejected. Access is limited to eight sources and
60 seconds in total, with 1 MiB per response. Source text is untrusted reference
data; records retain only access metadata. Projectless sessions live under the
external `global/chat` directory without a project identity; model answers are
not archived. A conversation's `completed` status means a response was delivered,
not that tests passed or its factual accuracy was verified.

```text
erol
/help
/language auto
/connect codex
/connect claude
/connect antigravity
/connect openai work OPENAI_API_KEY
/connect anthropic review ANTHROPIC_API_KEY
/connect gemini google GEMINI_API_KEY
/providers
/models refresh
/settings api_budget_usd 5
/model auto
/plan Prepare an implementation plan appropriate for this task
```

Ordinary prompts automatically select relevant skills, admit their bodies into
model context, and show the selected names in the terminal; you do not need to
type `/plan` separately. Project mode considers built-in skills, active learned
project skills, and relevant memory together. Projectless mode uses only built-in
EROL skills and does not load project memory. Simple unrelated questions load no
skills. Skills omitted because of the context budget do not count as used. A
skill is guidance/reference data; it does not itself launch a command or agent,
or expand the current role's tool permissions.

CLI connections use their native login. The `antigravity` connection targets
the official `agy` headless CLI, not the Antigravity IDE launcher. Put API keys
in environment variables; settings store only their variable names. CLI and API
connections from the same provider can coexist under separate identities.
`/connect` saves a connection and displays a short summary; check login/access
with `/providers`. A listed profile is not proof of account access. If Codex is
missing from PATH on Windows, EROL checks the native CLI in the desktop app's
known `%LOCALAPPDATA%/OpenAI/Codex/bin` directory. If Claude requires login, run
`claude auth login` in a normal terminal, then check `/providers` again in EROL.
Example custom endpoint:
`/connect compatible local LOCAL_API_KEY http://localhost:8000/v1`.
Add a profile with
`/models add local {"id":"model-id","level":2,"input_price":1,"output_price":5}`.
Prices are USD per million tokens; both prices can be `0` for a free local model.

| Command | Purpose |
| --- | --- |
| `/help` | Commands and examples |
| `/project` | Show the project; select/change it with `/project PATH` |
| `/general`, `/research` | Projectless conversation or source research, with an optional message |
| `/providers` | Check login/capabilities; `enable ID`, `disable ID` |
| `/models`, `/model` | Profiles, refresh access, `auto`, or `CONNECTION:MODEL` |
| `/settings` | Budget, policy, allowed commands, test manifest, and time limits |
| `/plan` | An EROL plan without starting execution |
| `/diff`, `/tests` | Task-relative file changes and observed test output |
| `/usage`, `/status` | Tokens, estimated cost, and session status |
| `/new`, `/resume`, `/exit` | New session, load/continue a saved session, and exit |
| `/logo` | Expand/contract the right logo panel; static logo in plain mode |
| `/language` | Persistent interface language: `auto`, `en`, `tr` |
| `/clear`, `/view`, `/motion` | Clear visible conversation, compact/full view, animation on/off |

Model routing considers task risk/scope and the EROL plan. Unknown work starts
at a medium level; small explicit fixes prefer economical profiles, while
substantial or risky tasks require stronger profiles. Exact simple greetings
such as `selam`, `merhaba`, and `hello` also use an economical tier and low
reasoning effort. If account access, context, or budget makes a lower tier
ineligible, the selection reason explains that. Large tasks start with read-only
planning, followed by one implementer and up to two concurrent read-only
reviewers. Test/review findings are sent back for repair within three
implementation attempts; automatic routing may escalate to a stronger model
when required. A manually selected model is never silently replaced. The
selection reason and active role/model appear on screen.

Initial capability levels and latency ranks are engineering priors, not measured
success rates. Actual account model access is checked separately. Catalog
sources and limitations are in the [terminal contract](docs/terminal.md).
Windows terminal and local package checks were performed. During the initial
local project trial, Codex's sandbox blocked project access, Claude was not
logged in, and `agy` was not installed. Live API execution and macOS/Linux
interactive terminal operation were not verified for this version. Actual
measurements are in the
[implementation report](docs/implementation-plan.md#erol-terminal-milestone-020-local-unpublished).

The projectless update also passed a live Codex general-conversation call. This
does not verify project file access, live web research, or other provider
accounts. [Update results](docs/implementation-plan.md#projectless-conversation-and-terminal-usability-2026-10-05).

Edits are made directly in the current folder; pre-existing changes are
distinguished from the file state at task start. Non-Git folders are supported.
There is no automatic stash, reset, or commit. A single-writer lock applies to
each project. CLI tool permissions depend on the harness's supported sandbox.
API tools provide project reads/searches, hash-guarded writes/deletes, and
explicitly allowed argv commands. Review roles have only read/search access.

Build caches such as `.next`, `.dart_tool`, and `.gradle` are excluded from
comparison. Binary files larger than 2 MiB are tracked with SHA256 without being
loaded into memory; oversized source text produces an error naming the file.
The aggregate scan limit is 64 MiB. If a folder contains several apps, narrow
the context by selecting the relevant app's folder with `/project PATH`.

To run meaningful tests automatically, use the existing
[check manifest](docs/execution.md) format:

```text
/settings checks_path C:/checks/my-project.json
/settings allowed_commands [["python","-m","unittest","discover","-s","tests"]]
```

Manifest commands are also available to implementer API tools. EROL records
observed command output. It does not report `completed` / verified success until
acceptance tests and independent review both pass. Missing verification yields
`implemented_unverified`; findings/errors yield `needs_attention`; cancellation
yields `cancelled`.

The default USD 5 budget covers all API roles, tool rounds, and retries.
Subscription CLI conversations show input/output token usage. API USD accounting
is shown only when an API call or retained API accounting exists. If a provider
does not report tokens or quota, the value remains unknown. Estimated input/output
cost is reserved before each call; when usage is not reported, that reservation
counts as spent. Insufficient budget saves `waiting_budget`. Increase it with
`/settings api_budget_usd 10`, then use `/resume SESSION_ID continue` to resume
with cumulative accounting and a bounded task summary. `/diff` also shows
continuation-step changes. This guard is not a guaranteed invoice ceiling; CLI
subscription quota is reported separately from API USD accounting.

Settings live in `connections.json` under the external EROL home and do not
change existing learning settings. Session records are external and scoped to
the project identity. Headless example:
`erol chat --prompt "TASK" --model codex:gpt-6.1-sol`.
Projectless example:
`erol chat --mode general --prompt "Evaluate this idea"`.
Research example:
`erol chat --mode research --prompt "Examine https://example.org"`.
`erol terminal --command "/help"` returns JSON. Without a TTY, a call without a
subcommand shows help and does not automatically start a conversation/model call.

<a id="günlük-kullanım"></a>

## Everyday use

Display the reference praying mantis as green and black terminal output:

```console
erol logo
erol logo --width 100
```

From a source checkout, use `npx --no-install erol logo`. The figure uses
half-block characters derived from the reference image; no runtime image
library is required. For the best appearance, use a monospace font and a terminal
supporting 24-bit ANSI color. Default width adapts to the terminal, up to
80 columns; `--width` selects 8–160 columns. Font cell proportions affect its
appearance. `--color never` disables color; `--color always` includes color even
when output is redirected. Automatic color is disabled for non-terminal output,
`NO_COLOR`, or `TERM=dumb`. This command does not create project memory.

Open a terminal in your own project's folder. Windows example:

```powershell
Set-Location 'C:\Projects\MyProject'
erol --version
erol status
erol doctor
erol plan --task 'Fix the API bug, add regression tests, and prepare a code review'
erol explain --task 'Prepare market research and competitor analysis for small businesses'
erol skills list --category backend
erol skills list --category growth
erol skill show --name market-research
erol memory search 'database timeout' --mode hybrid
erol runs list
erol panel --open
```

`status` shows the project identity, version, and memory. `doctor` checks the
package/environment; it does not prove model login or task success. `plan`
provides recommendations; `explain` gives selection reasons. `panel` displays
local task, queue, and evidence records. Each launch generates a fresh access
token; Ctrl+C in the terminal stops the server. Open it with `--open` or the
token-bearing link printed in the terminal. `/api/state` rejects requests without
a token. The token is kept in browser memory and removed from the URL; reuse the
original link after refreshing the page. Do not share that link.

Use `--project` from another folder, or `--home` to choose different external
memory storage. **These options must precede the subcommand:**

```powershell
erol --project 'C:\Projects\MyProject' status
erol --project 'C:\Projects\MyProject' --home 'D:\EROL-Memory' runs list
```

Replace `RUN_ID`, `JOB_ID`, and similar placeholders with actual IDs from the
results. Quote paths containing spaces or Turkish characters.

<a id="otonom-geliştirme-görevi"></a>

## Autonomous development task

### 1. Prepare the project and acceptance checks

A local Git repository, a HEAD commit, and a clean working tree are required.
Check `git status` first. Test tools and project dependencies must be installed
in the environment used by the check executable. Create `checks.json` in the
project. Example for a **project using Python unittest**:

```json
{
  "schema_version": 1,
  "checks": [
    {
      "name": "acceptance-tests",
      "kind": "acceptance",
      "argv": ["python", "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
      "timeout_seconds": 300
    }
  ]
}
```

Adapt this to your test framework. `unittest discover` can exit successfully even
when it finds no tests; first verify manually that relevant tests exist and
catch the target bug. Each check needs `name`, `kind`, literal `argv`, and
`timeout_seconds` between 1 and 300. At least one `acceptance` check is required;
`static` lint/type checks alone cannot complete a task.

Commands run inside the worktree without shell interpretation. Do not use `&&`,
pipes, or a single string containing the whole command. If `python` selects the
wrong environment, set `argv[0]` to the installed Python's absolute path. On
Windows, use a native executable rather than a `.cmd/.bat/.ps1` wrapper; for
example, a Node test uses `["node", "--test", "tests/add.test.mjs"]`. If you add
the manifest to the project, review and commit it; an untracked file makes the
working tree dirty. [Schema](schemas/checks.schema.json) and
[example](examples/checks.json).

A manifest being present in the repository does not authorize its execution.
Review its `argv`, invoked scripts/tests, and dependencies, then explicitly
approve it:

```powershell
erol checks show --file '.\checks.json'
erol checks trust --file '.\checks.json'
```

Approval is stored in the external EROL home and bound to the real project root
and manifest content digest. A changed manifest requires fresh approval;
`erol checks revoke --file PATH` revokes approval for that content. `run`,
`scan --checks`, terminal checks, API check tools, and continuation all verify
this approval. Only basic PATH/system/temp/language environment variables are
passed through; API keys and interpreter startup variables are not inherited.
Required non-secret variables can be added with `checks trust --env NAME`.

Approval and worktrees are not OS sandboxes. Approval does not make future
changes to invoked code trustworthy. For untrusted projects, configure a
literal argv prefix for a sandbox or separate-user executor you prepared with
`--prefix JSON`. EROL does not verify that prefix's OS isolation.
[Execution limits and example](docs/execution.md#check-authorization-and-command-environment).

### 2. Run the task

```powershell
erol run --task 'Fix the specified API bug and pass the relevant tests' --harness codex --checks '.\checks.json'
```

Use `--harness claude` for Claude implementation, `--review-harness claude` for
Codex implementation with Claude review, and `--reviewers 2` or `--reviewers 3`
for two or three reviewers. The default is a separate review session on the
same harness. An optional `--task-id` must be fresh and unique; reused IDs are
rejected.

Baseline checks are recorded, implementation takes place in a separate worktree,
checks are run, and a separate session reviews the result. Completion requires
passing acceptance checks and no open critical/high findings against the same
change digest. One implementer runs per project; reviewers receive no editing
tools.

Default limits are 60 minutes per task, 15 minutes per model session, and up to
5 minutes per check. After initial implementation, at most two repair rounds
are allowed; repeatedly failing strategies require replanning. Hitting a limit
preserves the work with `needs_attention`. The existing CLI model setting is
used; EROL does not assign a model name in this isolated runner. Missing
capability, permission, or login is reported rather than silently switching
harnesses.

### 3. Review, resume, or cancel

```powershell
erol runs list
erol runs show --id RUN_ID
erol runs resume --id RUN_ID
erol runs cancel --id RUN_ID
```

Results include the worktree path, patch, observed checks, and review report.
Inspect the changes with a normal Git diff in that worktree. `run` does not
merge, push, or publish automatically; you decide how to deliver the result.

`resume` validates the project, worktree, check definition, and process state.
A second worker is not started while a session is running or its state is
uncertain. Changed content invalidates old test/review evidence. Completed or
cancelled tasks are not resumed as new tasks. `cancel` is a persistent request;
records and worktrees are retained.
[Execution contract and platform limits](docs/execution.md).

<a id="teknik-ürün-ve-rakip-araştırması"></a>

## Technical, product, and competitor research

Select EROL in your chat and request research. Specify the decision, product,
geography, target customer, and comparison criteria:

```text
Technical: Compare SQLite and PostgreSQL for a local/offline application.
Evaluate data integrity, concurrent writes, maintenance, and deployment using official sources.

Product/competitors: Compare our product with A and B for small businesses in Turkey.
Cite current pricing, feature limits, target customers, and switching costs.
Separate verified facts from inferences; identify unavailable or conflicting information.
```

For persistent research artifacts produced by the executor:

```powershell
erol run --mode research --task 'Prepare a decision report for a local application using official SQLite and PostgreSQL sources' --harness codex --checks '.\research-checks.json'
```

A clean Git project and meaningful acceptance checks specific to the question
are still required. A separate small Git repository with a committed research
brief is sufficient. `research-checks.json` is not bundled; it must define
commands that test your criteria. For the SQLite/PostgreSQL question, create
`scripts/check_research.py` in the target project as an example **scope check**:

```python
import json
from pathlib import Path
from urllib.parse import urlsplit

report = Path("research/report.md").read_text("utf-8").casefold()
ledger = json.loads(Path("research/sources.json").read_text("utf-8"))
assert "sqlite" in report and "postgresql" in report
# Accept English or Turkish concurrency terminology.
assert any(term in report for term in ("concurrency", "eşzaman", "es zaman"))
assert ledger["claims"] and ledger["limitations"]
hosts = {urlsplit(source["url"]).hostname for source in ledger["sources"]}
assert hosts & {"sqlite.org", "www.sqlite.org"}
assert hosts & {"postgresql.org", "www.postgresql.org"}
```

A `research-checks.json` manifest invoking that script:

```json
{
  "schema_version": 1,
  "checks": [
    {"name": "research-scope", "kind": "acceptance",
     "argv": ["python", "-B", "scripts/check_research.py"], "timeout_seconds": 60}
  ]
}
```

Create and commit the scripts/files. For product/competitor questions, adapt the
check to the expected products and criteria. This checks scope; word or source
counts are not proof of factual accuracy.

Outputs are `research/report.md` and `research/sources.json` in the worktree,
including source links, claims, access dates, contradictions, and uncertainties.
EROL also observes public HTTPS access with time/HTTP/hash/byte metadata without
archiving source bodies. A separate reviewer compares claims with sources.
Unavailable/conflicting sources or missing review block completion. An access
receipt is not proof of source correctness or a platform signature; model
review can also be wrong. Native web access depends on CLI permissions.
[Research contract](docs/research-execution.md), [ledger schema](schemas/research.schema.json),
and [synthetic example format](examples/research-sources.json).

<a id="görev-keşfi-kuyruk-ve-paralel-inceleme"></a>

## Task discovery, queue, and parallel review

`scan` discovers TODOs and imported issues. **When you pass `scan --checks`,
check commands actually run in the source project.** Supply only a manifest you
have reviewed. The queue requires an explicit project policy:

```powershell
$erolChecks = (Resolve-Path '.\checks.json').Path
$erolPolicy = Join-Path $env:USERPROFILE '.erol\policies\my-project.json'
New-Item -ItemType Directory -Path (Split-Path $erolPolicy) -Force | Out-Null

erol scan --checks $erolChecks
erol queue policy --harness codex --checks $erolChecks --output $erolPolicy --max-tasks 2 --reviewers 2
# Review the generated policy, then:
erol queue enqueue --policy $erolPolicy
erol queue list
erol queue work --policy $erolPolicy
```

The default rule matches check failures; do not assume every TODO will run
automatically. Policies bind project identity, check digest, rules, and resource
limits. There is no continuously running background daemon.

```console
erol queue depend --id CHILD_JOB --on PARENT_JOB
erol queue resume --id JOB_ID --policy /absolute/policy.json
erol queue cancel --id JOB_ID
```

Dependencies are acyclic; verified parent-task patches are applied to the child
worktree. Conflicts require attention. Parallelism applies to read-only review;
implementers do not write concurrently in the same project.
[Policy and recovery contract](docs/autonomous-work.md).

Behavioral measurements require explicit synthetic fixtures and real CLI sessions:

```console
erol benchmark --suite examples/behavior-suite.json --harness codex --report /absolute/behavior-report.json
erol panel --port 8765 --open
```

Point the suite path to the checkout's [example](examples/behavior-suite.json)
or your own suite. Extract each case's `checks` object into a separate JSON file,
review its fixture code, and approve it with `checks trust --file PATH` before
running the benchmark. Benchmarks make model calls and consume time/usage.
They compare the same fixture with and without EROL context, retaining runner
checks/review in both arms. This is a context ablation, not a pure harness
comparison. A single pair does not establish general speed or token savings.
The panel serves selected read-only evidence on 127.0.0.1 only; it does not start
tasks or expose raw conversations/credentials. API access requires a per-launch
token. Secret scanning also rejects short/numeric AWS/Stripe credential fields;
heuristic scanning does not guarantee detection of every secret.

<a id="hafıza-ve-öğrenme"></a>

## Memory and learning

Memory is stored outside project and plugin directories:

```text
Windows: %USERPROFILE%\.erol\state\<project-id>\memory.db
macOS/Linux: ~/.erol/state/<project-id>/memory.db
Additional records: runs.db, work.db, and rebuildable search.db
```

Identity comes from a credential-free Git remote, or the canonical root path
when no remote exists. Codex and Claude share memory when they use the same
project identity and `--home`. The home must be outside the repository. SQLite
is canonical; Markdown export is a readable view. EROL does not copy raw
conversations/credentials or implement transcript uploads/telemetry. Model calls
remain subject to your selected provider's policies.

```console
erol memory status
erol memory index
erol memory search "database timeout" --mode hybrid --max-chars 6000
erol memory search "database timeout" --mode lexical
erol memory export
erol learning status
erol learning candidates
```

Learning pipeline:

```text
incident → repeated pattern → candidate → eval → project skill
         → verified use in a real task → controlled promotion
```

After a verified repair and separate review, record sanitized evidence using
the [incident format](examples/incident.json):

```console
erol incident record --input /path/to/reviewed-incident.json
erol incident match --component contact-import --exception ImportCursorError --error "ImportCursorError skipped rows"
erol learning candidates
erol learning eval --id CANDIDATE_ID --input /path/to/reviewed-behavior-eval.json
erol learning activate --id CANDIDATE_ID
erol plan --task-id UNIQUE_TASK_ID --task "Current development task"
erol skill usage --task-id UNIQUE_TASK_ID --input /path/to/reviewed-completion.json
erol skill metrics --name SKILL_NAME
erol learning promotion --name SKILL_NAME
```

By default, three distinct verified tasks, a consistent cause/solution, and
quality gates produce a project candidate. Replaying the same task/incident does
not increase its evidence count. Activation requires positive/negative trigger,
behavior, security, and context-budget evaluation. Usage credit requires the
same full revision digest to be actually admitted to a fresh task's context.
Failed or incorrect use removes that revision from routing. Global promotion
requires explicit approval and cross-project evidence; automatic global skill
installation is not implemented. Example JSON files are synthetic formats,
not evidence of a real repair. [Learning cycle](docs/learning.md) and
[evaluation contracts](docs/eval-plan.md).

<a id="güncelleme-ve-kaldırma"></a>

## Update and uninstall

### Update native plugins

```console
codex plugin marketplace upgrade erol
codex plugin add erol@erol
claude plugin marketplace update erol
claude plugin update erol@erol
```

Use the updated version in a new/reloaded session. `stable` is a moving channel;
a fixed `vX.Y.Z` ref stays on that version. A local-path marketplace does not
update itself from GitHub. If you have a local `erol` marketplace, remove only
that source with the native marketplace removal command, then add the Git
source; reinstall the plugin in Claude.

Claude auto-update: `/plugin` → Marketplaces → erol → auto-update.
Optional scheduled native refresh on Windows, run from an EROL checkout:

```powershell
./scripts/update-plugins.ps1 -Harness Both -Register
./scripts/update-plugins.ps1 -Harness Both
./scripts/update-plugins.ps1 -Unregister
```

The task runs at login and every six hours while the user is signed in. It must
be installed separately on each machine. It does not update the CLI wheel
environment. The updater lives in `~/.erol/updater`.
[Release and updater limitations](docs/releases.md).

### Update or uninstall the CLI

On Windows, repeat the wheel/SHA256/venv steps with a new `$erolVersion` and copy
the global launcher again. On macOS/Linux, use the environment's Python to
install the new release wheel with
`-m pip install --upgrade --no-deps <WHEEL_URL_OR_PATH>`.
Replace the placeholder with your chosen asset's URL/path.

Uninstall native plugins:

```console
codex plugin remove erol@erol
claude plugin uninstall erol@erol
```

Preview project-specific bridge removal first:

```console
erol --project /path/to/project uninstall --harness codex
erol --project /path/to/project uninstall --harness codex --apply
erol --project /path/to/project uninstall --harness claude --apply
```

Run `-m pip uninstall erol-ai` with the Python from the environment you installed
for the CLI; remove the global Windows launcher copy too. Canonical memory is
preserved on uninstall. Do not delete the entire `~/.erol` directory: memory
and retained worktrees may share that home.

<a id="sorun-giderme"></a>

## Troubleshooting

| Symptom | Check / fix |
| --- | --- |
| `erol` is not recognized | The plugin does not install a global CLI. Install the CLI and try the full venv executable path. On Windows, check the user `.local\bin` PATH entry and open a new terminal. |
| Python is too old | Check `py -3 --version` / `python3 --version`; use 3.11+. For Node, set the executable path with `EROL_PYTHON`. |
| Skill does not appear | Check plugin enablement/version and start a new session or restart. Use `/erol:erol` in Claude or `$erol` in Codex CLI. |
| Claude OAuth expired / HTTP 401 | Run `/login` inside Claude Code, then retry. EROL does not copy credentials or bypass login. |
| Codex is not logged in | Complete the native `codex login` flow; check the native CLI before using EROL. |
| `clean Git working tree` | Inspect tracked/untracked changes with `git status`; commit required files through your normal workflow. |
| Check executable not found | Install test tools/dependencies; use an absolute executable path or suitable PATH for `argv[0]`. |
| Shell wrapper / pipe rejected | Use a separate-argument `argv` list and native Python/Node executables. |
| `needs_attention` | Read the check/review/timeout reason with `runs show`, resolve it, then use `runs resume` when appropriate. |
| Worker / uncertain process state | Do not start another worker; verify the relevant native session/process and use cancel/resume tools. |
| Skill is not selected | Check `explain`, `skills list`, and `skill show`; explicit phrase matching does not understand every paraphrase. |
| Node → Python spawn denied | The plugin provides a bundled direct Python path under the same permissions. Do not bypass host permissions. See installation documentation. |
| Panel port is in use | Run `erol panel --port 8766 --open`; stop the server with Ctrl+C. |

Passing environment/plugin checks does not mean a live model task passed.
Model calls remain subject to provider time/usage limits.

<a id="doğrulama-ve-geliştirme"></a>

## Validation and development

Full check sequence from a source checkout, using a development virtual environment:

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

Run `npm install --ignore-scripts --no-audit --no-fund` before the Node tests.
`erol eval` is a deterministic routing/pack check, not evidence of live model
or research success.

For `v0.1.6`, the [full main CI matrix](https://github.com/erolemir/EROL/actions/runs/37073828803)
passed all Linux/macOS/Windows × Python 3.11/3.14 jobs. That suite contains
183 Python and 12 Node tests; Windows skips one POSIX permission test. The
[release workflow](https://github.com/erolemir/EROL/actions/runs/37074391455)
rebuilt and tested versioned packages. `RELEASE.json` identifies the source
commit, and `SHA256SUMS` contains the hashes of the three archives.
[Local/live validation records](docs/validation.md).

<a id="yetenekler-ve-sınırlar"></a>

## Capabilities and limitations

- 96 built-in skills and 18 advisory roles across backend, frontend, coding,
  security, DevOps, SEO, marketing, growth, and data/AI.
  [Full catalog](docs/skill-catalog.md).
- Turkish and ASCII Turkish are supported through explicit triggers/aliases.
  Memory uses BM25 and bilingual concept matching; neural embeddings are not
  implemented.
- Usage evidence is bound to a full revision and a unique task that actually
  admitted it into context. Memory is historical reference data; current code
  takes precedence when they disagree.
- Opt-in execution supports one implementer per project, a bounded queue, and
  parallel read-only review. Discovery is not general autonomous decision-making
  or a daemon.
- A worktree is not an OS sandbox. Native CLI permissions and Windows/POSIX
  process cleanup have their own limits. Lint or an agent message alone is not
  evidence of success or containment.
- Live Codex repair/resume, queue with parallel review, source access, and one
  benchmark pair were measured. Claude passed fake-protocol tests, but live
  tests after expired OAuth were skipped at the user's request. Live Desktop
  picker acceptance is a separate step.
- CI establishes deterministic test/package coverage, not live Codex/Claude
  execution on every platform or broad product/competitor research accuracy.
- General speed, success-rate, or token savings have not been established.
  Global skill installation, automatic native event ingestion, and concurrent
  writing workers remain unimplemented.

EROL is in early development. [Implementation plan](docs/implementation-plan.md),
[architecture](docs/architecture.md), [capabilities](docs/capabilities.md), and
[delivery report](docs/delivery-report.md).

<a id="lisans-ve-katkı"></a>

## License and contributions

[AGPL-3.0-only](LICENSE). You may use, modify, and distribute EROL while preserving
required notices; the license's source-sharing requirements apply.
[Contributing](CONTRIBUTING.md), [security reporting](SECURITY.md), and
[open an issue](https://github.com/erolemir/EROL/issues).
