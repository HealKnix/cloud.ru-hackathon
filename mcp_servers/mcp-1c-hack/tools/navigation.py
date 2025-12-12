"""Navigation helpers: find 1C object and build e1c links."""

from __future__ import annotations

import asyncio
import os
from typing import Dict, Tuple

from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field
from thefuzz import fuzz, process

from manager import OneCManager
from mcp_instance import mcp
from tools.utils import ToolResult

tracer = trace.get_tracer(__name__)

_manager = OneCManager()


def _e1c_base_prefix() -> str:
    return (os.getenv("E1C_NAV_BASE") or "").strip()


def _build_link_suffix(type_name: str, object_name: str) -> str:
    if type_name in {"Catalog", "Document", "InformationRegister", "AccumulationRegister", "ChartOfAccounts"}:
        prefix = "e1cib/list"
    else:
        prefix = "e1cib/app"
    return f"#{prefix}/{type_name}.{object_name}"


def _build_link(type_name: str, object_name: str) -> Tuple[str, str]:
    suffix = _build_link_suffix(type_name, object_name)
    base = _e1c_base_prefix()
    return (f"{base}{suffix}" if base else suffix, suffix)


def _build_data_link(entity: str, ref: str | None) -> str | None:
    """
    Build e1cib/data link for a single 1C object by OData entity + ref key.

    Returns:
        Full e1c://... link (if `E1C_NAV_BASE` is set) or link suffix otherwise.
    """

    if not ref or "_" not in (entity or ""):
        return None

    prefix, name = entity.split("_", 1)
    mapping = {
        "Catalog": "Справочник",
        "Document": "Документ",
        "InformationRegister": "РегистрСведений",
        "AccumulationRegister": "РегистрНакопления",
        "ChartOfAccounts": "ПланСчетов",
    }
    mapped = mapping.get(prefix, prefix)
    suffix = f"#e1cib/data/{mapped}.{name}?ref={ref}"
    base = _e1c_base_prefix()
    return f"{base}{suffix}" if base else suffix


def _format_result(best: Dict[str, str], score: int) -> str:
    link, _ = _build_link(best["type"], best["name"])
    return (
        f"Найден объект: {best['type']}.{best['name']} (score={score})\n"
        f"Синоним: {best.get('synonym') or '-'}\n"
        f"Ссылка: {link}"
    )


@mcp.tool(
    name="get_navigation_link",
    description=(
        "По запросу (имя/синоним) находит объект конфигурации 1С и возвращает e1c ссылку для навигации."
    ),
)
async def get_navigation_link(
    query: str = Field(..., description="Имя/синоним объекта, например: 'Справочник Номенклатура'."),
    connection_string: str = Field(
        default="",
        description="IBConnectionString для выгрузки метаданных (если пусто — ONEC_CONNECTION_STRING).",
    ),
    username: str = Field(
        default="",
        description="Пользователь 1С Designer (если пусто — ONEC_USERNAME).",
    ),
    password: str = Field(
        default="",
        description="Пароль 1С Designer (если пусто — ONEC_PASSWORD).",
    ),
    force_update: bool = Field(default=False, description="Принудительно пересоздать кеш метаданных."),
    ctx: Context = None,
) -> ToolResult:
    """
    Find a 1C configuration object and return a navigation link.

    Args:
        query: Search query (name or synonym).
        connection_string: 1C connection string for metadata dump.
        username: 1C Designer username.
        password: 1C Designer password.
        force_update: Rebuild metadata cache.
        ctx: MCP context for logging/progress.

    Returns:
        ToolResult with `structured_content.match/score/link`.

    Raises:
        McpError: If required configuration is missing or dump fails.
    """

    with tracer.start_as_current_span("get_navigation_link") as span:
        span.set_attribute("query", query)
        span.set_attribute("force_update", force_update)

        conn = (connection_string or "").strip() or (os.getenv("ONEC_CONNECTION_STRING") or "").strip()
        user = (username or "").strip() or (os.getenv("ONEC_USERNAME") or "").strip()
        pwd = (password or "").strip() or (os.getenv("ONEC_PASSWORD") or "").strip()

        if not conn:
            raise McpError(ErrorData(code=-32602, message="Не задана строка подключения: connection_string/ONEC_CONNECTION_STRING"))

        if ctx:
            await ctx.info("Начинаем поиск объекта 1С")
            await ctx.report_progress(progress=0, total=100)

        try:
            index = await asyncio.to_thread(_manager.get_index, conn, user, pwd, force_update)
        except Exception as exc:  # noqa: BLE001
            span.set_attribute("error", str(exc))
            if ctx:
                await ctx.error(f"Ошибка построения индекса: {exc}")
            raise McpError(ErrorData(code=-32603, message=f"Не удалось построить индекс 1С: {exc}")) from exc

        if not index:
            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.warning("Индекс пуст — проверьте подключение и права доступа")
            return ToolResult(
                content=[TextContent(type="text", text="Индекс 1С пуст. Проверьте подключение и права доступа.")],
                structured_content={"match": None, "score": 0, "link": None},
                meta={"status": "ok"},
            )

        if ctx:
            await ctx.report_progress(progress=50, total=100)
            await ctx.info("Выполняем fuzzy-поиск по индексу")

        choices = [(item["search_text"], item) for item in index if item.get("search_text")]
        search_strings = [c[0] for c in choices]
        best_match = process.extractOne(query, search_strings, scorer=fuzz.WRatio)

        if not best_match:
            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.info("Совпадений не найдено")
            return ToolResult(
                content=[TextContent(type="text", text="Совпадений не найдено.")],
                structured_content={"match": None, "score": 0, "link": None},
                meta={"status": "ok"},
            )

        matched_text, score = best_match[0], int(best_match[1])
        matched_item = choices[search_strings.index(matched_text)][1]

        span.set_attribute("match_score", score)
        span.set_attribute("match_type", matched_item.get("type", ""))
        span.set_attribute("match_name", matched_item.get("name", ""))

        link, link_suffix = _build_link(matched_item["type"], matched_item["name"])
        text = _format_result(matched_item, score)

        if ctx:
            await ctx.report_progress(progress=100, total=100)
            await ctx.info("Поиск завершен")

        return ToolResult(
            content=[TextContent(type="text", text=text)],
            structured_content={
                "match": matched_item,
                "score": score,
                "link": link,
                "link_suffix": link_suffix,
            },
            meta={"status": "ok"},
        )

