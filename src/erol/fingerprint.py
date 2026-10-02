"""Lightweight error-family normalization; HTTP/SQL status codes retain meaning."""

from __future__ import annotations

import hashlib
import re


def normalize_error(error: str) -> str:
    value = error.lower()
    value = re.sub(
        r"\b(?:request(?:[_-]?id)?|trace(?:[_-]?id)?|session(?:[_-]?id)?|correlation[_-]?id)\s*[:=]\s*\S+",
        "",
        value,
    )
    value = re.sub(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", "<id>", value
    )
    value = re.sub(
        r"\b\d{4}-\d{2}-\d{2}(?:[t ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:z|[+-]\d{2}:\d{2})?)?\b",
        "",
        value,
    )
    value = re.sub(r"\b(?:at\s+)?\d{1,2}:\d{2}(?::\d{2})?\b", "", value)
    value = re.sub(r"\b(?:at\s+)?line\s+\d+\b", "line <n>", value)
    value = re.sub(r"\b[0-9a-f]{12,}\b", "<id>", value)
    # Numbers are deliberately retained: SQLSTATE, HTTP codes, errno and schema versions matter.
    return " ".join(re.findall(r"[\w<>]+", value))


def fingerprint(error: str, component: str, exception: str = "", root_category: str = "") -> str:
    family = "|".join(
        (
            normalize_error(error),
            component.casefold().strip(),
            exception.casefold().strip(),
            root_category.casefold().strip(),
        )
    )
    return hashlib.sha256(family.encode("utf-8")).hexdigest()[:24]
