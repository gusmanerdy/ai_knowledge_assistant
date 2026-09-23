from __future__ import annotations

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from backend.app.clients.model_client import ModelError
from backend.app.core.paths import PROJECT_ROOT


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-3.8-flash"

load_dotenv(PROJECT_ROOT / ".env")


class OpenRouterClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        if not self.api_key:
            raise ModelError("OPENROUTER_API_KEY belum diatur pada server.")

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        schema_name: str,
        schema: dict[str, Any],
        max_tokens: int,
        temperature: float = 0,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
            "provider": {"require_parameters": True},
            "plugins": [{"id": "response-healing"}],
        }

        parse_error: Exception | None = None
        for _attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(
                        OPENROUTER_URL,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in (401, 403):
                    raise ModelError("Kunci API OpenRouter ditolak. Periksa OPENROUTER_API_KEY.") from exc
                if exc.response.status_code == 402:
                    raise ModelError("Saldo OpenRouter tidak mencukupi.") from exc
                raise ModelError(f"OpenRouter gagal merespons (HTTP {exc.response.status_code}).") from exc
            except httpx.RequestError as exc:
                raise ModelError("OpenRouter tidak dapat dihubungi saat ini.") from exc

            try:
                content = response.json()["choices"][0]["message"]["content"]
                result = json.loads(content)
                if not isinstance(result, dict):
                    raise ValueError("Expected a JSON object")
                return result
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                parse_error = exc

        raise ModelError(
            "Format jawaban OpenRouter tidak dapat dibaca setelah dicoba ulang."
        ) from parse_error
