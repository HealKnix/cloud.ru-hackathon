# Agent (AG-UI + MCP)

Этот модуль поднимает Python-бэкенд агента с API в стиле **AG-UI** и подключением инструментов через **MCP**.

## Что внутри

- `server.py` — FastAPI приложение:
  - AG-UI endpoints: `POST /api/agui`, `POST /api/agent`
  - MCP endpoints для фронта: `GET /api/mcp/servers`, `POST /api/mcp/servers/{id}/state`
- `simple.py` — LangGraph-граф агента (LangChain tools + MCP tools).
- `agui-agent-example.json` — конфиг LLM + MCP серверов и их инструментов.
- `.mcp_state.json` — локальное состояние (включён/выключен MCP сервер), создаётся автоматически.

## Требования

- Windows / macOS / Linux
- Python 3.12+ (в проекте используется виртуальное окружение в `agent/.venv`)
- Docker (если используете MCP сервер `opensearch-rag` через `stdio` + `docker exec`)

## Быстрый старт (Windows / PowerShell)

1. Запустить API агента:

```powershell
cd "F:\Projects\cloud.ru hackathon"
agent\.venv\Scripts\uvicorn.exe agent.server:app --reload --reload-dir agent --port 5001
```

2. Проверить health:

```powershell
curl http://localhost:5001/healthz
```

## Как фронт ходит в агента

Фронтенд ожидает базовый URL API вида `http://localhost:5001/api`.

Ключевые запросы:

- Чат (AG-UI):
  - `POST /api/agui` (алиас `POST /api/agent`)
  - Тело: `{ "messages": [{ "role": "user", "content": "..." }], "metadata": {...} }`

### Stream / non-stream режимы

`/api/agui` и `/api/agent` поддерживают оба режима:

- **Stream (SSE)** — по умолчанию (или если `Accept: text/event-stream`).
- **Non-stream (JSON)** — если `Accept: application/json` или query-параметр `?stream=false`.

Примеры:

```bash
# JSON ответ
curl -X POST "http://localhost:5001/api/agui?stream=false" ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Привет\"}]}"

# SSE (стрим)
curl -N -X POST "http://localhost:5001/api/agui" ^
  -H "Content-Type: application/json" ^
  -H "Accept: text/event-stream" ^
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Привет\"}]}"
```

Если внутри произошла ошибка (например, у провайдера LLM закончился баланс), endpoint вернёт:

- в JSON режиме: `200` + `{ "error": true, "message": "..." }`
- в SSE режиме: поток с текстом ошибки и завершением `[DONE]`

## MCP серверы

MCP сервера настраиваются в `agui-agent-example.json` в секции `mcp`.
Агент выбирает сервер по имени инструмента (tool name).

### `odata` (transport: `streamable-http`)

Пример:

```json
"odata": {
  "transport": "streamable-http",
  "endpoint": "http://localhost:8000/mcp",
  "tools": ["get_navigation_link", "query_1c_data", "list_odata_entities"]
}
```

Технологии:

- MCP transport: `streamable-http`
- Источник данных: 1С OData (внешний сервис)

### `opensearch-rag` (transport: `stdio`)

Пример:

```json
"opensearch-rag": {
  "transport": "stdio",
  "command": "docker",
  "args": ["exec", "-i", "mcp-server", "python", "/app/mcp_server.py"],
  "tools": ["upload_document", "ask_question", "search_documents"]
}
```

Технологии:

- MCP transport: `stdio` (процесс запускается локально через `docker exec`)
- MCP сервер: Python FastMCP внутри контейнера
- Хранилище/поиск: OpenSearch 2.11 + kNN (векторный поиск)
- RAG: поиск + генерация (в зависимости от настройки MCP сервера)

Подробности по OpenSearch MCP см. `agent/MCP_GUIDE.md`.

## Управление включением MCP серверов

Фронтенд дергает:

- `GET /api/mcp/servers` — список серверов и тулов
- `POST /api/mcp/servers/{id}/state` — включить/выключить сервер

Состояние хранится в `agent/.mcp_state.json`.

## Конфигурация LLM

Секция `llm` лежит в `agui-agent-example.json`.

Важно:

- поле `api_key_env` поддерживает два режима:
  - если в окружении есть переменная с таким именем — берётся её значение
  - иначе строка используется как ключ напрямую (не рекомендуется хранить ключ в репозитории)

## Отладка

Чтобы печатать traceback в консоль при ошибках:

```powershell
$env:AGENT_DEBUG="true"
agent\.venv\Scripts\uvicorn.exe agent.server:app --reload --reload-dir agent --port 5001
```

## Частые проблемы

### `openai.APIStatusError: Not enough money`

Это ошибка провайдера LLM (например, OpenRouter): закончился баланс/лимиты/невалидный ключ.
Нужно заменить ключ/модель или пополнить баланс.

### `ConnectError` при вызове MCP OData

Обычно означает, что `endpoint` (`http://localhost:8000/mcp`) недоступен.
Либо поднимите MCP сервис, либо отключите `odata` через `POST /api/mcp/servers/odata/state`.
