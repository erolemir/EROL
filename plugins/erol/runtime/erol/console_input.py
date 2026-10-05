"""Windows input records preserve native wheel events and Unicode keyboard input."""

from __future__ import annotations

import ctypes
from ctypes import wintypes


class Coord(ctypes.Structure):
    _fields_ = [("x", wintypes.SHORT), ("y", wintypes.SHORT)]


class KeyEvent(ctypes.Structure):
    _fields_ = [
        ("down", wintypes.BOOL),
        ("repeat", wintypes.WORD),
        ("key", wintypes.WORD),
        ("scan", wintypes.WORD),
        ("char", wintypes.WCHAR),
        ("control", wintypes.DWORD),
    ]


class MouseEvent(ctypes.Structure):
    _fields_ = [
        ("position", Coord),
        ("buttons", wintypes.DWORD),
        ("control", wintypes.DWORD),
        ("flags", wintypes.DWORD),
    ]


class EventData(ctypes.Union):
    _fields_ = [("key", KeyEvent), ("mouse", MouseEvent)]


class InputRecord(ctypes.Structure):
    _fields_ = [("type", wintypes.WORD), ("data", EventData)]


def decode_record(record: InputRecord) -> str:
    if record.type == 2 and record.data.mouse.flags == 4:
        delta = ctypes.c_short(record.data.mouse.buttons >> 16).value
        if delta:
            return "\x1b[<64;1;1M" if delta > 0 else "\x1b[<65;1;1M"
    if record.type == 1 and (
        record.data.key.down or (record.data.key.key == 18 and record.data.key.char != "\x00")
    ):
        # ConPTY/Alt-code Unicode characters can be delivered on VK_MENU key-up.
        # Ordinary key-up records must still be discarded to avoid duplicate input.
        event = record.data.key
        char = event.char
        if not char or char == "\x00":
            char = {
                8: "\x7f",
                13: "\r",
                33: "\x1b[5~",
                34: "\x1b[6~",
                35: "\x1b[F",
                36: "\x1b[H",
                37: "\x1b[D",
                38: "\x1b[A",
                39: "\x1b[C",
                40: "\x1b[B",
                46: "\x1b[3~",
            }.get(event.key, "")
        return char * max(1, min(event.repeat, 128))
    return ""
