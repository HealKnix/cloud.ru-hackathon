# Агент 1С — UI + Agent + MCP

Проект состоит из фронтенда (чат‑интерфейс) и Python‑бэкенда агента, который отдаёт API в стиле **AG‑UI** и умеет вызывать внешние инструменты через **MCP** (1С OData, OpenSearch RAG и др.).

## Состав проекта

- `src/` — фронтенд (React + Vite): чат, стриминг ответа, выбор MCP‑серверов, автокомплит инструментов по `/`.
- `agent/` — бэкенд агента (FastAPI + LangGraph/LangChain): `POST /api/agui` (SSE/JSON) + API для списка MCP‑серверов.
- `mcp_servers/` — отдельные MCP‑серверы:
  - `mcp-1c-hack/` — MCP для 1С через OData (transport: `streamable-http`).
  - `opensearch-service/` — OpenSearch + MCP RAG (по умолчанию transport: `stdio`, запуск в Docker).

## Как это работает

1. UI отправляет сообщение в `agent` на `POST /api/agui` (по умолчанию — SSE‑стрим).
2. `agent` обрабатывает запрос, при необходимости вызывает MCP‑инструменты (по конфигу `agent/agui-agent-example.json`).
3. Ответ стримится обратно в UI.

## Технологии

- Frontend: React 19, TypeScript, Vite, React Router, TanStack Query, Zustand, Tailwind CSS + shadcn/ui.
- Backend: Python 3.12+, FastAPI, Uvicorn, LangGraph/LangChain, MCP client.

## Запуск (локально)

### Предварительные требования

- Node.js 18+ / 20+
- Python 3.12+
- `uv` (используется для установки зависимостей агента)
- Docker (опционально, для `opensearch-service`)

### Быстрый старт (UI + Agent)

```bash
npm i
cp example.env .env
npm run dev
```

- UI: `http://localhost:3000`
- Agent API: `http://localhost:5001` (base: `http://localhost:5001/api`)

Примечание: после `npm i` автоматически запускается `uv sync` в `agent/` (см. `scripts/setup-agent.*`). Если `uv` не установлен или автосетап упал, выполните вручную:

```bash
cd agent
uv sync
```

### Мок‑режим (только UI, без бэкенда)

```bash
npm run dev:mock
```

UI будет использовать `.env.mock` и моки из `src/shared/api/mock`.

## Конфигурация и переменные окружения

### UI (`.env` / `example.env`)

Vite‑переменные (нужен префикс `VITE_`):

- `VITE_API_URL` — base URL для API агента (например, `http://localhost:5001/api`).
- `VITE_AGUI_URL` (опционально) — endpoint AG‑UI. По умолчанию `${VITE_API_URL}/agui`.
- `VITE_API_MOCK` — `true/false`, включает мок‑режим на фронте.

### Agent (`agent/`)

- MCP/LLM конфиг: `agent/agui-agent-example.json`
- `AGENT_DEBUG=true` — печатать traceback при ошибках.

> Рекомендуемо хранить ключи доступа к LLM в переменных окружения и в `agent/agui-agent-example.json` указывать имя переменной (поле `llm.api_key_env`).

### MCP серверы (`mcp_servers/`)

- 1С OData MCP: `mcp_servers/mcp-1c-hack/.env.example`
- OpenSearch RAG: `mcp_servers/opensearch-service/.env.example`

## MCP серверы (опционально)

### 1) 1С OData (`mcp_servers/mcp-1c-hack`)

Поднимает MCP endpoint `http://localhost:8000/mcp` (transport: `streamable-http`).

```bash
cd mcp_servers/mcp-1c-hack
cp .env.example .env
python -m venv .venv
python -m pip install -r requirements.txt
python server.py
```

После запуска агент сможет вызывать инструменты `get_navigation_link`, `query_1c_data`, `list_odata_entities` (если они включены в UI).

### 2) OpenSearch RAG (`mcp_servers/opensearch-service`)

Запускает OpenSearch + контейнер `mcp-server` (MCP transport: `stdio`). Агент подключается через команду из `agent/agui-agent-example.json`:
`docker exec -i mcp-server python /app/mcp_server.py`.

```bash
cd mcp_servers/opensearch-service
cp .env.example .env
docker compose up -d
```

## Архитектура (структура папок)

```
agent/                 # FastAPI агент (AG-UI) + MCP client
mcp_servers/           # отдельные MCP сервера (1С OData, OpenSearch RAG)
public/                # статические файлы фронта
scripts/               # helper-скрипты (установка зависимостей агента)
src/                   # фронтенд (FSD: app/pages/widgets/features/entities/shared)
```

## Скрипты (npm)

- `npm run dev` — UI + Agent (concurrently)
- `npm run dev:ui` — только UI
- `npm run dev:agent` — только Agent (порт `5001`)
- `npm run dev:mock` — UI в мок‑режиме
- `npm run build` / `npm run preview` — сборка/предпросмотр UI
- `npm run lint` — prettier + eslint + type-check
