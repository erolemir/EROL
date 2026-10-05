"""Human-readable terminal views; machine command results stay unchanged."""

from __future__ import annotations

import json

from .i18n import message

STATUS_KEYS = {
    "ready",
    "running",
    "completed",
    "needs_attention",
    "cancelled",
    "implemented_unverified",
    "waiting_budget",
}


def api_observed(usage: dict, events: list[dict] | None = None) -> bool:
    """An allocated budget alone is not evidence that API billing occurred."""
    return any(
        usage.get(key, 0) > 0
        for key in ("api_calls", "accounted_usd", "pending_reserved_usd", "unreported_reserved_usd")
    ) or any(usage_transport(item) == "api" for item in events or [])


def usage_transport(item: dict) -> str:
    data = item.get("data", {})
    if data.get("source") in {"cli", "native_cli_usage"}:
        return "cli"
    transport = data.get("transport", item.get("transport"))
    if transport in {"cli", "api"}:
        return transport
    if data.get("billing_evidence") or data.get("estimated_cost_usd") is not None:
        return "api"
    return "unknown"


def token_summary(events: list[dict], transport: str, language: str) -> str:
    selected = [item for item in events if usage_transport(item) == transport]
    totals: dict[str, int | None] = {}
    for key in ("input_tokens", "output_tokens"):
        values = [
            item.get("data", {}).get("counts", item.get("data", {})).get(key) for item in selected
        ]
        totals[key] = sum(values) if values and all(type(v) is int for v in values) else None
    input_count, output_count = totals["input_tokens"], totals["output_tokens"]
    total = (
        input_count + output_count if input_count is not None and output_count is not None else None
    )
    return message(
        language,
        "token_counts",
        input=input_count if input_count is not None else "?",
        output=output_count if output_count is not None else "?",
        total=total if total is not None else "?",
    )


def usage_summary(usage: dict, events: list[dict], language: str, transport: str = "") -> str:
    parts = []
    if transport == "cli" or any(usage_transport(item) == "cli" for item in events):
        parts.append("CLI · " + token_summary(events, "cli", language))
        parts.append(message(language, "cli_quota_unknown"))
    if api_observed(usage, events):
        parts.append("API · " + token_summary(events, "api", language))
        parts.append(message(language, "accounted") + f" ${usage.get('accounted_usd', 0):.4f}")
        if usage.get("unreported_reserved_usd", 0):
            parts.append(
                message(language, "unreported_reservation", amount=usage["unreported_reserved_usd"])
            )
    if not parts:
        parts.append(message(language, "no_usage"))
    return " · ".join(parts)


