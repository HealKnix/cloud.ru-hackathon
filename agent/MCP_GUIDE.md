# MCP: OpenSearch RAG Server

FastMCP сервер, который через OpenSearch умеет:

- `upload_document` — загрузить текст, нарезать на чанки, получить эмбеддинги Yandex и проиндексировать в OpenSearch.
- `ask_question` — сделать RAG: поиск + генерация ответа через Yandex GPT.
- `search_documents` — поиск без генерации (BM25 + vector rerank).

## Требования

- OpenSearch 2.11.x (без security/TLS по умолчанию) с включённым kNN.
- Доступ к Yandex API: `YANDEX_API_KEY`, `YANDEX_FOLDER_ID`.
- Python 3.10+ (если запуск без Docker).

## Запуск

### В Docker (рекомендуется)

```bash
cd /Users/admin/cloud/opensearch-service
cp env.example .env   # заполнить YANDEX_API_KEY / YANDEX_FOLDER_ID
docker compose up -d --build
```

- OpenSearch: `http://localhost:9200`
- Dashboards: `http://localhost:5601`
- MCP: stdio внутри контейнера `mcp-server`

### Локально (без Docker)

```bash
cd F:/Projects/opensearch-service/opensearch-service
pip install -r requirements.txt
python mcp_server.py
```

Переменные окружения можно задать через `.env` (см. `env.example`).

## Подключение в MCP-клиентах

### Cursor / Claude Desktop (stdio через docker exec)

```json
{
  "opensearch-rag": {
    "transport": "stdio",
    "command": "docker",
    "args": ["exec", "-i", "mcp-server", "python", "/app/mcp_server.py"]
  }
}
```

### Локальный запуск (без docker exec)

```json
{
  "opensearch-rag": {
    "transport": "stdio",
    "command": "python",
    "args": ["F:/Projects/opensearch-service/opensearch-service/mcp_server.py"],
    "env": {
      "OPENSEARCH_HOST": "localhost",
      "OPENSEARCH_PORT": "9200",
      "OPENSEARCH_INDEX": "makar_cloud_semantic",
      "YANDEX_API_KEY": "<your_key>",
      "YANDEX_FOLDER_ID": "<your_folder>",
      "YANDEX_EMBEDDING_MODEL": "text-search-doc",
      "YANDEX_EMBEDDINGS_URL": "https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding"
    }
  }
}
```

## Как пользоваться

1. Убедитесь, что индекс создан автоматически при первом вызове (`makar_cloud_semantic`). В маппинге kNN используется `space_type: l2`; если нужен косинус, нормализуйте вектора перед записью.
2. `upload_document` — передайте текст (или файл) и `source_name`; опционально `index_name`.
3. `ask_question` — задайте вопрос, опционально `index_name`.
4. `search_documents` — задайте запрос, опционально `index_name`.
5. Сброс индекса: `curl -X DELETE http://localhost:9200/makar_cloud_semantic`.

## Отладка

- Логи Docker: `docker compose logs -f mcp`.
- Проверка MCP без клиента: `PYTHONPATH=. python test_mcp.py`.
- Проверка OpenSearch: `curl http://localhost:9200/_cluster/health`.
