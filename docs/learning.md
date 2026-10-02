# Evidence-gated project learning

1. A repaired incident needs a distinct task ID, normalized error, component, cause,
   remedy, confidence, passing check references and an independent reviewer.
2. Repeated family matching returns historical evidence with a current-code warning.
   HTTP/SQL codes retain meaning; request IDs and timestamps normalize. Same symptom
   with different causes or remedies forms separate patterns.
3. A consistent family observed in three independent reviewed tasks with average
   confidence >=0.8 creates a draft. Duplicate detection prevents workflow proliferation.
4. Qualification requires explicit positive AND negative trigger tasks, workflow lint,
   a context budget, secret/instruction scan, and independently reviewed behavior evidence.
   Every report binds the full skill digest. No arbitrary skill code executes.
5. Activation enters only the current project's registry. Export is an optional
   versioned snapshot with standard SKILL.md frontmatter; the bridge uses SQLite directly.
6. `plan --task-id` records precisely the project revisions admitted to context.
   `skill usage` accepts reviewed completion evidence once. Unadmitted or superseded
   revisions and reused IDs cannot earn success credit.
7. A failed use (`--failed`, reason/reference) or false trigger puts a revision in
   `needs_revision` and removes it from routing. `skill create` drafts a new revision;
   the new digest must independently pass eval before activation. `skill rollback`
   requires a previous passing revision with no recorded real-use failures.
8. At least three successful distinct real uses, no failures and a sufficiently low
   false-trigger rate produce a promotion candidate. Nothing is written globally.
9. `learning promote --approve --input` requires independent evidence from another
   project and current qualification. It records `approved_for_generalization`.
   A project remedy remains project-specific. Actual portable global revision creation,
   eval and installation are not implemented. `global_auto_promotion=true` is rejected
   explicitly instead of silently implying support.

Report format for successful usage:

```json
{
  "verification": {
    "implementer": "worker",
    "reviewer": "independent-reviewer",
    "tests": [{"name": "heldout-regression", "passed": true, "reference": "local-report@revision"}],
    "findings": []
  },
  "false_triggers": []
}
```

EROL validates the structure and consistency of local attestations, not the identity
of a reviewer or authenticity of references. The supported trust boundary is one
local user/harness writing reviewed reports. It is not a multi-user authorization
service or automatic proof that an LLM followed the workflow.

Config lives in `<home>/config.json`, with optional `<project>/.erol.json` overrides.
Schema version is 1. Defaults can be inspected with `erol status`. Learning,
project activation, recurrence thresholds and context caps are configurable.
