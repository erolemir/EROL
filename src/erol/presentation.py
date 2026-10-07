"""Human-readable terminal views; machine command results stay unchanged."""

from __future__ import annotations

import json

from .i18n import message
from .resultview import changes_view, files_view

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


def task_result(record: dict, language: str = "en") -> str:
    """One result view based only on observed task records."""
    tr = language == "tr"
    selection = record.get("selection", {})
    lines = [record.get("summary", "")]
    lines.append(
        ("Kullanılan skill: " if tr else "Admitted skills: ")
        + (", ".join(record.get("selected_skills", [])) or "—")
    )
    if selection:
        lines.append(
            f"{selection['connection']}:{selection['model']} · {selection['effort']} · "
            + selection["reason"]
        )
    lines.append("Değişen dosyalar:" if tr else "Changed files:")
    lines.extend(
        changes_view(record.get("changes", []), record.get("project_root", ""), language) or ["—"]
    )
    checks, reviews = record.get("checks", []), record.get("reviews", [])
    lines.append(
        ("Test / review: " if tr else "Checks / review: ")
        + f"{sum(c.get('passed') is True for c in checks)}/{len(checks)} · "
        + f"{sum(r.get('approved') is True for r in reviews)}/{len(reviews)}"
    )
    if record.get("artifact_directory"):
        lines.extend(files_view({**record, "changes": []}, language))
    reason = record.get("error") or (record.get("verification") or {}).get("missing_checks_reason")
    if reason:
        lines.append(str(reason))
    lines.append(
        ("Sonraki adım: " if tr else "Next step: ")
        + ("—" if record.get("status") == "completed" else "/tests · /diff · /usage")
    )
    if record.get("changes") or record.get("artifact_directory"):
        lines.append("/files · /diff NUMBER [PAGE] · /tests · /usage")
    return "\n".join(line for line in lines if line)


