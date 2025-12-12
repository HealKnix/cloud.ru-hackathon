from __future__ import annotations

from typing import List

from .metadata import Candidate

SYSTEM_PROMPT = """
Ты ассистент для создания OData запросов к 1C.
ВАЖНО: Возвращай ТОЛЬКО валидный JSON без markdown-обёртки.

Формат ответа:
{
  "entity": "Prefix_EntityName",
  "filter_group": {
    "logic": "and",
    "conditions": [
      {"field": "FieldName", "operator": "eq", "value": "...", "value_type": "string"}
    ]
  },
  "select": ["Field1", "Field2"],
  "top": 100,
  "orderby": [["Date", "desc"]]
}

Правила:
- entity: используй ТОЛЬКО сущности из списка ниже
- operator: eq, ne, gt, lt, ge, le
- value_type: string, number, boolean, datetime, guid
- Для дат используй формат YYYY-MM-DD или YYYY-MM-DDTHH:MM:SS
""".strip()


FEW_SHOTS = [
    (
        "Покажи товары с ценой больше 1000",
        {
            "entity": "Catalog_Номенклатура",
            "filter_group": {
                "logic": "and",
                "conditions": [
                    {"field": "Цена", "operator": "gt", "value": 1000, "value_type": "number"}
                ],
            },
            "top": 100,
        },
    ),
    (
        "Документы за январь 2024",
        {
            "entity": "Document_РеализацияТоваровУслуг",
            "filter_group": {
                "logic": "and",
                "conditions": [
                    {"field": "Date", "operator": "ge", "value": "2024-01-01", "value_type": "datetime"},
                    {"field": "Date", "operator": "lt", "value": "2024-02-01", "value_type": "datetime"},
                ],
            },
            "orderby": [["Date", "desc"]],
            "top": 100,
        },
    ),
    (
        "Найди контрагента ООО Ромашка",
        {
            "entity": "Catalog_Контрагенты",
            "filter_group": {
                "logic": "and",
                "conditions": [
                    {"field": "Наименование", "operator": "eq", "value": "ООО Ромашка", "value_type": "string"}
                ],
            },
            "top": 10,
        },
    ),
    (
        "Активные договоры с суммой больше 1 млн",
        {
            "entity": "Document_Договор",
            "filter_group": {
                "logic": "and",
                "conditions": [
                    {"field": "Сумма", "operator": "gt", "value": 1000000, "value_type": "number"},
                    {"field": "Активен", "operator": "eq", "value": True, "value_type": "boolean"},
                ],
            },
            "select": ["Номер", "Дата", "Контрагент", "Сумма"],
            "orderby": [["Дата", "desc"]],
            "top": 50,
        },
    ),
    (
        "Найди справки с датой ранее 01.04.2024",
        {
            "entity": "Document_Справка",
            "filter_group": {
                "logic": "and",
                "conditions": [
                    {"field": "Date", "operator": "lt", "value": "2024-04-01", "value_type": "datetime"}
                ],
            },
            "top": 20,
        },
    ),
]


def _render_few_shots() -> str:
    lines: list[str] = []
    for query, response in FEW_SHOTS:
        lines.append(f"Запрос: \"{query}\"\n{response}")
    return "\n\n".join(lines)


def build_prompt(user_query: str, candidates: List[Candidate]) -> list[dict]:
    """Construct LLM prompt with available entities and few-shot examples."""
    entities_text = "\n".join(
        f"- {c.entity} ({c.synonym or c.name or '-'})"
        + (f": поля - {', '.join(c.fields[:5])}" if c.fields else "")
        for c in candidates
    )

    system_content = (
        SYSTEM_PROMPT
        + "\n\nПримеры:\n"
        + _render_few_shots()
        + "\n\nДоступные сущности:\n"
        + entities_text
    )

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_query},
    ]
