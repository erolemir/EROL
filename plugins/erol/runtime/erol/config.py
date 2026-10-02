"""Versioned configuration; global promotion remains explicitly opt-in."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from erol.common import ErolError
from erol.security import assert_secret_safe


@dataclass(frozen=True)
class Config:
    schema_version: int = 1
    learning_enabled: bool = True
    minimum_pattern_occurrences: int = 3
    minimum_confidence: float = 0.8
    project_skill_activation: bool = True
    global_auto_promotion: bool = False
    context_tokens: int = 4000
    max_active_skills: int = 4
    max_skill_chars: int = 12000
    minimum_successful_uses: int = 3
    maximum_false_trigger_rate: float = 0.1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def load(cls, home: Path, project: Path) -> Config:
        merged: dict = {}
        for path in (home / "config.json", project / ".erol.json"):
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    raise ErolError("Invalid EROL configuration") from exc
                if not isinstance(data, dict):
                    raise ErolError("Configuration must be an object")
                assert_secret_safe(data)
                unknown = set(data) - set(cls.__dataclass_fields__)
                if unknown:
                    raise ErolError("Unknown configuration fields")
                merged.update(data)
        config = cls(**merged)
        if type(config.schema_version) is not int or config.schema_version != 1:
            raise ErolError("Unsupported configuration schema")
        for field in ("learning_enabled", "project_skill_activation", "global_auto_promotion"):
            if type(getattr(config, field)) is not bool:
                raise ErolError(f"{field} must be boolean")
        if config.global_auto_promotion:
            raise ErolError(
                "Global auto-promotion is not implemented; use reviewed promotion candidates"
            )
        for field in (
            "minimum_pattern_occurrences",
            "context_tokens",
            "max_active_skills",
            "max_skill_chars",
            "minimum_successful_uses",
        ):
            value = getattr(config, field)
            if type(value) is not int or value < 1 or value > 100000:
                raise ErolError(f"{field} must be a positive bounded integer")
        if config.minimum_pattern_occurrences < 2:
            raise ErolError("Patterns require at least two distinct tasks")
        if config.max_active_skills > 6:
            raise ErolError("At most six active skills are supported")
        for field in ("minimum_confidence", "maximum_false_trigger_rate"):
            value = getattr(config, field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= value <= 1
            ):
                raise ErolError(f"{field} must be between zero and one")
        return config
