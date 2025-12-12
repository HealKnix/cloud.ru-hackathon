"""Natural-language query tool: build OData plan with LLM and execute it."""

from __future__ import annotations

import asyncio
import os
import re
from typing import Any, Dict, List

import httpx
from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from manager import OneCManager
from mcp_instance import mcp
from query_tool import (
    Candidate,
    CloudLLMClient,
    LLMClientError,
    ODataClient,
    ODataClientError,
    PlanParseError,
    QueryPlan,
    choose_candidates,
)
from tools.list_entities import _metadata_url, _parse_entity_sets, list_odata_entities
from tools.navigation import _build_data_link
from tools.utils import ToolResult, format_api_error

tracer = trace.get_tracer(__name__)
_manager = OneCManager()

_ENTITY_PATTERN = re.compile(
    r"\\b(?P<prefix>Catalog|Document|InformationRegister|AccumulationRegister|ChartOfAccounts)_(?P<name>\\w+)\\b",
    re.IGNORECASE,
)


def _extract_explicit_entity(text: str) -> str | None:
    match = _ENTITY_PATTERN.search(text or "")
    if not match:
        return None
    return f"{match.group('prefix')}_{match.group('name')}"


def _extract_top_hint(text: str, default: int = 5) -> int:
    numbers = [int(n) for n in re.findall(r"\\b(\\d{1,3})\\b", text or "") if int(n) <= 100]
    return min(numbers) if numbers else default


