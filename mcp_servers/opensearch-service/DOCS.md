# OpenSearch RAG MCP Server

Единый документ: развёртывание, индексация, работа с MCP-сервером.

---

## 1. Быстрый старт через Docker

```bash
cd /Users/admin/cloud/opensearch-service

# Создать .env файл с ключами Cloud.ru (необязательно, только для семантики)
cat > .env << 'EOF'
# Укажите один из ключей (предпочтительно CLOUDRU_API_KEY; поддерживается и API_KEY)
CLOUDRU_API_KEY=<your_key>
# API_KEY=<your_key>

CLOUDRU_BASE_URL=https://foundation-models.api.cloud.ru/v1
CLOUDRU_EMBEDDING_MODEL=BAAI/bge-m3
CLOUDRU_CHAT_MODEL=zai-org/GLM-4.6
EMBEDDING_DIM=1024
EOF

# Запуск OpenSearch + MCP-сервера
docker compose up -d --build

# Проверить, что OpenSearch работает
curl -s http://localhost:9200 | jq .
```

После успешного запуска:

- OpenSearch: `http://localhost:9200`
- OpenSearch Dashboards: `http://localhost:5601`
- MCP-сервер: stdio внутри контейнера `mcp-server`

---

## 2. Индексация `1c_support_knowledge_base.txt`

### Вариант A — через Python-скрипт (локально)

```bash
# Удалить старый индекс
curl -X DELETE "http://localhost:9200/makar_cloud_semantic" || true

# Подготовить папку только с txt
rm -rf /tmp/cloud_idx && mkdir -p /tmp/cloud_idx
cp 1c_support_knowledge_base.txt /tmp/cloud_idx/

# Запустить индексацию
OPENSEARCH_HOST=localhost \
OPENSEARCH_PORT=9200 \
OPENSEARCH_USE_SSL=false \
PYTHONPATH=. python scripts/index_makar_cloud_semantic.py \
  --md-dir /tmp/cloud_idx \
  --index-name makar_cloud_semantic
```

### Вариант B — через MCP-инструмент `upload_document`

Если MCP-сервер уже запущен, можно загрузить документ напрямую:

```python
# Пример вызова через MCP-клиент (или Claude Desktop)
await client.call_tool("upload_document", {
    "content": open("1c_support_knowledge_base.txt").read(),
    "source_name": "1c_support_knowledge_base.txt",
    "index_name": "makar_cloud_semantic",
})
```

### Проверка индекса

```bash
curl "http://localhost:9200/makar_cloud_semantic/_count"
# Ожидаем ~34 чанка
```

---

## 3. MCP-сервер (FastMCP)

Сервер написан на **FastMCP** и работает через **stdio**.

### Локальный запуск (без Docker)

```bash
cd /Users/admin/cloud/opensearch-service
source .env  # или export переменные вручную
python server.py
```

Примечание: `mcp_server.py` оставлен как совместимый wrapper, основной вход — `server.py`.

### Доступные инструменты

| Инструмент         | Описание                                            |
| ------------------ | --------------------------------------------------- |
| `upload_document`  | Загрузить документ: разбивает на чанки, индексирует |
| `ask_question`     | RAG: поиск + генерация ответа через Cloud.ru        |
| `search_documents` | Поиск без генерации — возвращает список фрагментов  |

### Конфигурация для Claude Desktop

Добавьте в `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "opensearch-rag": {
      "command": "docker",
      "args": ["exec", "-i", "mcp-server", "python", "server.py"]
    }
  }
}
```

Либо локально (без Docker):

```json
{
  "mcpServers": {
    "opensearch-rag": {
      "command": "python",
      "args": ["/Users/admin/cloud/opensearch-service/server.py"],
      "env": {
        "OPENSEARCH_HOST": "localhost",
        "OPENSEARCH_PORT": "9200",
        "CLOUDRU_API_KEY": "<your_key>",
        "CLOUDRU_BASE_URL": "https://foundation-models.api.cloud.ru/v1",
        "CLOUDRU_EMBEDDING_MODEL": "BAAI/bge-m3",
        "CLOUDRU_CHAT_MODEL": "zai-org/GLM-4.6",
        "EMBEDDING_DIM": "1024"
      }
    }
  }
}
```

---

## 4. Тестирование MCP

```bash
# Установить зависимости (если ещё не)
pip install -r requirements.txt

# Запустить тест-клиент
PYTHONPATH=. python test_mcp.py
```

