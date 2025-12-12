"""List OData entity sets via $metadata."""

from __future__ import annotations

import os
from typing import List
from xml.etree import ElementTree as ET

import httpx
from fastmcp import Context
from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from tools.utils import ToolResult, format_api_error

tracer = trace.get_tracer(__name__)


def _metadata_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if not base.lower().endswith("$metadata"):
        base = f"{base}/$metadata"
    return base


def _parse_entity_sets(xml_text: str) -> List[str]:
    names: List[str] = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return names
    for es in root.findall(".//{*}EntitySet"):
        name = es.get("Name")
        if name:
            names.append(name)
    return names


@mcp.tool(
    name="list_odata_entities",
    description="Возвращает список сущностей из OData ($metadata).",
)
async def list_odata_entities(
    username: str = Field(default="", description="Пользователь OData/1С (если пусто — ODATA_1C_USER)."),
    password: str = Field(default="", description="Пароль OData/1С (если пусто — ODATA_1C_PASSWORD)."),
    ctx: Context = None,
) -> ToolResult:
    """
    Load `$metadata` from 1C OData endpoint and extract entity sets.

    Args:
        username: Optional OData username.
        password: Optional OData password.
        ctx: MCP context for logging.

    Returns:
        ToolResult with `structured_content.odata_entities`.

    Raises:
        McpError: For configuration/network/HTTP errors.
    """

    with tracer.start_as_current_span("list_odata_entities") as span:
        odata_url = (os.getenv("ODATA_1C_URL") or "").strip()
        default_user = (os.getenv("ODATA_1C_USER") or "").strip()
        default_password = (os.getenv("ODATA_1C_PASSWORD") or "").strip()

        def _float_env(name: str, default: float) -> float:
            try:
                return float(os.getenv(name, default))
            except (TypeError, ValueError):
                return float(default)

        odata_timeout = _float_env("ODATA_TIMEOUT", 20)
        user = (username or "").strip() or default_user
        pwd = (password or "").strip() or default_password

        if not odata_url:
            raise McpError(ErrorData(code=-32602, message="Не задан ODATA_1C_URL"))

        meta_url = _metadata_url(odata_url)
        span.set_attribute("metadata_url", meta_url)

        if ctx:
            await ctx.info("Запрашиваем OData $metadata")
            await ctx.report_progress(progress=0, total=100)

        try:
            async with httpx.AsyncClient(timeout=odata_timeout, auth=(user, pwd) if user or pwd else None) as client:
                response = await client.get(meta_url, headers={"Accept": "application/xml"})
        except Exception as exc:  # noqa: BLE001
            raise McpError(ErrorData(code=-32603, message=f"Ошибка сети при обращении к OData: {exc}")) from exc

        if response.status_code >= 400:
            raise McpError(ErrorData(code=-32603, message=format_api_error(response.text, response.status_code)))

        entity_sets = _parse_entity_sets(response.text)
        if not entity_sets:
            raise McpError(ErrorData(code=-32603, message="Не удалось распарсить список сущностей из $metadata"))

        if ctx:
            await ctx.report_progress(progress=100, total=100)
            await ctx.info(f"Найдено сущностей: {len(entity_sets)}")

        return ToolResult(
            content=[TextContent(type="text", text=f"Сущностей в OData: {len(entity_sets)}")],
            structured_content={"odata_entities": entity_sets, "metadata_url": meta_url},
            meta={"status": "ok"},
        )

