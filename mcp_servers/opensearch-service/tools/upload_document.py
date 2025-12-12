"""MCP tool: upload_document."""

from __future__ import annotations

from fastmcp import Context
from opentelemetry import trace
from pydantic import Field
from mcp.shared.exceptions import McpError

from mcp_instance import mcp

from .opensearch_services import get_services
from .utils import (
    ToolResult,
    ctx_error,
    ctx_info,
    ctx_progress,
    mcp_internal_error,
    require_any_env_var,
    tool_result_text,
)

tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="upload_document",
    description=(
        "Загрузить и проиндексировать документ в OpenSearch. "
        "Документ будет разбит на семантические чанки и проиндексирован для поиска."
    ),
)
async def upload_document(
    content: str = Field(..., description="Текст документа для индексации."),
    source_name: str = Field(..., description="Имя источника документа (например, имя файла)."),
    index_name: str | None = Field(default=None, description="Имя индекса OpenSearch (опционально)."),
    ctx: Context | None = None,
) -> ToolResult:
    with tracer.start_as_current_span("upload_document") as span:
        span.set_attribute("source_name", source_name)
        span.set_attribute("index_name", index_name or "")
        span.set_attribute("content_length", len(content))

        await ctx_info(ctx, "🚀 Начинаем индексацию документа")
        await ctx_progress(ctx, 0)

        try:
            require_any_env_var(["CLOUDRU_API_KEY", "API_KEY"])

            _, _, document_indexer = get_services()

            await ctx_info(ctx, "🗂️ Проверяем/создаём индекс")
            await ctx_progress(ctx, 25)
            document_indexer.create_index_if_not_exists(index_name)

            await ctx_info(ctx, "🧩 Создаём чанки и индексируем")
            await ctx_progress(ctx, 50)
            result = await document_indexer.index_document(
                content=content,
                source_name=source_name,
                index_name=index_name,
            )

            await ctx_progress(ctx, 100)
            await ctx_info(ctx, "✅ Документ успешно проиндексирован")

            span.set_attribute("chunks", int(result.get("chunks", 0) or 0))
            span.set_attribute("indexed", int(result.get("indexed", 0) or 0))

            text = (
                "Документ успешно проиндексирован:\n"
                f"- Источник: {result.get('source', source_name)}\n"
                f"- Индекс: {result.get('index', index_name or '')}\n"
                f"- Создано чанков: {result.get('chunks', 0)}\n"
                f"- Проиндексировано: {result.get('indexed', 0)}"
            )
            return tool_result_text(
                text,
                structured_content=result,
                meta={"tool": "upload_document"},
            )
        except McpError:
            raise
        except Exception as e:
            await ctx_error(ctx, f"❌ Ошибка индексации: {e}")
            mcp_internal_error(f"Не удалось проиндексировать документ: {e}")
