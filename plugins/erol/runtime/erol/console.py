"""Portable stdlib terminal frontend with a multiline editor and a fixed status row."""

from __future__ import annotations

import importlib
import json
import os
import queue
import shlex
import shutil
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from . import modelmenu
from .chat import ChatEngine, Sessions
from .choices import Choice
from .common import ErolError, identifier, reject_links
from .connections import CLI_KINDS, KINDS, Model, Settings, read_settings
from .console_input import InputRecord, decode_record
from .display import Display
from .general import GeneralEngine
from .i18n import HELP_EN, message, resolve_language
from .identity import detect_project
from .presentation import (
    STATUS_KEYS,
    api_observed,
    present,
    task_result,
    usage_summary,
    usage_transport,
)
from .projects import ProjectCatalog, choose
from .providers import visible
from .resultview import diff_result
from .terminal import render_logo

COMMANDS = {
    "start": "Yönlendiren başlangıç: bağlantı, proje, model ve dil",
    "menu": "Eylem menüsü: proje, model, sohbet, dosyalar ve görünüm",
    "help": "Komutları ve örneklerini göster",
    "project": "Proje göster/seç: /project C:/Projects/my-app (boşluk varsa tırnak kullan)",
    "my-projects": "Projelerini listele/seç: /my-projects | /my-projects 1 | /my-projects add PATH",
    "chats": "Eski sohbetler: /chats | /chats 1 | /chats show 1 | /chats page 2",
    "rename": "Sohbete isim ver: /rename İSİM | /chats rename 1 İSİM",
    "general": "Projesiz genel sohbete geç: /general [MESAJ]",
    "research": "Projesiz kaynak araştırması: /research [SORU veya URL]",
    "connect": "CLI/API ekle: /connect codex | /connect openai work OPENAI_API_KEY",
    "providers": "Bağlantıların giriş/yetenek durumunu göster; /providers disable ID",
    "models": (
        "Model profilleri; /models compare TASK | /models refresh | /models add ID JSON_PROFILE"
    ),
    "model": "Model listesi/seçimi: /model | /model 1 | /model NAME | /model auto",
    "effort": "Akıl yürütme eforu: /effort auto | /effort high (desteklenen değerler: /models)",
    "files": "Son görevin çıktı dosyalarını tam yollarıyla göster",
    "settings": "Ayarları göster/değiştir: /settings api_budget_usd 5",
    "plan": "Çalıştırmadan planla: /plan GÖREV",
    "skills": "Skill seçimini düzelt: /skills use NAME… | /skills auto",
    "diff": "Değişiklik özeti; /diff 1 veya /diff 1 2 ile dosya/sayfa seç",
    "tests": "EROL'un gözlediği son test sonuçları",
    "usage": "Token olayları ve görev API bütçesi; kesin fatura değildir",
    "status": "Proje, oturum ve son görev durumu",
    "new": "Yeni oturum aç",
    "resume": "Oturumları listele/yükle: /resume ID | /resume ID continue",
    "logo": "Sağdaki logoyu büyüt/küçült; sade terminalde statik göster",
    "language": "Arayüz dili: /language auto | /language en | /language tr",
    "clear": "Görünür konuşmayı temizle; oturum kaydı ve dosyalar korunur",
    "view": "Görünüm: /view compact (geniş yanıt) | /view full (logo alanı)",
    "motion": "Logo hareketi: /motion on | /motion off",
    "exit": "Terminalden çık",
}


@contextmanager
def windows_console_mode(kind: int, flag: int, clear: int = 0):
    """Restore the caller's console mode even after Ctrl+C or a failed redraw."""
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    handle = kernel.GetStdHandle(kind)
    mode = wintypes.DWORD()
    enabled = bool(
        kernel.GetConsoleMode(handle, ctypes.byref(mode))
        and kernel.SetConsoleMode(handle, (mode.value & ~clear) | flag)
    )
    try:
        yield enabled
    finally:
        if enabled:
            kernel.SetConsoleMode(handle, mode.value)


@contextmanager
def windows_console_title():
    """Apply EROL branding temporarily; restore the host's title on every exit."""
    import ctypes
    from ctypes import wintypes

    kernel = None
    previous = ""
    changed = False
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        kernel.GetConsoleTitleW.argtypes = [wintypes.LPWSTR, wintypes.DWORD]
        kernel.GetConsoleTitleW.restype = wintypes.DWORD
        kernel.SetConsoleTitleW.argtypes = [wintypes.LPCWSTR]
        kernel.SetConsoleTitleW.restype = wintypes.BOOL
        title = ctypes.create_unicode_buffer(65536)
        if kernel.GetConsoleTitleW(title, len(title)):
            previous = title.value
            changed = bool(kernel.SetConsoleTitleW("EROL"))
    except (AttributeError, OSError):
        pass
    try:
        yield changed
    finally:
        if changed and kernel is not None:
            try:
                kernel.SetConsoleTitleW(previous)
            except (AttributeError, OSError):
                pass


def split_command(text: str, language: str = "en") -> list[str]:
    try:
        return shlex.split(text)
    except ValueError as exc:
        raise ErolError(message(language, "quote_error")) from exc


