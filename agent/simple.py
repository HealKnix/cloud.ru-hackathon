import json
import asyncio
import os
from pathlib import Path
from typing import Annotated, Dict, Any, List, Optional
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END, MessagesState
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langgraph.prebuilt import ToolNode

# --- MCP Client Imports ---
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp import ClientSession

ROOT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = ROOT_DIR / "agui-agent-example.json"
MCP_STATE_PATH = ROOT_DIR / ".mcp_state.json"

# --- MCP Tool Wrapper ---

def load_agent_config() -> Dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_mcp_servers(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mcp = config.get("mcp", {})
    if not isinstance(mcp, dict):
        return {}
    if "transport" in mcp and ("endpoint" in mcp or "command" in mcp):
        return {"default": mcp}
    return {str(k): v for k, v in mcp.items() if isinstance(v, dict)}


def load_mcp_state() -> Dict[str, bool]:
    if not MCP_STATE_PATH.exists():
        return {}
    try:
        raw = json.loads(MCP_STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {str(k): bool(v) for k, v in raw.items()}
    except Exception:
        return {}
    return {}


def is_mcp_server_enabled(server_id: str) -> bool:
    state = load_mcp_state()
    return bool(state.get(server_id, True))


def normalize_tool_args_for(tool_name: str, tool_args: Any) -> Dict[str, Any]:
    if isinstance(tool_args, dict):
        if "input" in tool_args and isinstance(tool_args["input"], (str, int, float, bool)):
            normalized = dict(tool_args)
            input_value = normalized.pop("input")

            if tool_name == "ask_question" and "question" not in normalized:
                normalized["question"] = str(input_value)
            elif tool_name == "search_documents" and "query" not in normalized:
                normalized["query"] = str(input_value)
            elif tool_name == "upload_document" and "text" not in normalized:
                normalized["text"] = str(input_value)
                normalized.setdefault("source_name", "chat")
            else:
                normalized["input"] = input_value

            return normalized

        return tool_args
    if tool_args is None:
        return {}

    if tool_name == "get_navigation_link":
        return {"query": tool_args}
    if tool_name == "query_1c_data":
        return {"user_query": tool_args}
    if tool_name == "list_odata_entities":
        return {}
    if tool_name == "ask_question":
        return {"question": str(tool_args)}
    if tool_name == "search_documents":
        return {"query": str(tool_args)}
    if tool_name == "upload_document":
        return {"text": str(tool_args), "source_name": "chat"}

    return {"input": tool_args}


async def call_mcp_tool_streamable_http(
    endpoint: str, tool_name: str, tool_args: Dict[str, Any]
) -> str:
    async with streamablehttp_client(endpoint) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)

            output_text = ""
            if result.content:
                for content in result.content:
                    if content.type == "text":
                        output_text += content.text

            return output_text if output_text else "Tool executed but returned no text."


async def call_mcp_tool_stdio(
    *,
    command: str,
    args: List[str],
    tool_name: str,
    tool_args: Dict[str, Any],
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[str] = None,
) -> str:
    server = StdioServerParameters(command=command, args=args, env=env, cwd=cwd)
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)

            output_text = ""
            if result.content:
                for content in result.content:
                    if content.type == "text":
                        output_text += content.text

            return output_text if output_text else "Tool executed but returned no text."


