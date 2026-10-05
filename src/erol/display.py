"""Owned terminal frames: content, editor and animated brand never share cells."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .i18n import message
from .terminal import render_logo

SGR = re.compile(r"\x1b\[[0-9;]*m")


def cells(text: str) -> int:
    return sum(cell_width(char) for char in SGR.sub("", text))


def cell_width(char: str) -> int:
    if unicodedata.combining(char) or unicodedata.category(char) in {"Cf", "Mn", "Me"}:
        return 0
    return 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1


def clip(text: str, width: int, start: int = 0) -> str:
    result, position = [], 0
    for char in text:
        size = cell_width(char)
        if position >= start + width or position + size > start + width:
            break
        if position >= start:
            result.append(char)
        elif position + size > start:
            result.append(" ")
        position += size
    return "".join(result)


def wrap(text: str, width: int) -> list[str]:
    lines = []
    fenced = False
    for line in text.expandtabs(4).split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        current, used = "", 0
        for char in line:
            size = cell_width(char)
            if used + size > width:
                space = current.rfind(" ")
                if not fenced and not line.startswith("    ") and space > 0:
                    lines.append(current[:space])
                    current = current[space + 1 :]
                    used = cells(current)
                else:
                    lines.append(current)
                    current, used = "", 0
            current += char
            used += size
        lines.append(current)
    return lines


@dataclass
class Frame:
    lines: list[str]
    cursor: tuple[int, int] | None


class Display:
    def __init__(self):
        self.text = ""
        self.editor: tuple[str, int] | None = None
        self.scroll = 0
        self.logo_width = 0
        self.expanded = False
        self.language = "tr"
        self.compact = False
        self.motion = True
        self.suggestions: list[str] = []
        self.context: list[str] = []
        self.running = False
        self.cached: tuple[str, int, list[str]] = ("", 0, [])

    def append(self, text: str) -> None:
        if self.scroll and self.cached[1]:
            width = self.cached[1]
            # Keep the viewed lines stationary while new streaming output arrives.
            old = len(wrap(self.text, width))
            combined = self.text + text
            self.scroll += len(wrap(combined, width)) - old
            self.text = combined[-200000:]
            return
        self.text = (self.text + text)[-200000:]
        self.scroll = 0

    def frame(self, columns: int, rows: int, status: str, pose: int = 0) -> Frame:
        rows = max(1, rows)
        width = max(1, columns - 1)  # Never trigger terminal auto-wrap in the last cell.
        if rows < 8:
            lines = wrap(self.text, width)[-max(1, rows - 2) :] if rows > 2 else []
            lines += [""] * (max(0, rows - 2) - len(lines))
            cursor = None
            if self.editor is not None:
                text, index = self.editor
                value = "erol › " + text.replace("\n", " ")
                column = cells("erol › " + text[:index].replace("\n", " "))
                offset = max(0, column - width + 1)
                lines.append(clip(value, width, offset))
                cursor = (max(1, rows - 1), column - offset + 1)
            else:
                lines.append("")
            if rows > 1:
                lines.append(clip(status, width))
            return Frame(lines[-rows:], cursor)
        height = max(1, rows - 7)
        sidebar = (
            (min(44, columns // 3) if self.expanded else min(32, columns // 4))
            if columns >= 72 and rows >= 18 and not self.compact
            else 0
        )
        content = max(1, width - sidebar - (3 if sidebar else 0))
        if self.cached[:2] != (self.text, content):
            self.cached = (self.text, content, wrap(self.text, content))
        wrapped = self.cached[2]
        self.scroll = min(max(0, self.scroll), max(0, len(wrapped) - height))
        end = len(wrapped) - self.scroll
        shown = wrapped[max(0, end - height) : end]
        lines = [clip(line, content) for line in shown] + [""] * (height - len(shown))
        if sidebar:
            self.logo_width = min(
                sidebar, max(8, int((height - 4) * 1.6)), 44 if self.expanded else 18
            )
            logo = render_logo(self.logo_width, bright=True, pose=pose).splitlines()
            panel = (
                ["EROL", *[clip(value, sidebar) for value in self.context[:2]], ""]
                + logo
                + ["", message(self.language, "working" if self.running else "ready")]
            )
            for i in range(height):
                right = panel[i] if i < len(panel) else ""
                lines[i] += " " * (content - cells(lines[i])) + " │ " + right
        else:
            self.logo_width = 0
        lines.append("─" * width)
        cursor = None
        inputs = ["", "", ""]
        if self.editor is not None:
            text, index = self.editor
            parts = ("erol › " + text).split("\n")
            before = text[:index]
            line_index = before.count("\n")
            first = max(0, line_index - 2)
            column = cells(before.rsplit("\n", 1)[-1]) + (7 if line_index == 0 else 0)
            offset = max(0, column - width + 1)
            for i in range(3):
                pos = first + i
                if pos < len(parts):
                    inputs[i] = clip(parts[pos], width, offset if pos == line_index else 0)
            cursor = (height + 2 + line_index - first, column - offset + 1)
        lines.extend(inputs)
        lines.append(
            clip(status + (message(self.language, "history_hint") if self.scroll else ""), width)
        )
        if self.suggestions:
            lines.append(clip("Tab › " + " · ".join(self.suggestions), width))
        else:
            lines.append(clip(message(self.language, "keys_short"), width))
        # Paint semantics after layout; ANSI never participates in clipping/wrapping.
        for i in range(height):
            left, separator, right = lines[i].partition(" │ ")
            stripped = left.lstrip()
            color = (
                "1;32"
                if stripped.startswith(("erol ›", "EROL ·", "##", "──"))
                else "31"
                if stripped.startswith(("Error:", "Hata:", "-")) and not stripped.startswith("- ")
                else "32"
                if stripped.startswith("+")
                else "36"
                if stripped.startswith(("/", "@@", "```"))
                else "0"
            )
            lines[i] = f"\x1b[{color}m{left}\x1b[0m" + separator + right
        lines.extend([""] * (rows - len(lines)))
        return Frame(lines[:rows], cursor)