class Editor:
    """State-only editor kept separate from OS key decoding for behavioral tests."""

    def __init__(self, history: list[str], completions: list[str]):
        self.text = ""
        self.cursor = 0
        self.history = history
        self.index = len(history)
        self.draft = ""
        self.completions = completions
        self.pasting = False
        self.tab_choices: list[str] = []
        self.tab_index = -1

    def suggestions(self) -> list[str]:
        if not self.text.startswith("/") or "\n" in self.text:
            return []
        return [c for c in self.completions if c.startswith(self.text) and c != self.text][:5]

    def key(self, key: str) -> str | None:
        if key != "tab":
            self.tab_choices, self.tab_index = [], -1
        if key == "paste_start":
            self.pasting = True
        elif key == "paste_end":
            self.pasting = False
        elif self.pasting:
            if key == "eof":
                raise EOFError
            if key in {"enter", "newline"}:
                self.insert("\n")
            elif len(key) == 1 and key.isprintable():
                self.insert(key)
        elif key == "enter" and not self.pasting:
            return self.text
        elif key in {"newline", "enter"}:
            self.insert("\n")
        elif key == "backspace" and self.cursor:
            self.text = self.text[: self.cursor - 1] + self.text[self.cursor :]
            self.cursor -= 1
        elif key == "delete":
            self.text = self.text[: self.cursor] + self.text[self.cursor + 1 :]
        elif key == "clear_input":
            self.text, self.cursor = "", 0
        elif key == "erase_word":
            start = self.cursor
            while start and self.text[start - 1].isspace():
                start -= 1
            while start and not self.text[start - 1].isspace():
                start -= 1
            self.text, self.cursor = self.text[:start] + self.text[self.cursor :], start
        elif key == "erase_end":
            end = self.text.find("\n", self.cursor)
            self.text = self.text[: self.cursor] + self.text[end if end >= 0 else len(self.text) :]
        elif key == "left":
            self.cursor = max(0, self.cursor - 1)
        elif key == "right":
            self.cursor = min(len(self.text), self.cursor + 1)
        elif key == "home":
            self.cursor = 0
        elif key == "end":
            self.cursor = len(self.text)
        elif key in {"up", "down"}:
            # Multiline editing takes priority over recalling another prompt.
            before = self.text[: self.cursor]
            start = before.rfind("\n") + 1
            column = self.cursor - start
            end = self.text.find("\n", self.cursor)
            if key == "up" and start:
                previous = self.text.rfind("\n", 0, start - 1) + 1
                self.cursor = previous + min(column, start - previous - 1)
                return None
            if key == "down" and end >= 0:
                following = self.text.find("\n", end + 1)
                self.cursor = (
                    end
                    + 1
                    + min(column, (following if following >= 0 else len(self.text)) - end - 1)
                )
                return None
            if "\n" in self.text:
                return None
            if self.index == len(self.history):
                self.draft = self.text
            self.index = max(0, min(len(self.history), self.index + (-1 if key == "up" else 1)))
            self.text = self.history[self.index] if self.index < len(self.history) else self.draft
            self.cursor = len(self.text)
        elif key == "tab":
            if not self.tab_choices:
                self.tab_choices = [c for c in self.completions if c.startswith(self.text)]
                common = os.path.commonprefix(self.tab_choices)
                if len(common) > len(self.text):
                    self.text, self.cursor = common, len(common)
                    return None
            if self.tab_choices:
                self.tab_index = (self.tab_index + 1) % len(self.tab_choices)
                self.text = self.tab_choices[self.tab_index]
                self.cursor = len(self.text)
        elif key == "escape":
            self.text, self.cursor = "", 0
        elif key == "cancel":
            raise KeyboardInterrupt
        elif key == "eof":
            raise EOFError
        elif len(key) == 1 and key.isprintable():
            self.insert(key)
        return None

    def insert(self, value: str) -> None:
        if len(self.text) + len(value) <= 16000:
            self.text = self.text[: self.cursor] + value + self.text[self.cursor :]
            self.cursor += len(value)


