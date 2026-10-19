"""Access policy for the remote Stella endpoint (fastmcp middleware).

Two gates, both tiny on purpose so they can be unit-tested in memory:

- LoginAllowlist: the OAuth proxy (GitHubProvider) authenticates the caller; this
  middleware authorises them by GitHub ``login`` claim. Anything not on the list is
  refused on every MCP request, including initialize.
- ToolDenylist: optional. Hides and blocks named tools. Ships empty; set
  STELLA_HTTP_DENY_TOOLS=name1,name2 to block specific tools without a code change.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from fastmcp.exceptions import MCPError, ToolError
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext


# JSON-RPC server-error range; -32003 is the conventional 'forbidden' slot.
FORBIDDEN = -32003


class LoginAllowlist(Middleware):
    """Refuse every request whose access token is missing or whose ``login`` claim
    is not in ``allowed``."""

    def __init__(self, allowed: Iterable[str], token_getter: Callable[[], Any] = get_access_token):
        self.allowed = {a.strip() for a in allowed if a and a.strip()}
        if not self.allowed:
            raise ValueError("LoginAllowlist needs at least one allowed login; refusing to start open")
        self._get_token = token_getter

    def _login(self) -> str | None:
        token = self._get_token()
        claims = getattr(token, "claims", None) or {}
        return claims.get("login")

    # The HTTP/OAuth layer has already authenticated the caller by the time any MCP
    # request arrives. Let the protocol handshake through so a refused caller gets a
    # readable error on their first real request instead of an opaque handshake failure.
    HANDSHAKE_METHODS = frozenset({"server/discover", "initialize", "ping"})

    async def on_request(self, context: MiddlewareContext, call_next):
        if context.method in self.HANDSHAKE_METHODS:
            return await call_next(context)
        login = self._login()
        if login not in self.allowed:
            raise MCPError(FORBIDDEN, f"forbidden: GitHub login {login!r} is not allowed on this endpoint")
        return await call_next(context)


class ToolDenylist(Middleware):
    """Hide denied tools from list_tools and refuse call_tool for them."""

    def __init__(self, denied: Iterable[str]):
        self.denied = {d.strip() for d in denied if d and d.strip()}

    @staticmethod
    def from_env_value(value: str | None) -> set[str]:
        if not value:
            return set()
        return {part.strip() for part in value.split(",") if part.strip()}

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools = await call_next(context)
        if not self.denied:
            return tools
        return [t for t in tools if t.name not in self.denied]

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        name = getattr(context.message, "name", None)
        if name in self.denied:
            raise ToolError(f"tool {name!r} is disabled on the remote endpoint")
        return await call_next(context)
