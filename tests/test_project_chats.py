"""External project catalog and saved chat navigation; no live provider calls."""

import copy
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import test_chat
import test_general

from erol.chat import ChatEngine, Sessions
from erol.common import ErolError
from erol.console import command
from erol.general import GeneralEngine
from erol.identity import detect_project
from erol.presentation import present
from erol.projects import ProjectCatalog, choose
from erol.store import Store


class ProjectChatTests(unittest.TestCase):
    def test_terminal_loop_selects_catalog_and_opens_saved_project_chat(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            home, project = base / "home", base / "workspace"
            project.mkdir()
            prior = ChatEngine(project, home)
            self.saved(prior)
            with patch("erol.console.read_choice", side_effect=["/my-projects 1", "/chats 1"]):
                result, output, engines = test_chat.StartupTests().start(
                    base, home, ["/my-projects", "/chats", "/chats show 1", "/exit"]
                )
            self.assertEqual(result, 0)
            engines.assert_called_once()
            self.assertEqual(engines.call_args.args[0], project)
            self.assertIn("Pagination fixed", output)
            self.assertIn("+fixed", output)

    def test_planning_blocks_new_resume_switch_and_parallel_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            started, release = threading.Event(), threading.Event()
            original = engine.plan
            results = []
            session_id = engine.session_id

            def blocked(task):
                started.set()
                self.assertTrue(release.wait(10))
                return original(task)

            with patch.object(engine, "plan", side_effect=blocked):
                worker = threading.Thread(target=lambda: results.append(engine.execute("Fix typo")))
                worker.start()
                try:
                    self.assertTrue(started.wait(5))
                    for action in (
                        engine.new,
                        lambda: engine.resume("session-other"),
                        lambda: command(engine, "/my-projects 1"),
                        lambda: command(engine, "/rename Racing"),
                        lambda: engine.execute("Second task"),
                    ):
                        with self.assertRaises(ErolError):
                            action()
                    self.assertEqual(engine.session_id, session_id)
                finally:
                    release.set()
                    worker.join(10)
                self.assertFalse(worker.is_alive())
            self.assertEqual(results[0]["id"], session_id)
            self.assertFalse(engine.busy)
            with patch.object(engine, "plan", side_effect=ErolError("Synthetic preflight failure")):
                with self.assertRaises(ErolError):
                    engine.execute("Fail preflight")
            self.assertFalse(engine.busy)
            self.assertNotEqual(engine.new(), session_id)

    def test_long_project_name_remains_selectable(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / ("a" * 129)
            root.mkdir()
            engine = ChatEngine(root, base / "home")
            rows = command(engine, "/my-projects")["projects"]
            self.assertEqual(rows[0]["name"], root.name)
            self.assertEqual(command(engine, "/my-projects 1")["select_project"], str(root))

    def test_empty_listing_does_not_create_home(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, home = Path(temporary), Path(temporary) / "home"
            engine = GeneralEngine(root, home)
            self.assertEqual(command(engine, "/my-projects"), {"projects": []})
            self.assertEqual(command(engine, "/chats")["sessions"], [])
            self.assertFalse(home.exists())

    def test_catalog_discovers_legacy_metadata_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root, home = base / "Türkçe proje", base / "home"
            root.mkdir()
            project = detect_project(root)
            with Store(home, project) as store:
                database = store.directory / "memory.db"
            before = database.read_bytes()
            catalog = ProjectCatalog(home)
            rows = catalog.list()
            self.assertEqual(rows[0]["root"], str(root))
            self.assertEqual(rows[0]["project_id"], project.id)
            self.assertTrue(rows[0]["available"])
            self.assertEqual(database.read_bytes(), before)
            self.assertFalse(catalog.path.exists())

    def test_project_selection_uses_displayed_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            engine = GeneralEngine(base, base / "home")
            first, second = base / "İlk proje", base / "second"
            first.mkdir()
            second.mkdir()
            command(engine, f'/my-projects add "{first}"')
            shown = command(engine, "/my-projects")["projects"]
            ProjectCatalog(engine.home).remember(detect_project(second))
            self.assertEqual(command(engine, "/my-projects 1")["select_project"], str(first))
            replacement = ChatEngine(first, engine.home)
            self.assertEqual(replacement.previous_task, "")
            self.assertEqual(replacement.previous_summary, "")
            self.assertFalse(replacement.record)
            self.assertEqual(choose(shown, shown[0]["id"])["root"], str(first))
            first.rmdir()
            with self.assertRaises(ErolError):
                command(engine, "/my-projects 1")

    def test_checkout_ids_distinguish_same_project_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            roots = [base / "first", base / "second"]
            catalog = ProjectCatalog(base / "home")
            for root in roots:
                root.mkdir()
                project = detect_project(root)
                catalog.remember(type(project)("shared-id", "same", str(root), project.source))
            rows = catalog.list()
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({r["id"] for r in rows}), 2)
            with self.assertRaisesRegex(ErolError, "ambiguous"):
                choose(rows, "same")

    def test_catalog_rejects_invalid_records_and_home_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            home = base / "home"
            catalog = ProjectCatalog(home)
            with self.assertRaises(ErolError):
                catalog.remember(detect_project(base))
            catalog.path.parent.mkdir(parents=True)
            catalog.path.write_text('{"schema_version":1,"projects":[{}]}', "utf-8")
            with self.assertRaisesRegex(ErolError, "Invalid project catalog"):
                catalog.list()

    def saved(self, engine, session_id="session-old", **values):
        record = {
            "schema_version": 1,
            "id": session_id,
            "project_id": engine.project.id if engine.project else None,
            "mode": "general",
            "task": "Fix the pagination API",
            "status": "implemented_unverified",
            "updated": "2026-10-06T10:00:00+00:00",
            "summary": "Pagination fixed; a check remains missing",
            "changes": [{"path": "api.py", "diff": "+fixed"}],
            "checks": [{"name": "acceptance", "passed": False, "exit_code": 1}],
            "verification": None,
            **values,
        }
        engine.sessions.save(record)
        return record

    def test_show_and_open_existing_evidence_without_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            engine = GeneralEngine(base, base / "home")
            old = self.saved(engine)
            rows = command(engine, "/chats")["sessions"]
            self.assertEqual(rows[0]["title"], old["task"])
            with patch.object(engine, "execute", side_effect=AssertionError("No model call")):
                detail = command(engine, "/chats show 1")
                text = present(detail, "en")
                self.assertIn("+fixed", text)
                self.assertIn("acceptance", text)
                self.assertIn("full message transcript", text)
                result = command(engine, "/chats 1")
                self.assertEqual(result["summary"], old["summary"])
                self.assertNotIn("continue_task", result)
                self.assertEqual(command(engine, "/chats continue 1")["continue_task"], old["task"])

    def test_rename_preserves_verification_and_survives_reopen(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            engine = GeneralEngine(base, base / "home")
            old = self.saved(engine, verification={"verified": False, "reasons": ["missing"]})
            command(engine, "/chats")
            command(engine, '/chats rename 1 "API kontrolü"')
            expected = copy.deepcopy(old)
            expected["title"] = "API kontrolü"
            self.assertEqual(engine.sessions.load(old["id"]), expected)
            other = GeneralEngine(base, engine.home)
            self.assertEqual(command(other, '/chats "API kontrolü"')["id"], old["id"])
            command(other, "/rename Yeni isim")
            self.assertEqual(other.sessions.load(old["id"])["title"], "Yeni isim")

    def test_rename_rejects_active_locked_and_unsafe_sessions(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            engine = GeneralEngine(base, base / "home")
            self.saved(engine, status="running", owner_pid=os.getpid())
            with self.assertRaises(ErolError):
                engine.sessions.rename("session-old", "Live")
            self.saved(engine, status="completed")
            with engine.sessions.lease("session-old"), self.assertRaises(ErolError):
                engine.sessions.rename("session-old", "Locked")
            for title in ("", "x" * 121, "line\nline", "bad\x1btitle"):
                with self.subTest(title=title), self.assertRaises(ErolError):
                    Sessions.title(title)
            with self.assertRaises(ErolError):
                engine.sessions.rename("../session-old", "Traversal")

    def test_chat_pagination_keeps_displayed_selection(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            engine = GeneralEngine(base, base / "home")
            for index in range(51):
                record = self.saved(engine, f"session-{index}", title=f"Task {index}")
                path = engine.sessions.directory / (record["id"] + ".json")
                os.utime(path, (1000 + index, 1000 + index))
            page = command(engine, "/chats page 2")["sessions"]
            self.assertEqual(len(page), 1)
            self.saved(engine, "session-new")
            self.assertEqual(command(engine, "/chats 1")["id"], page[0]["id"])
            for invalid in ("0", "-1", "bad"):
                with self.assertRaises(ErolError):
                    command(engine, "/chats page " + invalid)

    def test_saved_chats_are_scoped_to_project_and_general(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            first = test_chat.EngineTests().make(temporary)
            self.saved(first)
            second_root = base / "other"
            second_root.mkdir()
            second = ChatEngine(second_root, first.home)
            general = GeneralEngine(base, first.home)
            for engine in (second, general):
                self.assertEqual(command(engine, "/chats")["sessions"], [])
                with self.assertRaises(ErolError):
                    command(engine, "/chats session-old")

    def test_project_execution_keeps_title_across_followup(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            command(engine, "/rename Hata çözümü")
            first = engine.execute("Small fix: typo")
            self.assertEqual(first["title"], "Hata çözümü")
            engine.sessions.rename(engine.session_id, "Externally renamed")
            result = engine.execute("Fix another typo", resume=True)
            self.assertEqual(result["title"], "Externally renamed")
            self.assertEqual(result["owner_pid"], None)
            engine.new()
            self.assertEqual(engine.session_title, "")
            self.assertFalse(list(engine.root.glob("*.md")))

    def test_general_execution_keeps_title_across_followup(self):
        helper = test_general.GeneralTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        engine = helper.make()
        command(engine, "/rename Araştırmam")
        self.assertEqual(engine.execute("Hello")["title"], "Araştırmam")
        engine.sessions.rename(engine.session_id, "New title")
        self.assertEqual(engine.execute("Explain more", resume=True)["title"], "New title")
        engine.new()
        self.assertEqual(engine.session_title, "")


if __name__ == "__main__":
    unittest.main()
