"""Explainable native agent recommendations; never launches or configures a host."""

import os
from pathlib import Path

from .common import ErolError, canonical
from .connections import KINDS, Connection, ConnectionStore, Settings, classify, route, seed_models


def current_harness(value: str = "auto") -> str | None:
    if value != "auto":
        if value not in KINDS:
            raise ErolError("Unsupported planning harness")
        return value
    codex = bool(os.environ.get("CODEX_THREAD_ID"))
    claude = bool(os.environ.get("CLAUDECODE"))
    return "codex" if codex and not claude else "claude" if claude and not codex else None


def recommend_agents(
    plan: dict,
    home: Path,
    root: Path,
    *,
    harness: str = "auto",
    model: str | None = None,
    effort: str | None = None,
) -> dict:
    host = current_harness(harness)
    settings = ConnectionStore(home, root).settings
    connections = [c for c in settings.connections if c.enabled and c.kind == host]
    # A profile recommendation is not account access evidence. Unknown or disabled
    # configured connections must never silently become another provider.
    if (
        not connections
        and host in {"codex", "claude"}
        and not any(c.kind == host for c in settings.connections)
    ):
        connections = [Connection(host, host, models=seed_models(host))]
    available = {
        c.id: [m for m in c.models if model is not None or effort is None or effort in m.efforts]
        for c in connections
    }
    policy = Settings.load(
        {
            **settings.to_dict(),
            "connections": [c.to_dict() for c in connections],
            "preferred_connection": settings.preferred_connection
            if settings.preferred_connection in available
            else None,
        }
    )
    result = {**plan, "agents": []}
    for entry in plan["agents"]:
        role = entry["name"]
        context = (
            len(
                canonical(
                    {
                        "context": plan["context"]["packet"],
                        "role": entry,
                        "tools": plan["tool_categories"],
                    }
                ).encode("utf-8")
            )
            + 4096
        )
        requested_role = "planner" if role == "planner" else role
        try:
            if not host or not available:
                raise ErolError("Host/model inventory unknown; inherit current host settings")
            override = model
            if model and model not in {f"{c.id}:{m.id}" for c in connections for m in c.models}:
                matching = [
                    f"{c.id}:{m.id}" for c in connections for m in c.models if m.id == model
                ]
                if len(matching) != 1:
                    raise ErolError("Manual model is absent or ambiguous in host profiles")
                override = matching[0]
            choice = route(
                policy,
                plan["task"],
                available,
                role=requested_role,
                override=override,
                context_tokens=context,
                plan=plan,
            )
            selected = next(
                m
                for c in connections
                if c.id == choice["connection"]
                for m in c.models
                if m.id == choice["model"]
            )
            if effort is not None:
                if effort not in selected.efforts:
                    raise ErolError("Manual effort is unsupported by the selected model profile")
                choice.update(effort=effort, effort_reason="explicit user preference")
            choice.update(
                status="recommended",
                model_access_verified=False,
                manual_model=model is not None,
                manual_effort=effort is not None,
            )
        except ErolError as exc:
            if model is not None or effort is not None:
                raise
            assessment = classify(plan["task"], plan)
            choice = {
                "status": "inherit",
                "model": None,
                "effort": None,
                "recommended_effort": "high"
                if assessment["risk"]
                else "medium"
                if assessment["complexity"] != "small"
                else "low",
                "reason": str(exc),
                "eligible_alternatives": [],
                "model_access_verified": False,
                "behavioral_success_rate": None,
            }
        choice["binding"] = (
            {"model": choice["model"], "reasoning_effort": choice["effort"]}
            if host == "codex" and choice["status"] == "recommended"
            else {
                "model": choice["model"],
                **({"effort": choice["effort"]} if choice["effort"] != "none" else {}),
            }
            if host == "claude" and choice["status"] == "recommended"
            else None
        )
        result["agents"].append({**entry, "model_selection": choice})
    result["agent_selection_policy"] = {
        "harness": host,
        "mode": "automatic" if model is None and effort is None else "manual",
        "execution_supported": False,
        "native_binding": host in {"codex", "claude"},
        "criteria": [
            "role and actual task risk",
            "full prepared context proxy and output reserve",
            "profile tools and supported efforts",
            "budget and preferred connection",
            "resource/latency priors; no unmeasured success rates",
        ],
        "context_limit": (
            "Native hidden instructions and runtime tools are unknown; recheck before spawning"
        ),
        "application": (
            "Use binding only when the current delegation tool accepts it; "
            "otherwise inherit and report"
        ),
    }
    return result
