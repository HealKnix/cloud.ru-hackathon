# ---------------------------------------------------------------------------
# Dockerfile для MCP-сервера opensearch-rag
# ---------------------------------------------------------------------------
FROM python:3.11-slim

WORKDIR /app

# Установить зависимости сначала (кэшируется)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать код
COPY scripts/ ./scripts/
COPY tools/ ./tools/
COPY mcp_instance.py server.py mcp_server.py .
COPY env_options.json mcp_tools.json .

# Для отладки — можно подключить .env через volume/env-file
# По умолчанию читаются переменные окружения контейнера.

# FastMCP работает через stdio; точка входа
CMD ["python", "server.py"]
