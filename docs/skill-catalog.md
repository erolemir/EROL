# Ready-made skill catalog

EROL bundles 96 original curated workflow skills and 18 advisory roles. Discovery reads
metadata; only the selected bodies enter context, with a default limit of four skills.
These workflows are ready-made guidance, not independently proven specialist models.

Browse domains without loading bodies:

```console
erol skills list --category backend
erol skills list --category marketing
erol skill show paid-search-campaign
erol explain --task "API integration with regression tests and code review"
```

Categories: `backend`, `frontend`, `coding`, `security`, `devops`, `seo`, `marketing`, `growth`, `data`.
Learned project workflows remain separate and appear as `project` when active.

Each new workflow has an English and Turkish routing fixture plus an unrelated contrast
case. These check deterministic selection, not the quality of every real-world outcome.

## Domains

| Domain | Skills |
| --- | ---: |
| Backend | 15 |
| Frontend | 10 |
| General coding and project learning | 22 |
| Cybersecurity | 9 |
| Servers and DevOps | 12 |
| SEO | 6 |
| Marketing and advertising | 8 |
| Business growth | 8 |
| Data, analytics and AI | 6 |

## Backend

| Skill | When to use |
| --- | --- |
| [api-contract-design](../src/erol/data/skills/api-contract-design/SKILL.md) | Evolve service contracts with compatibility, validation, and failure semantics. |
| [background-job-reliability](../src/erol/data/skills/background-job-reliability/SKILL.md) | Make queued work recoverable through acknowledgements, leases, bounded retries and safe replay. |
| [caching-strategy](../src/erol/data/skills/caching-strategy/SKILL.md) | Design cache keys, invalidation and freshness policies from measured read behavior and correctness requirements. |
| [database-migration-safety](../src/erol/data/skills/database-migration-safety/SKILL.md) | Prepare compatible schema changes with recovery and data-integrity verification. |
| [database-query-performance](../src/erol/data/skills/database-query-performance/SKILL.md) | Measure and improve slow SQL through query plans and representative workload evidence. |
| [distributed-workflow](../src/erol/data/skills/distributed-workflow/SKILL.md) | Coordinate multi-service effects using durable states, reconciliation and explicit compensation limits. |
| [file-upload-pipeline](../src/erol/data/skills/file-upload-pipeline/SKILL.md) | Build resumable file ingestion with bounded resources, durable ownership and visible processing states. |
| [message-idempotency](../src/erol/data/skills/message-idempotency/SKILL.md) | Prevent duplicate side effects in retried requests and at-least-once message consumers. |
| [multi-tenant-isolation](../src/erol/data/skills/multi-tenant-isolation/SKILL.md) | Verify tenant scoping across queries, jobs, caches and object references. |
| [rate-limit-design](../src/erol/data/skills/rate-limit-design/SKILL.md) | Design bounded request quotas with explicit identities, burst behavior and fair failure responses. |
| [realtime-service](../src/erol/data/skills/realtime-service/SKILL.md) | Design authenticated realtime connections with bounded delivery, reconnect and backpressure behavior. |
| [service-api-integration](../src/erol/data/skills/service-api-integration/SKILL.md) | Implement external service adapters from verified provider contracts, including credentials, timeouts and uncertain outcomes. |
| [stable-pagination](../src/erol/data/skills/stable-pagination/SKILL.md) | Diagnose missing or repeated rows at pagination and batch-import boundaries. |
| [transaction-boundaries](../src/erol/data/skills/transaction-boundaries/SKILL.md) | Define database transaction ownership and concurrency invariants for multi-step writes. |
| [webhook-delivery](../src/erol/data/skills/webhook-delivery/SKILL.md) | Implement inbound or outbound webhook delivery with verification, durable acknowledgement and replay handling. |

## Frontend

| Skill | When to use |
| --- | --- |
| [accessibility-audit](../src/erol/data/skills/accessibility-audit/SKILL.md) | Improve interactive UI access through keyboard, semantics, focus, and perceivable feedback. |
| [dashboard-design](../src/erol/data/skills/dashboard-design/SKILL.md) | Design operational dashboards around decisions, metric definitions and comparable data states. |
| [design-system-components](../src/erol/data/skills/design-system-components/SKILL.md) | Create reusable UI components with explicit variants, interaction contracts and consistent tokens. |
| [form-validation](../src/erol/data/skills/form-validation/SKILL.md) | Implement form validation, submission and recovery without losing user input or trusting client checks alone. |
| [frontend-data-fetching](../src/erol/data/skills/frontend-data-fetching/SKILL.md) | Manage remote UI data through cache keys, cancellation and consistent loading/error states. |
| [frontend-e2e-testing](../src/erol/data/skills/frontend-e2e-testing/SKILL.md) | Test critical browser journeys with stable state setup, meaningful assertions and controlled dependencies. |
| [frontend-state-correctness](../src/erol/data/skills/frontend-state-correctness/SKILL.md) | Diagnose stale UI, asynchronous races, and inconsistent client state transitions. |
| [internationalization](../src/erol/data/skills/internationalization/SKILL.md) | Implement locale-aware UI strings, formats and directionality without changing canonical stored values. |
| [responsive-layout](../src/erol/data/skills/responsive-layout/SKILL.md) | Build layouts that remain usable across viewport sizes, zoom and variable content. |
| [web-performance-budget](../src/erol/data/skills/web-performance-budget/SKILL.md) | Measure web loading and interaction bottlenecks with repeatable budgets and representative users. |

