"""Authenticated HTTP facade for Stella's stdio MCP server."""

from __future__ import annotations

import asyncio
import hmac
import ipaddress
import json
import os
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Any, Callable, Protocol

from fastapi import Body, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
STELLA_DIR = HERE.parent
DEFAULT_PYTHON = STELLA_DIR / ".venv" / "bin" / "python"
DEFAULT_SERVER = STELLA_DIR / "stella_server.py"

# Keep this list explicit and reviewable. These tools write/delete state, expose
# unrestricted Cypher, or read/write Stella's adaptive chart-memory state.
DENIED_TOOLS = frozenset(
    {
        "graph_cypher",
        "delete_chart",
        "store_chart",
        "reflect",
        "recall",
        "validate",
        "chart_memory_stats",
        "autopoietic_init",
        "autopoietic_submit",
        "autopoietic_converge",
        "autopoietic_status",
    }
)
SNAPSHOT_TOOLS = {
    "moon": "get_current_moon",
    "planets": "get_planet_positions",
    "aspects": "get_planet_aspects",
    "dignities": "get_current_dignities",
}


class Gateway(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def list_tools(self) -> Any: ...
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


class StdioMCPGateway:
    """Own one initialized MCP session and its Stella subprocess."""

    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def start(self) -> None:
        if self._session is not None:
            return
        stack = AsyncExitStack()
        try:
            params = StdioServerParameters(
                command=os.getenv("STELLA_MCP_PYTHON", str(DEFAULT_PYTHON)),
                args=[os.getenv("STELLA_MCP_SERVER", str(DEFAULT_SERVER))],
                env=dict(os.environ),
            )
            read_stream, write_stream = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
        except BaseException:
            await stack.aclose()
            raise
        self._stack = stack
        self._session = session

    async def stop(self) -> None:
        stack, self._stack, self._session = self._stack, None, None
        if stack is not None:
            await stack.aclose()

    def _require_session(self) -> ClientSession:
        if self._session is None:
            raise RuntimeError("MCP gateway is not started")
        return self._session

    async def list_tools(self) -> Any:
        return await self._require_session().list_tools()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return await self._require_session().call_tool(name, arguments=arguments)


def is_loopback_host(host: str) -> bool:
    """Return whether a configured bind host is loopback-only."""
    normalized = host.strip().lower().strip("[]")
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _decode_text(text: str) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return text


def convert_call_result(result: Any) -> dict[str, Any]:
    """Convert MCP CallToolResult/content blocks to stable JSON."""
    is_error = bool(getattr(result, "isError", getattr(result, "is_error", False)))
    structured = getattr(
        result, "structuredContent", getattr(result, "structured_content", None)
    )
    if structured is not None:
        payload = _jsonable(structured)
        # FastMCP wraps scalar/unstructured tool returns in a single
        # ``result`` field.  Remove that transport wrapper so HTTP clients
        # receive the same object the Stella tool returned.
        if isinstance(payload, dict) and set(payload) == {"result"}:
            payload = payload["result"]
        if isinstance(payload, str):
            payload = _decode_text(payload)
    else:
        content = getattr(result, "content", result)
        blocks = content if isinstance(content, (list, tuple)) else [content]
        converted = []
        for block in blocks:
            if hasattr(block, "text"):
                converted.append(_decode_text(block.text))
            else:
                converted.append(_jsonable(block))
        payload = converted[0] if len(converted) == 1 else converted
    return {"isError": is_error, "result": payload}


def _tools_from_response(response: Any) -> list[Any]:
    tools = getattr(response, "tools", response)
    return list(tools or [])


def _tool_name(tool: Any) -> str:
    return tool.get("name", "") if isinstance(tool, dict) else getattr(tool, "name", "")


def _public_tool(tool: Any) -> dict[str, Any]:
    if isinstance(tool, dict):
        raw = tool
    elif hasattr(tool, "model_dump"):
        raw = tool.model_dump(mode="json", by_alias=True, exclude_none=True)
    else:
        raw = {
            "name": getattr(tool, "name", ""),
            "description": getattr(tool, "description", None),
            "inputSchema": getattr(tool, "inputSchema", {}),
        }
    return _jsonable(raw)


def create_app(gateway_factory: Callable[[], Gateway] = StdioMCPGateway) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        token = os.getenv("STELLA_API_TOKEN", "").strip()
        host = os.getenv("STELLA_API_HOST", "127.0.0.1")
        if not is_loopback_host(host) and not token:
            raise RuntimeError(
                "STELLA_API_TOKEN is required when STELLA_API_HOST is not loopback"
            )
        gateway = gateway_factory()
        await gateway.start()
        app.state.gateway = gateway
        app.state.api_token = token or None
        try:
            yield
        finally:
            await gateway.stop()

    app = FastAPI(
        title="Stella API Bridge",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    async def authorize(request: Request) -> None:
        token: str | None = request.app.state.api_token
        if token is None:
            return
        authorization = request.headers.get("Authorization", "")
        scheme, separator, supplied = authorization.partition(" ")
        if not separator or scheme.lower() != "bearer" or not hmac.compare_digest(
            supplied, token
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    async def available_tools(request: Request) -> list[Any]:
        response = await request.app.state.gateway.list_tools()
        return [
            tool
            for tool in _tools_from_response(response)
            if _tool_name(tool) and _tool_name(tool) not in DENIED_TOOLS
        ]

    @app.exception_handler(Exception)
    async def unhandled_error(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": "Stella MCP request failed", "error": str(exc)},
        )

    @app.get("/health")
    async def health(request: Request) -> dict[str, Any]:
        return {
            "status": "ok",
            "mcp": "connected" if hasattr(request.app.state, "gateway") else "disconnected",
        }

    @app.get("/v1/tools", dependencies=[Depends(authorize)])
    async def list_tools(request: Request) -> dict[str, Any]:
        tools = [_public_tool(tool) for tool in await available_tools(request)]
        return {"tools": tools, "count": len(tools)}

    @app.post("/v1/tools/{name}", dependencies=[Depends(authorize)])
    async def call_tool(
        name: str, request: Request, arguments: dict[str, Any] = Body(default={})
    ) -> dict[str, Any]:
        if name in DENIED_TOOLS:
            raise HTTPException(status_code=403, detail="Tool is not exposed by this facade")
        allowed = {_tool_name(tool) for tool in await available_tools(request)}
        if name not in allowed:
            raise HTTPException(status_code=404, detail="Unknown tool")
        converted = convert_call_result(
            await request.app.state.gateway.call_tool(name, arguments)
        )
        return {"tool": name, **converted}

    @app.get("/v1/snapshot", dependencies=[Depends(authorize)])
    async def snapshot(request: Request) -> dict[str, Any]:
        gateway: Gateway = request.app.state.gateway

        async def invoke(tool_name: str) -> dict[str, Any]:
            return convert_call_result(await gateway.call_tool(tool_name, {}))

        outcomes = await asyncio.gather(
            *(invoke(tool_name) for tool_name in SNAPSHOT_TOOLS.values()),
            return_exceptions=True,
        )
        data: dict[str, Any] = {}
        errors: dict[str, str] = {}
        for key, outcome in zip(SNAPSHOT_TOOLS, outcomes):
            if isinstance(outcome, BaseException):
                errors[key] = str(outcome)
            elif outcome["isError"]:
                errors[key] = str(outcome["result"])
            else:
                data[key] = outcome["result"]
        return {"data": data, "errors": errors, "partial": bool(errors)}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=os.getenv("STELLA_API_HOST", "127.0.0.1"),
        port=int(os.getenv("STELLA_API_PORT", "3010")),
        log_level=os.getenv("STELLA_LOG_LEVEL", "info"),
    )