async def call_mcp_tool(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """
    Calls MCP tool using the transport defined in agui-agent-example.json.
    """
    tool_args = normalize_tool_args_for(tool_name, tool_args)
    try:
        config = load_agent_config()
        servers = load_mcp_servers(config)

        server_id: Optional[str] = None
        server_cfg: Optional[Dict[str, Any]] = None
        for candidate_id, candidate_cfg in servers.items():
            tools = candidate_cfg.get("tools", []) or []
            if tool_name in tools:
                server_id = candidate_id
                server_cfg = candidate_cfg
                break

        if not server_id or not server_cfg:
            return f"Tool '{tool_name}' is not configured in MCP."

        if not is_mcp_server_enabled(server_id):
            return f"MCP server '{server_id}' is disabled."

        transport = str(server_cfg.get("transport", "")).strip().lower()
        print(f"--- MCP CALL: {server_id}.{tool_name} with {tool_args} ---")

        if transport == "streamable-http":
            endpoint = str(server_cfg.get("endpoint", "")).strip()
            if not endpoint:
                return f"MCP server '{server_id}' missing endpoint."
            return await call_mcp_tool_streamable_http(endpoint, tool_name, tool_args)

        if transport == "stdio":
            command = str(server_cfg.get("command", "")).strip()
            args = server_cfg.get("args", []) or []
            if not command:
                return f"MCP server '{server_id}' missing command."
            if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
                return f"MCP server '{server_id}' has invalid args."

            env = server_cfg.get("env")
            if env is not None and not isinstance(env, dict):
                env = None
            cwd = server_cfg.get("cwd")
            cwd = str(cwd) if cwd is not None else None

            return await call_mcp_tool_stdio(
                command=command,
                args=args,
                tool_name=tool_name,
                tool_args=tool_args,
                env=env,
                cwd=cwd,
            )

        return f"Unsupported MCP transport '{transport}' for server '{server_id}'."
    except Exception:
        import traceback
        traceback.print_exc()
        return f"Error calling MCP tool '{tool_name}'."


def sync_wrapper(tool_name: str, args: Dict[str, Any]):
    """Sync wrapper для вызова async функции."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(call_mcp_tool(tool_name, args))
    finally:
        loop.close()


# --- Tool Definitions ---

def build_mcp_tools() -> List[Tool]:
    config = load_agent_config()
    servers = load_mcp_servers(config)

    seen: Dict[str, str] = {}
    tools: List[Tool] = []
    for server_id, server_cfg in servers.items():
        for tool_name in server_cfg.get("tools", []) or []:
            tool_name = str(tool_name)
            if tool_name in seen and seen[tool_name] != server_id:
                raise ValueError(
                    f"Duplicate MCP tool name '{tool_name}' in '{seen[tool_name]}' and '{server_id}'."
                )
            seen[tool_name] = server_id

            def _make_fn(_tool_name: str):
                return lambda x: sync_wrapper(_tool_name, normalize_tool_args_for(_tool_name, x))

            tools.append(
                Tool(
                    name=tool_name,
                    func=_make_fn(tool_name),
                    description=f"[{server_id}] MCP tool '{tool_name}'",
                )
            )
    return tools


mcp_tools = build_mcp_tools()

# --- Agent State ---

class AgentState(MessagesState):
    proverbs: List[str]
    tools: List[Any]

# --- Graph Nodes ---

async def agent_node(state: AgentState):
    """The primary node that calls the LLM."""
    
    config = load_agent_config()
    
    llm_config = config.get("llm", {})
    system_prompt = config.get("system_prompt", "You are a helpful assistant.")

    api_key_field = llm_config.get("api_key_env")
    api_key = os.getenv(api_key_field, api_key_field) if isinstance(api_key_field, str) else None
    extra_headers = llm_config.get("extra_headers") if isinstance(llm_config, dict) else None

    model = ChatOpenAI(
        model=llm_config.get("model"),
        base_url=llm_config.get("base_url"),
        api_key=api_key,
        default_headers=extra_headers if isinstance(extra_headers, dict) else None,
    ).bind_tools([
        *state.get("tools", []),
        *mcp_tools
    ])

    messages = [SystemMessage(content=system_prompt)] + state.get("messages", [])
    response = await model.ainvoke(messages)
    return {"messages": [response]}

# --- Graph Definition ---

tool_node = ToolNode(mcp_tools)

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", tool_node)

graph.set_entry_point("agent")

def should_continue(state: AgentState):
    messages = state.get("messages", [])
    if not messages:
        return END
    last_message = messages[-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return END

graph.add_conditional_edges("agent", should_continue)
graph.add_edge("tools", "agent")

graph = graph.compile()