class Screen:
    def __init__(self, stream=None):
        self.stream = stream or sys.stdout
        self.tty = self.stream.isatty()
        self.rich = self.tty and os.environ.get("TERM") != "dumb" and "NO_COLOR" not in os.environ
        self.status = "Hazır · /help · Enter gönder · Ctrl+J yeni satır"
        self.lock = threading.RLock()
        self.console_mode = None
        self.title_mode = None
        self.owns_windows_title = False
        self.windows_keys: WindowsKeys | None = None
        self.pending_keys: list[str] = []
        self.draft = ""
        self.started = 0.0
        self.running = False
        self.tokens = 0
        self.estimated_cost = 0.0
        self.role_model = ""
        self.transport = ""
        self.usage_events: list[dict] = []
        self.usage: dict = {}
        self.connection_transports: dict[str, str] = {}
        self.context_name = ""
        self.resources = ""
        self.display = Display()
        self.preference = "auto"
        self.language = resolve_language("auto")
        self.set_language("auto")
        self.active = False
        self.previous: list[str] = []
        self.dimensions = (0, 0)
        self.animation_stop = threading.Event()
        self.animation: threading.Thread | None = None
        self.animation_error = False
        if self.rich and os.name == "nt":
            self.console_mode = windows_console_mode(-11, 4)
            self.rich = self.console_mode.__enter__()

    def set_language(self, preference: str) -> None:
        if preference not in {"auto", "en", "tr"}:
            raise ErolError(self.t("language_invalid"))
        self.preference, self.language = preference, resolve_language(preference)
        self.display.language = self.language
        self.status = self.t("ready_hint")

    def t(self, key: str, **values) -> str:
        return message(self.language, key, **values)

    def configure_connections(self, settings: Settings, context: str = "") -> None:
        self.connection_transports = {
            c.id: "cli" if c.kind in CLI_KINDS else "api" for c in settings.connections
        }
        self.context_name = context or self.context_name
        has_api = any(c.enabled and c.kind not in CLI_KINDS for c in settings.connections)
        has_cli = any(c.enabled and c.kind in CLI_KINDS for c in settings.connections)
        self.resources = settings.policy
        if has_api:
            self.resources += " · " + self.t("api_budget", budget=settings.api_budget_usd)
        elif has_cli:
            self.resources += " · " + self.t("cli_subscription")
        self.update_context()

    def update_context(self) -> None:
        resource = self.resources
        if self.transport == "cli" and not api_observed(self.usage, self.usage_events):
            complete = self.usage_events and all(
                type(item["data"].get("counts", item["data"]).get(key)) is int
                for item in self.usage_events
                for key in ("input_tokens", "output_tokens")
            )
            resource = f"CLI · {self.tokens if complete else '?'} token"
        elif api_observed(self.usage, self.usage_events):
            resource = "API · " + self.t("estimate") + f" ${self.usage.get('accounted_usd', 0):.4f}"
        elif self.transport:
            resource = "API · ? token"
        self.display.context = [self.context_name, resource]

    def configure_selection(self, engine: ChatEngine | GeneralEngine) -> None:
        self.display.selection = (
            f"{engine.selected_model or 'auto'} · {engine.selected_effort or 'auto'}"
        )
        self.display.context.insert(1, engine.selected_model or "Model: auto")

    def write(self, text: str, *, raw: bool = False) -> None:
        with self.lock:
            if self.rich and self.active and not raw:
                self.display.append(visible(text))
                self.refresh()
            else:
                self.stream.write(text if raw else visible(text))
                self.stream.flush()

    def setup(self) -> None:
        if self.rich:
            if os.name == "nt":
                self.title_mode = windows_console_title()
                self.owns_windows_title = bool(self.title_mode.__enter__())
            columns, rows = shutil.get_terminal_size()
            if rows >= 12 and columns >= 20:
                self.active = True
                self.write(
                    "\x1b[?1049h\x1b[2J\x1b[H\x1b[r\x1b[?2004h\x1b[?1000h\x1b[?1006h", raw=True
                )
                self.refresh()
                self.animation_stop.clear()
                self.animation = threading.Thread(target=self.animate, daemon=True)
                self.animation.start()
            else:
                self.rich = False

    def animate(self) -> None:
        while not self.animation_stop.wait(0.20):
            try:
                self.refresh()
            except (OSError, ValueError):
                self.animation_error = True
                return

    def close(self) -> None:
        self.animation_stop.set()
        try:
            if self.animation is not None and self.animation.ident is not None:
                self.animation.join(timeout=1)
            with self.lock:
                if self.active:
                    self.active = False
                    self.owns_windows_title = False
                    self.write(
                        "\x1b[r\x1b[?1006l\x1b[?1000l\x1b[?2004l\x1b[0m\x1b[?25h\x1b[?1049l",
                        raw=True,
                    )
        finally:
            try:
                if self.console_mode is not None:
                    self.console_mode.__exit__(None, None, None)
            finally:
                if self.title_mode is not None:
                    self.title_mode.__exit__(None, None, None)
                    self.title_mode = None

    def refresh(self) -> None:
        if self.rich:
            with self.lock:
                if not self.active:
                    return
                columns, rows = shutil.get_terminal_size()
                status = self.status
                if self.running:
                    self.display.running = True
                    if self.role_model and not status.startswith(self.role_model):
                        status = self.role_model + " · " + status
                    status += f" · {time.monotonic() - self.started:.0f}s"
                    status += " · " + usage_summary(
                        self.usage, self.usage_events, self.language, self.transport
                    )
                else:
                    self.display.running = False
                frame = self.display.frame(
                    columns,
                    rows,
                    visible(status),
                    pose=int(time.monotonic() * 4) % 24 if self.display.motion else 0,
                )
                output = ["\x1b[?25l"]
                if self.owns_windows_title:
                    # Native probes can rename the shared console. Reassert the owned title
                    # through ConPTY's documented OSC 2 on every bounded repaint.
                    output.append("\x1b]2;EROL\x07")
                if self.dimensions != (columns, rows):
                    output.append("\x1b[2J")
                    self.previous = []
                    self.dimensions = (columns, rows)
                for i, line in enumerate(frame.lines):
                    if i >= len(self.previous) or line != self.previous[i]:
                        output.append(f"\x1b[{i + 1};1H\x1b[0m\x1b[2K" + line)
                self.previous = frame.lines
                if frame.cursor is not None:
                    row, column = frame.cursor
                    output.append(f"\x1b[{row};{column}H\x1b[?25h")
                self.write("".join(output), raw=True)

    def edit(self, text: str | None, cursor: int = 0) -> None:
        with self.lock:
            self.display.editor = None if text is None else (text, cursor)
            self.refresh()

    def logo(self) -> None:
        if self.rich:
            with self.lock:
                if not self.active:
                    return
                self.display.expanded = not self.display.expanded
                self.refresh()
                if not self.display.logo_width:
                    self.write(self.t("logo_size"))
        else:
            self.write(
                render_logo(min(40, max(8, shutil.get_terminal_size().columns - 1)), color=False)
                + "\n"
            )

    def event(self, item: dict) -> None:
        data, kind = item["data"], item["type"]
        if kind == "text_delta":
            # Worker/reviewer streams contain protocol JSON. Their validated
            # summaries and evidence are rendered by the final status event.
            if item.get("role") not in {"implementer", "reviewer"}:
                self.write(data.get("text", ""))
        elif kind == "skills":
            names = data.get("names", [])
            self.write(
                self.t("skills_used", names=", ".join(names)) + "\n"
                if names
                else self.t("skills_none") + "\n"
            )
        elif kind == "routing":
            self.transport = data.get("transport") or self.connection_transports.get(
                data["connection"], ""
            )
            self.status = (
                f"{data['role']} · {data['connection']}:{data['model']} · {data['effort']}"
            )
            self.role_model = self.status
            self.write(f"\n[{self.status}] {data['reason']}\n")
        elif kind in {"tool_start", "tool_result"}:
            failed = data.get("is_error") or data.get("error")
            label = self.t("error" if failed else "working" if kind == "tool_start" else "done")
            self.status = f"{data.get('tool', '')} · {label}"
            if kind == "tool_start" or failed:
                self.write(f"\n  {data.get('tool', '')}: {label}\n")
                if failed:
                    self.write("  " + str(data.get("error") or data.get("summary", "")) + "\n")
        elif kind == "file_change":
            self.write(f"\n  {data['status']}: {data['path']}\n")
        elif kind == "error":
            self.write(f"\n{self.t('error')}: {data['message']}\n")
        elif kind == "usage":
            item = dict(item)
            item["data"] = dict(data)
            if usage_transport(item) == "unknown":
                item["data"]["transport"] = self.connection_transports.get(
                    item.get("connection", ""), self.transport
                )
            self.usage_events.append(item)
            counts = data.get("counts", data)
            self.tokens += counts.get("input_tokens", 0) + counts.get("output_tokens", 0)
            cost = data.get("estimated_cost_usd")
            if usage_transport(item) == "api":
                reserved = data.get("unreported_reserved_usd", 0)
                self.estimated_cost += cost if cost is not None else reserved
                self.usage["accounted_usd"] = self.estimated_cost
                self.usage["unreported_reserved_usd"] = (
                    self.usage.get("unreported_reserved_usd", 0) + reserved
                )
        elif kind == "status":
            hints = (
                "/usage /research" if data.get("project_tools") is False else "/diff /tests /usage"
            )
            outcome = self.t(data["status"]) if data["status"] in STATUS_KEYS else data["status"]
            self.usage = data.get("usage", {})
            self.status = (
                outcome
                + " · "
                + usage_summary(self.usage, self.usage_events, self.language, self.transport)
                + " · "
                + hints
            )
            self.write(f"\n{self.status}\n")
            if data.get("result"):
                self.write(task_result(data["result"], self.language) + "\n")
        self.update_context()
        self.refresh()