## General coding and project learning

| Skill | When to use |
| --- | --- |
| [architecture-decision](../src/erol/data/skills/architecture-decision/SKILL.md) | Make bounded architectural decisions backed by repository constraints and explicit tradeoffs. |
| [configuration-management](../src/erol/data/skills/configuration-management/SKILL.md) | Make configuration explicit, validated and environment-consistent without exposing secrets. |
| [context-handoff](../src/erol/data/skills/context-handoff/SKILL.md) | Prepare bounded task and agent handoffs with evidence and explicit unresolved work. |
| [dependency-boundaries](../src/erol/data/skills/dependency-boundaries/SKILL.md) | Restructure modules around dependency direction, ownership and testable interfaces. |
| [dependency-upgrade](../src/erol/data/skills/dependency-upgrade/SKILL.md) | Upgrade dependencies through compatibility research, reproducible resolution, and rollback evidence. |
| [documentation-maintenance](../src/erol/data/skills/documentation-maintenance/SKILL.md) | Update project documentation from observed behavior and reproducible examples. |
| [error-handling-contracts](../src/erol/data/skills/error-handling-contracts/SKILL.md) | Design errors that preserve causality, stable caller behavior and safe operational diagnostics. |
| [evidence-code-review](../src/erol/data/skills/evidence-code-review/SKILL.md) | Review changes for concrete correctness risks with reproducible findings. |
| [git-branch-integration](../src/erol/data/skills/git-branch-integration/SKILL.md) | Synchronize and integrate Git branches while preserving local work and divergent history. |
| [incident-debugging](../src/erol/data/skills/incident-debugging/SKILL.md) | Investigate reproducible failures and preserve verified causes and regression evidence. |
| [learning-pattern-discovery](../src/erol/data/skills/learning-pattern-discovery/SKILL.md) | Turn repeated verified incidents into bounded project workflow candidates. |
| [legacy-modernization](../src/erol/data/skills/legacy-modernization/SKILL.md) | Modernize legacy code incrementally with characterization, compatibility seams and recoverable rollout. |
| [memory-hygiene](../src/erol/data/skills/memory-hygiene/SKILL.md) | Preserve small, evidence-backed project memory with redaction, staleness, and provenance. |
| [performance-profiling](../src/erol/data/skills/performance-profiling/SKILL.md) | Measure bottlenecks before optimizing CPU, memory, or end-to-end latency. |
| [regression-test-design](../src/erol/data/skills/regression-test-design/SKILL.md) | Select focused tests that demonstrate behavioral changes and protect meaningful boundaries. |
| [repository-change-planning](../src/erol/data/skills/repository-change-planning/SKILL.md) | Plan a scoped code change from affected callers, compatibility constraints and verifiable milestones. |
| [repository-exploration](../src/erol/data/skills/repository-exploration/SKILL.md) | Find relevant code paths and project conventions before planning a change. |
| [requirements-acceptance](../src/erol/data/skills/requirements-acceptance/SKILL.md) | Turn feature requests into observable acceptance criteria, boundaries and unresolved decisions. |
| [safe-refactoring](../src/erol/data/skills/safe-refactoring/SKILL.md) | Change structure while preserving externally observable behavior and project style. |
| [skill-quality-evaluation](../src/erol/data/skills/skill-quality-evaluation/SKILL.md) | Evaluate skill metadata, triggers, context overhead, and real usage evidence without overstating static checks. |
| [test-fixture-design](../src/erol/data/skills/test-fixture-design/SKILL.md) | Build deterministic fixtures that expose behavioral failures without reproducing implementation details. |
| [tool-capability-selection](../src/erol/data/skills/tool-capability-selection/SKILL.md) | Choose tools from observed capabilities and scope without inventing APIs or permissions. |

## Cybersecurity