def present(result: dict, language: str) -> str:
    def t(key: str, **values) -> str:
        return message(language, key, **values)

    def status(value) -> str:
        return t(value) if value in STATUS_KEYS else str(value)

    lines: list[str] = []
    if "commands" in result:
        groups = [
            ("help_conversation", ["general", "research", "project", "plan", "new", "resume"]),
            (
                "help_connections",
                ["connect", "providers", "models", "model", "settings", "language"],
            ),
            ("help_evidence", ["diff", "tests", "usage", "status"]),
            ("help_display", ["clear", "view", "motion", "logo", "help", "exit"]),
        ]
        for title, names in groups:
            lines.extend(["", "── " + t(title)])
            for name in names:
                if "/" + name in result["commands"]:
                    lines.append(f"/{name}  ·  {result['commands']['/' + name]}")
        lines.extend(["", result["keys"]])
    elif "providers" in result and "selection" not in result:
        lines.append("── " + t("help_connections"))
        for row in result["providers"]:
            state = t("ready") if row.get("available") else row.get("reason", t("unavailable"))
            lines.append(f"{row['id']}  ·  {row['kind']}  ·  {state}")
            if row.get("available"):
                lines.append("  " + t("access_note", value=row.get("model_access", "unknown")))
        profiles = result.get("profiles", {})
        kinds = {row["id"]: row["kind"] for row in result["providers"]}
        for connection, models in profiles.items():
            for model in models:
                if kinds.get(connection) in {"codex", "claude", "antigravity"}:
                    lines.append(
                        f"  {connection}:{model['id']}  ·  L{model['level']}  ·  "
                        + t("cli_subscription")
                    )
                    continue
                prices = (model.get("input_price"), model.get("output_price"))
                cost = (
                    f"${prices[0]:g} / ${prices[1]:g}"
                    if all(p is not None for p in prices)
                    else t("unknown_price")
                )
                lines.append(
                    f"  {connection}:{model['id']}  ·  L{model['level']}  ·  {cost} / 1M token"
                )
        if not result["providers"]:
            lines.append(t("no_connections"))
    elif "project" in result:
        project = result["project"]
        lines.append("── " + t("status_title"))
        lines.append(str(project["root"]) if project else t("no_project"))
        for key in ("mode", "session", "status"):
            if key in result:
                value = status(result[key]) if key == "status" else result[key]
                lines.append(f"{t(key + '_label')}: {value}")
        if "selection" in result:
            selection = result["selection"]
            lines.extend(
                [
                    f"{selection['connection']}:{selection['model']} · {selection['effort']}",
                    selection["reason"],
                    t("not_started"),
                ]
            )
            names = result.get("context", {}).get("selected_skills", [])
            lines.append(t("skills_used", names=", ".join(names)) if names else t("skills_none"))
        if result.get("native_cli_policy"):
            lines.append(t("native_policy"))
    elif "settings" in result:
        lines.append("── " + t("settings_title"))
        for key, value in result["settings"].items():
            if key not in {"schema_version", "connections"}:
                lines.append(f"{key}  ·  {json.dumps(value, ensure_ascii=False)}")
        lines.append(t("settings_example"))
    elif "model" in result:
        lines.append(t("model_selected", value=result["model"]))
    elif "usage" in result:
        usage = result["usage"]
        events = result.get("events", [])
        if not usage and not events:
            lines.append(t("no_usage"))
        else:
            lines.append("── " + t("usage_title"))
            for key in (
                "budget_usd",
                "accounted_usd",
                "pending_reserved_usd",
                "unreported_reserved_usd",
                "remaining_usd",
                "api_calls",
            ):
                if key in usage and api_observed(usage, events):
                    value = usage[key]
                    lines.append(f"{key}  ·  {value if key == 'api_calls' else f'${value:.4f}'}")
            for item in events:
                data = item["data"]
                counts = data.get("counts", data)
                lines.append(
                    f"{item.get('connection', '?')}:{item.get('model', '?')}  ·  "
                    f"{counts.get('input_tokens', '?')} → {counts.get('output_tokens', '?')} "
                    f"token  ·  {data.get('source', 'provider')}"
                )
            if any(usage_transport(item) == "cli" for item in events):
                lines.append("CLI · " + token_summary(events, "cli", language))
                lines.append(t("cli_quota_unknown"))
            if api_observed(usage, events):
                lines.append("API · " + token_summary(events, "api", language))
                lines.append(t("invoice_note"))
            elif not events:
                lines.append(t("no_usage"))
    elif "tests" in result:
        lines.append("── " + t("tests_title"))
        checks = result["tests"]
        if not checks:
            lines.append(t("no_tests"))
        for check in checks:
            outcome = t("check_passed") if check.get("passed") is True else t("check_failed")
            lines.append(
                f"{check.get('id', check.get('name', '?'))}  ·  {outcome}  ·  "
                f"exit {check.get('exit_code', '?')}"
            )
            lines.append("  " + " ".join(check.get("argv", [])))
            for key in ("reason", "stdout", "stderr", "output"):
                if check.get(key):
                    lines.append(str(check[key]))
    elif "sessions" in result:
        lines.append("── " + t("sessions_title"))
        for record in result["sessions"]:
            lines.append(
                f"{record['id']}  ·  {status(record['status'])}  ·  {record.get('updated', '')}"
            )
            lines.append("  " + record.get("summary", record.get("task", ""))[:160])
        if not result["sessions"]:
            lines.append(t("no_sessions"))
        lines.append("/resume SESSION_ID · /resume SESSION_ID continue")
    elif "session" in result or ("summary" in result and "id" in result):
        lines.append(t("session_label") + ": " + result.get("session", result.get("id", "")))
        if result.get("summary"):
            lines.append(result["summary"])
    elif "phases" in result:
        lines.extend(["── " + t("plan_title"), result.get("task", ""), t("not_started")])
        for phase in result["phases"]:
            lines.append(f"{phase['name']}  ·  {phase['goal']}")
        names = result.get("context", {}).get("selected_skills", [])
        if names:
            lines.append("Skills: " + ", ".join(names))
        for limitation in result.get("limitations", []):
            lines.append(str(limitation))
    else:
        lines.append(json.dumps(result, ensure_ascii=False, indent=2))
    return "\n".join(lines) + "\n"