---

## 5. Развёртывание OpenSearch (подробно)

### 5.1 Docker (рекомендуется)

Уже включён в `docker-compose.yml`:

```yaml
services:
  opensearch:
    image: opensearchproject/opensearch:2.11.1
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
    ports:
      - '9200:9200'
```

**С включённой безопасностью** (для продакшена):

```yaml
services:
  opensearch:
    image: opensearchproject/opensearch:2.11.1
    environment:
      - discovery.type=single-node
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin123!
    ports:
      - '9200:9200'
```

Тогда в `.env`:

```
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=Admin123!
OPENSEARCH_USE_SSL=true
```

### 5.2 Без Docker (локально на macOS)

```bash
# Установить через Homebrew
brew install opensearch

# Запустить
opensearch

# Проверить
curl -k https://localhost:9200
```

### 5.3 Managed-сервисы

- **Yandex Managed Service for OpenSearch** — идеально для продакшена в Yandex Cloud
- **AWS OpenSearch Service** — аналог в AWS

---

## 6. Структура проекта

```
opensearch-service/
├── server.py                    # FastMCP сервер (точка входа)
├── mcp_instance.py              # Единый экземпляр FastMCP
├── tools/                       # MCP инструменты (1 файл = 1 tool)
├── mcp_server.py                # Совместимый wrapper (deprecated)
├── Dockerfile                   # Образ для MCP-сервера
├── docker-compose.yml           # OpenSearch + Dashboards + MCP
├── requirements.txt             # Python-зависимости
├── .env                         # Секреты (не коммитить!)
├── 1c_support_knowledge_base.txt # Документ для индексации
├── test_mcp.py                  # Тест MCP-клиент
├── scripts/
│   ├── opensearch_config.py     # Конфигурация подключения
│   ├── index_makar_cloud_semantic.py  # Скрипт индексации
│   ├── services/
│   │   ├── search_service.py    # Поиск + RAG
│   │   ├── document_indexer.py  # Семантическое чанкирование
│   │   ├── cloudru_service.py   # Cloud.ru LLM / embeddings
│   │   ├── opensearch_service.py # Клиент OpenSearch
│   │   ├── hyde_service.py      # HyDE
│   │   └── colbert_reranker.py  # ColBERT реранкинг
│   └── api/
│       ├── main.py              # FastAPI (альтернативный REST)
│       └── schemas.py           # Pydantic-схемы
└── DOCS.md                      # Этот файл
```

---

## 7. Переменные окружения

| Переменная                | По умолчанию                                | Описание                          |
| ------------------------- | ------------------------------------------- | --------------------------------- |
| `OPENSEARCH_HOST`         | `localhost`                                 | Хост OpenSearch                   |
| `OPENSEARCH_PORT`         | `9200`                                      | Порт OpenSearch                   |
| `OPENSEARCH_USER`         | (пусто)                                     | Пользователь (если security вкл)  |
| `OPENSEARCH_PASSWORD`     | (пусто)                                     | Пароль                            |
| `OPENSEARCH_USE_SSL`      | `false`                                     | Использовать HTTPS                |
| `OPENSEARCH_INDEX`        | `makar_cloud_semantic`                      | Индекс по умолчанию               |
| `CLOUDRU_API_KEY`         | -                                           | API-ключ Cloud.ru (или `API_KEY`) |
| `CLOUDRU_BASE_URL`        | `https://foundation-models.api.cloud.ru/v1` | Base URL Cloud.ru API             |
| `CLOUDRU_EMBEDDING_MODEL` | `BAAI/bge-m3`                               | Модель embeddings                 |
| `CLOUDRU_CHAT_MODEL`      | `zai-org/GLM-4.6`                           | Модель chat-completions           |
| `EMBEDDING_DIM`           | `1024`                                      | Размерность embeddings            |

---

## 8. FAQ

**Q: Как проверить, что MCP работает?**

```bash
python test_mcp.py
```

**Q: Ошибка «Connection refused» к OpenSearch?**

Убедитесь, что контейнер запущен:

```bash
docker compose ps
docker compose logs opensearch
```

**Q: Можно ли использовать без Cloud.ru API?**

Да, но только BM25-поиск. Семантический поиск и RAG-генерация требуют ключа Cloud.ru.

---

_Последнее обновление: декабрь 2025_
