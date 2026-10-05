"""Render the reference mantis using terminal half blocks and standard-library data."""

from __future__ import annotations

import base64
import json
import math
import zlib
from functools import lru_cache
from importlib.resources import files


@lru_cache(maxsize=128)
def render_logo(width: int = 80, *, color: bool = True, bright: bool = False, pose: int = 0) -> str:
    """Scale the reference to square half cells; each text row holds two pixels."""
    if not 8 <= width <= 160:
        raise ValueError("Logo width must be between 8 and 160 columns")
    asset = json.loads(files("erol").joinpath("data/terminal-logo.json").read_text("utf-8"))
    source_width, source_height = asset["width"], asset["height"]
    pixels = zlib.decompress(base64.b64decode(asset["green_zlib_base64"]))
    height = max(2, 2 * math.ceil(source_height * width / source_width / 2))
    scaled = []
    for y in range(height):
        y0, y1 = y * source_height // height, (y + 1) * source_height // height
        row = []
        for x in range(width):
            x0, x1 = x * source_width // width, (x + 1) * source_width // width
            total = sum(
                sum(pixels[sy * source_width + x0 : sy * source_width + x1]) for sy in range(y0, y1)
            )
            # Retain anti-aliased stroke edges, dropping near-black source noise.
            intensity = round(total / ((x1 - x0) * (y1 - y0)))
            if bright and intensity >= 8:
                intensity = round(255 * (intensity / 255) ** 0.25)
            row.append(intensity if intensity >= 8 else 0)
        scaled.append(row)
    if pose:
        # Keep the abdomen still while antennae and forelegs gently flex.
        motion = (0, 1, 1, 0, -1, -1)[pose % 6]
        for y, row in enumerate(scaled):
            if y < height * 0.18 or height * 0.30 < y < height * 0.56:
                moved = [0] * width
                for x, intensity in enumerate(row):
                    offset = motion * (-1 if x < width // 2 else 1)
                    if 0 <= x + offset < width:
                        moved[x + offset] = intensity
                scaled[y] = moved
    lines = []
    for y in range(0, height, 2):
        parts = []
        previous = None
        for top, bottom in zip(scaled[y], scaled[y + 1], strict=True):
            if color:
                pair = (top, bottom)
                if pair != previous:
                    parts.append(f"\x1b[38;2;0;{top};0m\x1b[48;2;0;{bottom};0m")
                    previous = pair
                parts.append("▀" if top or bottom else " ")
            else:
                parts.append("█" if top and bottom else "▀" if top else "▄" if bottom else " ")
        lines.append("".join(parts) + ("\x1b[0m" if color else ""))
    return "\n".join(lines)