| Skill | When to use |
| --- | --- |
| [authentication-session-security](../src/erol/data/skills/authentication-session-security/SKILL.md) | Review login, tokens and session lifecycle for binding, expiry, revocation and recovery weaknesses. |
| [authorized-security-testing](../src/erol/data/skills/authorized-security-testing/SKILL.md) | Plan and execute bounded security tests on explicitly authorized targets with reproducible findings. |
| [dependency-supply-chain-review](../src/erol/data/skills/dependency-supply-chain-review/SKILL.md) | Review dependency provenance, build scripts and artifact integrity for supply-chain exposure. |
| [secrets-rotation](../src/erol/data/skills/secrets-rotation/SKILL.md) | Plan and verify credential rotation with overlap, revocation and recoverable dependent-service updates. |
| [secure-file-handling](../src/erol/data/skills/secure-file-handling/SKILL.md) | Review untrusted file parsing, paths and storage boundaries for traversal and resource exhaustion. |
| [security-boundary-review](../src/erol/data/skills/security-boundary-review/SKILL.md) | Examine untrusted inputs, authorization boundaries, secret handling, and dangerous side effects. |
| [security-log-detection](../src/erol/data/skills/security-log-detection/SKILL.md) | Design actionable security detections from reliable event semantics and tested false-positive controls. |
| [threat-modeling](../src/erol/data/skills/threat-modeling/SKILL.md) | Model assets, trust boundaries and concrete abuse paths before choosing security controls. |
| [vulnerability-triage](../src/erol/data/skills/vulnerability-triage/SKILL.md) | Assess vulnerability reports by reachable behavior, exact versions and evidence-backed remediation. |

## Servers and DevOps

| Skill | When to use |
| --- | --- |
| [ci-failure-triage](../src/erol/data/skills/ci-failure-triage/SKILL.md) | Diagnose build and CI failures through reproducible environment comparisons. |
| [cloud-cost-optimization](../src/erol/data/skills/cloud-cost-optimization/SKILL.md) | Reduce cloud spend using attributable usage, unit costs and reversible capacity decisions. |
| [container-runtime-hardening](../src/erol/data/skills/container-runtime-hardening/SKILL.md) | Reduce container privileges and image exposure while preserving required runtime behavior. |
| [database-backup-restore](../src/erol/data/skills/database-backup-restore/SKILL.md) | Design backup and restore procedures around recoverable data, dependencies and measured recovery objectives. |
| [disaster-recovery](../src/erol/data/skills/disaster-recovery/SKILL.md) | Plan disaster recovery across infrastructure, data, credentials and routing with a tested failback boundary. |
| [infrastructure-change-plan](../src/erol/data/skills/infrastructure-change-plan/SKILL.md) | Review infrastructure changes for drift, state ownership, blast radius and recoverable application impact. |
| [kubernetes-rollout](../src/erol/data/skills/kubernetes-rollout/SKILL.md) | Plan recoverable Kubernetes deployments using readiness, capacity, versioned artifacts and rollback checks. |
| [linux-service-operations](../src/erol/data/skills/linux-service-operations/SKILL.md) | Diagnose Linux service health from process ownership, logs, resources and configuration before changing service state. |
| [observability-design](../src/erol/data/skills/observability-design/SKILL.md) | Design logs, metrics and traces that explain user-visible failures without excessive cardinality or sensitive payloads. |
| [production-incident-response](../src/erol/data/skills/production-incident-response/SKILL.md) | Respond to production incidents with evidence preservation, scoped mitigation and recovery verification. |
| [release-verification](../src/erol/data/skills/release-verification/SKILL.md) | Prepare evidence-backed releases with explicit readiness gates and recoverable rollout. |
| [reverse-proxy-tls](../src/erol/data/skills/reverse-proxy-tls/SKILL.md) | Configure proxy routing and TLS while preserving trusted client identity and upstream request semantics. |

## SEO

| Skill | When to use |
| --- | --- |
| [seo-content-brief](../src/erol/data/skills/seo-content-brief/SKILL.md) | Create useful search-oriented content briefs from audience questions, original evidence and clear page intent. |
| [seo-international-sites](../src/erol/data/skills/seo-international-sites/SKILL.md) | Design localized URL discovery, alternate-language annotations and consistent international page targeting. |
| [seo-migration](../src/erol/data/skills/seo-migration/SKILL.md) | Plan URL or domain migrations with preserved destinations, redirects and post-move search monitoring. |
| [seo-performance-measurement](../src/erol/data/skills/seo-performance-measurement/SKILL.md) | Measure organic-search outcomes using comparable query/page cohorts and explicit attribution limits. |
| [seo-structured-data](../src/erol/data/skills/seo-structured-data/SKILL.md) | Implement structured data that reflects visible page content and the current supported search feature. |
| [seo-technical-audit](../src/erol/data/skills/seo-technical-audit/SKILL.md) | Audit crawlability, rendering, canonical URLs and index eligibility from page and search evidence. |

## Marketing and advertising

