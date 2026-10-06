"""SDK-free CLI/API adapters, native stream decoding, and per-task budget accounting."""

from __future__ import annotations

import json
import os
import queue
import re
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import ErolError, canonical, identifier, now
from .connections import CLI_KINDS, Connection, Model, number
from .harness import WORKER_SCHEMA, command_prefix, probe, validate_result
from .runprocess import observe
from .security import scan_secrets

MAX_RESPONSE = 8 * 1024 * 1024


def visible(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    if scan_secrets(text):
        return "[redacted sensitive output]"
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)[:128000]


def event(kind: str, request: Request, **payload: Any) -> dict:
    return {
        "schema_version": 1,
        "type": kind,
        "task_id": request.task_id,
        "connection": request.connection.id,
        "model": request.model.id,
        "role": request.role,
        "time": now(),
        "data": payload,
    }


def implementation_report(raw: Any) -> dict | None:
    try:
        if isinstance(raw, str):
            raw = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
        return validate_result(raw, "implementer")
    except (ErolError, ValueError, TypeError, KeyError):
        return None


@dataclass
class Request:
    task_id: str
    connection: Connection
    model: Model
    prompt: str
    role: str = "implementer"
    effort: str = "medium"
    native_session: str | None = None
    timeout: float = 900
    mode: str = "project"
    report_directory: str | None = None


class BudgetExhausted(ErolError):
    """A saved task may continue after the user adjusts its total budget."""


class CleanupFailure(ErolError):
    """Uncertain child containment must stop every subsequent task role."""


class Budget:
    """Reserve estimates before dispatch; missing usage retains the reservation."""

    def __init__(self, limit: float):
        self.limit = number(limit, "budget", 0.01, 1000)
        self.spent = 0.0
        self.reserved = 0.0
        self.unreported = 0.0
        self.calls = 0
        self.lock = threading.Lock()

    def reserve(self, model: Model, payload: dict) -> float:
        if model.input_price is None or model.output_price is None:
            raise ErolError("API model prices are required for the budget guard")
        # UTF-8 bytes form a deliberately generous token-size proxy, not a tokenizer.
        estimated_input = len(canonical(payload).encode("utf-8"))
        if estimated_input + model.output_limit > model.context_window:
            raise ErolError("Request exceeds the model context guard; narrow the task")
        amount = (
            estimated_input * model.input_price + model.output_limit * model.output_price
        ) / 1000000
        with self.lock:
            if self.spent + self.reserved + amount > self.limit:
                raise BudgetExhausted(
                    "API task budget exhausted; increase /settings api_budget_usd to resume"
                )
            self.reserved += amount
            self.calls += 1
        return amount

    def settle(self, model: Model, reserved: float, usage: dict) -> dict:
        cost = None
        if "input_tokens" in usage and "output_tokens" in usage:
            cost = (
                usage["input_tokens"] * (model.input_price or 0)
                + usage["output_tokens"] * (model.output_price or 0)
            ) / 1000000
        with self.lock:
            self.reserved = max(0.0, self.reserved - reserved)
            self.spent += cost if cost is not None else reserved
            if cost is None:
                self.unreported += reserved
        return {
            **usage,
            "estimated_cost_usd": cost,
            "unreported_reserved_usd": reserved if cost is None else 0,
            "billing_evidence": "provider_tokens_times_profile_prices"
            if cost is not None
            else "reserved_estimate_only",
        }

    def summary(self) -> dict:
        with self.lock:
            return {
                "budget_usd": self.limit,
                "accounted_usd": round(self.spent, 6),
                "pending_reserved_usd": round(self.reserved, 6),
                "unreported_reserved_usd": round(self.unreported, 6),
                "api_calls": self.calls,
                "remaining_usd": round(max(0.0, self.limit - self.spent - self.reserved), 6),
                "limit_is_invoice_guarantee": False,
            }


