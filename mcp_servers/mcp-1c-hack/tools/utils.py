"""Shared utilities for MCP tools."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mcp.shared.exceptions import ErrorData, McpError
from mcp.types import Content, TextContent


@dataclass
class ToolResult:
    """Standard return type for MCP tools."""

    content: List[Content]
    structured_content: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None


def _require_env_vars(names: list[str]) -> Dict[str, str]:
    """
    Validate that required environment variables are present.

    Args:
        names: Environment variable names.

    Returns:
        Mapping of name -> value.

    Raises:
        McpError: If any variables are missing.
    """

    missing = [name for name in names if not (os.getenv(name) or "").strip()]
    if missing:
        raise McpError(
            ErrorData(
                code=-32602,
                message="Отсутствуют обязательные переменные окружения: " + ", ".join(missing),
            )
        )
    return {name: (os.getenv(name) or "").strip() for name in names}


def format_api_error(response_text: str, status_code: int) -> str:
    """
    Format an HTTP API error into a human-readable message.

    Args:
        response_text: Raw response body.
        status_code: HTTP status code.

    Returns:
        Human-readable error message.
    """

    response_text = response_text or ""
    try:
        payload = json.loads(response_text)
        if isinstance(payload, dict):
            code = payload.get("code", "unknown")
            message = payload.get("message") or payload.get("error") or response_text
            return f"HTTP {status_code} (code={code}): {message}"
    except Exception:
        pass
    return f"HTTP {status_code}: {response_text}"


def text_result(text: str, structured: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None) -> ToolResult:
    """Helper to build a simple text ToolResult."""

    return ToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=structured,
        meta=meta,
    )

