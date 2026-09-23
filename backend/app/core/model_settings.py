from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from backend.app.core.paths import MODEL_SETTINGS_PATH


SETTINGS_PATH = MODEL_SETTINGS_PATH


class ModelSettings(BaseModel):
    provider: Literal["openrouter", "local"] = "openrouter"
    intent: str = Field(
        "Menjawab pertanyaan riset berdasarkan paper yang ditemukan",
        min_length=3,
        max_length=160,
    )
    response_instruction: str = Field(
        (
            "Berikan sintesis yang jelas, langsung menjawab pertanyaan, dan jelaskan "
            "implikasi penting tanpa melebih-lebihkan bukti."
        ),
        min_length=10,
        max_length=2000,
    )
    max_tokens: int = Field(1800, ge=128, le=4096)
    paragraph_count: int = Field(3, ge=1, le=5)
    temperature: float = Field(0.2, ge=0, le=1)
    evidence_policy: Literal["strict", "balanced", "exploratory"] = "strict"


DEFAULT_MODEL_SETTINGS = ModelSettings()


def load_model_settings() -> ModelSettings:
    if not SETTINGS_PATH.exists():
        return DEFAULT_MODEL_SETTINGS.model_copy(deep=True)

    try:
        return ModelSettings.model_validate_json(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValidationError, json.JSONDecodeError):
        return DEFAULT_MODEL_SETTINGS.model_copy(deep=True)


def save_model_settings(settings: ModelSettings) -> ModelSettings:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = SETTINGS_PATH.with_suffix(".tmp")
    temporary_path.write_text(
        settings.model_dump_json(indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(SETTINGS_PATH)
    return settings


def reset_model_settings() -> ModelSettings:
    settings = DEFAULT_MODEL_SETTINGS.model_copy(deep=True)
    return save_model_settings(settings)
