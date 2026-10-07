"""Keyboard choice state; opening a menu never runs a model or changes a preference."""

from __future__ import annotations

import unicodedata


def search_text(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold().replace("ı", "i"))
        if not unicodedata.combining(char)
    )


class Choice:
    def __init__(self, rows: list[dict], current: str = ""):
        self.rows = rows
        self.all_rows = rows
        self.query = ""
        self.index = next((i for i, row in enumerate(rows) if row["value"] == current), 0)
        self.number = ""
        self.pasting = False

    def search(self, query: str) -> None:
        self.query = query[:128]
        needle = search_text(self.query)
        self.rows = [
            row
            for row in self.all_rows
            if needle in search_text(" ".join(str(row.get(key, "")) for key in ("label", "detail")))
        ]
        self.index = 0
        self.number = ""

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
            if self.query:
                self.search(self.query[:-1])
            else:
                self.number = self.number[:-1]
        elif len(key) == 1 and key.isascii() and key.isdecimal() and not self.query:
            self.number = (self.number + key)[:6]
        elif len(key) == 1 and key.isprintable():
            self.search(self.query + key)
        elif key == "enter" and self.rows:
            if self.number:
                index = int(self.number) - 1
                if not 0 <= index < len(self.rows):
                    return None
                self.index = index
            return self.rows[self.index]["value"]
        return None

    def lines(self, title: str, hint: str, height: int, empty: str = "No matches") -> list[str]:
        hint += " · " + (self.query or self.number) if self.query or self.number else ""
        if height < 6:
            row = self.rows[self.index] if self.rows else {"label": empty}
            return [f"› {self.index + 1}. {row['label']}", hint][: max(1, height)]
        count = max(1, height - 5)
        first = max(0, min(self.index - count // 2, len(self.rows) - count))
        lines = [title, "" if self.rows else empty]
        for index in range(first, min(len(self.rows), first + count)):
            row = self.rows[index]
            lines.append(f"{'›' if index == self.index else ' '} {index + 1}. {row['label']}")
        selected = self.rows[self.index] if self.rows else {}
        lines += [
            "",
            selected.get("detail", ""),
            hint,
        ]
        return lines
