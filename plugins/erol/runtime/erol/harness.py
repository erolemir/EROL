"""CLI adapters: observed native events, explicit capabilities, no provider SDK."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .common import ErolError, atomic_write, canonical, identifier, reject_links, required_text
from .runprocess import observe
from .security import assert_secret_safe, scan_secrets

WORKER_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "strategy": {"type": "string"},
        "status": {"type": "string", "enum": ["implemented", "needs_attention"]},
    },
    "required": ["summary", "strategy", "status"],
    "additionalProperties": False,
}
REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "resolved": {"type": "boolean"},
                    "message": {"type": "string"},
                },
                "required": ["severity", "resolved", "message"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "findings"],
    "additionalProperties": False,
}
RESEARCH_REVIEW_SCHEMA = {
    **REVIEW_SCHEMA,
    "properties": {
        **REVIEW_SCHEMA["properties"],
        "source_checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["verified", "unavailable", "contradicted"],
                    },
                    "reason": {"type": "string"},
                },
                "required": ["source_id", "status", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "findings", "source_checks"],
}


def windows_codex_executable() -> str | None:
    """Inspect the observed desktop install, never recursively search user files."""
    local = os.environ.get("LOCALAPPDATA")
    if not local or not Path(local).is_absolute():
        return None
    directory = Path(local) / "OpenAI" / "Codex" / "bin"
    try:
        reject_links(directory)
        if not directory.is_dir():
            return None
        candidates = [directory / "codex.exe"]
        with os.scandir(directory) as entries:
            for count, entry in enumerate(entries):
                if count >= 64:
                    return None
                if re.fullmatch(r"[a-f0-9]{16}", entry.name) and entry.is_dir(
                    follow_symlinks=False
                ):
                    candidates.append(directory / entry.name / "codex.exe")
        native = []
        for candidate in candidates:
            try:
                reject_links(candidate)
                if candidate.is_file():
                    native.append((candidate.stat().st_mtime_ns, str(candidate)))
            except (ErolError, OSError):
                continue
        return max(native)[1] if native else None
    except (ErolError, OSError):
        return None


def command_prefix(name: str) -> list[str]:
    executable = shutil.which(name)
    if not executable and name == "codex" and os.name == "nt":
        executable = windows_codex_executable()
    if not executable:
        raise ErolError(
            "Requested harness executable is unavailable; install the native CLI or add it "
            "to PATH. A connection can also specify an absolute native executable path."
        )
    path = Path(executable)
    if os.name == "nt" and path.suffix.lower() in {".cmd", ".bat", ".ps1"}:
        if name not in {"codex", "claude"}:
            raise ErolError("Unsupported CLI shell wrapper; configure a native executable")
        package = (
            "@openai/codex/bin/codex.js" if name == "codex" else "@anthropic-ai/claude-code/cli.js"
        )
        entry = path.parent / "node_modules" / package
        node = shutil.which("node")
        if not node or Path(node).suffix.lower() in {".cmd", ".bat", ".ps1"} or not entry.is_file():
            raise ErolError("Harness shell wrapper has no supported native or Node entry point")
        return [node, str(entry)]
    return [executable]


def probe(argv: list[str], cwd: Path) -> str:
    result = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        timeout=20,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode:
        raise ErolError("Harness capability or authentication probe failed")
    return result.stdout + result.stderr


def validate_result(result: Any, role: str) -> dict:
    if not isinstance(result, dict):
        raise ErolError("Harness did not return the required structured result")
    assert_secret_safe(result)
    if len(canonical(result)) > 16000:
        raise ErolError("Harness result exceeds the structured output budget")
    summary = required_text(result.get("summary"), "result summary", 4000)
    if role == "implementer":
        if set(result) != {"summary", "strategy", "status"} or result["status"] not in {
            "implemented",
            "needs_attention",
        }:
            raise ErolError("Invalid implementer result")
        return {
            "summary": summary,
            "strategy": required_text(result["strategy"], "strategy", 4000),
            "status": result["status"],
        }
    fields = (
        {"summary", "findings", "source_checks"}
        if role == "research_reviewer"
        else {"summary", "findings"}
    )
    if set(result) != fields or not isinstance(result["findings"], list):
        raise ErolError("Invalid reviewer result")
    if len(result["findings"]) > 30:
        raise ErolError("Too many review findings")
    findings = []
    for item in result["findings"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"severity", "resolved", "message"}
            or item["severity"] not in {"critical", "high", "medium", "low"}
            or type(item["resolved"]) is not bool
        ):
            raise ErolError("Invalid reviewer finding")
        findings.append({**item, "message": required_text(item["message"], "finding", 1000)})
    validated = {"summary": summary, "findings": findings}
    if role == "research_reviewer":
        checks = result["source_checks"]
        if not isinstance(checks, list) or len(checks) > 30:
            raise ErolError("Invalid independent source review")
        for check in checks:
            if (
                not isinstance(check, dict)
                or set(check) != {"source_id", "status", "reason"}
                or check["status"] not in {"verified", "unavailable", "contradicted"}
            ):
                raise ErolError("Invalid independent source review entry")
            identifier(check["source_id"])
            required_text(check["reason"], "source review reason", 1000)
        validated["source_checks"] = checks
    return validated


class EventDecoder:
    def __init__(self, harness: str, role: str, session_id: str | None = None):
        self.harness = harness
        self.role = role
        self.session_id = session_id
        self.result: dict | None = None
        self.usage: dict[str, int | float] = {}
        self.completed = False
        self.failed = False
        self.events = 0
        self.diagnostics: list[str] = []

    def line(self, line: str) -> None:
        if not line.strip():
            return
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ErolError("Malformed harness event stream") from exc
        if not isinstance(event, dict):
            raise ErolError("Malformed harness event")
        self.events += 1
        session = event.get("thread_id") if self.harness == "codex" else event.get("session_id")
        if session:
            identifier(session)
            if self.session_id and self.session_id != session:
                raise ErolError("Harness resumed a different session")
            self.session_id = session
        output = None
        if self.harness == "codex":
            kind = event.get("type")
            if kind == "turn.completed":
                self.completed = True
            if kind in {"turn.failed", "error"}:
                self.failed = True
            item = event.get("item", {})
            if kind == "item.completed" and isinstance(item, dict):
                if item.get("type") == "agent_message":
                    # Only the final schema-shaped answer is kept, never reasoning or tool text.
                    try:
                        output = json.loads(item.get("text", ""))
                    except (json.JSONDecodeError, TypeError):
                        pass
        elif event.get("type") == "result":
            self.completed = True
            self.failed = (
                event.get("is_error", False) is not False or event.get("subtype") != "success"
            )
            output = event.get("structured_output")
            if self.failed:
                subtype = event.get("subtype")
                if isinstance(subtype, str) and re.fullmatch(r"[a-z_]{1,100}", subtype):
                    self.diagnostics.append(subtype)
                errors = event.get("errors", [])
                if isinstance(errors, list):
                    if isinstance(event.get("result"), str):
                        errors = [*errors, event["result"]]
                    for error in errors[:3]:
                        if isinstance(error, str):
                            self.diagnostics.append(
                                "[redacted native error]" if scan_secrets(error) else error[:300]
                            )
            if output is None:
                try:
                    output = json.loads(event.get("result", ""))
                except (json.JSONDecodeError, TypeError):
                    pass
        if output is not None:
            self.result = validate_result(output, self.role)
        usage = event.get("usage", {})
        if isinstance(usage, dict):
            for key in (
                "input_tokens",
                "output_tokens",
                "cached_input_tokens",
                "cache_read_input_tokens",
            ):
                value = usage.get(key)
                if type(value) is int and 0 <= value <= 10**12:
                    self.usage[key] = value
        cost = event.get("total_cost_usd")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool) and 0 <= cost <= 10**6:
            self.usage["reported_cost_usd_estimate"] = cost


class CliHarness:
    def __init__(self, name: str, cwd: Path):
        if name not in {"codex", "claude"}:
            raise ErolError("Unsupported execution harness")
        self.name = name
        self.cwd = cwd
        self.prefix = command_prefix(name)
        self.configure("development")

    def configure(
        self,
        mode: str,
        model: str | None = None,
        report_directory: str | None = None,
        effort: str | None = None,
    ) -> CliHarness:
        self.mode = mode
        self.model = model
        self.report_directory = report_directory
        self.effort = effort
        return self

    def preflight(self) -> dict:
        raw_version = probe([*self.prefix, "--version"], self.cwd)
        match = re.search(r"\d+\.\d+\.\d+(?:[-.][a-zA-Z0-9.]+)?", raw_version)
        if not match:
            raise ErolError("Harness version could not be identified")
        version = match.group()
        if self.name == "codex":
            help_text = probe([*self.prefix, "exec", "--help"], self.cwd)
            resume_help = probe([*self.prefix, "exec", "resume", "--help"], self.cwd)
            required: tuple[str, ...] = ("--json", "--output-schema", "--sandbox")
            if any(option not in help_text for option in required) or any(
                option not in resume_help for option in ("--json", "--output-schema")
            ):
                raise ErolError("Codex lacks required execution or resume capabilities")
            probe([*self.prefix, "login", "status"], self.cwd)
            if getattr(self, "mode", "development") == "research":
                if "--search" not in probe([*self.prefix, "--help"], self.cwd):
                    raise ErolError("Codex lacks required live web-search capability")
        else:
            help_text = probe([*self.prefix, "--help"], self.cwd)
            required = (
                "--output-format",
                "--json-schema",
                "--resume",
                "--tools",
                "--allowedTools",
                "--permission-mode",
                "dontAsk",
                "--strict-mcp-config",
            )
            if any(option not in help_text for option in required):
                raise ErolError(
                    "Claude lacks required execution, tool restriction or resume capabilities"
                )
            try:
                auth = json.loads(probe([*self.prefix, "auth", "status", "--json"], self.cwd))
            except json.JSONDecodeError as exc:
                raise ErolError("Claude authentication probe is unsupported") from exc
            if not isinstance(auth, dict) or auth.get("loggedIn") is not True:
                raise ErolError("Claude authentication is required")
        if self.model and "--model" not in help_text:
            raise ErolError("Harness lacks explicit model selection")
        if self.effort and self.name == "claude" and "--effort" not in help_text:
            raise ErolError("Claude lacks explicit effort selection")
        if self.report_directory and "--add-dir" not in help_text:
            raise ErolError("Harness lacks external report-directory support")
        return {
            "requested_model": self.model,
            "name": self.name,
            "version": version,
            "capabilities_checked": True,
            "mode": getattr(self, "mode", "development"),
        }

    def argv(self, role: str, schema_path: Path, session_id: str | None) -> list[str]:
        if session_id:
            identifier(session_id)
        if self.name == "codex":
            sandbox = "read-only" if role == "reviewer" else "workspace-write"
            args = [*self.prefix, "-a", "never", "-s", sandbox, "exec"]
            if getattr(self, "mode", "development") == "research":
                args.insert(len(self.prefix), "--search")
            if self.effort:
                args += ["-c", f'model_reasoning_effort="{self.effort}"']
            if self.model:
                args += ["--model", self.model]
            if self.report_directory and role == "implementer":
                args += ["--add-dir", self.report_directory]
            if session_id:
                args += ["resume", session_id]
            args += ["--json", "--output-schema", str(schema_path), "-"]
            return args
        tools = "Read,Glob,Grep" if role == "reviewer" else "Read,Glob,Grep,Edit,Write"
        if getattr(self, "mode", "development") == "research":
            tools += ",WebSearch,WebFetch"
        args = [
            *self.prefix,
            "-p",
            "--output-format",
            "stream-json",
            "--verbose",
            "--json-schema",
            schema_path.read_text(encoding="utf-8"),
            "--permission-mode",
            "dontAsk",
            "--tools",
            tools,
            "--allowedTools",
            tools,
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
        ]
        if self.effort:
            args += ["--effort", self.effort]
        if self.model:
            args += ["--model", self.model]
        if self.report_directory:
            args += ["--add-dir", self.report_directory]
        if session_id:
            args += ["--resume", session_id]
        return args

    def execute(
        self,
        role: str,
        prompt: str,
        artifact_directory: Path,
        *,
        timeout: float,
        session_id: str | None = None,
        on_start: Callable[[int | None], None],
        on_session: Callable[[str], None],
        cancelled: Callable[[], bool],
    ) -> dict[str, Any]:
        research_review = role == "reviewer" and getattr(self, "mode", "development") == "research"
        schema = (
            RESEARCH_REVIEW_SCHEMA
            if research_review
            else REVIEW_SCHEMA
            if role == "reviewer"
            else WORKER_SCHEMA
        )
        schema_path = artifact_directory / f"{role}-schema.json"
        atomic_write(schema_path, canonical(schema))
        decoder = EventDecoder(
            self.name, "research_reviewer" if research_review else role, session_id
        )

        def event(line: str) -> None:
            before = decoder.session_id
            decoder.line(line)
            if decoder.session_id and decoder.session_id != before:
                on_session(decoder.session_id)

        observed = observe(
            self.argv(role, schema_path, session_id),
            self.cwd,
            timeout=timeout,
            prompt=prompt,
            on_line=event,
            on_start=on_start,
            cancelled=cancelled,
            environment={**os.environ, "EROL_RUN_ACTIVE": "1"},
        )
        if not observed["reason"] and (
            observed["exit_code"] != 0
            or not observed["input_delivered"]
            or not decoder.completed
            or decoder.failed
            or decoder.result is None
            or decoder.session_id is None
        ):
            observed["reason"] = "harness_incomplete_or_failed"
        return {
            **observed,
            "session_id": decoder.session_id,
            "result": decoder.result,
            "usage": decoder.usage,
            "event_count": decoder.events,
            "diagnostics": decoder.diagnostics,
        }