def present(result: dict, language: str) -> str:
    def t(key: str, **values) -> str:
        return message(language, key, **values)

    def status(value) -> str:
        return t(value) if value in STATUS_KEYS else str(value)

    lines: list[str] = []
    if "model_comparison" in result:
        for choice in result["model_comparison"]:
            lines.append(
                choice["role"]
                + " · "
                + choice.get("model", "—")
                + " · "
                + choice.get("effort", "—")
            )
            lines.append(choice["reason"])
            if choice.get("effort_reason"):
                lines.append(choice["effort_reason"])
            for profile in choice.get("eligible_alternatives", []):
                lines.append(
                    f"  {profile['connection']}:{profile['model']} · L{profile['level']} · "
                    + f"context {profile['context_window']} · {profile['profile_source']}"
                )
        lines.append(result["note"])
    elif "commands" in result:
        groups = [
            (
                "help_conversation",
                [
                    "general",
                    "research",
                    "project",
                    "my-projects",
                    "chats",
                    "rename",
                    "plan",
                    "skills",
                    "new",
                    "resume",
                ],
            ),
            (
                "help_connections",
                ["connect", "providers", "models", "model", "effort", "settings", "language"],
            ),
            ("help_evidence", ["files", "diff", "tests", "usage", "status"]),
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
        profiles = result.get("profiles", {}) if "model_choices" not in result else {}
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
        if "model_choices" in result:
            for index, choice in enumerate(result["model_choices"], 1):
                marker = " *" if choice["value"] == result["model"] else ""
                lines.append(
                    f"{index}. {choice['value']}{marker} · " + ", ".join(choice["efforts"])
                )
                profile = choice["profile"]
                native = kinds.get(choice["value"].partition(":")[0]) in {
                    "codex",
                    "claude",
                    "antigravity",
                }
                prices = (profile.get("input_price"), profile.get("output_price"))
                cost = (
                    t("cli_subscription")
                    if native
                    else (
                        f"${prices[0]:g} / ${prices[1]:g} / 1M token"
                        if all(p is not None for p in prices)
                        else t("unknown_price")
                    )
                )
                lines.append(
                    f"   L{profile['level']} · context {profile['context_window']} · {cost}"
                )
                lines.append("   " + t("access_note", value=choice["access"]))
            lines.append(
                t("model_selected", value=result["model"]) + " · effort: " + result["effort"]
            )
            lines.append("/model NUMBER · /model NAME · /model CONNECTION:MODEL · /model auto")
            lines.append("/effort auto · /effort VALUE · /models refresh")
    elif "files" in result:
        lines.extend(files_view(result["files"], language))
    elif "diff" in result:
        root = result.get("project_root", "")
        page = result.get("diff_page")
        command = result.get("diff_command", "/diff")
        if result.get("previous_task"):
            lines.append(t("previous", task_id=result["previous_task"]))
        if page:
            lines.extend(
                changes_view(result["diff"], root, language, preview=False, start=page["index"])
            )
            lines.append(f"{page['page']}/{page['pages']}")
            lines.extend(page["lines"])
            if page["page"] < page["pages"]:
                lines.append(f"{command} {page['index']} {page['page'] + 1}")
        else:
            for index, step in enumerate(result.get("continuation_history", []), 1):
                lines.append(t("previous", task_id=step["task_id"]))
                lines.extend(
                    changes_view(
                        step["changes"], step.get("project_root", root), language, preview=False
                    )
                )
                lines.append(f"/diff previous {index} NUMBER [PAGE]")
            lines.extend(
                changes_view(result["diff"], root, language, preview=command == "/diff")
                or [t("no_changes")]
            )
            lines.append(f"{command} NUMBER [PAGE] · /files")
    elif "projects" in result:
        lines.append("── " + t("projects_title"))
        for index, row in enumerate(result["projects"], 1):
            lines.append(f"{index}. {row['name']} · {row['id']}")
            lines.append("  " + row["root"])
            if not row["available"]:
                lines.append("  " + t("missing_project"))
        if not result["projects"]:
            lines.append(t("no_projects"))
        lines.append(t("projects_hint"))
    elif "saved_chat" in result:
        record = result["saved_chat"]
        lines.append(
            t(
                "chat_title",
                title=record.get("title") or record.get("task", "")[:80] or record["id"],
            )
        )
        lines.append(record["id"] + " · " + status(record["status"]))
        lines.append(t("saved_chat_note"))
        lines.append(task_result(record, language))
        for check in record.get("checks", []):
            lines.append(
                check["name"] + " · " + t("check_passed" if check.get("passed") else "check_failed")
            )
    elif "project" in result:
        project = result["project"]
        lines.append("── " + t("status_title"))
        lines.append(str(project["root"]) if project else t("no_project"))
        for key in ("mode", "session", "status"):
            if key in result:
                value = status(result[key]) if key == "status" else result[key]
                lines.append(f"{t(key + '_label')}: {value}")
        if "model_preference" in result:
            lines.append(
                t("model_selected", value=result["model_preference"])
                + " · effort: "
                + result["effort_preference"]
            )
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
        lines.append("effort: " + result.get("effort", "auto"))
        lines.append("/model · /models · /effort auto")
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
        for index, record in enumerate(result["sessions"], 1):
            lines.append(
                f"{index}. {record.get('title') or record['id']}  ·  "
                f"{status(record['status'])}  ·  {record.get('updated', '')}"
            )
            lines.append("  " + record["id"])
            lines.append("  " + record.get("summary", record.get("task", ""))[:160])
        if not result["sessions"]:
            lines.append(t("no_sessions"))
        lines.append(t("chats_hint", next=result.get("page", 1) + 1))
        lines.append("/resume SESSION_ID · /resume SESSION_ID continue")
    elif "session" in result or ("summary" in result and "id" in result):
        lines.append(t("session_label") + ": " + result.get("session", result.get("id", "")))
        if result.get("title"):
            lines.append(t("chat_title", title=result["title"]))
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
