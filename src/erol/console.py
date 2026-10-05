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
from dataclasses import asdict
from pathlib import Path

from .chat import ChatEngine
from .common import ErolError, reject_links
from .connections import KINDS, Model, Settings, read_settings
from .console_input import InputRecord, decode_record
from .display import Display
from .general import GeneralEngine
from .i18n import HELP_EN, message, resolve_language
from .identity import detect_project
from .presentation import STATUS_KEYS, present
from .providers import visible
from .terminal import render_logo

COMMANDS = {
    "help": "Komutları ve örneklerini göster",
    "project": "Proje göster/seç: /project C:/Projects/my-app (boşluk varsa tırnak kullan)",
    "general": "Projesiz genel sohbete geç: /general [MESAJ]",
    "research": "Projesiz kaynak araştırması: /research [SORU veya URL]",
    "connect": "CLI/API ekle: /connect codex | /connect openai work OPENAI_API_KEY",
    "providers": "Bağlantıların giriş/yetenek durumunu göster; /providers disable ID",
    "models": "Model profilleri; /models refresh | /models add ID JSON_PROFILE",
    "model": "Otomatik veya elle seçim: /model auto | /model CONNECTION:MODEL",
    "settings": "Ayarları göster/değiştir: /settings api_budget_usd 5",
    "plan": "Çalıştırmadan planla: /plan GÖREV",
    "diff": "Son görevin eklenen/değişen/silinen dosyaları ve diff'i",
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

    def suggestions(self) -> list[str]:
        if not self.text.startswith("/") or "\n" in self.text:
            return []
        return [c for c in self.completions if c.startswith(self.text) and c != self.text][:5]

    def key(self, key: str) -> str | None:
        if key == "paste_start":
            self.pasting = True
        elif key == "paste_end":
            self.pasting = False
        elif key == "enter" and not self.pasting:
            if self.text.strip():
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
            options = [c for c in self.completions if c.startswith(self.text)]
            if options:
                self.text = os.path.commonprefix(options)
                self.cursor = len(self.text)
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
        self.windows_keys: WindowsKeys | None = None
        self.pending_keys: list[str] = []
        self.started = 0.0
        self.running = False
        self.tokens = 0
        self.estimated_cost = 0.0
        self.role_model = ""
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
                    self.write(
                        "\x1b[r\x1b[?1006l\x1b[?1000l\x1b[?2004l\x1b[0m\x1b[?25h\x1b[?1049l",
                        raw=True,
                    )
        finally:
            if self.console_mode is not None:
                self.console_mode.__exit__(None, None, None)

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
                    status += f" · {time.monotonic() - self.started:.0f}s · {self.tokens} token"
                    if self.estimated_cost:
                        status += f" · {self.t('estimate')} ${self.estimated_cost:.4f}"
                else:
                    self.display.running = False
                frame = self.display.frame(
                    columns,
                    rows,
                    visible(status),
                    pose=int(time.monotonic() * 2) % 6 if self.display.motion else 0,
                )
                output = ["\x1b[?25l"]
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
            self.write(data.get("text", ""))
        elif kind == "skills":
            names = data.get("names", [])
            self.write(
                self.t("skills_used", names=", ".join(names)) + "\n"
                if names
                else self.t("skills_none") + "\n"
            )
        elif kind == "routing":
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
            counts = data.get("counts", data)
            self.tokens += counts.get("input_tokens", 0) + counts.get("output_tokens", 0)
            cost = data.get("estimated_cost_usd")
            if cost is not None:
                self.estimated_cost += cost
        elif kind == "status":
            hints = (
                "/usage /research" if data.get("project_tools") is False else "/diff /tests /usage"
            )
            outcome = self.t(data["status"]) if data["status"] in STATUS_KEYS else data["status"]
            self.status = (
                f"{outcome} · {self.t('accounted')} ${data['usage']['accounted_usd']:.4f} · {hints}"
            )
            self.write(f"\n{self.status}\n")
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


def read_prompt(screen: Screen, history: list[str], completions: list[str]) -> str:
    if not screen.rich:
        return input("erol › ")
    editor = Editor(history, completions)
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
                result = editor.key(key)
                if result is not None:
                    screen.edit(None)
                    screen.write("erol › " + result + "\n")
                    return result
        finally:
            screen.display.suggestions = []
            screen.edit(None)


def command(engine: ChatEngine | GeneralEngine, text: str) -> dict:
    name, _, rest = text.removeprefix("/").partition(" ")
    language = resolve_language(engine.connections.settings.language)
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
        if isinstance(engine, GeneralEngine):
            engine.ensure_idle()
        return {"select_project": str(project_directory(rest, engine.root, engine.home, language))}
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
        if rest.startswith("add "):
            connection_id, _, profile = rest[4:].partition(" ")
            model = Model.load(json.loads(profile))
            connection = engine.connections.get(connection_id)
            connection.models = [m for m in connection.models if m.id != model.id] + [model]
            engine.connections.save()
        rows, models = engine.providers(refresh=rest == "refresh")
        return {
            "providers": rows,
            "profiles": {k: [asdict(m) for m in v] for k, v in models.items()},
        }
    if name == "model":
        if rest:
            if rest == "auto":
                engine.selected_model = None
            else:
                cid, sep, mid = rest.partition(":")
                if not sep or not any(m.id == mid for m in engine.connections.get(cid).models):
                    raise ErolError("Use /model CONNECTION:MODEL or /model auto")
                engine.selected_model = rest
        return {"model": engine.selected_model or "auto"}
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
    if name in {"diff", "tests", "usage"}:
        if name == "usage":
            return {
                "usage": engine.record.get("usage", {}),
                "events": engine.record.get("usage_events", []),
            }
        if name == "diff":
            return {
                "diff": engine.record.get("changes", []),
                "continuation_history": engine.record.get("continuation_history", []),
            }
        return {name: engine.record.get("changes" if name == "diff" else "checks", [])}
    if name == "status":
        return {
            "project": engine.project.to_dict() if engine.project else None,
            "session": engine.session_id,
            "status": engine.record.get("status", "ready"),
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
    project = Path(detect_project(path).root)
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
        screen.write(
            screen.t("general_header", budget=engine.connections.settings.api_budget_usd)
            if engine.project is None
            else screen.t(
                "header",
                name=engine.project.name,
                root=engine.root,
                budget=engine.connections.settings.api_budget_usd,
            )
        )
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
                screen.display.context = [
                    engine.mode if isinstance(engine, GeneralEngine) else engine.project.name,
                    f"API ${settings.api_budget_usd:g} · {settings.policy}",
                ]
                completions += [f"/connect {kind}" for kind in KINDS]
                completions += ["/language " + value for value in ("auto", "en", "tr")]
                completions += ["/view compact", "/view full", "/motion on", "/motion off"]
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
                history.append(text)
                history = history[-100:]
                if text.startswith("/"):
                    result = command(engine, text)
                    if screen.preference != engine.connections.settings.language:
                        screen.set_language(engine.connections.settings.language)
                    if result.get("exit"):
                        break
                    if "select_project" in result:
                        replacement = ChatEngine(Path(result["select_project"]), home)
                        replacement.selected_model = engine.selected_model
                        engine.cancel()
                        engine = replacement
                        history = []
                        screen.status = screen.t("ready_hint")
                        screen.write(
                            screen.t("project_changed", root=engine.root, session=engine.session_id)
                        )
                    elif result.get("select_general"):
                        if not isinstance(engine, GeneralEngine):
                            replacement_general = GeneralEngine(engine.root, home)
                            replacement_general.selected_model = engine.selected_model
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
                    elif "diff" in result:
                        if not result["diff"] and not result.get("continuation_history"):
                            screen.write(screen.t("no_changes") + "\n")
                        for step in result.get("continuation_history", []):
                            screen.write(screen.t("previous", task_id=step["task_id"]))
                            for item in step["changes"]:
                                screen.write(f"{item['status']}: {item['path']}\n{item['diff']}\n")
                        for item in result["diff"]:
                            screen.write(f"{item['status']}: {item['path']}\n{item['diff']}\n")
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
                    elif "commands" in result:
                        screen.write(present(result, screen.language))
                    else:
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
