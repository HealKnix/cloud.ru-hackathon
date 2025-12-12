"""Universal 1C MCP server (navigation + OData queries)."""

from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv

from mcp_instance import mcp

load_dotenv(find_dotenv())

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Register tools
from tools.navigation import get_navigation_link  # noqa: E402,F401
from tools.query_data import query_1c_data  # noqa: E402,F401
from tools.list_entities import list_odata_entities  # noqa: E402,F401


@mcp.prompt()
def navigation_prompt(query: str = "", connection_string: str = "") -> str:
    """Prompt template for navigation helper."""

    return f"Найди объект 1С по запросу '{query}'. Строка подключения: {connection_string}"


def main() -> None:
    """Run MCP server with streamable-http transport."""

    print("=" * 60)
    print("MCP Server: Universal 1C (OData)")
    print("=" * 60)
    print(f"MCP Endpoint: http://{HOST}:{PORT}/mcp")
    print("=" * 60)

    mcp.run(
        transport="streamable-http",
        host=HOST,
        port=PORT,
        stateless_http=True,
    )


if __name__ == "__main__":
    main()

