from __future__ import annotations

import os
from typing import Any, NoReturn

from fastmcp import Context
from mcp.shared.exceptions import McpError
from mcp.types import CallToolResult, ErrorData, TextContent

ToolResult = CallToolResult


def tool_result_text(
    text: str,
    *,
    structured_content: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> ToolResult:
    return ToolResult(
        content=[TextContent(type="text", text=text)],
        structuredContent=structured_content,
        meta=meta,
    )


def mcp_invalid_params(message: str) -> NoReturn:
    raise McpError(ErrorData(code=-32602, message=message))


def mcp_internal_error(message: str) -> NoReturn:
    raise McpError(ErrorData(code=-32603, message=message))


def require_env_vars(names: list[str]) -> dict[str, str]:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        mcp_invalid_params(
            "Отсутствуют обязательные переменные окружения: " + ", ".join(missing),
        )
    return {name: os.getenv(name, "") for name in names}


def require_any_env_var(names: list[str]) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    mcp_invalid_params(
        "Отсутствует обязательная переменная окружения (одна из): " + ", ".join(names),
    )


async def ctx_progress(ctx: Context | None, progress: int, total: int = 100) -> None:
    if ctx is None:
        return
    await ctx.report_progress(progress=progress, total=total)


async def ctx_info(ctx: Context | None, message: str) -> None:
    if ctx is None:
        return
    await ctx.info(message)


async def ctx_warning(ctx: Context | None, message: str) -> None:
    if ctx is None:
        return
    await ctx.warning(message)


async def ctx_error(ctx: Context | None, message: str) -> None:
    if ctx is None:
        return
    await ctx.error(message)