@mcp.tool(
    name="query_1c_data",
    description=(
        "Принимает запрос на естественном языке, строит OData план через Cloud.ru LLM и выполняет запрос к 1С OData."
    ),
)
async def query_1c_data(
    user_query: str = Field(..., description="Запрос пользователя на естественном языке."),
    connection_string: str = Field(
        default="",
        description="IBConnectionString для выгрузки метаданных (если пусто — ONEC_CONNECTION_STRING).",
    ),
    username: str = Field(
        default="",
        description="Пользователь OData/1С (если пусто — ODATA_1C_USER).",
    ),
    password: str = Field(
        default="",
        description="Пароль OData/1С (если пусто — ODATA_1C_PASSWORD).",
    ),
    ctx: Context = None,
) -> ToolResult:
    """
    Build an OData query plan with LLM and execute it.

    Args:
        user_query: Natural-language query.
        connection_string: Optional 1C connection string used to build metadata index.
        username: Optional OData username.
        password: Optional OData password.
        ctx: MCP context for logging/progress.

    Returns:
        ToolResult with summary text and structured fields:
        `plan`, `plan_raw`, `odata_url`, `odata_params`, `odata_response`, `navigation_links`.

    Raises:
        McpError: For configuration, LLM, or OData failures.
    """

    with tracer.start_as_current_span("query_1c_data") as span:
        span.set_attribute("user_query", user_query)

        odata_url = (os.getenv("ODATA_1C_URL") or "").strip()
        api_key = (os.getenv("API_KEY") or "").strip()
        model_id = (os.getenv("CLOUD_MODEL_ID") or "").strip()
        cloud_base_url = (os.getenv("CLOUD_API_URL") or "").strip() or None

        default_user = (os.getenv("ODATA_1C_USER") or "").strip()
        default_password = (os.getenv("ODATA_1C_PASSWORD") or "").strip()
        odata_user = (username or "").strip() or default_user
        odata_pwd = (password or "").strip() or default_password

        designer_user = (os.getenv("ONEC_USERNAME") or "").strip()
        designer_password = (os.getenv("ONEC_PASSWORD") or "").strip()
        conn = (connection_string or "").strip() or (os.getenv("ONEC_CONNECTION_STRING") or "").strip()

        def _float_env(name: str, default: float) -> float:
            try:
                return float(os.getenv(name, default))
            except (TypeError, ValueError):
                return float(default)

        llm_timeout = _float_env("LLM_TIMEOUT", 30)
        odata_timeout = _float_env("ODATA_TIMEOUT", 20)

        if not odata_url:
            raise McpError(ErrorData(code=-32602, message="Не задан ODATA_1C_URL"))
        if not api_key or not model_id:
            raise McpError(ErrorData(code=-32602, message="Не заданы API_KEY и/или CLOUD_MODEL_ID"))

        explicit_entity = _extract_explicit_entity(user_query)

        if ctx:
            await ctx.info("Готовим кандидатов сущностей")
            await ctx.report_progress(progress=0, total=100)

        index: List[Dict[str, Any]] = []
        if conn:
            try:
                index = await asyncio.to_thread(_manager.get_index, conn, designer_user, designer_password, False)
            except FileNotFoundError as exc:
                if ctx:
                    await ctx.warning(f"1C не найден (ONEC_BIN_PATH): {exc}. Продолжаем через OData $metadata.")
            except Exception as exc:  # noqa: BLE001
                if ctx:
                    await ctx.warning(f"Не удалось построить индекс 1С: {exc}. Продолжаем через OData $metadata.")

        candidates = choose_candidates(index, user_query, limit=10) if index else []
        if explicit_entity and not any(c.entity.lower() == explicit_entity.lower() for c in candidates):
            type_part, obj_part = explicit_entity.split("_", 1) if "_" in explicit_entity else ("", explicit_entity)
            candidates.insert(
                0,
                Candidate(entity=explicit_entity, name=obj_part, synonym=obj_part, type=type_part, score=100),
            )

        if not candidates:
            if ctx:
                await ctx.info("Кандидаты из индекса не найдены — пробуем OData $metadata")

            try:
                meta_res = await list_odata_entities(username=odata_user, password=odata_pwd, ctx=ctx)
                entity_sets = meta_res.structured_content.get("odata_entities") if meta_res.structured_content else []
            except Exception:
                entity_sets = []

            if not entity_sets:
                meta_url = _metadata_url(odata_url)
                try:
                    async with httpx.AsyncClient(
                        timeout=odata_timeout,
                        auth=(odata_user, odata_pwd) if odata_user or odata_pwd else None,
                    ) as client:
                        response = await client.get(meta_url, headers={"Accept": "application/xml"})
                except Exception as exc:  # noqa: BLE001
                    raise McpError(ErrorData(code=-32603, message=f"Ошибка запроса $metadata: {exc}")) from exc

                if response.status_code >= 400:
                    raise McpError(ErrorData(code=-32603, message=format_api_error(response.text, response.status_code)))

                entity_sets = _parse_entity_sets(response.text)

            candidates = [
                Candidate(
                    entity=name,
                    name=name.split("_", 1)[1] if "_" in name else name,
                    synonym=name.split("_", 1)[1] if "_" in name else name,
                    type=name.split("_", 1)[0] if "_" in name else "",
                    score=0,
                )
                for name in entity_sets[:50]
            ]

            if explicit_entity and not any(c.entity.lower() == explicit_entity.lower() for c in candidates):
                type_part, obj_part = explicit_entity.split("_", 1) if "_" in explicit_entity else ("", explicit_entity)
                candidates.insert(
                    0,
                    Candidate(entity=explicit_entity, name=obj_part, synonym=obj_part, type=type_part, score=100),
                )

        if ctx:
            await ctx.report_progress(progress=30, total=100)
            await ctx.info("Строим OData план через LLM")

        llm_client = CloudLLMClient(
            api_key=api_key,
            model_id=model_id,
            base_url=cloud_base_url,
            timeout=llm_timeout,
            auth_scheme="Bearer",
            extra_headers=None,
        )

        raw_llm = ""
        llm_ms: int | None = None
        if explicit_entity:
            plan = QueryPlan(entity=explicit_entity, params={"$top": _extract_top_hint(user_query, default=5)})
        else:
            try:
                plan, llm_ms, raw_llm = await llm_client.generate_plan(user_query, candidates)
            except (LLMClientError, PlanParseError) as exc:
                raise McpError(ErrorData(code=-32603, message=f"Ошибка LLM: {exc}")) from exc

        if not plan.entity:
            raise McpError(ErrorData(code=-32603, message="LLM не смог определить сущность OData"))

        if "$top" not in plan.params:
            plan.params["$top"] = _extract_top_hint(user_query, default=5)

        if ctx:
            await ctx.report_progress(progress=60, total=100)
            await ctx.info("Выполняем OData запрос")

        odata_client = ODataClient(base_url=odata_url, username=odata_user, password=odata_pwd, timeout=odata_timeout)
        try:
            odata_result = await odata_client.fetch(plan.entity, plan.params)
        except ODataClientError as exc:
            detail = getattr(exc, "response", None)
            msg = str(exc)
            if detail is not None:
                msg = f"{msg}. Response: {detail}"
            raise McpError(ErrorData(code=-32603, message=msg)) from exc

        payload = odata_result["payload"]
        count = None
        preview_fields: List[str] = []
        nav_links: List[str] = []

        if isinstance(payload, dict):
            values = payload.get("value")
            if isinstance(values, list):
                count = len(values)
                if values:
                    preview_fields = list(values[0].keys())[:5]
                    for item in values:
                        ref_val = item.get("Ref_Key") or item.get("Ref")
                        link = _build_data_link(plan.entity, ref_val)
                        if link:
                            nav_links.append(link)
                        if len(nav_links) >= 5:
                            break

        lines = [
            f"Запрос: {user_query}",
            f"Сущность: {plan.entity}",
            f"Количество строк: {count if count is not None else 'n/a'}",
        ]
        if preview_fields:
            lines.append("Поля (пример): " + ", ".join(preview_fields))
        if nav_links:
            lines.append("Навигационные ссылки:\n" + "\n".join(f"- {link}" for link in nav_links))

        meta = {
            "status": "ok",
            "llm_ms": llm_ms,
            "odata_ms": odata_result.get("elapsed_ms"),
            "status_code": odata_result.get("status_code"),
        }

        if ctx:
            await ctx.report_progress(progress=100, total=100)
            await ctx.info("Готово")

        return ToolResult(
            content=[TextContent(type="text", text="\n".join(lines))],
            structured_content={
                "plan": plan.model_dump(),
                "plan_raw": raw_llm,
                "odata_url": odata_result["url"],
                "odata_params": odata_result.get("params"),
                "odata_response": payload,
                "navigation_links": nav_links,
            },
            meta=meta,
        )