| Skill | When to use |
| --- | --- |
| [brand-positioning](../src/erol/data/skills/brand-positioning/SKILL.md) | Develop positioning from customer alternatives, credible differentiation and proof. |
| [content-distribution-plan](../src/erol/data/skills/content-distribution-plan/SKILL.md) | Plan reusable content and channel distribution around audience needs, capacity and measurable outcomes. |
| [customer-segmentation](../src/erol/data/skills/customer-segmentation/SKILL.md) | Define actionable customer segments from needs, behavior and reachable evidence rather than invented personas. |
| [lifecycle-email-marketing](../src/erol/data/skills/lifecycle-email-marketing/SKILL.md) | Design permission-aware lifecycle emails triggered by meaningful product states and measured user outcomes. |
| [market-research](../src/erol/data/skills/market-research/SKILL.md) | Research a market and competitors with dated evidence, explicit segments and defensible comparisons. |
| [marketing-copywriting](../src/erol/data/skills/marketing-copywriting/SKILL.md) | Write truthful campaign or product copy matched to audience intent, channel constraints and a clear action. |
| [paid-search-campaign](../src/erol/data/skills/paid-search-campaign/SKILL.md) | Design paid-search campaign drafts with intent separation, budget boundaries and reliable conversion measurement. |
| [paid-social-campaign](../src/erol/data/skills/paid-social-campaign/SKILL.md) | Prepare paid-social creative tests with credible messages, audience boundaries and budget-aware measurement. |

## Business growth

| Skill | When to use |
| --- | --- |
| [conversion-funnel-analysis](../src/erol/data/skills/conversion-funnel-analysis/SKILL.md) | Analyze conversion funnels with consistent identities, event ordering and meaningful denominators. |
| [customer-discovery](../src/erol/data/skills/customer-discovery/SKILL.md) | Plan unbiased customer discovery that separates observed problems from reactions to a proposed solution. |
| [growth-experiment-design](../src/erol/data/skills/growth-experiment-design/SKILL.md) | Design bounded business growth experiments with falsifiable hypotheses, guardrails and decision rules. |
| [landing-page-optimization](../src/erol/data/skills/landing-page-optimization/SKILL.md) | Improve landing pages through message/offer alignment, user friction and measured conversion hypotheses. |
| [partnership-strategy](../src/erol/data/skills/partnership-strategy/SKILL.md) | Evaluate partnerships from mutual customer value, economics, responsibilities and pilot evidence. |
| [pricing-packaging-research](../src/erol/data/skills/pricing-packaging-research/SKILL.md) | Research product pricing and packaging from customer value, unit economics and defensible willingness-to-pay evidence. |
| [retention-cohort-analysis](../src/erol/data/skills/retention-cohort-analysis/SKILL.md) | Measure retention using comparable cohorts, meaningful activity definitions and censoring-aware windows. |
| [sales-pipeline-design](../src/erol/data/skills/sales-pipeline-design/SKILL.md) | Design a sales pipeline around buyer evidence, stage exit criteria and reliable operational reporting. |

## Data, analytics and AI

| Skill | When to use |
| --- | --- |
| [analytics-event-contracts](../src/erol/data/skills/analytics-event-contracts/SKILL.md) | Define analytics events with stable identities, semantics and privacy-aware verification. |
| [data-pipeline-integrity](../src/erol/data/skills/data-pipeline-integrity/SKILL.md) | Build batch or streaming pipelines with explicit schemas, reconciliation and recoverable checkpoints. |
| [experiment-statistics](../src/erol/data/skills/experiment-statistics/SKILL.md) | Evaluate experiments with valid randomization, uncertainty and predeclared outcome decisions. |
| [llm-feature-evaluation](../src/erol/data/skills/llm-feature-evaluation/SKILL.md) | Evaluate LLM features on representative fixtures, failure categories, cost and human-review requirements. |
| [privacy-data-retention](../src/erol/data/skills/privacy-data-retention/SKILL.md) | Map sensitive data collection, retention and deletion to concrete systems and stated policy requirements. |
| [product-prioritization](../src/erol/data/skills/product-prioritization/SKILL.md) | Prioritize product work using customer evidence, constraints and transparent impact assumptions. |

## Evidence and current references

Platform-specific settings must be rechecked against the deployed version and current
official documentation. The workflows link applicable primary references for
[search content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content),
[structured data](https://developers.google.com/search/docs/appearance/structured-data/sd-policies),
[search ads](https://support.google.com/google-ads/answer/6167115),
[OWASP verification](https://owasp.org/projects/asvs),
[Docker](https://docs.docker.com/engine/security/),
[Kubernetes deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) and
[database restore](https://www.postgresql.org/docs/current/backup.html).

Publishing, outreach, advertising spend, production operations and security testing
retain the original task authorization boundaries. No catalog entry grants new
permissions or claims that an advisory plan executed external actions.
