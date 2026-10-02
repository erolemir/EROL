# Architecture

One canonical Python core supports both harnesses. There is no per-harness memory copy.

| Module | Responsibility |
|---|---|
| identity | Normalize remote safely, fall back to Git root/path, stable hashed ID |
| store | SQLite transactions, revision-preserving stale facts, bounded retrieval, Markdown views |
| security | Pre-write secret rejection and conservative generated-instruction checks |
| registry/router | Metadata discovery, integrity checks, explicit triggers and negative matches |
| orchestration | Bounded context, advisory specialist roles, conceptual model tiers |
| verification | Validate independent reviewer and evidence-linked passing check attestations |
| learning | Incident families, consistent remedies, drafts, eval, activation, uses, rollback, promotion candidates |
| adapters/installer | Small harness bridges, managed blocks, backups, conflicts, ownership |
| plugin | Generated native manifests and bundled canonical runtime snapshots |
| cli | JSON contracts; deterministic exit status and safe input errors |

Python provides built-in SQLite and a standard-library core. A dependency-free
Node launcher provides the local npx command and plugin entry point, probing for
Python 3.11+ and passing argv directly without a shell. The npm package and native
plugin include the core; neither reimplements it nor downloads Python packages.
An isolated direct Python entry supports hosts that deny Node child-process creation.
Plugin runtime files are generated from canonical sources and checked for drift.
The Python-only package remains available through `pip install -e .`. Nothing has
been published. Schemas and adapter outputs are versioned repository artifacts.

SQLite `BEGIN IMMEDIATE` serializes lifecycle transitions. Reports are bound to the
complete skill content including routing metadata, version and project identity.
Project records cannot shadow builtins or leak across projects. All public lifecycle
changes use dedicated gates; arbitrary lifecycle JSON writes are not exposed by the CLI.

Native Agent Skills format carries name/description frontmatter; EROL metadata is
kept in the canonical registry or SQLite and optional adjacent `erol.json`. Export
leaf directories match the skill name and are nested under a version directory.
Exports are snapshots; the bridge consults current SQLite status rather than automatically
installing every learned body into native discovery. A previously exported snapshot
must not be manually installed as an always-current workflow.

Repo-independent memory holds sanitized knowledge, not transcripts. Stale facts are
excluded from retrieval; contradiction writes retain prior revisions and replace
the current logical fact. Current code and user instructions remain authoritative.
Per-record write limits and class soft-budget reports limit surprises; compaction
marks exact duplicates stale without erasing incidents or decisions. It does not
perform semantic summarization or reduce total historical database size.

Plans are execution contracts, not execution claims. Independent role recommendations
do not establish a real review. Completion must include explicit externally produced
evidence. There is no unsupported model name or synthetic harness capability.
