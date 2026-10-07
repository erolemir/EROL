"""Keyboard choice state; opening a menu never runs a model or changes a preference."""

from __future__ import annotations


class Choice:
    def __init__(self, rows: list[dict], current: str = ""):
        self.rows = rows
        self.index = next((i for i, row in enumerate(rows) if row["value"] == current), 0)
        self.number = ""
        self.pasting = False

    def key(self, key: str) -> str | None:
        if key == "paste_start":
            self.pasting = True
        elif key == "paste_end":
            self.pasting = False
        elif self.pasting:
            return None
        elif key in {"up", "down", "home", "end", "page_up", "page_down"}:
            delta = {"up": -1, "down": 1, "page_up": -5, "page_down": 5}.get(key, 0)
            self.index = (
                0
                if key == "home"
                else len(self.rows) - 1
                if key == "end"
                else max(0, min(len(self.rows) - 1, self.index + delta))
            )
            self.number = ""
        elif key == "backspace":
            self.number = self.number[:-1]
        elif len(key) == 1 and key.isascii() and key.isdecimal():
            self.number = (self.number + key)[:6]
        elif key == "enter" and self.rows:
            if self.number:
                index = int(self.number) - 1
                if not 0 <= index < len(self.rows):
                    return None
                self.index = index
            return self.rows[self.index]["value"]
        return None

    def lines(self, title: str, hint: str, height: int) -> list[str]:
        if height < 6:
            row = self.rows[self.index] if self.rows else {"label": ""}
            return [f"› {self.index + 1}. {row['label']}", hint][: max(1, height)]
        count = max(1, height - 5)
        first = max(0, min(self.index - count // 2, len(self.rows) - count))
        lines = [title, ""]
        for index in range(first, min(len(self.rows), first + count)):
            row = self.rows[index]
            lines.append(f"{'›' if index == self.index else ' '} {index + 1}. {row['label']}")
        selected = self.rows[self.index] if self.rows else {}
        lines += [
            "",
            selected.get("detail", ""),
            hint + (" · " + self.number if self.number else ""),
        ]
        return lines
