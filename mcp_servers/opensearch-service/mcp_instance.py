"""Единый экземпляр FastMCP для всего приложения."""

from fastmcp import FastMCP

mcp = FastMCP(
    name="opensearch-rag",
    instructions=(
        "Сервер для загрузки документов в OpenSearch и получения RAG-ответов. "
        "Используй upload_document для индексации, ask_question - для вопросов, "
        "search_documents - для чистого поиска без генерации ответа."
    ),
)

