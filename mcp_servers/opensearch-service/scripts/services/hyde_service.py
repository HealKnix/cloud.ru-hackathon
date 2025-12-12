"""
HyDE (Hypothetical Document Embeddings) — вспомогательный сервис для усиления поиска.

Адаптация файла из проекта «2гис» без изменений логики,
использует Cloud.ru LLM (OpenAI-совместимое API) для генерации гипотетических документов.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from scripts.services.cloudru_service import CloudRuService

logger = logging.getLogger(__name__)


class HyDEProcessor:
    """Класс для реализации HyDE‑подхода."""

    def __init__(self) -> None:
        self.llm = CloudRuService()

    async def generate_hypothetical_documents(
        self, query: str, num_hypotheses: int = 1
    ) -> List[str]:
        """Генерирует гипотетические документы для запроса."""
        try:
            print(f"HyDE: генерируем гипотезы для запроса: '{query}'")
            hypotheses: List[str] = []

            for i in range(num_hypotheses):
                prompts = [
                    f"Ключевые слова для поиска: {query}",
                    f"Поисковые термины: {query}",
                    f"Что искать: {query}",
                    f"Поиск: {query}",
                ]

                prompt = prompts[i % len(prompts)]
                print(f"HyDE: используем промпт {i + 1}: {prompt[:100]}...")
                hypothesis = await self._generate_hypothesis(prompt)

                if hypothesis and hypothesis not in hypotheses:
                    hypotheses.append(hypothesis)
                    print(
                        f"HyDE: сгенерирована гипотеза {i + 1}: {hypothesis[:100]}..."
                    )
                else:
                    print(f"HyDE: гипотеза {i + 1} не сгенерирована или дублируется")

            print(f"HyDE: всего сгенерировано гипотез: {len(hypotheses)}")
            return hypotheses
        except Exception as e:
            logger.error("Ошибка при генерации гипотетических документов: %s", e)
            return []

    async def _generate_hypothesis(self, prompt: str) -> Optional[str]:
        """Генерирует одну гипотезу через Cloud.ru LLM."""
        try:
            hypothesis = await self.llm.get_chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Ты эксперт по поиску. Генерируй только короткие ключевые "
                            "слова и термины для поиска, не более 10–15 слов. "
                            "Не создавай длинные описания."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=100,
                temperature=0.7,
            )
            if not hypothesis:
                print("HyDE: пустая гипотеза в ответе")
                return None

            print(f"HyDE гипотеза сгенерирована: {hypothesis[:100]}...")
            return hypothesis.strip()
        except Exception as e:
            logger.error("Ошибка при генерации гипотезы: %s", e)
            return None


hyde_processor = HyDEProcessor()
