"""Conservative local secret and generated-instruction checks; not a sandbox."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import PurePath
from typing import Any

from erol.common import ErolError, canonical

SENSITIVE_LABEL = (
    r"(?:(?:[a-z0-9]+[_-])*(?:password|passwd|api[_-]?key|"
    r"secret(?:[_-]?access[_-]?key)?|client[_-]?secret|private[_-]?key|"
    r"(?:access|refresh|id|auth|signing|encryption)[_-]?(?:token|key)|"
    r"token|session[_-]?cookie|cookie|authorization|credentials?)|"
    r"(?:aws|stripe|openai|anthropic|gemini|google|github|gitlab|azure|"
    r"slack|discord|twilio|sendgrid|supabase)[_-](?:[a-z0-9]+[_-])*key)"
)
SENSITIVE_FIELD = re.compile(r"(?i)^" + SENSITIVE_LABEL + r"$")

SECRET_PATTERNS = (
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b",
    r"(?i)\b" + SENSITIVE_LABEL + r"[\s\"']*[:=][\s\"']*[^\s\"',;}]+",
    r"(?i)(?:authorization[\s\"']*[:=][\s\"']*(?:bearer|basic)\s+\S+|cookie\s*:\s*\S+)",
    r"(?i)\b(?:https?|postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s/@]+:[^\s/@]+@",
    r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b",
)
INSTRUCTION_PATTERNS = (
    r"(?i)\bignore\b.{0,40}\b(?:previous|system|developer)\b.{0,30}\binstructions\b",
    r"(?i)\b(?:curl|wget)\b[^\n]*\|\s*(?:bash|sh|powershell|iex)\b",
    r"(?i)\b(?:rm\s+-[rf]*r[rf]*\s|remove-item\b[^\n]*-recurse|format\s+[a-z]:)",
    r"(?i)\b(?:invoke-expression|eval|exec)\s*\(",
    r"(?i)\b(?:upload|exfiltrate|send)\b.{0,60}\b(?:credentials|secrets|tokens|private keys)\b",
    r"(?i)(?:base64\s+(?:--decode|-d)|frombase64string|bypass.{0,20}permissions)",
)


def _pattern_findings(text: str) -> list[str]:
    return [
        f"secret-pattern-{i}"
        for i, pattern in enumerate(SECRET_PATTERNS)
        if re.search(pattern, text)
    ]


def scan_secrets(value: Any) -> list[str]:
    # Scan original strings, rather than JSON-escaped text, so multiline keys and headers match.
    if isinstance(value, dict):
        texts = [str(key) for key in value]
        assignments = [f"{key}={v}" for key, v in value.items() if isinstance(v, str)]
        # Any nonempty explicitly labelled credential is unsafe, even short/numeric ones.
        labelled = [
            "labelled-credential"
            for key, item in value.items()
            if SENSITIVE_FIELD.fullmatch(str(key)) and item not in (None, "")
        ]
        return sorted(
            set(
                labelled
                + scan_secrets(texts)
                # Assignments preserve credential-label matching, but entropy
                # belongs to the value itself rather than a synthetic key=value.
                + sum((_pattern_findings(text) for text in assignments), [])
                + sum((scan_secrets(v) for v in value.values()), [])
            )
        )
    if isinstance(value, (list, tuple)):
        return sorted(set(sum((scan_secrets(v) for v in value), [])))
    text = value if isinstance(value, str) else canonical(value)
    findings = _pattern_findings(text)
    for token in re.findall(r"[A-Za-z0-9+/=_-]{32,}", text):
        # Content hashes and normalized identifiers are routine, not credentials.
        if re.fullmatch(r"[a-fA-F0-9]{32,128}", token):
            continue
        if re.fullmatch(r"(?:project_id=)?[a-z0-9][a-z0-9-]{0,47}-[a-f0-9]{16}", token):
            # detect_project emits a normalized slug plus a 16-hex content hash.
            # Explicit credential labels and known secret patterns above still apply.
            continue
        entropy = -sum(
            (n / len(token)) * math.log2(n / len(token)) for n in Counter(token).values()
        )
        if entropy > 4.5 and re.search(r"[a-z]", token) and re.search(r"[A-Z0-9]", token):
            findings.append("high-entropy-value")
    return sorted(set(findings))


def assert_secret_safe(value: Any) -> None:
    try:
        findings = scan_secrets(value)
    except (ValueError, TypeError) as exc:
        raise ErolError("Persistent input must contain finite JSON-compatible values") from exc
    if findings:
        raise ErolError("Secret-like content rejected before persistence; sanitize the input")


def assert_project_path_safe(path: PurePath) -> None:
    """Scan a known filesystem path without mistaking joined components for base64.

    Only project detection/storage calls this entry. Arbitrary memory strings and
    credential fields retain the full-value scanner. Known credential patterns
    still inspect the entire path; entropy checks inspect each path component.
    """
    if not path.is_absolute():
        raise ErolError("Project path must be absolute")
    if _pattern_findings(str(path)):
        raise ErolError("Secret-like content rejected before persistence; sanitize the input")
    assert_secret_safe(path.parts)


def scan_instructions(body: str) -> list[str]:
    return scan_secrets(body) + [
        f"unsafe-instruction-{i}"
        for i, pattern in enumerate(INSTRUCTION_PATTERNS)
        if re.search(pattern, body)
    ]
