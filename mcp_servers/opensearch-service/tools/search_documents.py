"""MCP tool: search_documents."""

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
    name="search_documents",
    description=(
        "Выполнить поиск по проиндексированным документам без генерации ответа. "
        "Возвращает список релевантных документов."
    ),
)
async def search_documents(
    query: str = Field(..., description="Поисковый запрос."),
    index_name: str | None = Field(default=None, description="Индекс OpenSearch для поиска (опционально)."),
    max_results: int = Field(default=10, ge=1, le=50, description="Максимальное количество результатов (1-50)."),
    use_hyde: bool = Field(default=False, description="Включить HyDE для улучшения поиска."),
    use_colbert: bool = Field(default=True, description="Включить ColBERT реранкинг."),
    ctx: Context | None = None,
) -> ToolResult:
    with tracer.start_as_current_span("search_documents") as span:
        span.set_attribute("query_length", len(query))
        span.set_attribute("index_name", index_name or "")
        span.set_attribute("max_results", max_results)
        span.set_attribute("use_hyde", use_hyde)
        span.set_attribute("use_colbert", use_colbert)

        await ctx_info(ctx, "🚀 Начинаем поиск документов")
        await ctx_progress(ctx, 0)

        try:
            require_any_env_var(["CLOUDRU_API_KEY", "API_KEY"])

            _, search_service, _ = get_services()
            await ctx_info(ctx, "🔎 Выполняем поиск")
            await ctx_progress(ctx, 50)

            documents = await search_service.search_documents(
                query=query,
                size=max_results,
                semantic_weight=0.7,
                keyword_weight=0.3,
                use_hyde=use_hyde,
                use_colbert=use_colbert,
                index_name=index_name,
            )

            await ctx_progress(ctx, 100)
            await ctx_info(ctx, "✅ Поиск завершён")

            span.set_attribute("results_count", len(documents))

            lines: list[str] = [f"Найдено документов: {len(documents)}", ""]
            for i, doc in enumerate(documents[: max_results], 1):
                source = doc.get("source", "unknown")
                chunk_id = doc.get("chunk_id", "")
                score = doc.get("_score", 0) or 0
                text = (doc.get("text") or "").strip()
                snippet = (text[:400] + "...") if len(text) > 400 else text
                lines.append(f"{i}. [{source}::{chunk_id}] (score: {score:.2f})")
                lines.append(snippet)
                lines.append("")

            return tool_result_text(
                "\n".join(lines).strip(),
                structured_content={"documents": documents, "total": len(documents)},
                meta={"tool": "search_documents"},
            )
        except McpError:
            raise
        except Exception as e:
            await ctx_error(ctx, f"❌ Ошибка поиска: {e}")
            mcp_internal_error(f"Не удалось выполнить поиск: {e}")
