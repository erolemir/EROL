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


def intent_clauses(task: str) -> tuple[str, list[str]]:
    """Exclude explicitly forbidden operations, not general prevention requests.

    This bounded bilingual rule is not a semantic parser or an authorization gate.
    Keep positive clauses after punctuation or contrast markers independent.
    """
    pieces = re.split(
        r"([,;.!?\n]|\b(?:but|ama|fakat|ancak|sadece|only|and|ve)\b)", task, flags=re.I
    )
    clauses = pieces[::2]
    separators = [normalize(value) for value in pieces[1::2]]
    operations = r"(?:deploy|deployment|release|publish|publication|migration|migrate|refactor)"
    texts = [normalize(clause) for clause in clauses]
    forbidden = [
        bool(
            re.search(
                rf"\b(?:do not|don t|dont|never|skip)\s+(?:\w+\s+){{0,2}}{operations}\b"
                rf"|\b{operations}\b.*\b(?:yapma|yapmayin|etme|etmeyin|out of scope|kapsam disi)\b",
                text,
            )
        )
        for text in texts
    ]
    bare = [bool(re.fullmatch(rf"{operations}(?: the)?(?: database)?", text)) for text in texts]
    # Shared conjunction negation may travel only over bare operations; punctuation
    # and contrast markers always stop it. Positive actions remain independent.
    for _ in range(len(clauses)):
        for index, separator in enumerate(separators):
            if separator not in {"and", "ve"}:
                continue
            if forbidden[index] and bare[index + 1]:
                forbidden[index + 1] = True
            if bare[index] and forbidden[index + 1]:
                forbidden[index] = True
    active = [clause for clause, excluded in zip(clauses, forbidden, strict=True) if not excluded]
    excluded = [text for text, flag in zip(texts, forbidden, strict=True) if flag]
    return " ".join(active), excluded


def routing_task(task: str, previous: str = "") -> tuple[str, bool]:
    """Carry only an explicit continuation's bounded task context, never greetings."""
    text = normalize(task)
    replacement = any(
        phrase in text
        for phrase in (
            "bunu birak",
            "bunu unut",
            "vazgec",
            "yerine",
            "instead",
            "new task",
            "forget that",
        )
    )
    continuation = any(
        text.startswith(phrase)
        for phrase in (
            "ve daha ",
            "and make it ",
            "bunu ",
            "bu isi ",
            "ayrica bunu ",
            "make it ",
            "daha iyi calis",
            "daha hizli calis",
            "continue ",
            "devam et",
        )
    )
    inherited = bool(previous and continuation and not replacement)
    return (previous[:2000] + "\n" + task if inherited else task), inherited


def score(task: str, metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Only explicit trigger phrases activate a skill; exclusions win."""
    if metadata.get("scope") == "project":
        task = normalize_error(task)
    return _score_normalized(normalize(intent_clauses(task)[0]), metadata, normalize(task))


def _score_normalized(
    task: str, metadata: Mapping[str, Any], exclusion_task: str | None = None
) -> dict[str, Any]:
    """Reuse the normalized task across the builtin catalog without retaining task text."""
    padded_task = f" {task} "
    exclusions = f" {exclusion_task if exclusion_task is not None else task} "
    avoided = [
        phrase
        for phrase in metadata.get("avoid_when", [])
        if (normalized := normalize(phrase)) and f" {normalized} " in exclusions
    ]
    matches = [
        (phrase, normalized)
        for phrase in metadata.get("triggers", [])
        if (normalized := normalize(phrase)) and f" {normalized} " in padded_task
    ]
    matched = [phrase for phrase, _ in matches]
    points = sum(1 + len(normalized.split()) for _, normalized in matches)
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
    normalized_task = normalize(intent_clauses(task)[0])
    original_task = normalize(task)
    results = [
        score(task, entry)
        if entry.get("scope") == "project"
        else _score_normalized(normalized_task, entry, original_task)
        for entry in catalog
    ]
    results = [result for result in results if result["score"] > 0]
    # Prefer project expertise only at equal relevance. Stable ties are lexical.
    results.sort(key=lambda item: (-item["score"], item["scope"] != "project", item["name"]))
    return results[:limit]
