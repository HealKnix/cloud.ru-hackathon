import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, StreamingResponse

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from .simple import graph as agent_graph


ROOT_DIR = Path(__file__).resolve().parent
AGENT_CONFIG_PATH = ROOT_DIR / "agui-agent-example.json"
MCP_STATE_PATH = ROOT_DIR / ".mcp_state.json"
DEBUG = os.getenv("AGENT_DEBUG", "").lower() in {"1", "true", "yes", "on"}

try:
    import openai  # type: ignore
except Exception:  # pragma: no cover
    openai = None


def load_agent_config() -> Dict[str, Any]:
    if not AGENT_CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config file: {AGENT_CONFIG_PATH}")
    return json.loads(AGENT_CONFIG_PATH.read_text(encoding="utf-8"))


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


def save_mcp_state(state: Dict[str, bool]) -> None:
    MCP_STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def to_lc_messages(messages: List["AguiMessage"]) -> List[BaseMessage]:
    lc: List[BaseMessage] = []
    for msg in messages:
        if msg.role == "system":
            lc.append(SystemMessage(content=msg.content))
        elif msg.role == "assistant":
            lc.append(AIMessage(content=msg.content))
        else:
            lc.append(HumanMessage(content=msg.content))
    return lc


def chunk_text(text: str, *, max_chunk_len: int = 24) -> List[str]:
    if not text:
        return []
    words = text.split(" ")
    chunks: List[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip() if current else word
        if len(candidate) > max_chunk_len and current:
            chunks.append(current + " ")
            current = word
        else:
            current = candidate
    if current:
        chunks.append(current + " ")
    return chunks


class AguiMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class AguiRequest(BaseModel):
    messages: List[AguiMessage] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


app = FastAPI(title="AG-UI Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/chat/prompts")
def chat_prompts():
    return []


@app.get("/api/chat/history")
def chat_history():
    return []


@app.get("/api/mcp/servers")
def mcp_servers():
    config = load_agent_config()
    mcp_config = config.get("mcp", {})
    if not isinstance(mcp_config, dict):
        return []

    enabled_map = load_mcp_state()
    servers = []
    for server_id, server_cfg in mcp_config.items():
        if not isinstance(server_cfg, dict):
            continue

        transport = str(server_cfg.get("transport", "unknown"))
        endpoint_or_cmd = server_cfg.get("endpoint") or server_cfg.get("command") or ""
        tools = []
        for tool_name in server_cfg.get("tools", []) or []:
            tools.append(
                {
                    "id": f"{server_id}:{tool_name}",
                    "name": str(tool_name),
                    "description": "",
                    "command": str(endpoint_or_cmd),
                }
            )

        servers.append(
            {
                "id": str(server_id),
                "name": str(server_id),
                "description": f"MCP server ({transport})",
                "enabled": bool(enabled_map.get(str(server_id), True)),
                "tools": tools,
            }
        )

    return servers


class McpStateRequest(BaseModel):
    enabled: bool


@app.post("/api/mcp/servers/{server_id}/state")
def set_mcp_server_state(server_id: str, payload: McpStateRequest):
    state = load_mcp_state()
    state[str(server_id)] = bool(payload.enabled)
    save_mcp_state(state)
    return {"id": server_id, "enabled": payload.enabled}


async def run_agent(request: AguiRequest) -> str:
    if not request.messages:
        return ""
    lc_messages = to_lc_messages(request.messages)
    result = await agent_graph.ainvoke({"messages": lc_messages, "proverbs": [], "tools": []})
    result_messages = result.get("messages", [])
    if not result_messages:
        return ""
    last = result_messages[-1]
    content = getattr(last, "content", "")
    if isinstance(content, str):
        return content
    return str(content)


def agui_stream_response(text: str) -> StreamingResponse:
    async def event_stream():
        for chunk in chunk_text(text):
            yield f"data: {json.dumps({'delta': chunk}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def format_agent_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__

    status_code = getattr(exc, "status_code", None)
    if status_code == 402 or "not enough money" in message.lower():
        return "LLM провайдер вернул ошибку оплаты/лимитов (Not enough money). Проверь ключ/баланс/лимиты модели."

    if openai is not None and isinstance(exc, getattr(openai, "APIStatusError", ())):
        return message

    return message


def wants_stream_mode(req: Request, stream: Optional[bool]) -> bool:
    if stream is False:
        return False
    if stream is True:
        return True

    accept = (req.headers.get("accept") or "").lower()
    if not accept or "*/*" in accept:
        return True
    if "text/event-stream" in accept:
        return True
    if "application/json" in accept:
        return False
    return True


@app.post("/api/agent")
async def agui_agent(request: AguiRequest, http_request: Request, stream: Optional[bool] = None):
    stream_mode = wants_stream_mode(http_request, stream)
    try:
        text = await run_agent(request)
        if stream_mode:
            return agui_stream_response(text)
        return JSONResponse(status_code=200, content={"message": text})
    except HTTPException:
        raise
    except Exception as exc:
        if DEBUG:
            import traceback

            traceback.print_exc()
        message = format_agent_error(exc)
        if stream_mode:
            return agui_stream_response(f"Ошибка: {message}")
        return JSONResponse(status_code=200, content={"message": message, "error": True})


@app.post("/api/agui")
async def agui_alias(request: AguiRequest, http_request: Request, stream: Optional[bool] = None):
    return await agui_agent(request, http_request, stream=stream)
