"""Deterministic, explainable metadata routing; no model calls or body loading."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from typing import Any

from erol.fingerprint import normalize_error


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    # Casefold expands dotted capital İ to i + COMBINING DOT ABOVE, which
    # must not split a word. Fold Turkish letters for common ASCII typing;
    # this is explicit normalization, not stemming or fuzzy matching.
    text = text.replace("i\u0307", "i").translate(str.maketrans("ıçğöşü", "icgosu"))
    return " ".join(re.findall(r"[^\W_]+", text, flags=re.UNICODE))


def contains_phrase(task: str, phrase: str) -> bool:
    phrase = normalize(phrase)
    return bool(phrase) and f" {phrase} " in f" {normalize(task)} "


def score(task: str, metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Only explicit trigger phrases activate a skill; exclusions win."""
    if metadata.get("scope") == "project":
        task = normalize_error(task)
    avoided = [p for p in metadata.get("avoid_when", []) if contains_phrase(task, p)]
    matched = [p for p in metadata.get("triggers", []) if contains_phrase(task, p)]
    points = sum(1 + len(normalize(p).split()) for p in matched)
    return {
        "name": metadata["name"],
        "score": 0 if avoided else points,
        "matched_triggers": matched,
        "excluded_by": avoided,
        "scope": metadata.get("scope", "builtin"),
    }


def rank(task: str, catalog: Iterable[Mapping[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError("limit must be a nonnegative integer")
    results = [score(task, entry) for entry in catalog]
    results = [result for result in results if result["score"] > 0]
    # Prefer project expertise only at equal relevance. Stable ties are lexical.
    results.sort(key=lambda item: (-item["score"], item["scope"] != "project", item["name"]))
    return results[:limit]
