#!/usr/bin/env python3
"""MCP сервер на FastMCP для загрузки документов и RAG-ответов через OpenSearch."""

from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv

# Загружаем переменные окружения до импорта внутренних модулей/сервисов
load_dotenv(find_dotenv())

from mcp_instance import mcp

# Импорт инструментов (регистрация декораторов @mcp.tool)
import tools.ask_question  # noqa: F401
import tools.search_documents  # noqa: F401
import tools.upload_document  # noqa: F401


def main() -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    if transport in {"streamable-http", "http"}:
        port = int(os.getenv("PORT", "8000"))
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port, stateless_http=True)
        return

    mcp.run()


if __name__ == "__main__":
    main()

