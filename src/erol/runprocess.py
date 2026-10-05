"""Bounded subprocess observation; raw streams are never durable execution records."""

from __future__ import annotations

import os
import queue
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .common import ErolError

MAX_LINE = 1024 * 1024
MAX_STREAM = 16 * 1024 * 1024


def _darwin_group_terminated(pgid: int) -> bool:
    """EPERM can follow SIGKILL for a Darwin group containing only zombies.

    Do not swallow permissions errors on living/unknown groups. Query numeric
    group IDs and states only; process command lines are neither read nor saved.
    """
    try:
        result = subprocess.run(
            ["/bin/ps", "-axo", "pgid=,stat="],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if result.returncode or len(result.stdout) > MAX_LINE:
        return False
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) != 2 or not fields[0].isdigit():
            return False
        if int(fields[0]) == pgid and not fields[1].startswith("Z"):
            return False
    return True


def _darwin_cleanup_complete(process: subprocess.Popen) -> bool:
    """Allow a short reap race, then require proof that the whole group stopped."""
    if process.poll() is None:
        # killpg may find no signalable members while the leader's exit is still
        # becoming visible to waitpid. Waiting is not permission to skip a live
        # process: both the owned leader and every remaining member must be dead.
        try:
            process.wait(timeout=0.25)
        except (OSError, subprocess.SubprocessError):
            return False
        if process.poll() is None:
            return False
    return _darwin_group_terminated(process.pid)


def stop_process(process: subprocess.Popen) -> None:
    if os.name == "nt":
        # Only kill the tree of the Popen object owned by this runner, never a saved PID.
        if process.poll() is None:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                timeout=10,
                check=False,
            )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)  # type: ignore[attr-defined]
        except ProcessLookupError:
            pass
        except PermissionError:
            if sys.platform != "darwin" or not _darwin_cleanup_complete(process):
                raise
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def observe(
    argv: list[str],
    cwd: Path,
    *,
    timeout: float,
    prompt: str = "",
    on_line: Callable[[str], None] | None = None,
    on_output: Callable[[bool, bytes], None] | None = None,
    on_start: Callable[[int | None], None] = lambda pid: None,
    cancelled: Callable[[], bool] = lambda: False,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    if timeout <= 0:
        raise ErolError("Execution time budget exhausted")
    if os.name == "nt" and Path(argv[0]).suffix.lower() in {".cmd", ".bat", ".ps1"}:
        raise ErolError("Use a native executable or node entry point, not a Windows shell wrapper")
    started = time.monotonic()
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        start_new_session=os.name != "nt",
        creationflags=0x204 if os.name == "nt" else 0,  # NEW_PROCESS_GROUP | SUSPENDED
    )
    messages: queue.Queue = queue.Queue(maxsize=64)
    halt = threading.Event()

    def put(value: tuple) -> None:
        while not halt.is_set():
            try:
                messages.put(value, timeout=0.1)
                return
            except queue.Full:
                pass

    def pump(stream, is_stdout: bool) -> None:
        try:
            while not halt.is_set():
                line = stream.readline(MAX_LINE + 1)
                if not line:
                    break
                put((is_stdout, line))
                if len(line) > MAX_LINE:
                    break
        finally:
            put((is_stdout, None))

    threads = [
        threading.Thread(target=pump, args=(process.stdout, True), daemon=True),
        threading.Thread(target=pump, args=(process.stderr, False), daemon=True),
    ]
    reason = None
    output_bytes = 0
    ended = 0
    writer_error: list[Exception] = []

    def feed() -> None:
        try:
            assert process.stdin is not None
            process.stdin.write(prompt.encode("utf-8"))
            process.stdin.close()
        except (OSError, ValueError) as exc:
            writer_error.append(exc)

    writer = threading.Thread(target=feed, daemon=True)
    job = None
    try:
        on_start(process.pid)
        if os.name == "nt":
            from .runwin import OwnedJob

            job = OwnedJob(process.pid)
        for thread in threads:
            thread.start()
        writer.start()
        while ended < 2:
            if cancelled():
                reason = "cancelled"
                break
            if time.monotonic() - started >= timeout:
                reason = "timeout"
                break
            try:
                stdout, line = messages.get(timeout=0.1)
            except queue.Empty:
                continue
            if line is None:
                ended += 1
                continue
            output_bytes += len(line)
            if len(line) > MAX_LINE or output_bytes > MAX_STREAM:
                reason = "output_limit"
                break
            if on_output is not None:
                on_output(stdout, line)
            if stdout and on_line is not None:
                on_line(line.decode("utf-8", errors="strict").rstrip("\r\n"))
        if reason:
            stop_process(process)
        else:
            remaining = timeout - (time.monotonic() - started)
            try:
                process.wait(timeout=max(0.01, remaining))
            except subprocess.TimeoutExpired:
                reason = "timeout"
                stop_process(process)
        return {
            "exit_code": process.returncode,
            "reason": reason,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "output_bytes": output_bytes,
            "input_delivered": not writer_error,
        }
    finally:
        halt.set()
        if job is not None:
            job.close()  # terminates all owned descendants, even after the leader exits
        # Also terminate surviving POSIX descendants if the leader already exited.
        stop_process(process)
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()
        for thread in [*threads, writer]:
            if thread.ident is not None:
                thread.join(timeout=1)
        on_start(None)
