# Ecosystem research and design implications

Checked against primary sources on 2026-10-02. These are source observations and EROL design choices; they are not independent measurements of competing tools. Harness-specific configuration details belong in the capability matrix.

## ECC

ECC ships specialized agents, skills, rules, hooks, installer paths, and harness adapters. Its documented learning system observes sessions, derives confidence-weighted atomic instincts, isolates project state, and evolves groups into skills. EROL should not describe ECC as merely a static skill bundle. ECC also documents platform limitations for its background observer. [ECC repository](https://github.com/affaan-m/ECC), [continuous-learning-v2 source](https://github.com/affaan-m/ECC/blob/main/skills/continuous-learning-v2/SKILL.md).

Useful ideas are narrow specialist instructions, selective rule installation, project scope, and explicit install ownership. Risks to evaluate are overlapping install channels, broad always-loaded rule packs, and growth of learned instructions. EROL's differentiator is an auditable incident-to-skill lifecycle: independent validated occurrences, exact draft evaluation, revision-bound real-use evidence, and controlled global promotion. A frequency/confidence score alone does not establish portability. Those choices are EROL policy, not claims that ECC lacks every corresponding guardrail.

ECC's installer documentation distinguishes native plugin installation from legacy copied configuration and warns against layering both. EROL consequently uses one canonical registry and generated harness output, with dry-run/conflict checks and ownership-based uninstall. It must not copy ECC code, assume cross-harness feature parity, or automatically install the plugin as a development dependency. [ECC installation documentation](https://github.com/affaan-m/ECC#install-ecc).

## Agent Skills

The standard uses a directory containing `SKILL.md`, YAML frontmatter with required `name` and `description`, optional resources, and progressive disclosure. EROL keeps portable instructions in this format and richer routing/lifecycle data in its manifest. Skill metadata and selected bodies have separate budgets. `allowed-tools` is experimental; a manifest is not a permission grant. [Agent Skills specification](https://agentskills.io/specification).

## Memory and orchestration inspiration

LangGraph separates thread checkpoints from long-term stores using namespaces, and distinguishes factual, episodic, and procedural memory. This supports EROL's separate project facts, incident records, and evaluated workflow skills. Store namespaces inspire project isolation; adding LangGraph is unnecessary for a deterministic, local SQLite milestone. [LangGraph memory documentation](https://docs.langchain.com/oss/python/concepts/memory).

Anthropic distinguishes fixed workflows from dynamically controlled agents and recommends beginning with simple composable designs. EROL's learning gates are a deterministic workflow; harnesses perform reasoning and tool execution. Test/review results must anchor completion, and retry budgets must be finite. A generated orchestration plan does not prove delegated agents were executed. [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents).

## Resulting boundaries

Canonical project state lives outside the repository and is shared by adapters. Verified incidents can become project-local skills more readily than global skills. Global promotion requires evidence and an explicit decision by default. Retrieved memory remains untrusted contextual evidence; current code and tests win over stale entries. Secret scanning and static skill inspection are best-effort guards, never claims of a complete secret detector or sandbox. Imported/generated code is not automatically executed.

The first usable implementation proves deterministic selection, persistence, lifecycle gates, and adapter generation. Opt-in local model dispatch and independent review are now implemented; see execution.md and research-execution.md. Semantic retrieval, signed external execution receipts, OS containment, and measured cross-model efficiency remain separate milestones.
