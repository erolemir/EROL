"""External connection settings and explainable model selection; no provider SDKs."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .common import ErolError, atomic_write, canonical, identifier, reject_links
from .router import normalize

KINDS = {"codex", "claude", "antigravity", "openai", "anthropic", "gemini", "compatible"}
CLI_KINDS = {"codex", "claude", "antigravity"}
DEFAULT_ENDPOINTS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
}
DEFAULT_KEY_ENVS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def number(value: Any, name: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ErolError(f"{name} must be numeric")
    if not math.isfinite(value) or not low <= value <= high:
        raise ErolError(f"{name} is outside its supported range")
    return float(value)


def endpoint(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError
        if not parsed.hostname or parsed.scheme not in {"https", "http"}:
            raise ValueError
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError
        if any(char in value for char in "\r\n\x00"):
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise ErolError("Endpoint must be HTTPS (or localhost HTTP), without credentials") from exc
    return value.rstrip("/")


@dataclass
class Model:
    id: str
    level: int = 2
    input_price: float | None = None
    output_price: float | None = None
    context_window: int = 128000
    output_limit: int = 4096
    efforts: list[str] = field(default_factory=lambda: ["low", "medium", "high"])
    tools: bool = True
    latency_rank: int = 2
    source: str = "user_configured"

    @classmethod
    def load(cls, data: dict) -> Model:
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise ErolError("Invalid model profile fields")
        try:
            model = cls(**data)
        except TypeError as exc:
            raise ErolError("A model profile needs an id") from exc
        if not isinstance(model.id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", model.id
        ):
            raise ErolError("Invalid model id")
        for name, low, high in (
            ("level", 1, 4),
            ("context_window", 1024, 4000000),
            ("output_limit", 128, 128000),
            ("latency_rank", 1, 10),
        ):
            value = getattr(model, name)
            if type(value) is not int or not low <= value <= high:
                raise ErolError(f"Invalid model {name}")
        for name in ("input_price", "output_price"):
            value = getattr(model, name)
            if value is not None:
                number(value, name, 0, 10000)
        if type(model.tools) is not bool or not isinstance(model.efforts, list):
            raise ErolError("Invalid model capabilities")
        if not model.efforts or any(
            not isinstance(e, str) or e not in {"none", "low", "medium", "high", "max"}
            for e in model.efforts
        ):
            raise ErolError("Invalid model reasoning efforts")
        if not isinstance(model.source, str) or model.source not in {
            "official_profile",
            "user_configured",
            "provider_discovered",
        }:
            raise ErolError("Invalid model profile source")
        return model


@dataclass
class Connection:
    id: str
    kind: str
    enabled: bool = True
    key_env: str | None = None
    base_url: str | None = None
    executable: str | None = None
    models: list[Model] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def load(cls, data: dict) -> Connection:
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise ErolError("Invalid connection fields; store environment names, never keys")
        data = dict(data)
        if not isinstance(data.get("models", []), list) or len(data.get("models", [])) > 100:
            raise ErolError("Connection models must be a bounded list")
        data["models"] = [Model.load(m) for m in data.get("models", [])]
        try:
            connection = cls(**data)
        except TypeError as exc:
            raise ErolError("Connection needs id and kind") from exc
        identifier(connection.id)
        if connection.kind not in KINDS or type(connection.enabled) is not bool:
            raise ErolError("Unsupported connection kind or enabled value")
        if len(connection.models) > 100 or len({m.id for m in connection.models}) != len(
            connection.models
        ):
            raise ErolError("Connection models must be unique and bounded")
        if connection.kind in CLI_KINDS:
            if connection.key_env or connection.base_url:
                raise ErolError("CLI connections use their own login, not API credentials")
            if connection.executable is not None:
                path = Path(connection.executable)
                if not path.is_absolute() or any(c in str(path) for c in "\r\n\x00"):
                    raise ErolError("CLI executable must be an absolute path")
        else:
            connection.key_env = connection.key_env or DEFAULT_KEY_ENVS.get(connection.kind)
            if not isinstance(connection.key_env, str) or not re.fullmatch(
                r"[A-Z][A-Z0-9_]{0,99}", connection.key_env
            ):
                raise ErolError("API connection needs an uppercase key_env variable name")
            if connection.executable:
                raise ErolError("API connections cannot specify executables")
            url = connection.base_url or DEFAULT_ENDPOINTS.get(connection.kind)
            if not url:
                raise ErolError("Compatible connection needs an explicit base_url")
            connection.base_url = endpoint(url)
        return connection


def seed_models(kind: str) -> list[Model]:
    catalog = json.loads(files("erol").joinpath("data/models.json").read_text("utf-8"))
    family = {"codex": "openai", "claude": "anthropic", "antigravity": "agy"}.get(kind, kind)
    return [Model.load(m) for m in catalog.get(family, [])]


@dataclass
class Settings:
    schema_version: int = 1
    api_budget_usd: float = 5.0
    policy: str = "balanced"
    max_parallel: int = 3
    connections: list[Connection] = field(default_factory=list)
    checks_path: str | None = None
    allowed_commands: list[list[str]] = field(default_factory=list)
    task_timeout_seconds: int = 3600
    max_tool_rounds: int = 30
    language: str = "auto"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def load(cls, data: dict) -> Settings:
        if not isinstance(data, dict) or set(data) - set(cls.__dataclass_fields__):
            raise ErolError("Invalid terminal settings fields")
        data = dict(data)
        if (
            not isinstance(data.get("connections", []), list)
            or len(data.get("connections", [])) > 30
        ):
            raise ErolError("Connections must be a bounded list")
        data["connections"] = [Connection.load(c) for c in data.get("connections", [])]
        try:
            value = cls(**data)
        except TypeError as exc:
            raise ErolError("Invalid terminal settings") from exc
        if type(value.schema_version) is not int or value.schema_version != 1:
            raise ErolError("Unsupported terminal settings schema")
        number(value.api_budget_usd, "api_budget_usd", 0.01, 1000)
        if value.policy not in {"balanced", "subscription_first", "cli_only"}:
            raise ErolError("Unsupported routing policy")
        if not isinstance(value.language, str) or value.language not in {"auto", "en", "tr"}:
            raise ErolError("language must be auto, en or tr")
        for name, low, high in (
            ("max_parallel", 1, 3),
            ("task_timeout_seconds", 10, 7200),
            ("max_tool_rounds", 1, 100),
        ):
            n = getattr(value, name)
            if type(n) is not int or not low <= n <= high:
                raise ErolError(f"Invalid {name}")
        if len(value.connections) > 30 or len({c.id for c in value.connections}) != len(
            value.connections
        ):
            raise ErolError("Connection ids must be unique and bounded")
        if value.checks_path is not None and (
            not isinstance(value.checks_path, str)
            or not value.checks_path
            or "\x00" in value.checks_path
        ):
            raise ErolError("Invalid checks_path")
        if not isinstance(value.allowed_commands, list) or len(value.allowed_commands) > 50:
            raise ErolError("Invalid allowed_commands")
        for argv in value.allowed_commands:
            if (
                not isinstance(argv, list)
                or not argv
                or len(argv) > 100
                or any(not isinstance(a, str) or not a or "\x00" in a for a in argv)
            ):
                raise ErolError("Commands must be nonempty literal argv arrays")
        return value


def read_settings(path: Path) -> Settings:
    reject_links(path)
    if not path.exists():
        return Settings()
    if path.stat().st_size > 256000:
        raise ErolError("Connection settings exceed size limit")
    try:
        return Settings.load(json.loads(path.read_text("utf-8")))
    except (ValueError, TypeError) as exc:
        raise ErolError("Invalid connections.json; inspect configuration fields") from exc


class ConnectionStore:
    def __init__(self, home: Path, project: Path | None = None):
        reject_links(home.expanduser().absolute())
        self.home = home.expanduser().resolve()
        if project is not None:
            project = project.resolve()
            if self.home == project or project in self.home.parents:
                raise ErolError("EROL home must be outside the project")
        self.path = self.home / "connections.json"
        self.settings = read_settings(self.path)

    def save(self) -> None:
        checked = Settings.load(self.settings.to_dict())
        atomic_write(self.path, canonical(checked.to_dict()) + "\n")
        self.settings = checked

    def connect(self, kind: str, connection_id: str | None = None, **options: Any) -> Connection:
        connection = Connection.load(
            {
                "id": connection_id or kind,
                "kind": kind,
                "models": [asdict(m) for m in seed_models(kind)],
                **options,
            }
        )
        self.settings.connections = [
            c for c in self.settings.connections if c.id != connection.id
        ] + [connection]
        self.save()
        return connection

    def get(self, connection_id: str) -> Connection:
        for connection in self.settings.connections:
            if connection.id == connection_id:
                return connection
        raise ErolError("Unknown connection; use /providers")


def classify(task: str, plan: dict | None = None) -> dict:
    """Conservative scope priors, not a calibrated model-confidence score."""
    text = normalize(task)
    risk = any(
        word in text.split()
        for word in (
            "security",
            "authorization",
            "migration",
            "production",
            "deploy",
            "guvenlik",
            "yetki",
            "odeme",
            "payment",
        )
    )
    large = len(task) > 1200 or any(
        phrase in text
        for phrase in (
            "architecture",
            "mimari",
            "multi provider",
            "coklu",
            "build an",
            "implement this plan",
            "yeni ozellik",
            "buyuk",
            "refactor",
            "yeniden tasarla",
        )
    )
    small = len(task) < 300 and any(
        phrase in text
        for phrase in (
            "typo",
            "yazim hatasi",
            "rename",
            "isim degistir",
            "one line",
            "tek satir",
            "very easy",
            "cok kolay",
            "small fix",
            "kucuk duzeltme",
        )
    )
    complexity = "large" if large or risk else "small" if small else "medium"
    return {
        "complexity": complexity,
        "risk": risk,
        "minimum_level": 3 if large or risk else 1 if small else 2,
        "reason": "scope/risk priors; unknown tasks use medium",
        "plan_roles": len((plan or {}).get("agents", [])),
    }


def route(
    settings: Settings,
    task: str,
    available: dict[str, list[Model]],
    *,
    role: str = "implementer",
    override: str | None = None,
    minimum_level: int = 0,
    excluded: set[str] | None = None,
    context_tokens: int = 4000,
    require_tools: bool = True,
    plan: dict | None = None,
) -> dict:
    assessment = classify(task, plan)
    if plan and len(plan.get("skills", [])) >= 3:
        assessment.update(
            {
                "complexity": "large",
                "minimum_level": 3,
                "reason": "substantial multi-workflow EROL plan",
            }
        )
    level = max(assessment["minimum_level"], minimum_level)
    if role == "planner":
        level = max(level, 3)
    candidates = []
    for connection in settings.connections:
        if not connection.enabled or connection.id not in available:
            continue
        cli = connection.kind in CLI_KINDS
        if connection.kind == "antigravity" and role != "implementer":
            continue
        if settings.policy == "cli_only" and not cli and override is None:
            continue
        for model in available[connection.id]:
            name = f"{connection.id}:{model.id}"
            if name in (excluded or set()) or (override and override != name):
                continue
            if (
                (not override and model.level < level)
                or (require_tools and not model.tools)
                or model.context_window < context_tokens + model.output_limit
            ):
                continue
            cost = None
            if not cli:
                if model.input_price is None or model.output_price is None:
                    continue
                cost = (
                    context_tokens * model.input_price + model.output_limit * model.output_price
                ) / 1000000
                if cost > settings.api_budget_usd:
                    continue
            # CLI quota pressure is a configurable-profile prior, never a USD measurement.
            resource_rank = (0.02 * model.level) if cli else (cost or 0)
            priority = 0 if settings.policy == "subscription_first" and cli else 1
            candidates.append(
                ((priority, resource_rank, model.latency_rank, name), connection, model, cost)
            )
    if not candidates:
        raise ErolError(
            "No eligible model: connect a provider, configure "
            "prices/capabilities, or adjust the budget"
        )
    _, connection, model, cost = min(candidates, key=lambda c: c[0])
    effort = (
        "high"
        if assessment["risk"] or role == "planner"
        else "low"
        if assessment["complexity"] == "small"
        else "medium"
    )
    if effort not in model.efforts:
        effort = model.efforts[0]
    return {
        "connection": connection.id,
        "model": model.id,
        "role": role,
        "effort": effort,
        "assessment": assessment,
        "estimated_request_usd": cost,
        "reason": (
            f"{assessment['complexity']} task; eligible capability level {model.level}; "
            f"{settings.policy} resource ranking"
        ),
        "profile_source": model.source,
        "behavioral_success_rate": None,
    }
