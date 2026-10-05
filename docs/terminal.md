# EROL Terminal contract (0.2.0)

The core uses only Python's standard library. `erol` enters chat only when both
stdin/stdout are TTYs; explicit JSON commands and isolated `run` remain separate.
The original PNG is packaged byte-for-byte under `data/brand/erol.png`. Terminal
pixels use the existing compressed monochrome asset and Unicode half blocks.

The rich UI owns a cleared alternate screen. Transcript cells wrap only inside
the left column; a separate right panel animates antennae/forelegs while the
editor and status remain below both panels. `/logo` toggles panel width; PgUp/PgDn
or the mouse wheel scroll the bounded 200,000-character in-memory transcript,
including during execution. New stream chunks preserve a scrolled viewport;
the bottom follows output only when already at the bottom. Windows uses native
input records to retain mouse events, clears QuickEdit/echo while reading and
combines UTF-16 surrogate pairs; POSIX decodes SGR mouse reports. Both accept
Backspace BS/DEL, Delete and Ctrl+U (clear input). Keystrokes during a task are
bounded and queued for the next editor; Ctrl+C cancels immediately. Shift+click
can bypass reporting for selection in supporting terminals. Mouse support follows
[Microsoft console modes](https://learn.microsoft.com/en-us/windows/console/setconsolemode),
[input records](https://learn.microsoft.com/en-us/windows/console/readconsoleinput)
and [xterm SGR reporting](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html).
The sidebar appears
at 72 columns / 18 rows and disappears on smaller resizes. Unicode cell widths,
multiline editor positioning and differential row redraws preserve input during
animation. An idle refresh thread shares the output lock, stops on close, and
cannot repaint after the screen becomes inactive. Output/input modes and the
shell buffer are restored on exit or cleanup errors. Windows alternate buffer
support follows [Microsoft's VT contract](https://learn.microsoft.com/en-us/windows/console/console-virtual-terminal-sequences).
`NO_COLOR`, dumb terminals and unavailable VT use static sequential output;
the original standalone `erol logo` command remains unchanged.

When the working directory contains the external EROL home (including startup
from the user's home directory), auto mode opens projectless conversation.
`erol chat --mode general|research` explicitly selects this scope from any folder;
headless auto uses the same containment rule. `/connect`, `/providers`, `/models`,
`/model`, `/settings`, `/language`, `/help` and session commands need no project.
Startup/help alone do not create state or probe providers. Explicit changes persist
only global connection settings. `/general [MESSAGE]` and `/research [QUESTION or URL]`
switch scope; `/project PATH` validates the canonical root against home containment.
Switching scopes creates a fresh session and preserves manual model/settings.
Projectless `/diff` and `/tests` explain the need for a project.

UI catalogs support English and Turkish. Schema-1 settings gain an optional
`language` field defaulting to `auto`; `/language auto|en|tr` and `/settings language`
persist only the preference in external storage. Windows auto selection uses
[GetUserDefaultUILanguage](https://learn.microsoft.com/en-us/windows/win32/api/winnls/nf-winnls-getuserdefaultuilanguage),
independent of the regional/encoding locale. POSIX checks LC_ALL, LC_MESSAGES,
LANGUAGE and LANG, then the process locale. Turkish selects tr; unsupported or
unavailable locales select en. Existing saved choices are read before opening
an engine without creating state; explicit language changes persist immediately.
Help, chrome, editor hints and EROL UI messages are localized. Canonical command
names, identifiers, status values, numeric settings, USD calculations and JSON keys
remain unchanged. Provider diagnostics and model output are displayed as supplied.

Interactive provider/model/settings/status/usage/test/session/plan views render
human-readable summaries; headless results retain their JSON structure. Help is
grouped by purpose. Command and common argument suggestions appear below the
editor; Tab uses the common prefix. Ctrl+W erases a word, Ctrl+K erases to the
line end, and multiline up/down navigates lines before recalling prompt history.
Prose wraps at word boundaries while code fences/indented text preserve spacing.
Semantic heading/diff/error colors are added after layout, never interpreted from
model control sequences. Failures retain text labels and observed test output.
Successful tool results are quiet; failed tools remain visible and are marked
`is_error` in API events (and Anthropic tool-result responses).
`/clear` clears visible transcript only; `/view compact|full` hides/restores the
sidebar; `/motion on|off` controls logo motion. These display controls are session
preferences and do not reset task records. Native text selection remains terminal
dependent. No screen-reader or universal accessibility compliance is claimed.

## Projectless conversation and research

Ordinary prompts automatically route relevant EROL skills. Project mode uses
builtin and active project Registry entries plus relevant project memory;
projectless mode uses only the builtin Registry, memory=[] and a bounded default
context packet. Only bodies actually admitted by build_context reach the model
and only those names are shown in `skills` events and saved selected_skills.
Simple unrelated questions select none; omitted entries never earn use credit.
The model is instructed to apply relevant guidance within its role/tools. A
skill does not itself spawn an agent or grant file/web/command access, and
loading a body is not proof of behavioral success or learned-skill promotion.

GeneralEngine shares configuration/provider adapters with ChatEngine but does not
construct project identity, Store, Workspace, snapshots, leases for project files,
checks, or project learning. Task records are scoped to null project id under
external `global/chat`; answers and source bodies are not persisted. User intent
and an in-process bounded previous answer are untrusted continuation context;
restart restores only the saved intent summary. Native session ids are never
reused across these modes. Completed means delivered response, with verified=false.

Provider probes and turns use fresh neutral temporary directories. Codex uses
read-only sandbox, disables `features.shell_tool` and selects disabled/live
`web_search`; Claude uses an empty built-in tool list for general mode or only
WebSearch/WebFetch for research, with empty strict MCP configuration. Local CLI
capabilities must recognize these controls before a turn. Native configs/plugins
remain a provider policy limitation, not universal OS containment. `agy` is
ineligible because it cannot satisfy the read-only role. Contracts follow
[Codex configuration](https://developers.openai.com/codex/config-reference/) and
[Claude CLI](https://code.claude.com/docs/en/cli-reference).

General API turns omit empty tools lists; research exposes only `read_source(url)`.
It supports public HTTPS HTML/text, not search-index queries or PDF extraction.
DNS is pinned, redirects revalidated, private/local destinations and credential
URLs refused. Calls share an eight-source/60-second budget, the existing 1 MiB
response limit, deadline and cancellation. Text is capped at 64,000 characters;
scripts/styles are excluded. Source failures are explicit sanitized unavailable
receipts. Source access is evidence of retrieval, not factual correctness. All API
rounds share the task USD guard and continuation restores latest cumulative usage.

An in-process busy gate prevents replacing an active API record; a per-session
OS-held lock prevents concurrent headless continuations, releases on process exit,
and reloads latest accounting under lock. Live owner PIDs and uncertain native
cleanup prevent resume/new/project switch; no unrelated saved PID is signalled.

## Connections and trust

`connections.json` schema 1 lives in the external EROL home. Each connection has
an independent id, kind, enabled flag and model profiles. CLI uses native login;
API credentials are environment references, never saved keys. Explicit compatible
endpoints use HTTPS or localhost HTTP; authenticated redirects are rejected.
Native shell wrappers are resolved to supported node/native entries or rejected.
Antigravity's IDE launcher is not `agy`.

On Windows, missing PATH Codex discovery checks only the observed desktop
`LOCALAPPDATA/OpenAI/Codex/bin` directory and at most 64 immediate entries.
Root and 16-character hexadecimal version directories may supply a native
codex.exe; newest file mtime wins, with a deterministic path tie-breaker.
Links/reparse points are rejected. PATH and explicitly configured executables
retain precedence; broken PATH wrappers are not silently replaced. No credentials
are read during discovery. Claude authentication still uses its native login.

Adapters expose capabilities, models, stream, cancel, and resume (API resume is
EROL summary continuation; native session ids are reused only in matching
connection/model/role contexts). Event schema 1 carries task/connection/model/role,
UTC time and typed data: text_delta, tool_start/tool_result, file_change, usage,
routing, skills, process, final, status and error. Raw provider streams are not persisted
in memory. Sessions retain bounded task summaries, diffs and observed evidence.

API local tools: list_files/read_file/search; implementer also write_file,
delete_file and run_command. Reads are bounded; paths cannot escape the project,
follow symlinks or target protected credential/build directories. Edits/deletes
require the hash observed by that workspace instance. New writes require null
expected_sha256. Commands require exact argv allowlisting; there is no shell
interpolation. Configured acceptance manifest argv are also enabled. API review
and planning cannot write or run commands. Codex roles use native workspace-write
or read-only sandbox; Claude roles restrict native tool lists, disable MCP and
use dontAsk permissions. Native CLI containment remains the harness's capability,
not a universal EROL OS sandbox. EROL additionally detects source changes during
checks/review and refuses verified completion.

`agy` native sandbox automatically permits workspace writes. Therefore this
adapter is eligible only as implementer, never as read-only planner/reviewer.
Large tasks require another connection for those roles. The protocol is based on
[official headless documentation](https://www.antigravity.google/docs/cli/headless/)
and [CLI reference](https://www.antigravity.google/docs/cli/reference/).

## Selection, budget, execution

Conservative bilingual scope/risk rules and EROL plan size set capability floors.
Unknown work starts at medium; substantial/risky work starts at level 3. Eligibility
requires tools, context, availability and API price metadata; account model listing
is checked before API execution, native CLI model access finally on the turn.
Balanced ranking uses nominal request cost, configurable CLI resource pressure,
latency priors and stable ids; subscription_first prioritizes eligible CLIs.
cli_only excludes automatic API selection. A manual model is never silently
replaced; it may override the capability floor, but not tools/context/access.

These are declared profiles, not learned success probabilities. There is no
fabricated benchmark score. The initial catalog was checked on 2026-10-05 against
[OpenAI Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[OpenAI Luna](https://developers.openai.com/api/docs/models/gpt-6-luna),
[Anthropic models](https://platform.claude.com/docs/en/models/overview),
[Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/overview) and
[Gemini Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash).
Luna API pricing is unset, so it is CLI-only until a price profile is configured.
Catalog/model access and pricing can change; `/models refresh` checks access,
`/models add ID JSON` updates profiles. Profile source records provider metadata;
EROL capability levels and latency ranks remain engineering priors.

Complete simple greetings/thanks in Turkish or English route as small tasks
with low effort. Added task words retain ordinary conservative scope/risk
assessment. Missing eligible lower tiers are explained; a manual model remains
selected. Windows desktop Codex discovery and one automatic Luna greeting
were verified locally, without API calls.

The $5 default API task budget is shared across all roles, tool rounds and retries.
A lock atomically reserves each payload's UTF-8 byte proxy plus configured output
cap at nominal token prices. Reported tokens settle the estimate; absent usage
keeps the reservation as spent. CLI quota is reported separately and may be
unknown. Token prices, thinking/caching/tier billing and tokenizer behavior can
vary; this guard is not an invoice ceiling. A failed/closed HTTP stream retains
its reservation. Budget exhaustion saves waiting_budget; continuing a saved task
retains cumulative accounting. HTTP line/response/round/time budgets are bounded.

Interactive native subscription usage shows reported input/output/total tokens
and quota evidence, without USD when no API call/accounting was observed.
API and mixed-role summaries preserve API estimates and separate CLI token
counts. An allocated budget alone is not a billed call; missing token usage
remains unknown. Structured JSON budget records remain unchanged. Enabled API
settings may still show an explicitly labelled API budget in configuration.
On Windows, EROL sets the console title on entry and restores the previous title
on exit where the terminal accepts application titles.

At most three model calls run concurrently; there is one writer. Large tasks get
a planner and up to two distinct-model reviewers; a single eligible review model
still gets a fresh independent session. At most three implementer turns include
observed-check and review repair; automatic escalation after two unsuccessful
turns requires a higher actual model level. Unsupported access/containment stops
the task. Uncertain cleanup is fatal and never retries another writer.

Each execution step compares against its initial bounded source snapshot, including
pre-existing dirty content. Git lists tracked/unignored files; non-Git walking
excludes protected/generated folders, including nested .next/.dart_tool/.gradle.
Source text snapshots cap files at 2 MiB; oversized binary assets use streaming
SHA256/size fingerprints, retaining added/modified/deleted evidence without loading
their content. Aggregate bytes scanned remain capped at 64 MiB; oversized source
errors name the file and suggest narrowing /project. API reads/writes retain their
2 MiB limits. Text diff is bounded; binary changes carry hashes. No stash,
reset, commit or publication is automatic. Resume preserves partial edits, prior
step diffs and limited summaries; `/diff` shows step history, not a synthesized
whole-session patch. Old summaries/memory are untrusted references.

Windows process jobs / POSIX owned groups handle Ctrl+C cancellation. Shared Git
metadata leases interoperate with isolated runs and external homes; non-Git
leases use canonical-path identity under the OS temp folder. Child pids are saved
at startup and cleared only after observer cleanup. Native session state is
owned by each provider; EROL never signals arbitrary saved PIDs.

Completion requires an observed passing acceptance manifest and completed,
approved independent review against unchanged source. A model's statement that
tests passed is not evidence. Small work with no review and work without check
manifest remain implemented_unverified. Failures/findings remain needs_attention;
cancellation retains the partial diff. Project-memory promotion gates are unchanged;
terminal tasks do not automatically promote skills or award real-use receipts.

A configured `checks_path` must first be explicitly reviewed and approved with
`erol --project PATH --home HOME checks trust --file MANIFEST` using the terminal's
project and home. A repo file alone cannot authorize execution. Matching API tool
commands use the same receipt, minimized environment and optional executor prefix;
standalone `allowed_commands` are separately explicit host-command authorization.
Revoke/change a manifest and continuation cannot reuse its prior approval.
See [check trust and OS isolation limits](execution.md#check-authorization-and-command-environment).

## Validation coverage

Deterministic tests cover all CLI native decoders and all four API formats,
including a real loopback HTTP SSE server, tool-driven file edits, shared/missing
usage accounting, malformed/truncated streams, role/path/hash restrictions,
dirty/new/deleted/binary diffs, review repair, continuation, cancellation,
shared-home leases and whole-task check timeout. They are protocol/workspace
coverage, not live account or containment proof for every provider/platform.

Windows local terminal and live provider results are recorded in
implementation-plan.md. macOS/Linux terminal behavior and live API/Claude/agy
execution require separate platform/account trials. Plain fallback mode cannot
provide raw-key multiline/history/completion. Rich paste requires a terminal that
emits bracketed-paste markers; display assumes monospace Unicode and approximately
1:2 cells. Model routing remains a profile-based prior rather than a measured
"best model" guarantee.
