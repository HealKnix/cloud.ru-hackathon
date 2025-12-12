# Агент 1С — веб‑интерфейс

Фронтенд для чата с агентом (LLM/agent backend), с поддержкой подключения MCP‑серверов (инструментов), стриминга ответа и быстрых подсказок/истории.

## Возможности

- Чат с агентом со стримингом ответа (AG‑UI поток).
- Переключение MCP‑серверов и выбор доступных инструментов.
- Автокомплит инструментов по `/` в поле ввода.
- Быстрые промпты и история диалогов (через API или мок‑режим).
- Светлая/тёмная тема, рендер Markdown (GFM + KaTeX).

## Стек

- React 19 + TypeScript
- Vite
- React Router
- TanStack Query (react-query)
- Zustand (локальные сторы)
- Tailwind CSS + shadcn/ui (Radix primitives), Vaul (Drawer)
- Axios (REST) + `fetch` для стриминга
- ESLint + Prettier + Husky + lint-staged

## Быстрый старт

Рекомендуемый менеджер пакетов — `pnpm` (в репозитории есть `pnpm-lock.yaml`).

```bash
pnpm i
cp example.env .env
pnpm dev
```

Dev‑сервер стартует на `http://localhost:3000` (см. `vite.config.ts`).

### Мок‑режим (без бэкенда)

```bash
pnpm dev:mock
```

В этом режиме Vite подхватит `.env.mock`, а запросы истории/подсказок/MCP и стриминг ответа будут обслуживаться моками из `src/shared/api/mock`.

## Переменные окружения (.env)

Проект использует Vite‑переменные — нужен префикс `VITE_`.

- `VITE_API_URL` — базовый URL REST API. Используется для:
  - `GET /chat/prompts` — быстрые промпты
  - `GET /chat/history` — история диалогов
  - `GET /mcp/servers` — список MCP‑серверов
  - `POST /mcp/servers/:id/state` — сохранить состояние сервера
- `VITE_AGUI_URL` (опционально) — endpoint AG‑UI для стриминга ответа. Если не задан, используется `${VITE_API_URL}/agui`.
- `VITE_API_MOCK` — `true/false`, включает моки (см. также `pnpm dev:mock`).

### Как работать с `example.env`

1. Скопируйте `example.env` в `.env`.
2. При необходимости поменяйте `VITE_API_URL` (и/или `VITE_AGUI_URL`).
3. Для локальной разработки без бэкенда используйте `pnpm dev:mock` или установите `VITE_API_MOCK=true`.

> Файл `.env` игнорируется git’ом (см. `.gitignore`).

## Архитектура и структура папок

Структура близка к Feature-Sliced Design (FSD): `app / pages / widgets / features / entities / shared`.

```
public/                # статические файлы (лого и т.п.)
src/
  app/                 # инициализация приложения: роутер, провайдеры
  pages/               # страницы (сейчас: ChatPage)
  widgets/             # крупные UI-блоки (thread/toolbar/history)
  features/            # пользовательские фичи (отправка, MCP, автокомплит)
  entities/            # доменные сущности и сторы (chat, mcp, agent state)
  shared/              # переиспользуемое: api, ui-kit, lib, hooks, components
```

Ключевые места:

- `src/app/router.tsx` — маршрутизация (сейчас один маршрут `/`).
- `src/app/providers/app-providers.tsx` — провайдеры (React Query, тема).
- `src/shared/api/*` — клиенты API и стриминг AG‑UI.
- `src/shared/api/mock/*` — моки для режима `VITE_API_MOCK=true`.

## Скрипты

- `pnpm dev` — локальная разработка
- `pnpm dev:mock` — разработка с мок‑данными
- `pnpm build` — сборка в `dist/`
- `pnpm preview` — предпросмотр сборки
- `pnpm lint` — форматирование + eslint + typecheck
