"""Terminal results and model selection with local fixtures, no model calls."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_chat
import test_project_chats

from erol.artifacts import report_files
from erol.common import ErolError
from erol.connections import Model
from erol.console import command
from erol.general import GeneralEngine
from erol.presentation import present, task_result
from erol.workspace import changes


class TerminalResultTests(unittest.TestCase):
    def test_projectless_model_and_effort_selection_reaches_actual_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = GeneralEngine(
                Path(temporary), Path(temporary) / "home", factory=test_chat.FakeProvider
            )
            engine.connections.connect("codex")
            engine.connections.get("codex").models = [Model("single", level=3)]
            command(engine, "/models")
            command(engine, "/model 1")
            command(engine, "/effort high")
            seen = []
            original = test_chat.FakeProvider.stream

            def stream(provider, request, **options):
                seen.append(request)
                yield from original(provider, request, **options)

            with patch.object(test_chat.FakeProvider, "stream", stream):
                record = engine.execute("Hello")
            self.assertEqual(record["status"], "completed")
            self.assertEqual((seen[0].model.id, seen[0].effort), ("single", "high"))
            self.assertFalse(record["verified"])
            self.assertEqual(record["changes"], [])

    def test_number_page_grammar_and_quoted_numeric_paths_have_distinct_meanings(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            engine.record = {
                "changes": [
                    {"path": "normal.py", "diff": "\n".join(f"+line{i}" for i in range(250))},
                    {"path": "1 2", "diff": "+numeric-space-name"},
                    {"path": "2", "diff": "+numeric-name"},
                ]
            }
            view = present(command(engine, "/diff 1 2"), "en")
            self.assertIn("+line100", view)
            self.assertNotIn("+numeric-space-name", view)
            self.assertIn("+numeric-space-name", present(command(engine, '/diff "1 2"'), "en"))
            self.assertIn("+numeric-name", present(command(engine, '/diff "2"'), "en"))

    def test_saved_checkout_paths_and_numeric_filename_suffix_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            other = Path(temporary) / "other-checkout"
            prior = test_project_chats.ProjectChatTests().saved(engine, project_root=str(other))
            show = present(command(engine, "/chats show 1"), "en")
            self.assertIn(str(other / "api.py"), show)
            engine.record = {
                **prior,
                "changes": [
                    {"path": "report", "diff": "\n".join("+first" for _ in range(150))},
                    {"path": "report 2", "diff": "+second"},
                ],
            }
            for query in ("/files", "/diff"):
                self.assertIn(str(other / "report 2"), present(command(engine, query), "en"))
            for query in (
                "/diff report 2",
                "/diff " + str(other / "report 2"),
                '/diff "' + str(other / "report 2") + '"',
            ):
                view = present(command(engine, query), "en")
                self.assertIn("+second", view)
                self.assertNotIn("+first", view)
            self.assertEqual(engine.sessions.load(prior["id"]), prior)

    def test_full_model_names_take_precedence_over_raw_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            engine.connections.connect("claude")
            engine.connections.get("codex").models = [Model("same")]
            engine.connections.get("claude").models = [Model("codex:same")]
            command(engine, "/models")
            self.assertEqual(command(engine, "/model 1")["model"], "codex:same")
            self.assertEqual(
                command(engine, "/model claude:codex:same")["model"], "claude:codex:same"
            )

    def test_provider_inventory_change_never_reinterprets_old_number(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            models = [Model("first"), Model("second")]
            engine.connections.get("codex").models = models
            command(engine, "/models")
            with patch.object(
                engine,
                "providers",
                return_value=([{"id": "codex", "available": True}], {"codex": [models[1]]}),
            ):
                with self.assertRaises(ErolError):
                    command(engine, "/model 1")
                self.assertEqual(command(engine, "/model 2")["model"], "codex:second")

    def test_legacy_chat_paths_are_enriched_without_rewriting_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            prior = test_project_chats.ProjectChatTests().saved(engine)
            view = present(command(engine, "/chats show 1"), "en")
            self.assertIn(str(engine.root / "api.py"), view)
            self.assertEqual(prior, engine.sessions.load(prior["id"]))

    def test_historical_diffs_remain_navigable_and_numeric_paths_use_indexes(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            engine.record = {
                "changes": [
                    {"path": "2", "diff": "+numeric-file", "status": "added"},
                    {"path": "other", "diff": "+second-file", "status": "added"},
                ],
                "continuation_history": [
                    {
                        "task_id": "prior",
                        "changes": [
                            {"path": "old.py", "diff": "+prior-content", "status": "modified"}
                        ],
                    }
                ],
            }
            self.assertIn("+second-file", present(command(engine, "/diff 2"), "en"))
            self.assertIn("+numeric-file", present(command(engine, "/diff ./2"), "en"))
            self.assertIn("/diff previous 1", present(command(engine, "/diff"), "en"))
            self.assertIn("+prior-content", present(command(engine, "/diff previous 1 1"), "en"))

    def test_line_statistics_count_increment_and_decrement_source(self):
        delta = changes({"file.cpp": b"--counter;\n"}, {"file.cpp": b"++counter;\n"})
        self.assertEqual((delta[0]["added_lines"], delta[0]["removed_lines"]), (1, 1))

    def test_empty_or_oversized_report_inventory_is_honest(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / "reports"
            self.assertEqual(report_files(str(folder)), [])
            view = task_result({"artifact_directory": str(folder), "report_files": []}, "en")
            self.assertIn("No individual report files recorded", view)
            folder.mkdir()
            (folder / "oversized.md").write_bytes(b"x" * (1024 * 1024 + 1))
            with self.assertRaises(ErolError):
                report_files(str(folder))

    def test_numbered_model_selection_uses_displayed_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            engine.connections.settings.connections[0].models = [Model("first"), Model("second")]
            menu = command(engine, "/models")
            self.assertIn("1. codex:first", present(menu, "tr"))
            engine.connections.settings.connections[0].models.reverse()
            with self.assertRaises(ErolError):
                command(engine, "/model 1")
            command(engine, "/models")
            self.assertEqual(command(engine, "/model 1")["model"], "codex:second")
            self.assertEqual(command(engine, "/model first")["model"], "codex:first")
            self.assertEqual(command(engine, "/model auto")["model"], "auto")

    def test_unavailable_and_ambiguous_models_are_not_selectable(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            engine.connections.connect("claude")
            first = engine.connections.get("codex")
            second = engine.connections.get("claude")
            first.models = [Model("same")]
            second.models = [Model("same")]
            with self.assertRaises(ErolError):
                command(engine, "/model same")
            first.enabled = False
            with self.assertRaises(ErolError):
                command(engine, "/model codex:same")
            self.assertEqual(command(engine, "/model same")["model"], "claude:same")

    def test_busy_selection_is_rejected_and_supported_effort_reaches_worker(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            engine.connections.settings.connections[0].models = [Model("single", level=3)]
            engine.busy = True
            with self.assertRaises(ErolError):
                command(engine, "/model codex:single")
            engine.busy = False
            command(engine, "/model single")
            command(engine, "/effort high")
            result = engine.execute("Fix typo")
            self.assertEqual(result["selection"]["effort"], "high")
            self.assertTrue(result["selection"]["manual_effort"])
            with self.assertRaises(ErolError):
                command(engine, "/effort ultra")

    def test_actual_reports_and_changes_have_absolute_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            original = test_chat.FakeProvider.stream

            def stream(provider, request, **options):
                if request.role == "implementer":
                    report = Path(request.report_directory) / "analysis.md"
                    report.parent.mkdir(parents=True, exist_ok=True)
                    report.write_text("Verified fixture report", "utf-8")
                yield from original(provider, request, **options)

            with patch.object(test_chat.FakeProvider, "stream", stream):
                record = engine.execute("Fix typo")
            view = task_result(record, "tr")
            self.assertIn(str(engine.root / "edited.txt"), view)
            self.assertIn("+task change", view)
            self.assertIn(str(Path(record["artifact_directory"]) / "analysis.md"), view)
            files = present(command(engine, "/files"), "tr")
            self.assertIn("analysis.md", files)
            self.assertNotIn("missing.md", files)
            saved = engine.sessions.load(engine.session_id)
            self.assertEqual(saved["report_files"][0]["path"], "analysis.md")

    def test_diff_is_paged_with_explicit_incomplete_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = test_chat.EngineTests().make(temporary)
            engine.record = {
                "changes": [
                    {
                        "path": "edited.txt",
                        "status": "modified",
                        "diff": "\n".join(f"+line {i}" for i in range(250)),
                        "diff_truncated": True,
                    }
                ]
            }
            detail = present(command(engine, "/diff 1 2"), "en")
            self.assertIn("+line 100", detail)
            self.assertNotIn("+line 0\n", detail)
            self.assertIn("/diff 1 3", detail)
            self.assertIn("truncated", detail)
            with self.assertRaises(ErolError):
                command(engine, "/diff 1 99")


if __name__ == "__main__":
    unittest.main()
