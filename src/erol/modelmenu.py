"""Displayed model choices, validated against the current provider inventory."""

from dataclasses import asdict

from .common import ErolError, digest


def inventory(engine, *, refresh: bool = False) -> tuple[list[dict], list[dict], dict]:
    reports, models = engine.providers(refresh=refresh)
    ready = {r["id"]: r for r in reports if r.get("available")}
    choices = [
        {
            "value": f"{connection}:{model.id}",
            "efforts": model.efforts,
            "access": ready[connection].get("model_access", "unknown"),
            "profile": asdict(model),
        }
        for connection, profiles in models.items()
        if connection in ready
        for model in profiles
    ]
    return reports, choices, models


def menu(engine, *, refresh: bool = False) -> dict:
    reports, choices, models = inventory(engine, refresh=refresh)
    engine.model_choices = choices
    engine.model_configuration = digest(engine.connections.settings.to_dict())
    return {
        "providers": reports,
        "profiles": {k: [asdict(m) for m in v] for k, v in models.items()},
        "model_choices": choices,
        "model": engine.selected_model or "auto",
        "effort": engine.selected_effort or "auto",
    }


def select(engine, value: str) -> str:
    _, current, _ = inventory(engine)
    if value.isdecimal():
        if engine.model_choices is None or engine.model_configuration != digest(
            engine.connections.settings.to_dict()
        ):
            raise ErolError("Run /models first; the displayed list is missing or changed")
        number = int(value)
        if not 1 <= number <= len(engine.model_choices):
            raise ErolError("Model number is outside the displayed /models list")
        value = engine.model_choices[number - 1]["value"]
    matches = [c for c in current if c["value"] == value]
    if not matches:
        matches = [c for c in current if c["value"].partition(":")[2] == value]
    if len(matches) != 1:
        raise ErolError("Model unavailable or ambiguous; use /models then /model CONNECTION:MODEL")
    if engine.selected_effort and engine.selected_effort not in matches[0]["efforts"]:
        raise ErolError("Selected effort is unsupported; use /effort auto before changing model")
    return matches[0]["value"]


def effort(engine, value: str) -> str | None:
    if value == "auto":
        return None
    _, choices, _ = inventory(engine)
    eligible = [
        c for c in choices if not engine.selected_model or c["value"] == engine.selected_model
    ]
    if not any(value in c["efforts"] for c in eligible):
        raise ErolError("Unsupported effort for the current model; see /models or /effort auto")
    return value
