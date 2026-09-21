from __future__ import annotations

from typing import Any, Protocol


class ModelError(Exception):
    pass


class ModelClient(Protocol):
    model: str

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        schema_name: str,
        schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]: ...
