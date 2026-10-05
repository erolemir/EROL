"""Process cleanup races must retain proof of leader and group termination."""

import errno
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from erol.runprocess import observe, stop_process


class DarwinCleanupRaceTests(unittest.TestCase):
    def setUp(self):
        self.process = Mock(pid=1234)
        self.error = PermissionError(errno.EPERM, "Operation not permitted")
        self.patches = [
            patch(
                "erol.runprocess.os",
                SimpleNamespace(name="posix", killpg=Mock(side_effect=self.error)),
            ),
            patch("erol.runprocess.sys", SimpleNamespace(platform="darwin")),
            patch("erol.runprocess.signal", SimpleNamespace(SIGKILL=9)),
        ]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_exiting_leader_is_reaped_before_terminal_group_proof(self):
        self.process.poll.side_effect = [None, 0, 0]
        with patch(
            "erol.runprocess.subprocess.run",
            return_value=Mock(returncode=0, stdout="1234 Z\n5678 S\n"),
        ) as probe:
            stop_process(self.process)
        self.assertEqual(2, self.process.wait.call_count)
        self.assertGreater(self.process.wait.call_args_list[0].kwargs["timeout"], 0)
        self.assertLessEqual(self.process.wait.call_args_list[0].kwargs["timeout"], 1)
        probe.assert_called_once()
        self.process.kill.assert_not_called()

    def test_reap_timeout_preserves_original_permission_error(self):
        self.process.poll.return_value = None
        self.process.wait.side_effect = subprocess.TimeoutExpired("owned-process", 0.25)
        with patch("erol.runprocess.subprocess.run") as probe:
            with self.assertRaises(PermissionError) as raised:
                stop_process(self.process)
        self.assertIs(self.error, raised.exception)
        self.process.wait.assert_called_once_with(timeout=0.25)
        probe.assert_not_called()
        self.process.kill.assert_not_called()

    def test_reaped_leader_does_not_hide_live_descendant(self):
        self.process.poll.side_effect = [None, 0]
        with patch(
            "erol.runprocess.subprocess.run",
            return_value=Mock(returncode=0, stdout="1234 Z\n1234 S\n"),
        ) as probe:
            with self.assertRaises(PermissionError) as raised:
                stop_process(self.process)
        self.assertIs(self.error, raised.exception)
        probe.assert_called_once()

    def test_failed_group_observation_still_rejects_cleanup(self):
        for result in (
            Mock(returncode=1, stdout=""),
            Mock(returncode=0, stdout="unknown state\n"),
            Mock(returncode=0, stdout="1234\n"),
        ):
            with self.subTest(result=result):
                self.process.poll.side_effect = [None, 0]
                with patch("erol.runprocess.subprocess.run", return_value=result) as probe:
                    with self.assertRaises(PermissionError) as raised:
                        stop_process(self.process)
                self.assertIs(self.error, raised.exception)
                probe.assert_called_once()

    def test_wait_error_preserves_original_permission_error(self):
        self.process.poll.return_value = None
        self.process.wait.side_effect = OSError("wait failed")
        with patch("erol.runprocess.subprocess.run") as probe:
            with self.assertRaises(PermissionError) as raised:
                stop_process(self.process)
        self.assertIs(self.error, raised.exception)
        self.process.wait.assert_called_once_with(timeout=0.25)
        probe.assert_not_called()

    def test_wait_without_observed_exit_does_not_probe_group(self):
        self.process.poll.return_value = None
        with patch("erol.runprocess.subprocess.run") as probe:
            with self.assertRaises(PermissionError):
                stop_process(self.process)
        probe.assert_not_called()

    def test_non_darwin_permission_error_is_not_recovered(self):
        self.process.poll.return_value = 0
        with (
            patch("erol.runprocess.sys.platform", "linux"),
            patch("erol.runprocess.subprocess.run") as probe,
        ):
            with self.assertRaises(PermissionError) as raised:
                stop_process(self.process)
        self.assertIs(self.error, raised.exception)
        probe.assert_not_called()
        self.process.wait.assert_not_called()


class NativeDarwinCleanupTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "darwin", "requires native Darwin process semantics")
    def test_repeated_output_limit_cleanup(self):
        with tempfile.TemporaryDirectory(prefix="erol-cleanup-") as directory:
            for attempt in range(25):
                with self.subTest(attempt=attempt):
                    outcome = observe(
                        [sys.executable, "-c", "print('x' * (1024 * 1024 + 1))"],
                        Path(directory),
                        timeout=10,
                    )
                    self.assertEqual("output_limit", outcome["reason"])
                    self.assertIsNotNone(outcome["exit_code"])


if __name__ == "__main__":
    unittest.main()
