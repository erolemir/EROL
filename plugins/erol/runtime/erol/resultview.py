"""Bounded, navigable views of observed changes and output files."""

from pathlib import Path

from .common import ErolError


def full_path(root: str, relative: str) -> str:
    path = Path(relative)
    if not root or path.is_absolute() or ".." in path.parts:
        return relative
    return str(Path(root) / path)


def changes_view(
    changes: list[dict], root: str, language: str, *, preview: bool = True, start: int = 1
) -> list[str]:
    tr = language == "tr"
    labels = {"added": "Eklendi", "modified": "Değişti", "deleted": "Silindi"} if tr else {}
    lines = []
    for index, change in enumerate(changes, start):
        patch = change.get("diff", "").splitlines()
        added = change.get(
            "added_lines", sum(s.startswith("+") and not s.startswith("+++ b/") for s in patch)
        )
        removed = change.get(
            "removed_lines", sum(s.startswith("-") and not s.startswith("--- a/") for s in patch)
        )
        state = change.get("status", "changed")
        stats = "binary" if change.get("binary") else f"+{added} / -{removed}"
        if change.get("diff_truncated"):
            stats += " · " + ("kayıt kesilmiş" if tr else "stored diff truncated")
        lines.append(f"{index}. {labels.get(state, state)} · {stats}")
        lines.append("   " + full_path(root, change["path"]))
        if preview and index <= 8:
            lines.extend("   " + s for s in patch[:12])
            if len(patch) > 12:
                lines.append(f"   … /diff {index}")
    return lines


def diff_result(record: dict, root: str, selector: str) -> dict:
    if selector.startswith("previous "):
        step_text, _, rest = selector[9:].partition(" ")
        steps = record.get("continuation_history", [])
        if not step_text.isdecimal() or not 1 <= int(step_text) <= len(steps):
            raise ErolError("Use /diff previous STEP [NUMBER [PAGE]]")
        step = steps[int(step_text) - 1]
        result = diff_result({"changes": step["changes"]}, step.get("project_root", root), rest)
        result["diff_command"] = f"/diff previous {int(step_text)}"
        result["previous_task"] = step["task_id"]
        return result
    changes = record.get("changes", [])
    if not selector.strip():
        return {
            "diff": changes,
            "project_root": root,
            "continuation_history": record.get("continuation_history", []),
        }
    exact_path = any(selector.strip() in {c["path"], full_path(root, c["path"])} for c in changes)
    text = selector.strip()
    value, _, page_text = text.rpartition(" ")
    quoted = text.startswith(('"', "'"))
    numeric_page = value.isdecimal() and page_text.isdecimal()
    if quoted:
        end = text.find(text[0], 1)
        if end < 0:
            raise ErolError("Unclosed diff path quote")
        value, tail = text[1:end], text[end + 1 :].strip()
        if tail and not tail.isdecimal():
            raise ErolError("Use /diff PATH [PAGE]")
        page = int(tail) if tail else 1
    elif (exact_path and not numeric_page) or not value or not page_text.isdecimal():
        value, page = selector.strip(), 1
    else:
        page = int(page_text)
    if value.isdecimal() and not quoted:
        matches = [(i, c) for i, c in enumerate(changes, 1) if int(value) == i]
    else:
        matches = [
            (i, c)
            for i, c in enumerate(changes, 1)
            if value.removeprefix("./") == c["path"] or value == full_path(root, c["path"])
        ]
    if len(matches) != 1:
        raise ErolError("Use /diff NUMBER [PAGE] or /diff PATH from the current change list")
    index, change = matches[0]
    patch = change.get("diff", "").splitlines()
    pages = max(1, (len(patch) + 99) // 100)
    if not 1 <= page <= pages:
        raise ErolError(f"Diff page must be 1..{pages}")
    return {
        "diff": [change],
        "project_root": root,
        "diff_page": {
            "index": index,
            "page": page,
            "pages": pages,
            "lines": patch[(page - 1) * 100 : page * 100],
        },
    }


def files_view(record: dict, language: str) -> list[str]:
    tr = language == "tr"
    lines = []
    root = record.get("project_root", "")
    for change in record.get("changes", []):
        lines.append(f"{change.get('status', 'changed')} · " + full_path(root, change["path"]))
    base = record.get("artifact_directory", "")
    if base and root and not Path(base).is_absolute():
        base = full_path(root, base)
    reports = record.get("report_files", [])
    if reports:
        lines.append("Rapor dosyaları:" if tr else "Report files:")
        for row in reports:
            lines.append(full_path(base, row["path"]) + f" · {row.get('bytes', '?')} B")
    elif base:
        lines.append(("Rapor klasörü: " if tr else "Report directory: ") + base)
        lines.append(
            ("Kayıtta tekil rapor dosyası yok." if tr else "No individual report files recorded.")
            if "report_files" in record
            else (
                "Eski kayıtta tekil rapor listesi tutulmamış."
                if tr
                else "Legacy record has no individual report inventory."
            )
        )
    if record.get("outputs_unavailable"):
        lines.append(
            "Rapor listesi doğrulanamadı." if tr else "Report inventory could not be observed."
        )
    if not lines:
        lines.append("Kayıtlı çıktı dosyası yok." if tr else "No output files recorded.")
    return lines
