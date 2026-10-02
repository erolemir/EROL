# Routing, focused context, and harness handoffs

EROL ships one canonical pack of **96 original workflow skills** and **18 advisory
agent roles**. The [catalog](skill-catalog.md) covers development, data integrity,
verification, security, operations, SEO, marketing, growth and project learning.
Category filtering discovers a domain without loading its skill bodies.

`src/erol/data/registry.json` is the discovery index. Each workflow has one
canonical `skills/<name>/SKILL.md` body. Agent definitions live in `agents.json`.
The registry reads metadata at construction and leaves builtin skill bodies
unread until `get()` or `route()` selects them. Body digests detect an inconsistent
package. Duplicate analysis explicitly loads bodies because content comparison
requires them. Project records are read from the local SQLite store; its current
record API materializes their payloads, including bodies, into memory. Project
bodies still enter the **harness context** only after selection and budget admission.

This design follows the metadata-first progressive disclosure model described
in the official [Agent Skills specification](https://agentskills.io/specification).
The core index adds EROL-specific routing metadata; the canonical SKILL.md files
retain standard name and description frontmatter.

## Selection rules

Routing is local, deterministic phrase matching. Unicode normalization and
case-folding make case-insensitive matches; punctuation becomes word boundaries.
Turkish `İ`, `ı`, and `i` normalize together without splitting dotted capital
letters. Turkish `çğöşü` fold to `cgosu` for ASCII keyboard spellings. Explicit
Turkish task aliases cover all builtin workflows, including screen filters
and date ranges. This adds no stemming, fuzzy matching, model calls, or universal
"fix" trigger. A trigger must match a complete phrase,
so `metadata` does not trigger `data`. Longer phrases receive more weight.
An explicit `avoid_when` phrase overrides every positive trigger for that skill.
Equal scores prefer project skills, then sort by name. Default selection is
capped at four workflows, and unknown tasks select none.

The returned explanation names the matched phrases and scores. Scores express
matching strength, **not model confidence**. Routing has no semantic understanding
of negation, intent, or implied domain. A task that says “do not deploy” still
contains `deploy`; inspect ambiguous recommendations. This is a known limitation,
not a claim of language-model routing quality.

An active project record must have `status=project_active`, `scope=project`, and
the current store's `project_id`. Candidate, disabled, foreign-project, and
revision-needed records do not enter discovery. A full canonical skill digest
binds the body, triggers, exclusions, version, and ownership; modified active
records fail integrity validation. Generated names may not shadow builtin skills.
Registry snapshots can be refreshed with `refresh_project()` after store changes.

## Context admission

`build_context()` keeps the full task and an explicit trust notice. Selected
skills and retrieved memory are quoted structured JSON data. User and repository
instructions retain authority, and historical claims must be checked against
current code. Quoting and labeling are not a prompt-injection sandbox.

Entries are admitted whole in order, first selected workflows, then retrieved
memory. An entry that exceeds the remaining budget is omitted with a reason;
the function continues looking for smaller entries. Stale memory is omitted.
The task itself is never silently truncated. If the task and trust notice cannot
fit, the call fails with an instruction to increase the budget or narrow the task.

The packet reports `selected_skills`, which is the list actually admitted into
context. The plan's `skills` array describes routing recommendations and may
contain workflows omitted by the budget. Actual-use accounting must use the
admitted list. A caller must not log a skill as used solely because it was routed.
For the task-start CLI response, use `plan.context.selected_skills` for all admitted
builtin and project workflows. Its top-level `selected_skills` contains only learned
project revisions eligible for usage receipts. An empty project list or memory does
not imply that builtin routing selected nothing; bridges report these separately.

`estimated_tokens` uses rounded-up characters divided by four **for the canonical
packet text only**. This is a deterministic size heuristic, not a tokenizer,
provider bill, measured context consumption, or a guarantee that every model's
actual token budget is satisfied. Plan explanations and omission reports are
outside that packet budget; send the packet, not the entire plan, to a specialist.

## Advisory orchestration

`Orchestrator.plan()` recommends bounded roles, phases, tool categories,
verification evidence, and retry behavior. Simple unmatched tasks use a single
lead role. Material-risk tasks reserve an independent verifier or security
reviewer when the role budget permits. Overflow roles are listed explicitly.
Implementation plans keep tester and reviewer roles separate when the budget
permits; omitted verification roles remain explicit in `unassigned_roles`.
The response recommends an abstract FAST, BALANCED, REASONING, or REVIEW tier and
leaves actual model selection to the harness's available models.

These definitions do not spawn processes or agents, invoke models, run tools,
enforce retries, execute tests, or deploy software. `execution_supported=False`
and an unset verification result make that boundary explicit. A supported host
harness executes the work using its own permissions and sandbox. A role name or
tool category never establishes permission or proves a capability exists.

Every role's handoff asks for status, findings, evidence, changes, tests, risks,
and next actions. The caller should provide each role a bounded packet and
verified prior findings instead of the full catalog or memory archive.

## Evaluation and its limits

`routing_cases.json` contains 289 positive, negative, domain-overlap, whole-word,
and Turkish task fixtures. `routing_eval()` reports which expected workflows
were selected and which forbidden workflows were excluded. Unit tests additionally
check lazy reads, body integrity, project isolation, digest binding, negative
precedence, context overflow, and complete task preservation.
The expanded catalog includes adjacent technical-domain contrasts, such as
backend structured data versus SEO markup and Redis caches versus client UI caches.
Task normalization is reused within builtin ranking; project-error normalization
and explainable phrase scores remain unchanged.

`evaluate_skill()` checks metadata, workflow and verification guidance, context
size, conservative secret/instruction scan results, and deterministic trigger
fixtures. At least one positive and one negative fixture is required. Defaults
are synthetic trigger-derived fixtures and are labeled as such; explicit empty
or positive-only cases fail coverage. The report binds both body and full skill
digests and always reports `behavior_verified=False`, `security_verified=False`.

A static pass is insufficient evidence of real task success, effective
prompt-injection containment, a complete security audit, or cross-project
generalization. Project activation and global promotion use the separate learning
lifecycle's independently reviewed evidence. This pack's routing and unit test
results do not establish live Codex/Claude agent performance, provider token
savings, or production reliability.

## Python API

```python
from erol.registry import Registry, evaluate_skill
from erol.orchestration import Orchestrator, routing_eval

registry = Registry(project_store=store)
selection = registry.explain("RabbitMQ consumer duplicate delivery")
plan = Orchestrator(registry).plan(
    "RabbitMQ consumer duplicate delivery",
    memory=store.search("RabbitMQ duplicate"),
    token_budget=4000,
    max_skills=4,
    max_agents=3,
)
packet_for_harness = plan["context"]["text"]
static_report = evaluate_skill(registry.get("message-idempotency"))
routing_report = routing_eval(registry)
```

Run the deterministic checks with `python -m unittest discover -s tests` after
installing EROL in the active Python environment.

Committed bridge snapshots in `adapters/codex` and `adapters/claude` are generated
from `erol.adapters`, with the default canonical home. Run
`python scripts/check_adapter_drift.py --check` for a read-only byte comparison,
or `--write` after an intentional renderer change. A matching snapshot proves
static consistency only; it does not establish runtime harness integration.
