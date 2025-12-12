"""MCP tool: ask_question."""

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
    name="ask_question",
    description=(
        "Задать вопрос и получить ответ на основе проиндексированных документов. "
        "Использует RAG (Retrieval-Augmented Generation) для поиска релевантной "
        "информации и генерации ответа."
    ),
)
async def ask_question(
    question: str = Field(..., description="Вопрос пользователя."),
    index_name: str | None = Field(default=None, description="Индекс OpenSearch для поиска (опционально)."),
    max_results: int = Field(default=5, ge=1, le=20, description="Сколько фрагментов использовать для контекста (1-20)."),
    use_hyde: bool = Field(default=False, description="Включить HyDE для улучшения поиска."),
    use_colbert: bool = Field(default=True, description="Включить ColBERT реранкинг."),
    ctx: Context | None = None,
) -> ToolResult:
    with tracer.start_as_current_span("ask_question") as span:
        span.set_attribute("question_length", len(question))
        span.set_attribute("index_name", index_name or "")
        span.set_attribute("max_results", max_results)
        span.set_attribute("use_hyde", use_hyde)
        span.set_attribute("use_colbert", use_colbert)

        await ctx_info(ctx, "🚀 Начинаем RAG-запрос")
        await ctx_progress(ctx, 0)

        try:
            require_any_env_var(["CLOUDRU_API_KEY", "API_KEY"])

            await ctx_info(ctx, "🔎 Ищем релевантные фрагменты")
            await ctx_progress(ctx, 25)

            _, search_service, _ = get_services()
            result = await search_service.search_and_answer(
                query=question,
                size=max_results,
                semantic_weight=0.7,
                keyword_weight=0.3,
                use_hyde=use_hyde,
                use_colbert=use_colbert,
                index_name=index_name,
            )

            await ctx_progress(ctx, 100)
            await ctx_info(ctx, "✅ Ответ сформирован")

            documents = result.get("documents") or []
            total_documents = int(result.get("total_documents", len(documents)) or 0)
            answer = (result.get("answer") or "").strip()

            span.set_attribute("results_count", total_documents)

            lines: list[str] = [f"Ответ: {answer}", "", f"Найдено документов: {total_documents}", ""]
            if documents:
                lines.append("Релевантные фрагменты:")
                for i, doc in enumerate(documents[:3], 1):
                    source = doc.get("source", "unknown")
                    text = (doc.get("text") or "").strip()
                    snippet = (text[:400] + "...") if len(text) > 400 else text
                    lines.append(f"\n{i}. [{source}]")
                    lines.append(snippet)

            return tool_result_text(
                "\n".join(lines).strip(),
                structured_content={
                    "query": result.get("query", question),
                    "answer": answer,
                    "documents": documents,
                    "total_documents": total_documents,
                },
                meta={"tool": "ask_question"},
            )
        except McpError:
            raise
        except Exception as e:
            await ctx_error(ctx, f"❌ Ошибка RAG: {e}")
            mcp_internal_error(f"Не удалось получить ответ: {e}")