class WindowsKeys:
    """ReadConsole preserves VT paste/key sequences; CRT getwch resets input mode."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        self.ctypes, self.wintypes = ctypes, wintypes
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        self.kernel.GetStdHandle.argtypes = [wintypes.DWORD]
        self.kernel.GetStdHandle.restype = wintypes.HANDLE
        self.handle = self.kernel.GetStdHandle(-10)
        self.kernel.ReadConsoleW.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        self.kernel.ReadConsoleInputW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(InputRecord),
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.records = True
        self.kernel.GetNumberOfConsoleInputEvents.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        self.buffer = ""

    def raw_char(self) -> str:
        while not self.buffer and getattr(self, "records", False):
            record, count = InputRecord(), self.wintypes.DWORD()
            if not self.kernel.ReadConsoleInputW(
                self.handle, self.ctypes.byref(record), 1, self.ctypes.byref(count)
            ):
                raise ErolError("Windows console input unavailable")
            if not count.value:
                raise EOFError
            self.buffer = decode_record(record)
        if not self.buffer:
            buffer = self.ctypes.create_unicode_buffer(64)
            count = self.wintypes.DWORD()
            if not self.kernel.ReadConsoleW(
                self.handle, buffer, 64, self.ctypes.byref(count), None
            ):
                raise ErolError("Windows console input unavailable")
            if not count.value:
                raise EOFError
            self.buffer = "".join(buffer[: count.value])
        char, self.buffer = self.buffer[0], self.buffer[1:]
        return char

    def getwch(self) -> str:
        char = self.raw_char()
        if 0xD800 <= ord(char) <= 0xDBFF:
            second = self.raw_char()
            if len(second) == 1 and 0xDC00 <= ord(second) <= 0xDFFF:
                return chr(0x10000 + ((ord(char) - 0xD800) << 10) + ord(second) - 0xDC00)
            self.buffer = second + self.buffer
            return "\ufffd"
        if 0xDC00 <= ord(char) <= 0xDFFF:
            return "\ufffd"
        return char

    def kbhit(self) -> bool:
        if self.buffer:
            return True
        count = self.wintypes.DWORD()
        while (
            self.kernel.GetNumberOfConsoleInputEvents(self.handle, self.ctypes.byref(count))
            and count.value
        ):
            if not getattr(self, "records", False):
                return True
            record, read = InputRecord(), self.wintypes.DWORD()
            if not self.kernel.ReadConsoleInputW(
                self.handle, self.ctypes.byref(record), 1, self.ctypes.byref(read)
            ):
                raise ErolError("Windows console input unavailable")
            self.buffer = decode_record(record) if read.value else ""
            if self.buffer:
                return True
        return False


def key_windows(reader=None) -> str:
    module = reader or importlib.import_module("msvcrt")
    char = module.getwch()
    if char == "\x1b":
        sequence = char
        for _ in range(63):
            deadline = time.monotonic() + 0.03
            while not module.kbhit() and time.monotonic() < deadline:
                time.sleep(0.001)
            if not module.kbhit():
                break
            sequence += module.getwch()
            if sequence.endswith(("~", "A", "B", "C", "D", "H", "F", "M", "m")):
                break
        return escape_key(sequence)
    if char in {"\x00", "\xe0"}:
        return {
            "H": "up",
            "P": "down",
            "K": "left",
            "M": "right",
            "G": "home",
            "O": "end",
            "S": "delete",
            "I": "page_up",
            "Q": "page_down",
        }.get(module.getwch(), "unknown")
    return {
        "\x1b": "escape",
        "\r": "enter",
        "\n": "newline",
        "\x08": "backspace",
        "\x7f": "backspace",
        "\x15": "clear_input",
        "\x17": "erase_word",
        "\x0b": "erase_end",
        "\x03": "cancel",
        "\x04": "eof",
        "\x1a": "eof",
        "\t": "tab",
    }.get(char, char)


def escape_key(sequence: str) -> str:
    if sequence.startswith("\x1b[<") and sequence.endswith(("M", "m")):
        try:
            button, x, y = map(int, sequence[3:-1].split(";"))
            if button & 64 and sequence.endswith("M"):
                return (
                    "wheel_up"
                    if button & 3 == 0
                    else "wheel_down"
                    if button & 3 == 1
                    else "unknown"
                )
        except ValueError:
            pass
        return "unknown"
    return {
        "\x1b": "escape",
        "\x1b[A": "up",
        "\x1b[B": "down",
        "\x1b[C": "right",
        "\x1b[D": "left",
        "\x1b[H": "home",
        "\x1b[F": "end",
        "\x1b[3~": "delete",
        "\x1b[5~": "page_up",
        "\x1b[6~": "page_down",
        "\x1b[200~": "paste_start",
        "\x1b[201~": "paste_end",
    }.get(sequence, "unknown")


def key_posix(fd: int) -> str:
    import select

    char = os.read(fd, 1)
    if char == b"\x1b":
        seq = char
        for _ in range(63):
            if not select.select([fd], [], [], 0.03)[0]:
                break
            seq += os.read(fd, 1)
            if seq.endswith((b"~", b"A", b"B", b"C", b"D", b"H", b"F", b"M", b"m")):
                break
        return escape_key(seq.decode("ascii", errors="replace"))
    if char and char[0] >= 128:
        length = 2 if char[0] < 224 else 3 if char[0] < 240 else 4
        char += os.read(fd, length - 1)
    text = char.decode("utf-8", errors="replace")
    return {
        "\r": "enter",
        "\n": "newline",
        "\x7f": "backspace",
        "\x08": "backspace",
        "\x15": "clear_input",
        "\x03": "cancel",
        "\x17": "erase_word",
        "\x0b": "erase_end",
        "\x04": "eof",
        "\t": "tab",
        "": "eof",
    }.get(text, text)


@contextmanager
def input_session(screen: Screen):
    old = None
    windows_mode = None
    windows_keys = None
    fd = sys.stdin.fileno()
    try:
        if os.name == "nt":
            mode = windows_console_mode(-10, 0x200 | 0x80 | 0x10, clear=7 | 0x40)
            mode.__enter__()
            windows_mode = mode
            if screen.windows_keys is None:
                screen.windows_keys = WindowsKeys()
            windows_keys = screen.windows_keys
        else:
            termios = importlib.import_module("termios")
            tty = importlib.import_module("tty")
            old = termios.tcgetattr(fd)
            tty.setraw(fd)
        yield fd, windows_keys
    finally:
        if old is not None:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        if windows_mode is not None:
            windows_mode.__exit__(None, None, None)


def scroll_key(screen: Screen, key: str) -> bool:
    if key not in {"page_up", "page_down", "wheel_up", "wheel_down"}:
        return False
    with screen.lock:
        distance = 3 if key.startswith("wheel") else max(1, shutil.get_terminal_size().lines - 8)
        screen.display.scroll += (1 if key.endswith("up") else -1) * distance
        screen.refresh()
    return True


def read_prompt(
    screen: Screen, history: list[str], completions: list[str], *, cancel_on_escape: bool = False
) -> str:
    if not screen.rich:
        return input("erol › ")
    editor = Editor(history, completions)
    if not cancel_on_escape:
        editor.insert(screen.draft)
        screen.draft = ""
    with input_session(screen) as (fd, windows_keys):
        try:
            while True:
                screen.edit(editor.text, editor.cursor)
                screen.display.suggestions = editor.suggestions()
                key = (
                    screen.pending_keys.pop(0)
                    if screen.pending_keys
                    else key_windows(windows_keys)
                    if os.name == "nt"
                    else key_posix(fd)
                )
                if scroll_key(screen, key):
                    continue
                if cancel_on_escape and key == "escape" and not editor.pasting:
                    return ""
                result = editor.key(key)
                if result is not None:
                    screen.edit(None)
                    screen.write("erol › " + result + "\n")
                    return result
        finally:
            screen.display.suggestions = []
            screen.edit(None)


def read_choice(screen: Screen, title: str, rows: list[dict], current: str = "") -> str | None:
    """Temporary overlay: cancellation restores the conversation and its scroll position."""
    rows = [
        {
            **row,
            "label": visible(row["label"]).replace("\n", " "),
            "detail": visible(row.get("detail", "")).replace("\n", " "),
        }
        for row in rows
    ]
    choice = Choice(rows, current)
    if not rows:
        return None
    if not screen.rich:
        while True:
            screen.write(title + "\n")
            for index, row in enumerate(choice.rows, 1):
                screen.write(f"{index}. {row['label']}\n")
            if not choice.rows:
                screen.write(screen.t("no_matches") + "\n")
            value = input(screen.t("choice_plain")).strip()
            if not value or value.startswith("/"):
                return None
            if value.isascii() and value.isdecimal():
                return (
                    choice.rows[int(value) - 1]["value"]
                    if 1 <= int(value) <= len(choice.rows)
                    else None
                )
            choice.search(value)
    with input_session(screen) as (fd, windows_keys):
        try:
            while True:
                _, height = shutil.get_terminal_size()
                with screen.lock:
                    screen.display.overlay = choice.lines(
                        title, screen.t("choice_hint"), max(1, height - 7), screen.t("no_matches")
                    )
                    screen.refresh()
                key = (
                    screen.pending_keys.pop(0)
                    if screen.pending_keys
                    else key_windows(windows_keys)
                    if os.name == "nt"
                    else key_posix(fd)
                )
                if key == "eof":
                    raise EOFError
                if choice.pasting:
                    choice.key(key)
                    continue
                if key in {"escape", "cancel"}:
                    return None
                result = choice.key(key)
                if result is not None:
                    return result
        finally:
            with screen.lock:
                screen.display.overlay = None
                screen.refresh()


def interactive_command(engine: ChatEngine | GeneralEngine, text: str, screen: Screen) -> dict:
    """Use pickers only in the interactive frontend; CLI JSON commands stay repeatable."""
    while True:
        if text in {"/project", "/rename"}:
            screen.write(screen.t("folder_prompt" if text == "/project" else "rename_prompt"))
            value = read_prompt(screen, [], [], cancel_on_escape=True).strip()
            return command(engine, text + " " + value) if value else {}
        result = command(engine, text)
        rows: list[dict] = []
        title, current = screen.t("menu_title"), ""
        if text in {"/menu", "/start"}:
            rows = result["menu_choices"]
            for row in rows:
                if row["value"] == "/view compact" and screen.display.compact:
                    row["value"] = row["detail"] = "/view full"
        elif text == "/connect":
            title = screen.t("menu_start")
            rows = result["connection_choices"]
            current = "/connect use " + (engine.connections.settings.preferred_connection or "")
            screen.write(result["hint"] + "\n")
        elif text == "/language":
            rows = [
                {"value": "/language " + value, "label": label}
                for value, label in (("auto", "Auto"), ("tr", "Türkçe"), ("en", "English"))
            ]
        elif text == "/model":
            title, current = screen.t("help_connections"), "/model " + result["model"]
            rows = [{"value": "/model auto", "label": screen.t("auto_model")}]
            rows += [
                {
                    "value": "/model " + item["value"],
                    "label": item["value"],
                    "detail": screen.t("access_note", value=item["access"])
                    + " · effort: "
                    + ", ".join(item["efforts"]),
                }
                for item in result["model_choices"]
            ]
            if not result["model_choices"]:
                screen.write(present(result, screen.language))
                return {}
        elif text == "/effort":
            title, current = screen.t("menu_effort"), "/effort " + result["effort"]
            _, choices, _ = modelmenu.inventory(engine)
            values = dict.fromkeys(
                effort
                for row in choices
                if not engine.selected_model or row["value"] == engine.selected_model
                for effort in row["efforts"]
            )
            rows = [{"value": "/effort auto", "label": screen.t("auto_model")}]
            rows += [{"value": "/effort " + value, "label": value} for value in values]
        elif text == "/my-projects" or "sessions" in result:
            projects = text == "/my-projects"
            title = screen.t("projects_title" if projects else "sessions_title")
            entries = result["projects" if projects else "sessions"]
            rows = [
                {
                    "value": text + " " + str(index),
                    "label": item.get("name") if projects else item.get("title") or item["id"],
                    "detail": item["root"]
                    if projects
                    else item.get("summary", item.get("task", "")),
                }
                for index, item in enumerate(entries, 1)
            ]
            if projects:
                rows.append({"value": "/project", "label": screen.t("menu_folder")})
            if not projects:
                page = result.get("page", 1)
                if page > 1:
                    rows.append(
                        {"value": f"/chats page {page - 1}", "label": screen.t("previous_page")}
                    )
                if len(entries) == 50:
                    rows.append(
                        {"value": f"/chats page {page + 1}", "label": screen.t("next_page")}
                    )
                # Selections use the displayed page's snapshot, not its command prefix.
                for index, row in enumerate(rows[: len(entries)], 1):
                    row["value"] = "/chats " + str(index)
        if not rows:
            return result
        selected = read_choice(screen, title, rows, current)
        if selected is None:
            return {}
        text = selected


def command(engine: ChatEngine | GeneralEngine, text: str) -> dict:
    name, _, rest = text.removeprefix("/").partition(" ")
    language = resolve_language(engine.connections.settings.language)
    if name in {"menu", "start"}:
        return {
            "menu_choices": [
                {"value": value, "label": message(language, key), "detail": value}
                for value, key in (
                    ("/connect", "menu_start"),
                    ("/my-projects", "menu_projects"),
                    ("/project", "menu_folder"),
                    ("/model", "menu_models"),
                    ("/effort", "menu_effort"),
                    ("/chats", "menu_chats"),
                    ("/new", "menu_new"),
                    ("/rename", "menu_rename"),
                    ("/general", "menu_general"),
                    ("/research", "menu_research"),
                    ("/language", "menu_language"),
                    ("/files", "menu_files"),
                    ("/diff", "menu_changes"),
                    ("/tests", "menu_tests"),
                    ("/status", "menu_status"),
                    ("/view compact", "menu_view"),
                    ("/settings", "menu_settings"),
                    ("/help", "menu_help"),
                    ("/exit", "menu_exit"),
                )
                if name != "start"
                or value in {"/connect", "/project", "/model", "/language", "/help"}
            ]
        }
    if name == "language":
        if rest:
            if rest not in {"auto", "en", "tr"}:
                raise ErolError(message(language, "language_invalid"))
            engine.connections.settings.language = rest
            engine.connections.save()
        return {
            "language": resolve_language(engine.connections.settings.language),
            "preference": engine.connections.settings.language,
        }
    if name == "help":
        return {
            "commands": {
                "/" + k: v for k, v in (COMMANDS if language == "tr" else HELP_EN).items()
            },
            "keys": message(language, "keys"),
        }
    if name == "clear":
        return {"clear": True}
    if name == "view":
        if rest not in {"compact", "full"}:
            raise ErolError("/view compact|full")
        return {"view": rest}
    if name == "motion":
        if rest not in {"on", "off"}:
            raise ErolError("/motion on|off")
        return {"motion": rest == "on"}
    if name == "project":
        if not rest.strip():
            return {"project": engine.project.to_dict() if engine.project else None}
        engine.ensure_idle()
        return {"select_project": str(project_directory(rest, engine.root, engine.home, language))}
    if name == "my-projects":
        argv = split_command(rest, language)
        catalog = ProjectCatalog(engine.home)
        if not argv or argv == ["refresh"]:
            engine.project_choices = catalog.list()
            return {"projects": engine.project_choices}
        if len(argv) == 2 and argv[0] == "add":
            path = project_directory(argv[1], engine.root, engine.home, language)
            catalog.remember(detect_project(path))
            engine.project_choices = catalog.list()
            return {"projects": engine.project_choices}
        if len(argv) != 1:
            raise ErolError("/my-projects [NUMBER|ID|NAME] | /my-projects add PATH")
        engine.ensure_idle()
        rows = engine.project_choices if engine.project_choices is not None else catalog.list()
        selected = choose(rows, argv[0])
        path = project_directory(selected["root"], engine.root, engine.home, language)
        if detect_project(path).id != selected["project_id"]:
            raise ErolError("Project identity changed; refresh /my-projects before selecting")
        return {"select_project": str(path)}
    if name == "rename":
        engine.ensure_idle()
        title = Sessions.title(rest.strip().strip('"'))
        if engine.record:
            renamed = engine.sessions.rename(engine.session_id, title)
            engine.record["title"] = renamed["title"]
        engine.session_title = title
        engine.chat_choices = None
        return {"session": engine.session_id, "title": title}
    if name == "chats":
        argv = split_command(rest, language)
        if not argv or argv == ["refresh"] or (len(argv) == 2 and argv[0] == "page"):
            try:
                page = int(argv[1]) if len(argv) == 2 else 1
            except ValueError as exc:
                raise ErolError("/chats page NUMBER") from exc
            engine.chat_choices = engine.sessions.list(page=page)
            return {"sessions": engine.chat_choices, "page": page}
        action = argv[0] if argv[0] in {"open", "show", "continue", "rename"} else "open"
        selection = argv[1] if action == argv[0] and len(argv) > 1 else argv[0]
        if (action == "rename" and len(argv) < 3) or (
            action != "rename" and len(argv) != (2 if action == argv[0] else 1)
        ):
            raise ErolError("/chats [open|show|continue] NUMBER|ID | /chats rename NUMBER|ID TITLE")
        rows = engine.chat_choices if engine.chat_choices is not None else engine.sessions.list()
        session_id = (
            identifier(selection)
            if selection.startswith("session-")
            else choose(rows, selection)["id"]
        )
        if action == "show":
            saved = engine.sessions.load(session_id)
            return {
                "saved_chat": {
                    **saved,
                    "project_root": saved.get(
                        "project_root", str(engine.root) if engine.project else ""
                    ),
                }
            }
        engine.ensure_idle()
        if action == "rename":
            title = Sessions.title(" ".join(argv[2:]))
            renamed = engine.sessions.rename(session_id, title)
            if session_id == engine.session_id:
                engine.record["title"] = title
                engine.session_title = title
            engine.chat_choices = None
            return {"session": session_id, "title": renamed["title"]}
        result = engine.resume(session_id)
        if action == "continue":
            result["continue_task"] = engine.record["task"]
        return result
    if name in {"general", "research"}:
        return {
            "select_general": True,
            "mode": "general" if name == "general" else "research",
            **({"general_task": rest} if rest.strip() else {}),
        }
    if name in {"diff", "tests"} and engine.project is None:
        raise ErolError(message(language, "project_required"))
    if name == "connect":
        argv = split_command(rest, language)
        if not argv:
            configured = engine.connections.settings.connections
            existing = [
                {
                    "value": "/connect use " + c.id,
                    "label": c.id + " · " + c.kind,
                    "detail": message(
                        language, "connection_cli" if c.kind in CLI_KINDS else "connection_api"
                    ),
                }
                for c in configured
                if c.enabled
            ]
            return {
                "connection_choices": existing
                + [
                    {
                        "value": "/connect " + kind,
                        "label": kind,
                        "detail": message(
                            language, "connection_cli" if kind in CLI_KINDS else "connection_api"
                        ),
                    }
                    for kind in KINDS
                    if kind != "compatible" and kind not in {c.id for c in configured}
                ],
                "hint": message(language, "connection_custom"),
            }
        if argv[0] == "use" and len(argv) == 2:
            engine.ensure_idle()
            connection = engine.connections.get(argv[1])
            if not connection.enabled:
                raise ErolError("/providers enable " + connection.id)
            engine.connections.settings.preferred_connection = connection.id
            engine.connections.save()
            return {"connection": connection.to_dict()}
        if not argv or argv[0] not in KINDS:
            raise ErolError(
                "/connect KIND [ID] [KEY_ENV] [BASE_URL]; CLI: codex, claude, "
                "antigravity; API: openai, anthropic, gemini, compatible"
            )
        kind = argv[0]
        options = {}
        if len(argv) > 2:
            options["key_env"] = argv[2]
        if len(argv) > 3:
            options["base_url"] = argv[3]
        if len(argv) > 4:
            raise ErolError("Too many connection arguments")
        return {
            "connection": engine.connections.connect(
                kind, argv[1] if len(argv) > 1 else None, **options
            ).to_dict()
        }
    if name == "providers":
        argv = split_command(rest, language)
        if argv:
            if len(argv) != 2 or argv[0] not in {"enable", "disable"}:
                raise ErolError("/providers [enable|disable ID]")
            engine.connections.get(argv[1]).enabled = argv[0] == "enable"
            engine.connections.save()
        return {"providers": engine.providers()[0]}
    if name == "models":
        if rest.startswith("compare "):
            from .connections import route

            task = rest[8:].strip()
            plan = engine.plan(task)
            _, available = engine.providers()
            comparisons = []
            for role in ("implementer", "planner", "reviewer"):
                context_size = (
                    engine._context_size(task, plan, role)
                    if isinstance(engine, ChatEngine)
                    else len(json.dumps(plan).encode("utf-8")) + 1024
                )
                try:
                    choice = route(
                        engine.connections.settings,
                        task,
                        available,
                        role=role,
                        override=engine.selected_model if role == "implementer" else None,
                        effort_override=engine.selected_effort if role == "implementer" else None,
                        plan=plan,
                        context_tokens=context_size,
                    )
                    comparisons.append(choice)
                except ErolError as exc:
                    comparisons.append({"role": role, "reason": str(exc), "eligible": False})
            return {
                "model_comparison": comparisons,
                "note": (
                    "Profile priors; measured success rate unknown. "
                    "This command does not spawn agents."
                ),
            }
        if rest.startswith("add "):
            connection_id, _, profile = rest[4:].partition(" ")
            model = Model.load(json.loads(profile))
            connection = engine.connections.get(connection_id)
            connection.models = [m for m in connection.models if m.id != model.id] + [model]
            engine.connections.save()
        return modelmenu.menu(engine, refresh=rest == "refresh")
    if name == "model":
        if rest:
            with engine.lock:
                engine.ensure_idle()
                engine.selected_model = (
                    None if rest == "auto" else modelmenu.select(engine, rest.strip())
                )
            return {
                "model": engine.selected_model or "auto",
                "effort": engine.selected_effort or "auto",
            }
        return modelmenu.menu(engine)
    if name == "effort":
        if rest:
            with engine.lock:
                engine.ensure_idle()
                engine.selected_effort = modelmenu.effort(engine, rest.strip())
        return {
            "model": engine.selected_model or "auto",
            "effort": engine.selected_effort or "auto",
        }
    if name == "files":
        return {
            "files": {
                **engine.record,
                "project_root": engine.record.get(
                    "project_root", str(engine.root) if engine.project else ""
                ),
            }
        }
    if name == "settings":
        if rest:
            field, _, raw = rest.partition(" ")
            if field in {"schema_version", "connections"}:
                raise ErolError("Use /connect and /providers for connections")
            values = engine.connections.settings.to_dict()
            try:
                value = json.loads(raw)
            except ValueError:
                value = raw
            values[field] = value
            engine.connections.settings = Settings.load(values)
            engine.connections.save()
        return {"settings": engine.connections.settings.to_dict()}
    if name == "plan":
        return engine.plan(rest)
    if name == "skills":
        argv = split_command(rest, language)
        if argv == ["auto"]:
            engine.skill_names = None
        elif len(argv) > 1 and argv[0] == "use":
            from .config import Config
            from .registry import Registry
            from .store import Store

            if engine.project is not None:
                with Store(engine.home, engine.project) as store:
                    Registry(project_store=store).select(
                        "explicit selection",
                        Config.load(engine.home, engine.root).max_active_skills,
                        argv[1:],
                    )
            else:
                Registry().select("explicit selection", names=argv[1:])
            engine.skill_names = argv[1:]
        elif argv:
            raise ErolError("/skills use NAME... | /skills auto")
        return {
            "skill_selection": engine.skill_names,
            "mode": "automatic" if engine.skill_names is None else "explicit",
        }
    if name in {"diff", "tests", "usage"}:
        if name == "usage":
            return {
                "usage": engine.record.get("usage", {}),
                "events": engine.record.get("usage_events", []),
            }
        if name == "diff":
            return diff_result(
                engine.record, engine.record.get("project_root", str(engine.root)), rest
            )
        return {name: engine.record.get("changes" if name == "diff" else "checks", [])}
    if name == "status":
        return {
            "project": engine.project.to_dict() if engine.project else None,
            "session": engine.session_id,
            "status": engine.record.get("status", "ready"),
            "model_preference": engine.selected_model or "auto",
            "effort_preference": engine.selected_effort or "auto",
            **(
                {
                    "mode": engine.mode,
                    "project_tools": False,
                    "native_cli_policy": "provider settings apply; not universal OS isolation",
                }
                if isinstance(engine, GeneralEngine)
                else {}
            ),
        }
    if name == "new":
        return {"session": engine.new()}
    if name == "resume":
        argv = split_command(rest, language)
        if not argv:
            return {"sessions": engine.sessions.list()}
        result = engine.resume(argv[0])
        if len(argv) == 2 and argv[1] == "continue":
            result["continue_task"] = engine.record["task"]
        elif len(argv) > 1:
            raise ErolError("/resume ID [continue]")
        return result
    if name == "exit":
        return {"exit": True}
    if name == "logo":
        return {"logo": True}
    raise ErolError(message(language, "unknown"))


def run_task(
    engine: ChatEngine | GeneralEngine, task: str, screen: Screen, *, resume: bool = False
) -> dict:
    if not any(c.enabled for c in engine.connections.settings.connections):
        result = interactive_command(engine, "/connect", screen)
        if not result.get("connection"):
            screen.draft = task
            screen.write(screen.t("draft_kept"))
            if not screen.rich:
                screen.write(task + "\n")
            return {}
        screen.write(screen.t("setup_ready"))
    if not screen.rich:
        return execute_task(engine, task, screen, resume=resume)
    with input_session(screen) as (fd, reader):

        def poll() -> str | None:
            if os.name == "nt":
                return key_windows(reader) if reader.kbhit() else None
            import select

            return key_posix(fd) if select.select([fd], [], [], 0)[0] else None

        return execute_task(engine, task, screen, resume=resume, poll=poll)


def execute_task(
    engine: ChatEngine | GeneralEngine,
    task: str,
    screen: Screen,
    *,
    resume: bool = False,
    poll=lambda: None,
) -> dict:
    screen.started, screen.running, screen.tokens = time.monotonic(), True, 0
    screen.estimated_cost = 0.0
    screen.role_model = ""
    screen.transport = ""
    screen.usage_events = []
    screen.usage = dict(getattr(engine, "record", {}).get("usage", {})) if resume else {}
    screen.estimated_cost = screen.usage.get("accounted_usd", 0.0)
    connections = getattr(engine, "connections", None)
    if connections is not None:
        screen.configure_connections(connections.settings)
    messages: queue.Queue = queue.Queue(maxsize=256)
    results: list[dict] = []
    errors: list[BaseException] = []

    def emit(item: dict) -> None:
        while True:
            try:
                messages.put(item, timeout=0.1)
                return
            except queue.Full:
                if engine.stopped.is_set():
                    return

    def work() -> None:
        try:
            results.append(engine.execute(task, emit, resume=resume))
        except BaseException as exc:
            errors.append(exc)

    thread = threading.Thread(target=work)
    thread.start()
    interrupted = False
    try:
        while thread.is_alive() or not messages.empty():
            try:
                key = poll()
                if key == "cancel":
                    raise KeyboardInterrupt
                if (
                    key is not None
                    and not scroll_key(screen, key)
                    and len(screen.pending_keys) < 16000
                ):
                    screen.pending_keys.append(key)
                item = messages.get(timeout=0.1)
                screen.event(item)
            except queue.Empty:
                screen.refresh()
            except KeyboardInterrupt:
                engine.cancel()
                interrupted = True
                screen.status = screen.t("cancel")
                screen.refresh()
    finally:
        try:
            if thread.is_alive():
                engine.cancel()
        finally:
            # No second editor/writer may start until the current worker has stopped.
            try:
                thread.join()
            finally:
                screen.running = False
    if errors:
        error = errors[0]
        if isinstance(error, ErolError):
            raise error
        raise ErolError("Task interrupted or failed; inspect /status")
    if interrupted:
        screen.write(screen.t("stopped"))
    return results[0]


def project_directory(text: str, base: Path, home: Path, language: str = "en") -> Path:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        text = text[1:-1]
    if not text or "\n" in text or "\r" in text:
        raise ErolError(message(language, "path_required"))
    path = Path(text).expanduser()
    path = path if path.is_absolute() else base / path
    try:
        project = Path(detect_project(path).root)
    except OSError as exc:
        raise ErolError(message(language, "missing_project")) from exc
    if project == home or project in home.parents:
        raise ErolError(message(language, "home_overlap"))
    return project


def launch(
    root: Path,
    home: Path,
    *,
    model: str | None = None,
    resume: str | None = None,
    mode: str = "auto",
    skill_names: list[str] | None = None,
) -> int:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ErolError(
            "Interactive chat needs a terminal; use erol chat --prompt TEXT for JSON output"
        )
    reject_links(home.expanduser().absolute())
    home = home.expanduser().resolve()
    root = root.expanduser().resolve(strict=True)
    reject_links(root)
    if not root.is_dir():
        raise ErolError("Working directory must be a folder")
    preference = read_settings(home / "connections.json").language
    engine: ChatEngine | GeneralEngine | None = None
    screen = Screen()
    history: list[str] = []
    try:
        screen.set_language(preference)
        screen.setup()
        if not screen.rich:
            screen.write(render_logo(16, color=False) + "\n")
        if mode not in {"auto", "general", "research"}:
            raise ErolError("Use auto, general or research mode")
        engine = (
            GeneralEngine(root, home)
            if mode != "auto" or root == home or root in home.parents
            else ChatEngine(root, home)
        )
        if isinstance(engine, GeneralEngine):
            engine.mode = "research" if mode == "research" else "general"
        if screen.preference != preference:
            engine.connections.settings.language = screen.preference
            engine.connections.save()
        engine.selected_model = model
        engine.skill_names = skill_names
        if resume:
            engine.resume(resume)
        if engine.project is not None and not engine.connections.settings.connections:
            for kind, executable in (
                ("codex", "codex"),
                ("claude", "claude"),
                ("antigravity", "agy"),
            ):
                if shutil.which(executable):
                    engine.connections.connect(kind)
        screen.status = screen.t("ready_hint")
        screen.configure_connections(
            engine.connections.settings,
            engine.mode if isinstance(engine, GeneralEngine) else engine.project.name,
        )
        screen.write(
            screen.t("general_header", resources=screen.resources)
            if engine.project is None
            else screen.t(
                "header",
                name=engine.project.name,
                root=engine.root,
                resources=screen.resources,
            )
        )
        screen.write(screen.t("welcome_actions"))
        # Provider probes remain explicit in global mode; /help and exit create no state.
        for provider in engine.providers()[0] if engine.project is not None else []:
            screen.write(
                f"{provider['id']}: "
                + (
                    screen.t("ready")
                    if provider.get("available")
                    else str(provider.get("reason", "erişilemiyor"))
                )
                + "\n"
            )
        while True:
            try:
                completions = ["/" + name for name in COMMANDS]
                settings = engine.connections.settings
                screen.configure_connections(
                    settings,
                    engine.mode if isinstance(engine, GeneralEngine) else engine.project.name,
                )
                screen.configure_selection(engine)
                completions += [f"/connect {kind}" for kind in KINDS]
                completions += ["/language " + value for value in ("auto", "en", "tr")]
                completions += ["/view compact", "/view full", "/motion on", "/motion off"]
                completions += [
                    "/model auto",
                    "/effort auto",
                    "/effort low",
                    "/effort medium",
                    "/effort high",
                ]
                completions += [
                    f"/settings {field}"
                    for field in ("api_budget_usd", "policy", "checks_path", "task_timeout_seconds")
                ]
                completions += [
                    f"/model {c.id}:{m.id}"
                    for c in engine.connections.settings.connections
                    for m in c.models
                ]
                text = read_prompt(screen, history, completions)
                if not text.strip():
                    text = "/menu"
                history.append(text)
                history = history[-100:]
                if text.startswith("/"):
                    result = interactive_command(engine, text, screen)
                    if screen.preference != engine.connections.settings.language:
                        screen.set_language(engine.connections.settings.language)
                    if result.get("exit"):
                        break
                    if "select_project" in result:
                        replacement = ChatEngine(Path(result["select_project"]), home)
                        replacement.selected_model = engine.selected_model
                        replacement.selected_effort = engine.selected_effort
                        engine.cancel()
                        engine = replacement
                        screen.draft = ""
                        history = []
                        screen.status = screen.t("ready_hint")
                        screen.write(
                            screen.t("project_changed", root=engine.root, session=engine.session_id)
                        )
                    elif result.get("select_general"):
                        if not isinstance(engine, GeneralEngine):
                            replacement_general = GeneralEngine(engine.root, home)
                            replacement_general.selected_model = engine.selected_model
                            replacement_general.selected_effort = engine.selected_effort
                            engine.cancel()
                            engine = replacement_general
                        engine.mode = result["mode"]
                        screen.write(screen.t("general_mode", mode=engine.mode))
                        if "general_task" in result:
                            run_task(engine, result["general_task"], screen)
                    elif result.get("logo"):
                        screen.logo()
                    elif result.get("clear"):
                        with screen.lock:
                            screen.display.text, screen.display.scroll = "", 0
                            screen.refresh()
                        if not screen.rich:
                            screen.write(screen.t("cleared"))
                    elif "view" in result:
                        screen.display.compact = result["view"] == "compact"
                        screen.refresh()
                        screen.write(screen.t("view_changed", view=result["view"]))
                    elif "motion" in result:
                        screen.display.motion = result["motion"]
                        screen.refresh()
                        screen.write(
                            screen.t("motion_changed", value="on" if result["motion"] else "off")
                        )
                    elif "continue_task" in result:
                        run_task(engine, result["continue_task"], screen, resume=True)
                    elif "language" in result:
                        screen.write(screen.t("language", **result))
                    elif "connection" in result:
                        connection = result["connection"]
                        screen.write(
                            screen.t(
                                "connected",
                                id=connection["id"],
                                kind=connection["kind"],
                                count=len(connection["models"]),
                            )
                        )
                        screen.write(screen.t("setup_ready"))
                    elif "commands" in result:
                        screen.write(present(result, screen.language))
                    elif result:
                        screen.write(present(result, screen.language))
                else:
                    if any(char.isalnum() for char in text):
                        run_task(engine, text, screen)
                    else:
                        screen.write(screen.t("task_required"))
            except (KeyboardInterrupt, EOFError):
                screen.write("\n")
                if isinstance(sys.exc_info()[1], EOFError):
                    break
            except (ErolError, ValueError, OSError) as exc:
                screen.write(
                    "\n" + (str(exc) if isinstance(exc, ErolError) else screen.t("invalid")) + "\n"
                )
    finally:
        try:
            if engine is not None:
                engine.cancel()
        finally:
            screen.close()
    return 0
