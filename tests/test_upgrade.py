"""Behavioral acceptance for routing, observed credits and incremental retrieval."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from test_learning import verification

from erol.chat import ChatEngine
from erol.common import ErolError, canonical
from erol.connections import Model, classify
from erol.console import command
from erol.identity import detect_project
from erol.learning import LearningEngine
from erol.orchestration import Orchestrator, routing_eval
from erol.providers import event
from erol.registry import Registry, Skill
from erol.retrieval import MemoryIndex
from erol.store import Store
from erol.verification import complete_observed_task


class Provider:
    reused = False
    acknowledge = True
    hook = None
    probes = 0

    def __init__(self, connection, root):
        self.connection, self.root = connection, root

    def capabilities(self):
        type(self).probes += 1
        return {"available": True}

    def models(self):
        return self.connection.models

    def cancel(self):
        pass

    def stream(self, request, **options):
        if request.role == "implementer":
            (self.root / "answer.txt").write_text("fixed", "utf-8")
            text = canonical(
                {"summary": "Fixture repair", "strategy": "fixture", "status": "implemented"}
            )
        elif request.role == "reviewer":
            if type(self).hook:
                type(self).hook()
            text = canonical({"approved": True, "findings": [], "summary": "Fixture review"})
        else:
            text = "Fixture plan"
        yield event("text_delta", request, text=text)
        yield event(
            "final",
            request,
            completed=True,
            native_session=("fixture-shared" if type(self).reused else "fixture-" + request.role)
            if type(self).acknowledge
            else None,
        )


class UpgradeTests(unittest.TestCase):
    def engine(self, temporary, provider=Provider):
        root, home = Path(temporary) / "project", Path(temporary) / "home"
        root.mkdir()
        (root / "answer.txt").write_text("broken", "utf-8")
        engine = ChatEngine(root, home, factory=provider)
        engine.connections.connect("codex")
        engine.connections.settings.connections[0].models = [Model("fixture", level=3)]
        checks = {
            "schema_version": 1,
            "checks": [
                {
                    "name": "behavior",
                    "kind": "acceptance",
                    "timeout_seconds": 10,
                    "argv": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; assert Path('answer.txt').read_text()=='fixed'",
                    ],
                }
            ],
        }
        path = Path(temporary) / "checks.json"
        path.write_text(canonical(checks), "utf-8")
        engine.connections.settings.checks_path = str(path)
        engine.check_trust.approve(checks)
        engine.connections.save()
        skill = Skill(
            "fixture-repair",
            "Synthetic local test skill",
            ["fixture repair"],
            ["unrelated fixture"],
            "# Workflow\n1. Inspect the current fixture and reproduce its failure.\n"
            "2. Repair the observed behavior.\n"
            "3. Verify acceptance tests and independent review before recording use.\n",
            scope="project",
            project_id=engine.project.id,
        )
        with Store(home, engine.project) as store:
            learning = LearningEngine(store)
            candidate = learning.create_skill(skill.to_dict())
            learning.evaluate(
                candidate["id"],
                {
                    "positive_tasks": ["fixture repair"],
                    "negative_tasks": ["unrelated fixture"],
                    "behavior": verification("fixture:skill-qualification"),
                },
            )
            learning.activate(candidate["id"])
        return engine

    def test_fifty_new_acceptance_cases_and_old_pack(self):
        result = routing_eval()
        self.assertEqual(50, sum(c.get("upgrade_acceptance", False) for c in result["cases"]))
        self.assertEqual(339, result["total"])
        self.assertTrue(result["passed"], [c for c in result["cases"] if not c["passed"]])

    def test_negated_operation_is_not_risky_or_routed(self):
        task = "Deploy yapma, sadece yazım hatasını düzelt"
        self.assertEqual([], Registry().route(task))
        self.assertEqual("small", classify(task)["complexity"])
        self.assertEqual("medium", classify("Do not deploy; inspect this project")["complexity"])
        self.assertTrue(Registry().route("Do not duplicate messages: RabbitMQ idempotency"))

    def test_followup_inherits_only_bounded_task_and_explicit_request_resets(self):
        orchestrator = Orchestrator()
        followup = orchestrator.plan(
            "ve daha iyi çalışmasını nasıl sağlarım", previous_task="Bu uygulamayı incele"
        )
        self.assertTrue(followup["routing_diagnostics"]["context_inherited"])
        self.assertIn("repository-exploration", followup["context"]["selected_skills"])
        replacement = orchestrator.plan(
            "API contract tasarla", previous_task="Bu uygulamayı incele"
        )
        self.assertFalse(replacement["routing_diagnostics"]["context_inherited"])
        self.assertNotIn("repository-exploration", replacement["context"]["selected_skills"])
        self.assertFalse(orchestrator.plan("Selam", previous_task="security review")["skills"])

    def test_explicit_selection_rejects_duplicates_missing_and_budget_omission(self):
        orchestrator = Orchestrator()
        self.assertEqual(
            ["stable-pagination"],
            orchestrator.plan("inspect", skill_names=["stable-pagination"])["context"][
                "selected_skills"
            ],
        )
        with self.assertRaises(ValueError):
            orchestrator.plan("inspect", skill_names=["stable-pagination"] * 2)
        with self.assertRaises(KeyError):
            orchestrator.plan("inspect", skill_names=["disabled-foreign"])
        omitted = orchestrator.plan("inspect", skill_names=["stable-pagination"], token_budget=120)
        self.assertEqual([], omitted["context"]["selected_skills"])
        self.assertTrue(omitted["context"]["omitted"])

    def test_chat_credits_only_observed_admitted_revision_and_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = self.engine(temporary)
            command(engine, "/skills use fixture-repair")
            record = engine.execute("fixture repair")
            self.assertEqual("completed", record["status"], record)
            self.assertEqual(1, len(record["skill_uses"]))
            with Store(engine.home, engine.project) as store:
                from erol.config import Config
                from erol.learning import LearningEngine

                learning = LearningEngine(store, Config(), Registry(project_store=store))
                report = store.get("tasks", record["task_id"])["verification"]
                self.assertEqual([], complete_observed_task(learning, record["task_id"], report))
                self.assertEqual(1, len(store.list("uses")))
            command(engine, "/skills auto")
            engine.new()
            self.assertEqual("", engine.previous_task)

    def test_reused_or_missing_native_ack_cannot_credit(self):
        for settings in ({"reused": True}, {"acknowledge": False}):
            provider = type("InvalidSession", (Provider,), settings)
            with self.subTest(settings=settings), tempfile.TemporaryDirectory() as temporary:
                engine = self.engine(temporary, provider)
                record = engine.execute("fixture repair")
                self.assertEqual("needs_attention", record["status"], record)
                with Store(engine.home, engine.project) as store:
                    self.assertEqual([], store.list("uses"))

    def test_changed_checks_or_learned_revision_during_review_cannot_credit(self):
        for target in ("checks", "skill"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as temporary:
                provider = type("ChangedEvidence", (Provider,), {})
                engine = self.engine(temporary, provider)

                def change(target=target, engine=engine):
                    if target == "checks":
                        Path(engine.connections.settings.checks_path).write_text("{}", "utf-8")
                    else:
                        with Store(engine.home, engine.project) as store:
                            record = store.get("skills", "fixture-repair")
                            record["body"] += "Changed revision."
                            store.put("skills", record, replace=True)

                provider.hook = staticmethod(change)
                record = engine.execute("fixture repair")
                self.assertEqual("needs_attention", record["status"], record)
                with Store(engine.home, engine.project) as store:
                    self.assertEqual([], store.list("uses"))

    def test_incremental_index_reopen_stale_and_legacy_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            with Store(Path(temporary) / "home", detect_project(root)) as store:
                store.put(
                    "learnings", {"id": "one", "text": "pagination", "evidence": ["synthetic"]}
                )
                index = MemoryIndex(store)
                self.assertEqual("full", index.sync()["sync_mode"])
                self.assertEqual(0, index.sync()["records_examined"])
                store.db.execute(
                    "UPDATE records SET payload=? WHERE kind=? AND id=?",
                    (canonical({"id": "one", "text": "security"}), "learnings", "one"),
                )
                self.assertEqual(1, index.sync()["records_examined"])
                self.assertEqual([], index.search("pagination"))
                self.assertEqual(1, len(index.search("security")))
                index.close()
                index = MemoryIndex(store)
                self.assertEqual(0, index.sync()["records_examined"])
                store.mark_stale("learnings", "one")
                self.assertEqual([], index.search("security"))
                index.close()

    def test_provider_cache_invalidates_configuration_and_refresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            provider = type("Counted", (Provider,), {"probes": 0})
            engine = self.engine(temporary, provider)
            engine.providers()
            engine.providers()
            self.assertEqual(1, provider.probes)
            engine.connections.settings.connections[0].models.append(Model("second", level=3))
            engine.providers()
            self.assertEqual(2, provider.probes)
            engine.providers(refresh=True)
            self.assertEqual(3, provider.probes)

    def test_negation_stops_at_sentences_and_contrast_but_shares_bare_operations(self):
        from erol.router import intent_clauses

        for text, expected in (
            ("Do not deploy. Refactor pagination", "Refactor pagination"),
            ("Do not deploy but migrate the database", "migrate the database"),
            ("deploy ve migration yapma; yazim hatasini duzelt", "yazim hatasini duzelt"),
            ("Do not deploy and fix pagination", "fix pagination"),
        ):
            active, _ = intent_clauses(text)
            self.assertEqual(expected, active.strip())

    def test_index_never_commits_a_cursor_from_a_rolled_back_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            with Store(Path(temporary) / "home", detect_project(root)) as store:
                with closing(MemoryIndex(store)) as index:
                    index.sync()
                    with self.assertRaisesRegex(ErolError, "transaction commits"):
                        with store.transaction():
                            store.put("learnings", {"id": "rolled-back", "text": "alpha database"})
                            index.sync()
                    store.put("learnings", {"id": "committed", "text": "beta database"})
                    self.assertEqual(["committed"], [r["id"] for r in index.search("beta")])
                    self.assertEqual([], index.search("alpha"))

    def test_report_tools_are_external_discoverable_and_reviewer_cannot_write(self):
        from erol.artifacts import checked_directory, external_directory
        from erol.workspace import Workspace

        with tempfile.TemporaryDirectory() as temporary:
            root, home = Path(temporary) / "project", Path(temporary) / "home"
            root.mkdir()
            directory = external_directory(home, "project-id", "task-id")
            worker = Workspace(root, report_directory=directory)
            report = str(directory / "inspection.md")
            worker.dispatch(
                "write_file",
                {"path": report, "content": "verified fixture", "expected_sha256": None},
            )
            review = Workspace(root, report_directory=directory, readonly=True)
            self.assertIn(report, json.loads(review.dispatch("list_files", {}))["files"])
            self.assertIn("verified fixture", review.dispatch("read_file", {"path": report}))
            self.assertIn("inspection.md", review.dispatch("search", {"query": "verified"}))
            with self.assertRaises(ErolError):
                review.dispatch(
                    "write_file", {"path": report, "content": "changed", "expected_sha256": None}
                )
            for name in (str(home / "state/db.json"), str(directory / "../foreign.md")):
                with self.assertRaises(ErolError):
                    worker.path(name)
            with self.assertRaises(ErolError):
                checked_directory(root, str(home / "reports/../state"), home=home)
            self.assertEqual([], list(root.rglob("*.md")))

    def test_external_report_mutation_cannot_credit_a_reviewed_task(self):
        class ReportProvider(Provider):
            def stream(self, request, **options):
                directory = Path(request.report_directory)
                if request.role == "implementer":
                    (directory / "inspection.md").write_text("reviewed", encoding="utf-8")
                elif request.role == "reviewer":
                    (directory / "inspection.md").write_text("changed", encoding="utf-8")
                yield from super().stream(request, **options)

        with tempfile.TemporaryDirectory() as temporary:
            engine = self.engine(temporary, ReportProvider)
            record = engine.execute("fixture repair")
            self.assertEqual("needs_attention", record["status"])
            self.assertIn("review changed", record["error"])
            with Store(engine.home, engine.project) as store:
                self.assertEqual([], store.list("uses"))
            self.assertEqual([], list(engine.root.rglob("*.md")))

    def test_planner_context_and_escalation_floor_are_used_before_worker_selection(self):
        class LongPlanner(Provider):
            def stream(self, request, **options):
                if request.role == "planner":
                    yield event("text_delta", request, text="x" * 12000)
                    yield event("final", request, completed=True, native_session="planner-long")
                else:
                    for item in super().stream(request, **options):
                        if item["type"] == "final":
                            item["data"]["native_session"] += request.model.id
                        yield item

        with tempfile.TemporaryDirectory() as temporary:
            engine = self.engine(temporary, LongPlanner)
            plan = engine.plan("architecture fixture repair")
            narrow = (
                engine._context_size("architecture fixture repair", plan, "implementer")
                + 4096
                + 2000
            )
            engine.connections.settings.connections[0].models = [
                Model("narrow", level=3, context_window=narrow, latency_rank=1),
                Model("wide", level=3),
            ]
            record = engine.execute("architecture fixture repair")
            self.assertEqual("wide", record["attempts"][0]["model"].split(":")[1], record)

        class Blocked(Provider):
            def stream(self, request, **options):
                if request.role == "implementer":
                    yield event(
                        "text_delta",
                        request,
                        text=canonical(
                            {
                                "summary": "fixture blocked",
                                "strategy": "fixture",
                                "status": "needs_attention",
                            }
                        ),
                    )
                    yield event("final", request, completed=True, native_session="blocked-worker")
                else:
                    yield from super().stream(request, **options)

        with tempfile.TemporaryDirectory() as temporary:
            engine = self.engine(temporary, Blocked)
            engine.connections.settings.connections[0].models = [
                Model("a", level=2, latency_rank=1),
                Model("b", level=2),
                Model("c", level=3, latency_rank=3),
            ]
            record = engine.execute("fixture repair")
            self.assertEqual(
                ["codex:a:implementer", "codex:a:implementer", "codex:c:implementer"],
                [a["model"] for a in record["attempts"]],
            )

    def test_onboarding_preview_and_explicit_check_trust_and_panel_chat(self):
        from erol.checktrust import CheckTrust
        from erol.onboarding import onboard
        from erol.panel import panel_state

        with tempfile.TemporaryDirectory() as temporary:
            root, home = Path(temporary) / "root", Path(temporary) / "home"
            root.mkdir()
            checks = {
                "schema_version": 1,
                "checks": [
                    {
                        "name": "acceptance",
                        "kind": "acceptance",
                        "argv": [sys.executable, "-c", "assert True"],
                        "timeout_seconds": 10,
                    }
                ],
            }
            path = Path(temporary) / "checks.json"
            path.write_text(canonical(checks), encoding="utf-8")
            preview = onboard(root, home, budget=2, checks=str(path))
            self.assertFalse(preview["checks_authorized"])
            self.assertFalse(home.exists())
            with self.assertRaises(ErolError):
                onboard(root, home, checks=str(path), trust_checks=True)
            saved = onboard(root, home, checks=str(path), apply=True, trust_checks=True)
            self.assertTrue(saved["checks_authorized"])
            with Store(home, detect_project(root)) as store:
                CheckTrust(store.directory, root).require(checks)
        with tempfile.TemporaryDirectory() as temporary:
            engine = self.engine(temporary)
            record = engine.execute("fixture repair")
            with Store(engine.home, engine.project) as store:
                state = panel_state(store.directory, engine.project.id)
                self.assertEqual(record["id"], state["chats"][0]["id"])
                self.assertTrue(state["chats"][0]["verification"]["verified"])
                self.assertNotIn('"task":', canonical(state))
                self.assertIn('"phase_timings"', canonical(state))

    def test_six_fixture_suite_has_five_reproduced_bugs_and_regression_baselines(self):
        import subprocess

        from erol.benchmark import load_suite

        suite = load_suite(
            Path(__file__).resolve().parents[1] / "examples/upgrade-behavior-suite.json"
        )
        self.assertEqual(6, len(suite["cases"]))
        for case in suite["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for name, content in case["files"].items():
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
                codes = [
                    subprocess.run(
                        [sys.executable, *check["argv"][1:]], cwd=root, capture_output=True
                    ).returncode
                    for check in case["checks"]["checks"]
                ]
                self.assertEqual(0, codes[1])
                self.assertEqual(case["mode"] == "research", codes[0] == 0)

    def test_role_model_and_effort_comparison_uses_eligible_profiles(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = self.engine(temporary)
            comparison = command(
                engine, "/models compare Deploy yapma, sadece yazım hatasını düzelt"
            )
            choices = comparison["model_comparison"]
            self.assertEqual("low", choices[0]["effort"])
            self.assertEqual("high", choices[1]["effort"])
            self.assertIsNone(choices[0]["behavioral_success_rate"])
            self.assertTrue(choices[0]["eligible_alternatives"])
            self.assertFalse(choices[0]["assessment"]["risk"])
            self.assertEqual([], engine.record.get("attempts", []))

    def test_native_plans_choose_supported_pairs_preserve_manual_and_inherit_unknown(self):
        from erol.delegation import recommend_agents

        with tempfile.TemporaryDirectory() as temporary:
            root, home = Path(temporary) / "root", Path(temporary) / "home"
            root.mkdir()
            plan = Orchestrator().plan("Deploy yapma, sadece yazım hatasını düzelt")
            automatic = recommend_agents(plan, home, root, harness="codex")
            choice = automatic["agents"][0]["model_selection"]
            self.assertEqual("low", choice["effort"])
            self.assertFalse(choice["assessment"]["risk"])
            self.assertFalse(choice["model_access_verified"])
            self.assertEqual(choice["model"], choice["binding"]["model"])
            manual = recommend_agents(
                plan, home, root, harness="codex", model="gpt-6-astra", effort="high"
            )
            self.assertEqual("gpt-6-astra", manual["agents"][0]["model_selection"]["model"])
            self.assertEqual("high", manual["agents"][0]["model_selection"]["effort"])
            with self.assertRaises(ErolError):
                recommend_agents(plan, home, root, harness="codex", model="not-configured")
            claude = recommend_agents(plan, home, root, harness="claude")
            self.assertNotIn("effort", claude["agents"][0]["model_selection"]["binding"])
            high = recommend_agents(plan, home, root, harness="claude", effort="high")
            self.assertEqual("high", high["agents"][0]["model_selection"]["binding"]["effort"])
            with patch.dict("os.environ", {}, clear=True):
                unknown = recommend_agents(plan, home, root)
                self.assertEqual("inherit", unknown["agents"][0]["model_selection"]["status"])
                self.assertIsNone(unknown["agents"][0]["model_selection"]["binding"])
            with patch.dict("os.environ", {"CODEX_THREAD_ID": "host-id"}, clear=True):
                self.assertEqual(
                    "codex", recommend_agents(plan, home, root)["agent_selection_policy"]["harness"]
                )
            self.assertFalse(home.exists())

    def test_onboarding_wizard_binds_preview_and_clears_explicit_automatic(self):
        from erol.connections import ConnectionStore
        from erol.onboarding import onboard, wizard

        with tempfile.TemporaryDirectory() as temporary:
            root, home = Path(temporary) / "root", Path(temporary) / "home"
            root.mkdir()
            settings = ConnectionStore(home, root)
            settings.connect("codex")
            onboard(root, home, connection="codex", apply=True)
            onboard(root, home, apply=True)
            self.assertEqual("codex", ConnectionStore(home, root).settings.preferred_connection)
            answers = iter(["", "", "", "", "YES"])
            wizard(root, home, read=lambda _: next(answers), write=lambda _: None)
            self.assertIsNone(ConnectionStore(home, root).settings.preferred_connection)
            manifest = {
                "schema_version": 1,
                "checks": [
                    {
                        "name": "acceptance",
                        "kind": "acceptance",
                        "argv": [sys.executable, "-c", "assert True"],
                        "timeout_seconds": 10,
                    }
                ],
            }
            path = Path(temporary) / "checks.json"
            path.write_text(canonical(manifest), encoding="utf-8")
            answers = iter(["", "", "", str(path), "YES"])

            def read(prompt):
                if prompt.startswith("Save settings"):
                    manifest["checks"][0]["argv"][-1] = "raise Exception('never shown')"
                    path.write_text(canonical(manifest), encoding="utf-8")
                return next(answers)

            with self.assertRaisesRegex(ErolError, "changed after preview"):
                wizard(root, home, read=read, write=lambda _: None)
            self.assertIsNone(ConnectionStore(home, root).settings.checks_path)

    def test_doctor_separates_executable_presence_from_connection_access(self):
        from erol.health import health

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            with Store(Path(temporary) / "home", detect_project(root)) as store:
                with (
                    patch("erol.health.command_prefix", return_value=["native-cli"]),
                    patch(
                        "erol.health.ConnectionContext.providers",
                        return_value=([{"available": False, "reason": "login required"}], {}),
                    ),
                ):
                    result = health(store, {"passed": True})
                self.assertTrue(result["executables"]["codex"]["found"])
                self.assertFalse(result["executables"]["codex"]["model_access_verified"])
                self.assertFalse(result["connections"][0]["available"])
                self.assertFalse(result["validation"]["authorized"])

    def test_selected_skill_count_alone_cannot_escalate_a_simple_task(self):
        from erol.connections import Connection, Settings, route

        settings = Settings(
            connections=[Connection("codex", "codex", models=[Model("small", level=1)])]
        )
        plan = {"context": {"selected_skills": ["one", "two", "three"]}}
        choice = route(
            settings, "Correct typo", {"codex": settings.connections[0].models}, plan=plan
        )
        self.assertEqual("small", choice["model"])
        self.assertEqual("small", choice["assessment"]["complexity"])

    def test_general_followup_keeps_risk_in_model_and_effort_selection(self):
        from erol.general import GeneralEngine

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            engine = GeneralEngine(root, Path(temporary) / "home", factory=Provider)
            engine.connections.connect("codex")
            engine.connections.get("codex").models = [
                Model("medium", level=2),
                Model("large", level=3),
            ]
            engine.previous_task = "Investigate security authorization vulnerability"
            followup = engine.plan("make it better")
            self.assertTrue(followup["routing_diagnostics"]["context_inherited"])
            self.assertTrue(followup["selection"]["assessment"]["risk"])
            self.assertEqual("large", followup["selection"]["model"])
            self.assertEqual("high", followup["selection"]["effort"])
