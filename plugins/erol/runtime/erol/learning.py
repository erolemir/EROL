"""Incident-to-skill lifecycle with revision-bound gates and controlled promotion."""

from __future__ import annotations

from difflib import SequenceMatcher

from erol.common import (
    ErolError,
    atomic_write,
    canonical,
    confidence,
    digest,
    identifier,
    now,
    reject_links,
    required_text,
)
from erol.config import Config
from erol.fingerprint import fingerprint, normalize_error
from erol.registry import Registry, Skill, evaluate_skill
from erol.security import assert_secret_safe, scan_instructions
from erol.store import Store
from erol.verification import verify_report


class LearningEngine:
    def __init__(
        self, store: Store, config: Config | None = None, registry: Registry | None = None
    ):
        self.store = store
        self.config = config or Config()
        self.registry = registry or Registry(project_store=store)

    def _enabled(self) -> None:
        if not self.config.learning_enabled:
            raise ErolError("Learning is disabled in configuration")

    def matches(self, error: str, component: str, exception: str = "") -> list[dict]:
        normalized = normalize_error(error)
        result = []
        for incident in self.store.list("incidents"):
            if incident["component"].casefold() != component.casefold():
                continue
            if incident.get("exception", "").casefold() != exception.casefold():
                continue
            score = SequenceMatcher(None, normalized, incident["normalized_error"]).ratio()
            if score >= 0.88:
                result.append(
                    {
                        "id": incident["id"],
                        "similarity": round(score, 4),
                        "solution": incident["solution"],
                        "evidence": incident["verification"],
                        "verify_against_current_code": True,
                    }
                )
        return sorted(result, key=lambda item: item["similarity"], reverse=True)[:5]

    def record_incident(self, data: dict) -> dict:
        self._enabled()
        assert_secret_safe(data)
        incident: dict = {
            key: required_text(data.get(key), key)
            for key in ("id", "task_id", "symptom", "error", "component", "root_cause", "solution")
        }
        identifier(incident["id"])
        identifier(incident["task_id"])
        incident.update(
            {
                "confidence": confidence(data.get("confidence", 0)),
                "verification": verify_report(data.get("verification")),
                "exception": data.get("exception", ""),
                "root_category": data.get("root_category", ""),
                "files": data.get("files", []),
                "regression_risk": data.get("regression_risk", "unknown"),
            }
        )
        for key in ("exception", "root_category", "regression_risk"):
            if not isinstance(incident[key], str) or len(incident[key]) > 1000:
                raise ErolError(f"Invalid {key}")
        if not isinstance(incident["files"], list) or any(
            not isinstance(f, str) for f in incident["files"]
        ):
            raise ErolError("Files must be a list of path references")
        incident["normalized_error"] = normalize_error(incident["error"])
        if not incident["normalized_error"]:
            raise ErolError("Error contains no stable fingerprint signals")
        incident["fingerprint"] = fingerprint(
            incident["error"],
            incident["component"],
            incident["exception"],
            incident["root_category"],
        )
        incident["project_id"] = self.store.project_id
        incident["id"] = identifier(incident["id"])
        # Family equality cannot justify a shared remedy. Conflicting causes stay separate.
        pattern_id = (
            "pattern-"
            + digest(
                {
                    "family": incident["fingerprint"],
                    "cause": normalize_error(incident["root_cause"]),
                    "solution": normalize_error(incident["solution"]),
                }
            )[:20]
        )
        with self.store.transaction():
            prior = self.store.get("incidents", incident["id"], include_stale=True)
            if prior:
                if {k: v for k, v in prior.items() if k != "date"} != incident:
                    raise ErolError("Incident ID reused with different evidence")
                return {
                    "incident": prior,
                    "replayed": True,
                    "repeat_matches": [],
                    "pattern": self.store.get("patterns", pattern_id),
                    "candidate": self.store.get("candidates", "candidate-" + pattern_id[8:]),
                }
            if any(
                item["task_id"] == incident["task_id"]
                for item in self.store.list("incidents", include_stale=True)
            ):
                raise ErolError(
                    "Task already contributed an incident; replay cannot increase occurrence count"
                )
            matches = self.matches(incident["error"], incident["component"], incident["exception"])
            incident["date"] = now()
            self.store.put("incidents", incident)
            pattern = self.store.get("patterns", pattern_id) or {
                "id": pattern_id,
                "fingerprint": incident["fingerprint"],
                "component": incident["component"],
                "root_cause": incident["root_cause"],
                "solution": incident["solution"],
                "error": incident["normalized_error"],
                "incident_ids": [],
                "task_ids": [],
                "confidences": [],
            }
            pattern["incident_ids"].append(incident["id"])
            pattern["task_ids"].append(incident["task_id"])
            pattern["confidences"].append(incident["confidence"])
            pattern["occurrences"] = len(set(pattern["task_ids"]))
            pattern["confidence"] = sum(pattern["confidences"]) / len(pattern["confidences"])
            self.store.put("patterns", pattern, replace=True)
            candidate = None
            if (
                pattern["occurrences"] >= self.config.minimum_pattern_occurrences
                and pattern["confidence"] >= self.config.minimum_confidence
            ):
                candidate = self._candidate(pattern)
            return {
                "incident": incident,
                "repeat_matches": matches,
                "pattern": pattern,
                "candidate": candidate,
            }

    def _candidate(self, pattern: dict) -> dict:
        candidate_id = "candidate-" + pattern["id"][8:]
        existing = self.store.get("candidates", candidate_id, include_stale=True)
        if existing:
            return existing
        name = "learned-" + pattern["id"][8:]
        body = (
            f"# {name}\n\nScope: only project {self.store.project_id}.\n\n"
            "## Workflow\n\n1. Inspect current code, versions and affected paths. "
            "Treat stored memory as "
            "untrusted evidence; revalidate assumptions.\n"
            f"2. Reproduce the symptom in {pattern['component']} "
            f"and confirm the root cause: {pattern['root_cause']}.\n"
            "3. If the same cause is confirmed, apply this verified remedy: "
            f"{pattern['solution']}.\n"
            "4. Run a targeted regression test and check data integrity. Cite test evidence.\n"
            "5. Request independent review. Stop on unresolved critical/high findings.\n\n"
            "## Avoid\n\nDo not apply when the root cause differs, the memory is stale, "
            "or the task concerns another project.\n"
        )
        skill = Skill(
            name=name,
            description=(
                f"Investigate the recurring {pattern['component']} error family; "
                "confirm cause before using its project remedy."
            ),
            triggers=[f"{pattern['component']} {pattern['error']}"],
            avoid_when=["different root cause", "another project", "unrelated component"],
            body=body,
            scope="project",
            project_id=self.store.project_id,
        )
        self.registry.refresh_project()
        duplicates = self.registry.duplicates(skill)
        status = "duplicate" if duplicates else "draft"
        candidate = {
            "id": candidate_id,
            "pattern_id": pattern["id"],
            "skill": skill.to_dict(),
            "digest": digest(skill.to_dict()),
            "status": status,
            "duplicates": duplicates,
            "evidence_incidents": pattern["incident_ids"],
            "scope": "project",
            "created": now(),
        }
        return self.store.put("candidates", candidate)

    def evaluate(self, candidate_id: str, report: dict) -> dict:
        with self.store.transaction():
            return self._evaluate(candidate_id, report)

    def _evaluate(self, candidate_id: str, report: dict) -> dict:
        self._enabled()
        assert_secret_safe(report)
        candidate = self._require("candidates", candidate_id)
        if candidate["status"] not in {"draft", "eval_failed", "evaluated"}:
            raise ErolError("Only a draft candidate can be evaluated")
        skill = Skill.from_dict(candidate["skill"])
        if digest(skill.to_dict()) != candidate["digest"]:
            raise ErolError("Candidate content changed; create a new revision")
        positives, negatives = report.get("positive_tasks"), report.get("negative_tasks")
        if not isinstance(positives, list) or not isinstance(negatives, list):
            raise ErolError("Both positive and negative trigger fixtures must be lists")
        for fixtures in (positives, negatives):
            if not isinstance(fixtures, list) or not fixtures:
                raise ErolError("Both positive and negative trigger fixtures are required")
            for task in fixtures:
                required_text(task, "trigger fixture", 4000)
        if set(positives) & set(negatives):
            raise ErolError("Conflicting trigger fixtures")
        behavior = verify_report(report.get("behavior"))
        cases = [{"task": task, "should_trigger": True} for task in positives] + [
            {"task": task, "should_trigger": False} for task in negatives
        ]
        lint = evaluate_skill(skill, cases)
        security = scan_instructions(canonical(skill.to_dict())) + scan_instructions(skill.body)
        checks = {
            "static_trigger_workflow": lint["passed"],
            "security_scan": not security,
            "context_budget": len(skill.body) <= self.config.max_skill_chars,
            "behavior_evidence_reviewed": True,
        }
        result = {
            "id": "eval-" + candidate["digest"],
            "candidate_id": candidate_id,
            "digest": candidate["digest"],
            "passed": all(checks.values()),
            "checks": checks,
            "static": lint,
            "security_findings": security,
            "behavior": behavior,
            "positive_tasks": positives,
            "negative_tasks": negatives,
            "date": now(),
            "behavior_execution": (
                "external evidence attestation; EROL does not execute candidate code"
            ),
        }
        with self.store.transaction():
            self.store.put("evals", result, replace=True)
            candidate["status"] = "evaluated" if result["passed"] else "eval_failed"
            candidate["eval_id"] = result["id"]
            self.store.put("candidates", candidate, replace=True)
        return result

    def activate(self, candidate_id: str) -> dict:
        self._enabled()
        if not self.config.project_skill_activation:
            raise ErolError("Project skill activation is disabled")
        with self.store.transaction():
            candidate = self._require("candidates", candidate_id)
            if candidate["status"] == "project_active":
                active_record = self._require("skills", candidate["skill"]["name"])
                if (
                    active_record["status"] != "project_active"
                    or active_record["digest"] != candidate["digest"]
                ):
                    raise ErolError(
                        "Candidate revision is disabled or superseded; use revision/rollback"
                    )
                self._valid_eval(
                    Skill.from_dict(active_record), self._require("evals", active_record["eval_id"])
                )
                return active_record
            if candidate["status"] != "evaluated":
                raise ErolError("Candidate must pass evaluation before activation")
            skill = Skill.from_dict(candidate["skill"])
            evaluation = self._require("evals", candidate["eval_id"])
            self._valid_eval(skill, evaluation)
            self.registry.refresh_project()
            current = self.store.get("skills", skill.name)
            duplicates = [
                item for item in self.registry.duplicates(skill) if item["name"] != skill.name
            ]
            if duplicates:
                raise ErolError("An active skill already covers this candidate")
            record = {
                **skill.to_dict(),
                "id": skill.name,
                "status": "project_active",
                "digest": digest(skill.to_dict()),
                "eval_id": evaluation["id"],
                "candidate_id": candidate_id,
                "activated": now(),
            }
            revision_id = skill.name + "." + skill.version
            prior_revision = self.store.get("skill_revisions", revision_id)
            if prior_revision and prior_revision["digest"] != record["digest"]:
                raise ErolError("Version already exists; increment the revision version")
            self.store.put("skill_revisions", {**record, "id": revision_id})
            self.store.put("skills", record, replace=bool(current))
            candidate["status"] = "project_active"
            self.store.put("candidates", candidate, replace=True)
        self.registry.refresh_project()
        return record

    def _valid_eval(self, skill: Skill, evaluation: dict) -> None:
        if evaluation.get("passed") is not True or evaluation.get("digest") != digest(
            skill.to_dict()
        ):
            raise ErolError("Evaluation does not qualify the current skill revision")
        if scan_instructions(skill.body):
            raise ErolError("Current skill fails the security scan")

    def begin_task(self, task_id: str, task: str) -> dict:
        from erol.orchestration import Orchestrator

        identifier(task_id)
        required_text(task, "task")
        assert_secret_safe(task)
        self.registry.refresh_project()
        plan = Orchestrator(self.registry).plan(
            task,
            memory=self.store.search(task),
            token_budget=self.config.context_tokens,
            max_skills=self.config.max_active_skills,
        )
        admitted = set(plan["context"]["selected_skills"])
        selected = [
            {"name": s.name, "version": s.version, "digest": digest(s.to_dict())}
            for s in self.registry.route(task, self.config.max_active_skills)
            if s.scope == "project" and s.name in admitted
        ]
        record = {
            "id": task_id,
            "task": task,
            "status": "started",
            "selected_skills": selected,
            "date": now(),
        }
        with self.store.transaction():
            if self.store.get("tasks", task_id, include_stale=True):
                raise ErolError("Task ID already used; choose a distinct execution ID")
            self.store.put("tasks", record)
        return {"task_id": task_id, "plan": plan, "selected_skills": selected}

    def complete_task(
        self, task_id: str, verification: dict, false_triggers: list[str] | None = None
    ) -> dict:
        verification = verify_report(verification)
        false_triggers = false_triggers or []
        if not isinstance(false_triggers, list) or any(
            not isinstance(n, str) for n in false_triggers
        ):
            raise ErolError("False triggers must be a list of selected skill names")
        with self.store.transaction():
            task = self._require("tasks", task_id)
            if task["status"] != "started":
                raise ErolError("Task is already completed; replay cannot increase usage counts")
            names = {selection["name"] for selection in task["selected_skills"]}
            if set(false_triggers) - names:
                raise ErolError("False trigger refers to a skill not selected for this task")
            uses = []
            for selection in task["selected_skills"]:
                current = self._require("skills", selection["name"])
                if (
                    current["digest"] != selection["digest"]
                    or current["status"] != "project_active"
                ):
                    raise ErolError("Selected revision is no longer active; start a new task")
                use = {
                    "id": "use-" + digest({"task": task_id, "skill": selection})[:24],
                    "task_id": task_id,
                    "project_id": self.store.project_id,
                    **selection,
                    "successful": selection["name"] not in false_triggers,
                    "false_trigger": selection["name"] in false_triggers,
                    "verification": verification,
                    "date": now(),
                }
                self.store.put("uses", use)
                uses.append(use)
                if use["false_trigger"]:
                    current["status"] = "needs_revision"
                    self.store.put("skills", current, replace=True)
            task.update({"status": "completed", "verification": verification})
            self.store.put("tasks", task, replace=True)
        self.registry.refresh_project()
        return {"task_id": task_id, "uses": uses}

    def failed_task(self, task_id: str, evidence: dict) -> dict:
        """Record a failed real use without claiming it passes the verification gate."""
        assert_secret_safe(evidence)
        reason = required_text(evidence.get("reason"), "failure reason")
        reference = required_text(evidence.get("reference"), "failure evidence reference")
        with self.store.transaction():
            task = self._require("tasks", task_id)
            if task["status"] != "started":
                raise ErolError("Task already completed")
            for selected in task["selected_skills"]:
                self.store.put(
                    "uses",
                    {
                        "id": "use-" + digest({"task": task_id, "skill": selected})[:24],
                        "task_id": task_id,
                        "project_id": self.store.project_id,
                        **selected,
                        "successful": False,
                        "false_trigger": False,
                        "failure": {"reason": reason, "reference": reference},
                        "date": now(),
                    },
                )
                current = self._require("skills", selected["name"])
                if current["digest"] == selected["digest"]:
                    current["status"] = "needs_revision"
                    self.store.put("skills", current, replace=True)
            task["status"] = "failed"
            self.store.put("tasks", task, replace=True)
        self.registry.refresh_project()
        return task

    def metrics(self, name: str) -> dict:
        current = self._require("skills", name)
        uses = [
            use
            for use in self.store.list("uses")
            if use["name"] == name and use["digest"] == current["digest"]
        ]
        successes = sum(use["successful"] for use in uses)
        false = sum(use["false_trigger"] for use in uses)
        return {
            "name": name,
            "version": current["version"],
            "digest": current["digest"],
            "activations": len(uses),
            "successful_tasks": successes,
            "failed_tasks": len(uses) - successes,
            "false_triggers": false,
            "success_rate": successes / len(uses) if uses else None,
            "false_trigger_rate": false / len(uses) if uses else None,
        }

    def promotion_candidate(self, name: str) -> dict:
        with self.store.transaction():
            return self._promotion_candidate(name)

    def _promotion_candidate(self, name: str) -> dict:
        self._enabled()
        current = self._require("skills", name)
        if current["status"] != "project_active":
            raise ErolError("Only an active qualified revision can become a promotion candidate")
        self._valid_eval(Skill.from_dict(current), self._require("evals", current["eval_id"]))
        metrics = self.metrics(name)
        if (
            metrics["successful_tasks"] < self.config.minimum_successful_uses
            or metrics["false_trigger_rate"] > self.config.maximum_false_trigger_rate
            or metrics["failed_tasks"] > 0
        ):
            raise ErolError("Revision lacks enough successful real use or has unresolved failures")
        candidate = {
            "id": "promotion-" + current["digest"][:24],
            "name": name,
            "digest": current["digest"],
            "status": "promotion_candidate",
            "scope": "global_candidate",
            "source_project_id": self.store.project_id,
            "metrics": metrics,
            "cross_project_evidence_required": True,
            "global_registry_modified": False,
        }
        existing = self.store.get("promotions", candidate["id"])
        if existing and existing["status"] == "approved_for_generalization":
            return existing
        self.store.put("promotions", candidate, replace=bool(existing))
        # Generalization needs evidence and an independently reviewed portable revision.
        return candidate

    def promote(
        self, candidate_id: str, *, approve: bool = False, cross_project_report: dict | None = None
    ) -> dict:
        with self.store.transaction():
            return self._promote(
                candidate_id, approve=approve, cross_project_report=cross_project_report
            )

    def _promote(
        self, candidate_id: str, *, approve: bool = False, cross_project_report: dict | None = None
    ) -> dict:
        """Global promotion requires a reviewed portable revision."""
        candidate = self._require("promotions", candidate_id)
        if not approve:
            raise ErolError("Global promotion requires explicit approval")
        if not isinstance(cross_project_report, dict):
            raise ErolError("Global promotion requires reviewed cross-project evidence")
        assert_secret_safe(cross_project_report)
        foreign_id = identifier(cross_project_report.get("project_id", ""))
        if foreign_id == self.store.project_id:
            raise ErolError("Generalization must be tested in a different project")
        verification = verify_report(cross_project_report.get("verification"))
        current = self._require("skills", candidate["name"])
        if current["digest"] != candidate["digest"] or current["status"] != "project_active":
            raise ErolError("Promotion refers to a superseded or disabled revision")
        self._promotion_candidate(candidate["name"])
        # A project remedy needs a separate generic revision. Export review material only.
        result = {
            **candidate,
            "status": "approved_for_generalization",
            "cross_project_id": foreign_id,
            "cross_project_verification": verification,
            "approval_date": now(),
            "global_registry_modified": False,
            "next": (
                "Create a portable global revision and independently evaluate it "
                "before global installation"
            ),
        }
        self.store.put("promotions", result, replace=True)
        return result

    def revise(self, name: str, skill_data: dict) -> dict:
        self._enabled()
        current = self._require("skills", name)
        revised = Skill.from_dict(skill_data)
        if (
            revised.name != name
            or revised.scope != "project"
            or revised.project_id != self.store.project_id
        ):
            raise ErolError("Revision must retain its project scope and skill name")
        if revised.version == current["version"]:
            raise ErolError("Revision must have a new version")
        static = evaluate_skill(revised)
        if not static["passed"] or scan_instructions(revised.body):
            raise ErolError("Revision fails static/security validation")
        candidate: dict = {
            "id": "revision-" + digest(revised.to_dict())[:24],
            "pattern_id": None,
            "skill": revised.to_dict(),
            "digest": digest(revised.to_dict()),
            "status": "draft",
            "duplicates": [],
            "evidence_incidents": [],
            "scope": "project",
            "created": now(),
        }
        return self.store.put("candidates", candidate)

    def rollback(self, name: str, version: str) -> dict:
        with self.store.transaction():
            return self._rollback(name, version)

    def _rollback(self, name: str, version: str) -> dict:
        self._enabled()
        if not self.config.project_skill_activation:
            raise ErolError("Project skill activation is disabled")
        revision = self._require("skill_revisions", identifier(name + "." + version))
        skill = Skill.from_dict(revision)
        self._valid_eval(skill, self._require("evals", revision["eval_id"]))
        failed = [
            use
            for use in self.store.list("uses")
            if use["name"] == name and use["digest"] == revision["digest"] and not use["successful"]
        ]
        if failed:
            raise ErolError("Rollback revision has unresolved real-use failures")
        record = {**revision, "id": name, "status": "project_active", "rolled_back": now()}
        self.store.put("skills", record, replace=True)
        self.registry.refresh_project()
        return record

    def disable(self, name: str) -> dict:
        current = self._require("skills", name)
        current["status"] = "disabled"
        self.store.put("skills", current, replace=True)
        self.registry.refresh_project()
        return current

    def record_failure(
        self, task_id: str, attempt_id: str, error: str, component: str, strategy: str
    ) -> dict:
        self._enabled()
        assert_secret_safe({"error": error, "component": component, "strategy": strategy})
        key = identifier(attempt_id)
        identifier(task_id)
        required_text(strategy, "strategy")
        record = {
            "id": key,
            "task_id": task_id,
            "fingerprint": fingerprint(error, component),
            "strategy": strategy,
            "error": normalize_error(error),
        }
        with self.store.transaction():
            self.store.put("failures", record)
            count = 0
            for prior in reversed(self.store.list("failures")):
                if prior["task_id"] != task_id:
                    continue
                if prior["fingerprint"] != record["fingerprint"] or prior["strategy"] != strategy:
                    break
                count += 1
        return {
            "consecutive_family_attempts": count,
            "escalate": count >= 3,
            "next": [
                "reset assumptions",
                "retrieve incidents",
                "change specialist",
                "use reasoning tier",
            ]
            if count >= 3
            else [],
        }

    def export_skill(self, name: str) -> dict:
        record = self._require("skills", name)
        if record["status"] != "project_active":
            raise ErolError("Only an active qualified skill can be exported")
        skill = Skill.from_dict(record)
        self._valid_eval(skill, self._require("evals", record["eval_id"]))
        directory = self.store.directory / "skills" / identifier(skill.version) / identifier(name)
        for path in (self.store.directory / "skills", directory.parent, directory):
            reject_links(path)
        frontmatter = (
            f"---\nname: {canonical(skill.name)}\n"
            f"description: {canonical(skill.description)}\n---\n\n"
        )
        atomic_write(directory / "SKILL.md", frontmatter + skill.body)
        atomic_write(directory / "erol.json", canonical(skill.to_dict()) + "\n")
        return {
            "path": str(directory / "SKILL.md"),
            "scope": "project",
            "canonical_source": "SQLite",
        }

    def create_skill(self, skill_data: dict) -> dict:
        """Explicit manual drafts use the same gates as learned candidates."""
        self._enabled()
        assert_secret_safe(skill_data)
        skill = Skill.from_dict(skill_data)
        if skill.scope != "project" or skill.project_id != self.store.project_id:
            raise ErolError("Manual draft must explicitly match the current project scope")
        if not evaluate_skill(skill)["passed"] or scan_instructions(skill.body):
            raise ErolError("Manual draft fails static/security validation")
        self.registry.refresh_project()
        duplicates = self.registry.duplicates(skill)
        if duplicates:
            raise ErolError("An existing skill already covers the proposed draft")
        candidate: dict = {
            "id": "manual-" + digest(skill.to_dict())[:24],
            "pattern_id": None,
            "skill": skill.to_dict(),
            "digest": digest(skill.to_dict()),
            "status": "draft",
            "duplicates": [],
            "evidence_incidents": [],
            "scope": "project",
            "created": now(),
        }
        return self.store.put("candidates", candidate)

    def _require(self, kind: str, key: str) -> dict:
        value = self.store.get(kind, identifier(key))
        if value is None:
            raise ErolError(f"{kind} record not found")
        return value
