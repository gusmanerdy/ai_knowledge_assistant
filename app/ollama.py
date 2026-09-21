from __future__ import annotations

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from app.model_client import ModelError


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_LOCAL_MODEL = "qwen2.5-3b-instruct-q6k"

load_dotenv()


class OllamaClient:
    def __init__(self) -> None:
        base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL).strip()
        self.base_url = base_url.rstrip("/") or DEFAULT_OLLAMA_URL
        self.model = os.getenv("OLLAMA_MODEL", DEFAULT_LOCAL_MODEL).strip() or DEFAULT_LOCAL_MODEL

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        schema_name: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]:
        schema_instruction = (
            f"Return only JSON for {schema_name} matching this schema: "
            f"{json.dumps(schema, ensure_ascii=False)}"
        )
        prepared_messages = [dict(message) for message in messages]
        if prepared_messages and prepared_messages[0].get("role") == "system":
            prepared_messages[0]["content"] += f"\n\n{schema_instruction}"
        else:
            prepared_messages.insert(0, {"role": "system", "content": schema_instruction})

        payload = {
            "model": self.model,
            "messages": prepared_messages,
            "format": schema,
            "stream": False,
            "options": {"temperature": 0, "num_predict": max_tokens},
            "keep_alive": "10m",
        }

        parse_error: Exception | None = None
        for _attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=180) as client:
                    response = await client.post(f"{self.base_url}/api/chat", json=payload)
                    response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise ModelError(
                        f"Model lokal '{self.model}' belum tersedia. Jalankan: ollama pull {self.model}"
                    ) from exc
                raise ModelError(f"Ollama gagal merespons (HTTP {exc.response.status_code}).") from exc
            except httpx.RequestError as exc:
                raise ModelError(
                    "Ollama belum berjalan di perangkat ini. Instal dan jalankan Ollama terlebih dahulu."
                ) from exc

            try:
                content = response.json()["message"]["content"]
                result = json.loads(content)
                if not isinstance(result, dict):
                    raise ValueError("Expected a JSON object")
                return result
            except (KeyError, TypeError, ValueError) as exc:
                parse_error = exc

        raise ModelError(
            "Format jawaban model lokal tidak dapat dibaca setelah dicoba ulang."
        ) from parse_error
