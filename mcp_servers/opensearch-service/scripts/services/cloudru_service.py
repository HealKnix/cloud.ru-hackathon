"""Сервис для работы с Cloud.ru Foundation Models (OpenAI-совместимое API).

Используется для:
- embeddings (для семантического поиска / чанкинга / реранкинга)
- chat completions (для RAG-ответов и HyDE)
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


def _parse_int(value: str | None, default: int, min_value: int = 1) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
        if parsed < min_value:
            return default
        return parsed
    except (TypeError, ValueError):
        return default


def _parse_float(value: str | None, default: float, min_value: float = 0.0, max_value: float = 2.0) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
        if parsed < min_value or parsed > max_value:
            return default
        return parsed
    except (TypeError, ValueError):
        return default


class CloudRuService:
    """Cloud.ru LLM/Embeddings сервис через OpenAI SDK."""

    def __init__(self) -> None:
        self.api_key: str | None = os.getenv("CLOUDRU_API_KEY") or os.getenv("API_KEY")
        self.base_url: str = os.getenv("CLOUDRU_BASE_URL", "https://foundation-models.api.cloud.ru/v1")

        self.embedding_model: str = os.getenv("CLOUDRU_EMBEDDING_MODEL", "BAAI/bge-m3")
        self.chat_model: str = os.getenv("CLOUDRU_CHAT_MODEL", "zai-org/GLM-4.6")

        self.embedding_dim: int = _parse_int(
            os.getenv("EMBEDDING_DIM") or os.getenv("CLOUDRU_EMBEDDING_DIM"),
            default=1024,
            min_value=1,
        )

        self.default_temperature: float = _parse_float(
            os.getenv("CLOUDRU_TEMPERATURE"),
            default=0.5,
            min_value=0.0,
            max_value=2.0,
        )

        self.enabled: bool = bool(self.api_key)
        if not self.enabled:
            logger.warning(
                "CloudRuService: CLOUDRU_API_KEY/API_KEY не задан — embeddings/LLM будут заглушками.",
            )

        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from openai import AsyncOpenAI  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Не установлен пакет `openai`. Установите зависимости из requirements.txt.",
            ) from e

        self._client = AsyncOpenAI(api_key=self.api_key or "", base_url=self.base_url)
        return self._client

    async def get_embedding(self, text: str) -> List[float]:
        """Получить embedding текста."""
        if not self.enabled:
            return [0.0] * self.embedding_dim

        client = self._get_client()
        response = await client.embeddings.create(model=self.embedding_model, input=[text])
        return list(response.data[0].embedding)

    async def get_chat_completion(
        self,
        *,
        messages: list[dict[str, str]],
        max_tokens: int = 800,
        temperature: Optional[float] = None,
        top_p: float = 0.95,
        presence_penalty: float = 0.0,
    ) -> str:
        """Вызов chat.completions с массивом сообщений."""
        if not self.enabled:
            return (
                "Сервис генерации текста сейчас не настроен (нет CLOUDRU_API_KEY/API_KEY). "
                "Обратитесь к администратору, чтобы добавить ключ в переменные окружения."
            )

        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.chat_model,
            max_tokens=max_tokens,
            temperature=self.default_temperature if temperature is None else temperature,
            presence_penalty=presence_penalty,
            top_p=top_p,
            messages=messages,
        )
        return (response.choices[0].message.content or "").strip()

    async def get_completion(self, prompt: str, max_tokens: int = 1000) -> str:
        """Совместимость с текущим кодом: completion по одному prompt."""
        return await self.get_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )

