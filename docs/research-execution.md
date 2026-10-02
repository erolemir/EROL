# Technical, product and competitor research

Use research mode for decisions that need evidence outside the repository:

```console
erol --project /path/to/project --home /external/home run --mode research --harness codex --task "Compare SQLite and PostgreSQL for our local dependency-free service" --checks /path/to/reviewed-acceptance.json
erol --project /path/to/project --home /external/home run --mode research --harness claude --task "Compare the named competitors for this customer segment and region; verify current pricing and limitations" --checks /path/to/reviewed-acceptance.json
```

A committed local Git project and reviewed acceptance manifest are still required.
An empty research repository with a committed brief is sufficient. Outputs stay in
the retained worktree; the runner returns its patch and evidence. It never publishes
the report. Native authentication, provider availability and network rules apply.

The workflow defines the decision, audience, geography, versions and evaluation
criteria. Technical research prefers official documentation and original papers.
Product and competitor research compares original product/pricing evidence with
independent observations, substitutes, switching costs and distribution constraints.
It aligns currencies, billing periods and usage assumptions, investigates contrary
evidence, separates facts from inference, and explains uncertainty and next steps.
This is a workflow contract, not a measured guarantee of exhaustive research.

## Deliverables and completion

`research/report.md` presents the answer, comparison when appropriate, recommendation,
assumptions, conflicting evidence, limits and actionable next steps. Cite sources as
`[S1](https://example.test/docs)` with the exact ledger ID and URL.

`research/sources.json` follows the [ledger schema](../schemas/research.schema.json).
The [synthetic example](../examples/research-sources.json) illustrates the format;
its reserved example URL is not factual evidence. Unknown publication dates are
null; accessed dates must be real calendar dates no later than today. Facts and
inferences both link to source IDs, with high/medium/low confidence. Source IDs must
be unique, cited in the report and used by a claim. Limitations cannot be omitted.

EROL adds a **static** artifact check after the caller's acceptance checks. It
checks budgets, dates, URLs, citations and references. It does not fetch pages or
verify the truth of claims. The acceptance manifest must still contain at least
one meaningful acceptance command. Check the requested decision criteria and
requirements, known facts for a controlled fixture, or your domain-specific grader.
Avoid no-op commands and treating the source count as factual accuracy.

The distinct reviewer session opens cited sources through native tools, verifies
attributed claims and comparability, and examines important recommendations for
contrary evidence. Research review requires `source_checks` with one entry per
source: `source_id`, `status` (`verified`, `unavailable`, `contradicted`) and `reason`.
Missing entries or any unavailable/contradicted source produces a high finding and
blocks completion, even if the report's structural checks pass. The implementer
can replace an inaccessible source or correct the report within the existing retry
budget. A valid ledger and empty findings without source checks cannot complete.

Source review is labelled `model_review_assertion`: it is a native model's
assertion of claim verification. EROL additionally fetches cited public HTTPS
sources and records a separate timestamp/status/content hash/byte-count receipt,
without archiving the body. Private/mixed DNS, unsafe redirects, credentials,
oversized bodies and time budgets prevent unsupported access. These locally
observed receipts do not authenticate factual truth or provide a platform signature.
Native tool payloads are not retained. Reviewer mistakes,
inaccessible pages, stale vendor information and incomplete search remain possible.
Successful checks and review bind to the same report/source bytes; editing either
invalidates prior evidence on resume. Use `runs show` to inspect the review and
the worktree to read the complete report.

## Native capabilities and validation

Codex research runs explicitly enable live web search with `--search`; EROL checks
the installed CLI's help before using it. Claude adds only `WebSearch` and `WebFetch`
to the worker/reviewer tool sets. Reviewer editing tools remain absent. Native
permissions and provider policy can deny these tools; an unavailable tool/source
must be reported as blocked, never replaced silently with invented evidence.
Saved config, hooks, model defaults and credentials are not modified.

These mappings were checked against the official
[Codex CLI reference](https://developers.openai.com/codex/cli/reference) and
[Claude tools reference](https://code.claude.com/docs/en/tools-reference), plus the
installed CLI help. Worktree separation and tool lists do not establish OS isolation.

For an explicit narrow live trial:

```console
python scripts/research_trial.py --harness codex --report .validation/research-codex.json
python scripts/research_trial.py --harness claude --report .validation/research-claude.json
```

The fixture asks for a SQLite/PostgreSQL comparison, checks requested report
coverage and official-source requirements, and invokes independent source review.
Report coverage is locally observed; factual source checking is model review.
Deterministic fixtures test invalid URLs/dates/references, unavailable/contradicted
sources and completion gates without claiming real retrieval. Live results and
platform limitations are recorded separately in [validation](validation.md).
The user waived further Claude live tests after its earlier expired-OAuth result.
See [source access limits](autonomous-work.md) for the full receipt contract.