def usage_counts(data: Any, kind: str) -> dict:
    if not isinstance(data, dict):
        return {}
    mappings = {
        "openai": {"input_tokens": "input_tokens", "output_tokens": "output_tokens"},
        "compatible": {"input_tokens": "prompt_tokens", "output_tokens": "completion_tokens"},
        "anthropic": {"input_tokens": "input_tokens", "output_tokens": "output_tokens"},
        "gemini": {"input_tokens": "promptTokenCount", "output_tokens": "candidatesTokenCount"},
    }
    result = {}
    for name, native in mappings[kind].items():
        value = data.get(native)
        if type(value) is int and 0 <= value <= 10**12:
            result[name] = value
    if kind == "gemini" and "output_tokens" in result:
        thinking = data.get("thoughtsTokenCount", 0)
        if type(thinking) is int and 0 <= thinking <= 10**12:
            result["output_tokens"] += thinking
    if kind == "anthropic" and "input_tokens" in result:
        # Cache token prices vary; charge full nominal input conservatively.
        for key in ("cache_read_input_tokens", "cache_creation_input_tokens"):
            value = data.get(key, 0)
            if type(value) is int and 0 <= value <= 10**12:
                result["input_tokens"] += value
    return result


class CLIAdapter:
    def __init__(self, connection: Connection, root: Path):
        self.connection, self.root = connection, root
        self.stopped = threading.Event()
        name = {"antigravity": "agy"}.get(connection.kind, connection.kind)
        self.prefix = [connection.executable] if connection.executable else command_prefix(name)
        if os.name == "nt" and Path(self.prefix[0]).suffix.lower() in {".cmd", ".ps1", ".bat"}:
            raise ErolError(
                "Configure a native CLI executable; IDE and shell wrappers are not agent adapters"
            )

    def capabilities(self) -> dict:
        version = probe([*self.prefix, "--version"], self.root).strip()[:100]
        kind = self.connection.kind
        help_text = probe(
            [*self.prefix, "exec", "--help"] if kind == "codex" else [*self.prefix, "--help"],
            self.root,
        )
        required = {
            "codex": ("--json", "--model", "--sandbox", "--output-schema", "--skip-git-repo-check"),
            "claude": (
                "--model",
                "--output-format",
                "--tools",
                "--permission-mode",
                "--json-schema",
            ),
            "antigravity": (
                "--model",
                "--output-format",
                "--input-format",
                "--sandbox",
                "--json-schema",
            ),
        }[kind]
        if any(option not in help_text for option in required):
            raise ErolError("Installed CLI lacks required model/stream/permission capabilities")
        if kind == "codex":
            probe([*self.prefix, "login", "status"], self.root)
        elif kind == "claude":
            try:
                auth = json.loads(probe([*self.prefix, "auth", "status", "--json"], self.root))
            except ErolError as exc:
                raise ErolError("Claude login check failed; run claude auth login") from exc
            except ValueError as exc:
                raise ErolError("Claude authentication probe is unsupported") from exc
            if not isinstance(auth, dict) or auth.get("loggedIn") is not True:
                raise ErolError("Claude login required; run claude auth login")
        # agy model listing needs the native account; do not open an interactive login.
        elif not self.models():
            raise ErolError("Antigravity has no accessible models; authenticate with agy")
        return {
            "available": True,
            "version": visible(version),
            "stream": True,
            "resume": kind in {"codex", "claude", "antigravity"},
            "authentication": "native_login_checked"
            if kind != "antigravity"
            else "model_listing_checked",
        }

    def models(self) -> list[Model]:
        if self.connection.kind == "antigravity":
            raw = probe([*self.prefix, "models", "--json"], self.root)
            try:
                data = json.loads(raw)
            except ValueError as exc:
                raise ErolError(
                    "Antigravity machine-readable model listing is unavailable"
                ) from exc
            rows = data.get("models", []) if isinstance(data, dict) else data
            ids = {
                item if isinstance(item, str) else item.get("id", item.get("slug", ""))
                for item in rows
                if isinstance(item, (str, dict))
            }
            return [m for m in self.connection.models if m.id in ids]
        if self.connection.kind == "codex":
            cache = Path.home() / ".codex" / "models_cache.json"
            try:
                if cache.is_file() and cache.stat().st_size < 2000000:
                    data = json.loads(cache.read_text("utf-8"))
                    ids = {m.get("slug", m.get("id")) for m in data.get("models", [])}
                    return [m for m in self.connection.models if m.id in ids]
            except (OSError, ValueError, TypeError, AttributeError):
                pass
        return self.connection.models  # profiles; acceptance is checked on the native turn

    def cancel(self) -> None:
        self.stopped.set()

    def resume(self, request: Request, session: str) -> Iterator[dict]:
        request.native_session = identifier(session)
        return self.stream(request)

    def projectless_capabilities(self, mode: str) -> None:
        if self.connection.kind == "antigravity":
            raise ErolError("Antigravity needs a project; select another provider for general chat")
        if self.connection.kind == "codex":
            features = probe([*self.prefix, "features", "list"], self.root)
            if not re.search(r"(?m)^shell_tool\s", features):
                raise ErolError("Codex cannot verify shell disabling for projectless conversation")
            if mode == "research" and "--search" not in probe([*self.prefix, "--help"], self.root):
                raise ErolError("Codex native web search is unavailable")
        else:
            help_text = probe([*self.prefix, "--help"], self.root)
            if any(
                flag not in help_text for flag in ("--tools", "--strict-mcp-config", "--mcp-config")
            ):
                raise ErolError("Claude cannot verify projectless tool/MCP restrictions")

    def stream(self, request: Request, **_: Any) -> Iterator[dict]:
        kind = self.connection.kind
        if request.mode not in {"project", "general", "research"}:
            raise ErolError("Unknown conversation mode")
        if request.mode != "project" and request.role == "implementer":
            raise ErolError("Projectless requests cannot enable writing tools")
        if kind == "antigravity" and request.role != "implementer":
            # Native agy workspace writes are auto-allowed. Never present a prompt as containment.
            raise ErolError(
                "Antigravity read-only roles need a supported restrictive agent; use "
                "another provider for planner/review"
            )
        schema_directory = None
        if kind == "codex":
            args = [
                *self.prefix,
                "-a",
                "never",
                "-s",
                "workspace-write" if request.role == "implementer" else "read-only",
                "-c",
                f'model_reasoning_effort="{request.effort}"',
            ]
            if request.mode != "project":
                args += [
                    "-c",
                    "features.shell_tool=false",
                    "-c",
                    'web_search="live"' if request.mode == "research" else 'web_search="disabled"',
                ]
            args += ["exec"]
            if request.report_directory and request.role == "implementer":
                args += ["--add-dir", request.report_directory]
            if request.native_session:
                args += ["resume", identifier(request.native_session)]
            args += ["--skip-git-repo-check", "--model", request.model.id, "--json", "-"]
            if request.role == "implementer":
                schema_directory = tempfile.TemporaryDirectory(prefix="erol-worker-schema-")
                schema = Path(schema_directory.name) / "worker.json"
                schema.write_text(canonical(WORKER_SCHEMA), "utf-8")
                args[-1:-1] = ["--output-schema", str(schema)]
        elif kind == "claude":
            tools = "Read,Glob,Grep" + (",Edit,Write" if request.role == "implementer" else "")
            if request.mode != "project":
                tools = "WebSearch,WebFetch" if request.mode == "research" else ""
            args = [
                *self.prefix,
                "-p",
                "--model",
                request.model.id,
                "--output-format",
                "stream-json",
                "--verbose",
                "--include-partial-messages",
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
            if request.effort != "none":
                args += ["--effort", request.effort]
            if request.report_directory:
                args += ["--add-dir", request.report_directory]
            if request.native_session:
                args += ["--resume", identifier(request.native_session)]
            if request.role == "implementer":
                args += ["--json-schema", canonical(WORKER_SCHEMA)]
        else:
            args = [
                *self.prefix,
                "--input-format",
                "stream-json",
                "--model",
                request.model.id,
                "--effort",
                request.effort,
                "--output-format",
                "stream-json",
                "--sandbox",
            ]
            if request.native_session:
                args += ["--conversation", identifier(request.native_session)]
            args += ["--json-schema", canonical(WORKER_SCHEMA)]
        messages: queue.Queue = queue.Queue(maxsize=128)
        finished = threading.Event()
        native_id = request.native_session
        completed = False
        failed = False
        streamed = False
        report = None

        def put(item: dict) -> None:
            while not self.stopped.is_set() or item["type"] == "process":
                try:
                    messages.put(item, timeout=0.1)
                    break
                except queue.Full:
                    continue

        def decode(line: str) -> None:
            nonlocal native_id, completed, failed, streamed, report
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ErolError("Invalid native event")
            session = data.get("thread_id", data.get("session_id", data.get("conversation_id")))
            if session:
                native_id = identifier(session)
            text: Any = ""
            typ = data.get("type", data.get("event"))
            if kind == "codex":
                completed = completed or typ == "turn.completed"
                failed = failed or typ in {"turn.failed", "error"}
                item = data.get("item", {})
                if typ == "item.completed" and item.get("type") == "agent_message":
                    text = item.get("text", "")
                    if request.role == "implementer":
                        report = implementation_report(text)
                elif typ in {"item.started", "item.completed"}:
                    put(
                        event(
                            "tool_start" if typ == "item.started" else "tool_result",
                            request,
                            tool=visible(item.get("type", "native_tool")),
                        )
                    )
                    if typ == "item.completed" and item.get("type") == "file_change":
                        for change in item.get("changes", []):
                            if isinstance(change, dict) and isinstance(change.get("path"), str):
                                put(
                                    event(
                                        "file_change",
                                        request,
                                        path=visible(change["path"]),
                                        status="native_reported_" + str(change.get("kind", "edit")),
                                    )
                                )
            elif kind == "claude":
                if typ == "stream_event":
                    delta = data.get("event", {}).get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        streamed = True
                elif typ == "assistant" and not streamed:
                    text = "".join(
                        p.get("text", "")
                        for p in data.get("message", {}).get("content", [])
                        if p.get("type") == "text"
                    )
                elif typ == "result":
                    completed = True
                    failed = data.get("is_error", False) or data.get("subtype") != "success"
                    if request.role == "implementer":
                        report = implementation_report(data.get("structured_output"))
                        if report:
                            text = canonical(report)
            else:
                if typ == "result":
                    result = data.get("result", data)
                    completed = result.get("status") == "SUCCESS"
                    failed = not completed or bool(result.get("denied_actions"))
                    native_id = result.get("conversation_id", native_id)
                    text = result.get("response", "") if not streamed else ""
                    data = result
                    report = implementation_report(result.get("structured_output"))
                elif typ == "step_update":
                    step = data.get("step_update", {})
                    if step.get("step_type") == "agent_response":
                        text = step.get("text_delta", "")
                        streamed = bool(text) or streamed
                    elif step.get("step_type") == "tool":
                        put(
                            event(
                                "tool_start" if step.get("state") == "ACTIVE" else "tool_result",
                                request,
                                tool=visible(step.get("tool_name", "native_tool")),
                            )
                        )
                elif typ in {"message", "text", "text_delta"}:
                    text = data.get("text", data.get("content", ""))
                    streamed = bool(text) or streamed
            if text:
                put(event("text_delta", request, text=visible(text)))
            native_usage = data.get("usage")
            if isinstance(native_usage, dict):
                put(
                    event(
                        "usage",
                        request,
                        counts=usage_counts(
                            native_usage, "anthropic" if kind == "claude" else "openai"
                        ),
                        estimated_cost_usd=None,
                        source="native_cli_usage",
                        cli_quota_remaining=None,
                    )
                )
            if failed:
                put(
                    event(
                        "error",
                        request,
                        message="Native CLI turn failed or required actions were denied",
                    )
                )

        cleanup_errors: list[CleanupFailure] = []

        def work() -> None:
            process_pid: int | None = None

            def process(pid: int | None) -> None:
                nonlocal process_pid
                put(event("process", request, pid=pid, previous_pid=process_pid))
                process_pid = pid

            try:
                prompt = (
                    canonical({"event": "user", "message": {"content": request.prompt}}) + "\n"
                    if kind == "antigravity"
                    else request.prompt
                )
                result = observe(
                    args,
                    self.root,
                    prompt=prompt,
                    timeout=request.timeout,
                    on_line=decode,
                    cancelled=self.stopped.is_set,
                    on_start=process,
                    environment={**os.environ, "EROL_RUN_ACTIVE": "1"},
                )
                put(
                    event(
                        "final",
                        request,
                        completed=completed
                        and not failed
                        and result["exit_code"] == 0
                        and not result["reason"]
                        and (
                            request.role != "implementer"
                            or bool(report and report["status"] == "implemented")
                        ),
                        report=report,
                        native_session=native_id,
                        reason=result["reason"]
                        or ("native_failure" if failed or not completed else None),
                    )
                )
            except (ErolError, OSError, ValueError, TypeError, KeyError) as exc:
                if process_pid is not None:
                    cleanup_errors.append(
                        CleanupFailure("CLI cleanup is uncertain; do not start another writer")
                    )
                put(
                    event(
                        "error",
                        request,
                        message=str(exc)
                        if isinstance(exc, ErolError)
                        else "Malformed or unavailable CLI stream",
                    )
                )
            finally:
                finished.set()

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        try:
            while not finished.is_set() or not messages.empty():
                try:
                    yield messages.get(timeout=0.1)
                except queue.Empty:
                    continue
            if cleanup_errors:
                raise cleanup_errors[0]
        finally:
            self.cancel()
            thread.join(timeout=15)
            if thread.is_alive():
                raise CleanupFailure("CLI cleanup did not finish; do not start another writer")
            if schema_directory is not None:
                schema_directory.cleanup()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ErolError("Provider redirects are refused; configure its final API endpoint")


class APIAdapter:
    def __init__(self, connection: Connection, root: Path):
        self.connection, self.root = connection, root
        self.stopped = threading.Event()
        self.response: Any = None
        self.opener = urllib.request.build_opener(NoRedirect())

    def capabilities(self) -> dict:
        if not os.environ.get(self.connection.key_env or ""):
            raise ErolError("API key environment variable is missing")
        return {
            "available": True,
            "stream": True,
            "resume": False,
            "authentication": "environment_present_not_network_verified",
        }

    def models(self) -> list[Model]:
        self.capabilities()
        return self.connection.models

    def discover_models(self) -> list[str]:
        """Explicit /models refresh checks the account without invoking a model."""
        data = self._http("/models", None)
        rows = data.get("models", data.get("data", []))
        return [
            m.get("id", m.get("name", "").removeprefix("models/"))
            for m in rows
            if isinstance(m, dict)
        ]

    def cancel(self) -> None:
        self.stopped.set()
        if self.response is not None:
            try:
                self.response.close()
            except OSError:
                pass

    def resume(self, request: Request, session: str) -> Iterator[dict]:
        raise ErolError("API resumes use EROL task summaries, not native CLI session ids")

    def _http(self, path: str, payload: dict | None, stream: bool = False) -> Any:
        self.capabilities()
        key = os.environ[self.connection.key_env or ""]
        kind = self.connection.kind
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
        }
        if kind == "anthropic":
            headers.update({"x-api-key": key, "anthropic-version": "2023-06-01"})
        elif kind == "gemini":
            headers["x-goog-api-key"] = key
        else:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(
            (self.connection.base_url or "") + path,
            data=canonical(payload).encode("utf-8") if payload is not None else None,
            headers=headers,
            method="POST" if payload is not None else "GET",
        )
        try:
            response = self.opener.open(req, timeout=15)
        except urllib.error.HTTPError as exc:
            raise ErolError(
                f"API request failed (HTTP {exc.code}); inspect account/model access"
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ErolError("API connection unavailable or timed out") from None
        if stream:
            self.response = response
            return response
        with response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ErolError("API response exceeds size limit")
        return json.loads(raw)

    def _chunks(self, path: str, payload: dict) -> Iterator[dict]:
        response = self._http(path, payload, True)
        total = 0
        lines: list[str] = []
        try:
            while not self.stopped.is_set():
                raw = response.readline(1024 * 1024 + 1)
                if not raw:
                    break
                total += len(raw)
                if total > MAX_RESPONSE or len(raw) > 1024 * 1024:
                    raise ErolError("API stream exceeds output limit")
                line = raw.decode("utf-8").rstrip("\r\n")
                if not line:
                    if lines:
                        value = "\n".join(lines)
                        lines.clear()
                        if value == "[DONE]":
                            return
                        yield json.loads(value)
                elif line.startswith("data:"):
                    lines.append(line[5:].lstrip())
            if lines and not self.stopped.is_set():
                value = "\n".join(lines)
                if value != "[DONE]":
                    yield json.loads(value)
        finally:
            response.close()
            self.response = None

    def stream(
        self,
        request: Request,
        *,
        budget: Budget,
        tools: list[dict],
        dispatch: Callable[[str, dict], str],
        max_rounds: int = 30,
    ) -> Iterator[dict]:
        kind = self.connection.kind
        messages: list[dict] = [{"role": "user", "content": request.prompt}]
        openai_input: list[dict] = [{"role": "user", "content": request.prompt}]
        gemini_contents: list[dict] = [{"role": "user", "parts": [{"text": request.prompt}]}]
        started = time.monotonic()
        for _round in range(max_rounds):
            if self.stopped.is_set():
                yield event("final", request, completed=False, reason="cancelled")
                return
            if time.monotonic() - started >= request.timeout:
                raise ErolError("API task turn timed out")
            if kind == "openai":
                payload = {
                    "model": request.model.id,
                    "input": openai_input,
                    "stream": True,
                    "store": False,
                    "max_output_tokens": request.model.output_limit,
                    "tools": [
                        {
                            "type": "function",
                            "name": t["name"],
                            "description": t["description"],
                            "parameters": t["parameters"],
                        }
                        for t in tools
                    ],
                }
                if request.effort != "none":
                    payload["reasoning"] = {"effort": request.effort}
                path = "/responses"
            elif kind == "anthropic":
                payload = {
                    "model": request.model.id,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": request.model.output_limit,
                    "tools": [
                        {
                            "name": t["name"],
                            "description": t["description"],
                            "input_schema": t["parameters"],
                        }
                        for t in tools
                    ],
                }
                if request.model.id.startswith(("claude-opus-5", "claude-sonnet-5")):
                    payload.update(
                        {
                            "thinking": {"type": "adaptive"},
                            "output_config": {"effort": request.effort},
                        }
                    )
                path = "/messages"
            elif kind == "gemini":
                payload = {
                    "contents": gemini_contents,
                    "tools": [
                        {
                            "functionDeclarations": [
                                {
                                    "name": t["name"],
                                    "description": t["description"],
                                    "parametersJsonSchema": t["parameters"],
                                }
                                for t in tools
                            ]
                        }
                    ],
                    "generationConfig": {
                        "maxOutputTokens": request.model.output_limit,
                        "thinkingConfig": {"thinkingLevel": request.effort},
                    },
                }
                path = f"/models/{request.model.id}:streamGenerateContent?alt=sse"
            else:
                payload = {
                    "model": request.model.id,
                    "messages": messages,
                    "stream": True,
                    "max_tokens": request.model.output_limit,
                    "stream_options": {"include_usage": True},
                    "tools": [{"type": "function", "function": t} for t in tools],
                }
                path = "/chat/completions"
            if not tools:
                payload.pop("tools", None)
            if (
                len(canonical(payload).encode("utf-8")) + request.model.output_limit
                > request.model.context_window
            ):
                raise ErolError(
                    "Accumulated API context exceeds the model profile; start a narrower task"
                )
            reserved = budget.reserve(request.model, payload)
            counts: dict = {}
            calls: dict[Any, dict] = {}
            text = ""
            native_parts: list[dict] = []
            final_output: list[dict] = []
            success = False
            blocks: dict[int, dict] = {}
            try:
                for data in self._chunks(path, payload):
                    if time.monotonic() - started >= request.timeout:
                        raise ErolError("API turn exceeded its time budget")
                    if not isinstance(data, dict):
                        raise ErolError("Invalid API event envelope")
                    delta = ""
                    if kind == "openai":
                        typ = data.get("type")
                        if typ == "response.output_text.delta":
                            delta = data.get("delta", "")
                        elif typ == "response.completed":
                            response = data.get("response", {})
                            counts.update(usage_counts(response.get("usage"), kind))
                            final_output = response.get("output", [])
                            success = response.get("status", "completed") == "completed"
                            for part in final_output:
                                if part.get("type") == "function_call":
                                    calls[part["call_id"]] = {
                                        "id": part["call_id"],
                                        "name": part["name"],
                                        "arguments": part["arguments"],
                                    }
                        elif typ in {"error", "response.failed", "response.incomplete"}:
                            raise ErolError("OpenAI response failed or was incomplete")
                    elif kind == "anthropic":
                        typ = data.get("type")
                        if typ == "message_start":
                            counts.update(usage_counts(data.get("message", {}).get("usage"), kind))
                        elif typ == "content_block_start":
                            blocks[data["index"]] = dict(data.get("content_block", {}))
                        elif typ == "content_block_delta":
                            block = blocks.setdefault(data["index"], {})
                            item = data.get("delta", {})
                            if item.get("type") == "text_delta":
                                delta = item.get("text", "")
                                block["text"] = block.get("text", "") + delta
                            elif item.get("type") == "input_json_delta":
                                block["arguments"] = block.get("arguments", "") + item.get(
                                    "partial_json", ""
                                )
                            elif item.get("type") == "thinking_delta":
                                block["thinking"] = block.get("thinking", "") + item.get(
                                    "thinking", ""
                                )
                            elif item.get("type") == "signature_delta":
                                block["signature"] = block.get("signature", "") + item.get(
                                    "signature", ""
                                )
                        elif typ == "message_delta":
                            counts.update(usage_counts(data.get("usage"), kind))
                            success = data.get("delta", {}).get("stop_reason") in {
                                "end_turn",
                                "tool_use",
                            }
                        elif typ == "error":
                            raise ErolError("Anthropic stream returned an error")
                    elif kind == "gemini":
                        counts.update(usage_counts(data.get("usageMetadata"), kind))
                        if "error" in data:
                            raise ErolError("Gemini stream returned an error")
                        for candidate in data.get("candidates", []):
                            for part in candidate.get("content", {}).get("parts", []):
                                native_parts.append(part)
                                if part.get("text") and not part.get("thought"):
                                    delta += part["text"]
                                if "functionCall" in part:
                                    fc = part["functionCall"]
                                    call_id = str(len(calls))
                                    calls[call_id] = {
                                        "id": call_id,
                                        "name": fc["name"],
                                        "arguments": fc.get("args", {}),
                                    }
                            success = success or candidate.get("finishReason") == "STOP"
                    else:
                        counts.update(usage_counts(data.get("usage"), kind))
                        if "error" in data:
                            raise ErolError("Compatible API returned an error")
                        for choice in data.get("choices", []):
                            item = choice.get("delta", {})
                            delta += item.get("content") or ""
                            for call in item.get("tool_calls", []):
                                value = calls.setdefault(
                                    call["index"], {"id": "", "name": "", "arguments": ""}
                                )
                                value["id"] += call.get("id", "")
                                value["name"] += call.get("function", {}).get("name", "")
                                value["arguments"] += call.get("function", {}).get("arguments", "")
                            success = success or choice.get("finish_reason") in {
                                "stop",
                                "tool_calls",
                            }
                    if delta:
                        text += delta
                        yield event("text_delta", request, text=visible(delta))
                if kind == "anthropic":
                    for i, block in blocks.items():
                        if block.get("type") == "tool_use":
                            arguments = json.loads(block.pop("arguments", "{}"))
                            block["input"] = arguments
                            calls[i] = {
                                "id": block["id"],
                                "name": block["name"],
                                "arguments": arguments,
                            }
                if self.stopped.is_set():
                    success = False
            finally:
                accounted = budget.settle(request.model, reserved, counts)
            yield event("usage", request, **accounted)
            if not success:
                yield event(
                    "final",
                    request,
                    completed=False,
                    reason="cancelled" if self.stopped.is_set() else "incomplete_stream",
                )
                return
            if not calls:
                report = implementation_report(text) if request.role == "implementer" else None
                yield event(
                    "final",
                    request,
                    completed=request.role != "implementer"
                    or bool(report and report["status"] == "implemented"),
                    report=report,
                    native_session=None,
                )
                return
            if kind == "openai":
                openai_input.extend(final_output)
            elif kind == "anthropic":
                messages.append(
                    {"role": "assistant", "content": [blocks[i] for i in sorted(blocks)]}
                )
            elif kind == "gemini":
                gemini_contents.append({"role": "model", "parts": native_parts})
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": text or None,
                        "tool_calls": [
                            {
                                "id": c["id"],
                                "type": "function",
                                "function": {"name": c["name"], "arguments": c["arguments"]},
                            }
                            for c in calls.values()
                        ],
                    }
                )
            tool_results = []
            for call in calls.values():
                if self.stopped.is_set():
                    yield event("final", request, completed=False, reason="cancelled")
                    return
                arguments = call["arguments"]
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                if not isinstance(arguments, dict):
                    raise ErolError("Tool arguments must be an object")
                yield event("tool_start", request, tool=visible(call["name"]))
                failed = False
                failure_message = None
                try:
                    output = dispatch(call["name"], arguments)
                except ErolError as exc:
                    failed = True
                    failure_message = visible(str(exc))
                    output = canonical({"error": str(exc)})
                yield event(
                    "tool_result",
                    request,
                    tool=visible(call["name"]),
                    summary=visible(output[:500]),
                    is_error=failed,
                    error=failure_message,
                )
                if call["name"] in {"write_file", "delete_file"}:
                    changed = json.loads(output)
                    if isinstance(changed, dict) and "path" in changed:
                        yield event("file_change", request, **changed)
                if kind == "openai":
                    openai_input.append(
                        {"type": "function_call_output", "call_id": call["id"], "output": output}
                    )
                elif kind == "anthropic":
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call["id"],
                            "content": output,
                            "is_error": failed,
                        }
                    )
                elif kind == "gemini":
                    tool_results.append(
                        {"functionResponse": {"name": call["name"], "response": {"result": output}}}
                    )
                else:
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": output})
            if kind == "anthropic":
                messages.append({"role": "user", "content": tool_results})
            elif kind == "gemini":
                gemini_contents.append({"role": "user", "parts": tool_results})
        raise ErolError("API tool-round limit reached; narrow the task or resume")


def adapter(connection: Connection, root: Path) -> CLIAdapter | APIAdapter:
    return (
        CLIAdapter(connection, root)
        if connection.kind in CLI_KINDS
        else APIAdapter(connection, root)
    )
