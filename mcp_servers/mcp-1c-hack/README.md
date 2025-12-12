# Universal 1C MCP Server

On-demand MCP сервер для 1С: по строке подключения может выгрузить метаданные, построить индекс, а также выполнять запросы к 1С через OData. Для построения OData-плана используется Cloud.ru foundation models (OpenAI-compatible API, без stream).

## Возможности

- `get_navigation_link` — ищет объект конфигурации 1С по имени/синониму и возвращает e1c ссылку.
- `query_1c_data` — принимает запрос на естественном языке, строит OData-план через LLM и выполняет OData-запрос, возвращая итог и `structured_content`.
- `list_odata_entities` — запрашивает `$metadata` OData и возвращает список сущностей.

## Требования

- Windows с установленной 1С (`1cv8.exe`/`1cv8c.exe`) — требуется для построения индекса метаданных (по желанию; `query_1c_data` умеет работать и через `$metadata`).
- Python 3.11+
- Зависимости из `pyproject.toml` или `requirements.txt`

## Переменные окружения

- `ONEC_BIN_PATH` — путь к `1cv8.exe`/`1cv8c.exe` (если авто-поиск не нашел).
- `PORT` / `HOST` — параметры MCP сервера (по умолчанию `8000` / `0.0.0.0`).
- `API_KEY`, `CLOUD_MODEL_ID` (например, `zai-org/GLM-4.6`), опционально `CLOUD_API_URL` (по умолчанию `https://foundation-models.api.cloud.ru/v1`) — доступ к Cloud.ru foundation models.
- `ODATA_1C_URL`, `ODATA_1C_USER`, `ODATA_1C_PASSWORD` — подключение к OData 1С.
- `ONEC_CONNECTION_STRING` — строка подключения к 1С для кеширования метаданных (можно передать параметром в инструмент).
- `LLM_TIMEOUT`, `ODATA_TIMEOUT` — тайм-ауты в секундах для LLM и OData.
- `E1C_NAV_BASE` — префикс для e1c навигационных ссылок (опционально).

## Установка

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
# или
pip install -r requirements.txt
```

## Запуск

```bash
python server.py
# сервер слушает http://localhost:8000/mcp (transport: streamable-http)
```

## Использование инструментов

### get_navigation_link

- `query` (str, required) — имя/синоним, например: `Справочник Номенклатура`.
- `connection_string` (str, optional) — IBConnectionString; если не указан, используется `ONEC_CONNECTION_STRING`.
- `username` / `password` (optional) — учетные данные 1С Designer; если не заданы, берутся `ONEC_USERNAME` / `ONEC_PASSWORD`.
- `force_update` (bool) — принудительно пересоздать кеш.

Результат: текст с найденным объектом и ссылкой, а также `structured_content.match/score/link`.

### query_1c_data

- `user_query` (str, required) — произвольный запрос пользователя.
- `connection_string` (str, optional) — IBConnectionString; если не указан, используется `ONEC_CONNECTION_STRING` (если задан).
- `username` / `password` (optional) — учетные данные OData; если не заданы, берутся `ODATA_1C_USER` / `ODATA_1C_PASSWORD`.

Результат: краткое резюме выборки, `structured_content.plan` (entity + params), `structured_content.odata_url`, `structured_content.odata_response` и `meta` со статусом/таймингами.

### list_odata_entities

- `username` / `password` (optional) — учетные данные OData.

Результат: список сущностей из `$metadata` и `metadata_url` в `structured_content`.
