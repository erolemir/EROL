"""Adversarial fixtures use synthetic values and harmless local side effects only."""

import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from erol.checktrust import CheckTrust, command_environment
from erol.common import ErolError
from erol.identity import detect_project
from erol.panel import make_server
from erol.security import scan_secrets
from erol.store import Store
from erol.workspace import run_checks


class SecurityBoundaryTests(unittest.TestCase):
    def test_raw_assignments_and_store_reject_provider_labels_without_writes(self):
        for label in ("AWS_SECRET_ACCESS_KEY", "STRIPE_KEY", "GOOGLE_APPLICATION_CREDENTIALS"):
            self.assertTrue(scan_secrets(label + "=x"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            with Store(Path(temporary) / "home", detect_project(root)) as store:
                for label in ("AWS_SECRET_ACCESS_KEY", "STRIPE_KEY"):
                    with self.assertRaisesRegex(ErolError, "Secret-like"):
                        store.put("learnings", {"id": "fixture", label: 123})
                self.assertEqual(store.list("learnings"), [])
        for value in (
            {"key_env": "OPENAI_API_KEY"},
            {"model": "claude"},
            {"input_tokens": 123},
            {"worker_session": "11111111-1111-4111-8111-111111111111"},
            {"public_key": None},
        ):
            self.assertFalse(scan_secrets(value))

    def manifest(self, code="print('fixture')"):
        return {
            "schema_version": 1,
            "checks": [
                {
                    "name": "fixture",
                    "kind": "acceptance",
                    "argv": [sys.executable, "-c", code],
                    "timeout_seconds": 10,
                }
            ],
        }

    def test_content_bound_root_scoped_trust_revoke_and_injection_variables(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            first, second = base / "first", base / "second"
            first.mkdir()
            second.mkdir()
            trust = CheckTrust(base / "state", first)
            manifest = self.manifest()
            with self.assertRaisesRegex(ErolError, "Unreviewed"):
                trust.require(manifest)
            trust.approve(manifest)
            self.assertEqual(CheckTrust(base / "state", first).require(manifest)["prefix"], [])
            with self.assertRaisesRegex(ErolError, "Unreviewed"):
                trust.require(self.manifest("print('changed')"))
            with self.assertRaisesRegex(ErolError, "different"):
                run_checks(second, manifest, threading.Event(), trust=trust)
            with self.assertRaisesRegex(ErolError, "Unreviewed"):
                CheckTrust(base / "state", second).require(manifest)
            for name in ("NODE_OPTIONS", "PYTHONPATH", "LD_PRELOAD", "BASH_ENV", "ENV"):
                with self.assertRaisesRegex(ErolError, "injection"):
                    trust.approve(manifest, environment=[name])
                with self.assertRaisesRegex(ErolError, "injection"):
                    command_environment([name])
            trust.revoke(manifest)
            with self.assertRaisesRegex(ErolError, "Unreviewed"):
                trust.require(manifest)

    def test_observed_check_process_has_no_inherited_account_credentials(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "project"
            root.mkdir()
            manifest = self.manifest(
                "import os; assert not any(k in os.environ for k in "
                "('AWS_SECRET_ACCESS_KEY','STRIPE_KEY','NODE_OPTIONS','PYTHONPATH')); "
                "assert os.environ['EROL_RUN_ACTIVE']=='1'; print('minimal-env-observed')"
            )
            trust = CheckTrust(base / "state", root)
            trust.approve(manifest)
            with patch.dict(
                os.environ,
                {
                    "AWS_SECRET_ACCESS_KEY": "x",
                    "STRIPE_KEY": "x",
                    "NODE_OPTIONS": "injection",
                    "PYTHONPATH": "injection",
                },
            ):
                result = run_checks(root, manifest, threading.Event(), trust=trust)
            self.assertTrue(result[0]["passed"])
            self.assertIn("minimal-env-observed", result[0]["output"])

    def test_invalid_external_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "project"
            root.mkdir()
            trust = CheckTrust(base / "state", root)
            manifest = self.manifest()
            for invalid in ("", {}, False):
                with self.assertRaisesRegex(ErolError, "policy"):
                    trust.approve(manifest, prefix=invalid)
            trust.approve(manifest)
            trust.path.write_text(
                '{"schema_version":1,"root":"another-root","approvals":[]}', encoding="utf-8"
            )
            with self.assertRaisesRegex(ErolError, "Invalid external"):
                run_checks(root, manifest, threading.Event(), trust=trust)

    def test_cli_trust_commands_only_authorize_and_do_not_execute(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "project"
            root.mkdir()
            manifest = base / "checks.json"
            manifest.write_text(
                json.dumps(
                    self.manifest("from pathlib import Path; Path('marker').write_text('ran')")
                ),
                encoding="utf-8",
            )
            prefix = [
                sys.executable,
                "-m",
                "erol",
                "--project",
                str(root),
                "--home",
                str(base / "state"),
                "checks",
            ]

            def call(action):
                result = subprocess.run(
                    [*prefix, action, "--file", str(manifest)],
                    capture_output=True,
                    check=True,
                    timeout=20,
                )
                return json.loads(result.stdout)

            self.assertFalse(call("show")["trusted"])
            self.assertFalse(call("trust")["sandbox_verified"])
            self.assertTrue(call("show")["trusted"])
            self.assertFalse(call("revoke")["trusted"])
            self.assertFalse(call("show")["trusted"])
            self.assertFalse((root / "marker").exists())

    def test_check_environment_excludes_credentials_and_startup_hooks(self):
        with patch.dict(
            os.environ,
            {
                "AWS_SECRET_ACCESS_KEY": "x",
                "STRIPE_KEY": "x",
                "PYTHONPATH": "injection",
                "NODE_OPTIONS": "injection",
                "EROL_FIXTURE_PUBLIC": "ok",
                "LANG": "C",
            },
            clear=True,
        ):
            self.assertEqual(command_environment(), {"LANG": "C", "EROL_RUN_ACTIVE": "1"})
            self.assertEqual(
                command_environment(["EROL_FIXTURE_PUBLIC"])["EROL_FIXTURE_PUBLIC"], "ok"
            )
            with self.assertRaisesRegex(ErolError, "Secret-like"):
                command_environment(["AWS_SECRET_ACCESS_KEY"])

    def test_check_and_tool_commands_share_reviewed_external_executor(self):
        from erol.workspace import Workspace

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "project"
            root.mkdir()
            manifest = self.manifest("print('payload')")
            prefix = [
                sys.executable,
                "-c",
                "import sys; print('external-executor'); print(sys.argv[1:])",
            ]
            trust = CheckTrust(base / "trust", root)
            trust.approve(manifest, prefix=prefix)
            reports = run_checks(root, manifest, threading.Event(), trust=trust)
            self.assertTrue(reports[0]["passed"])
            self.assertIn("external-executor", reports[0]["output"])
            workspace = Workspace(
                root,
                allowed_commands=[manifest["checks"][0]["argv"]],
                check_trust=trust,
                checks_manifest=manifest,
            )
            result = json.loads(
                workspace.dispatch("run_command", {"argv": manifest["checks"][0]["argv"]})
            )
            self.assertIn("external-executor", result["output"])
            trust.revoke(manifest)
            with self.assertRaisesRegex(ErolError, "Unreviewed"):
                workspace.dispatch("run_command", {"argv": manifest["checks"][0]["argv"]})

    def test_panel_token_origin_scope_no_leak_and_rotation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            server = make_server(root, "fixture", 0)
            other = make_server(root, "fixture", 0)
            self.assertNotEqual(server.token, other.token)
            other.server_close()
            self.assertIn("#token=", server.access_url)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with patch("erol.panel.panel_state", return_value={"read_only": True}) as state:
                    with closing(
                        http.client.HTTPConnection("127.0.0.1", server.server_port)
                    ) as client:
                        for headers, status in (
                            ({}, 401),
                            ({"Authorization": "Bearer " + other.token}, 401),
                            (
                                {
                                    "Authorization": "Bearer " + server.token,
                                    "Origin": "https://attacker.test",
                                },
                                403,
                            ),
                            (
                                {
                                    "Authorization": "Bearer " + server.token,
                                    "Host": "attacker.test",
                                },
                                403,
                            ),
                        ):
                            client.request("GET", "/api/state", headers=headers)
                            response = client.getresponse()
                            self.assertEqual(response.status, status)
                            self.assertNotIn(server.token.encode(), response.read())
                        state.assert_not_called()
                        client.request(
                            "GET", "/api/state", headers={"Authorization": "Bearer " + server.token}
                        )
                        response = client.getresponse()
                        self.assertEqual(response.status, 200)
                        self.assertEqual(json.loads(response.read()), {"read_only": True})
                        client.request("GET", "/panel.js")
                        response = client.getresponse()
                        script = response.read().decode()
                        self.assertNotIn(server.token, script)
                        self.assertIn("history.replaceState", script)
                        self.assertIn("Authorization", script)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_provider_credential_labels_reject_short_values(self):
        for label in (
            "AWS_SECRET_ACCESS_KEY",
            "STRIPE_KEY",
            "OPENAI_API_KEY",
            "GITHUB_TOKEN",
            "GOOGLE_APPLICATION_CREDENTIALS",
        ):
            for value in ("x", 123, True, ["x"]):
                with self.subTest(label=label, value=value):
                    self.assertTrue(scan_secrets({label: value}))

    def test_panel_rejects_unauthenticated_state_before_reading_storage(self):
        with tempfile.TemporaryDirectory() as temporary:
            server = make_server(Path(temporary), "fixture", 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with closing(http.client.HTTPConnection("127.0.0.1", server.server_port)) as client:
                    client.request("GET", "/api/state")
                    response = client.getresponse()
                    self.assertEqual(response.status, 401)
                    response.read()
                self.assertFalse((Path(temporary) / "runs.db").exists())
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_unreviewed_check_does_not_execute_host_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = {
                "schema_version": 1,
                "checks": [
                    {
                        "name": "fixture",
                        "kind": "acceptance",
                        "argv": [
                            sys.executable,
                            "-c",
                            "from pathlib import Path; Path('marker').write_text('ran')",
                        ],
                        "timeout_seconds": 10,
                    }
                ],
            }
            with self.assertRaisesRegex(ErolError, "trust|review"):
                run_checks(root, manifest, threading.Event())
            self.assertFalse((root / "marker").exists())
