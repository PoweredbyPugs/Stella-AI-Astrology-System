#!/usr/bin/env python3
"""Remote entrypoint: Stella's tools over Streamable HTTP, behind OAuth.

Architecture
------------
The stdio server (stella_server.py, official MCP SDK, its own venv) stays the single
source of truth. This process is a *proxy* in front of it: it spawns the stdio server
as a persistent child, discovers its tools at runtime (new tools appear automatically
on restart), and serves them over HTTP on loopback. Tailscale Funnel terminates TLS
and forwards the public hostname to this port.

Gates: GitHubProvider (OAuth 2.1 + dynamic client registration, so claude.ai can
connect) authenticates; LoginAllowlist authorises by GitHub login; ToolDenylist is an
optional, empty-by-default escape hatch.

Runs under .venv-http (fastmcp 4.x needs mcp 2.x; Stella's venv pins mcp 1.x).
Configuration comes from stella/.env via scripts/run-stella-http.sh.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from fastmcp.client.transports.stdio import StdioTransport
from fastmcp.server import create_proxy

STELLA_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(STELLA_DIR))

from stella_http_policy import LoginAllowlist, ToolDenylist  # noqa: E402

DEFAULT_PORT = 8811
MCP_PATH = "/mcp"


class ConfigError(SystemExit):
    pass


def load_settings(env: dict[str, str] | None = None) -> dict:
    """Read and validate configuration. Missing auth settings are fatal: this
    endpoint is reachable from the internet and must never start open."""
    env = os.environ if env is None else env
    required = ("STELLA_GH_CLIENT_ID", "STELLA_GH_CLIENT_SECRET",
                "STELLA_PUBLIC_URL", "STELLA_ALLOWED_GH_LOGINS")
    missing = [k for k in required if not env.get(k, "").strip()]
    if missing:
        raise ConfigError(f"stella_http: refusing to start, missing {', '.join(missing)} in .env")
    public_url = env["STELLA_PUBLIC_URL"].strip().rstrip("/")
    parsed = urlparse(public_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ConfigError(f"stella_http: STELLA_PUBLIC_URL must be an https URL, got {public_url!r}")
    return {
        "client_id": env["STELLA_GH_CLIENT_ID"].strip(),
        "client_secret": env["STELLA_GH_CLIENT_SECRET"].strip(),
        "public_url": public_url,
        "public_host": parsed.netloc,
        "allowed_logins": {s.strip() for s in env["STELLA_ALLOWED_GH_LOGINS"].split(",") if s.strip()},
        "denied_tools": ToolDenylist.from_env_value(env.get("STELLA_HTTP_DENY_TOOLS")),
        "port": int(env.get("STELLA_HTTP_PORT", DEFAULT_PORT)),
    }


def build_transport() -> StdioTransport:
    """The stdio Stella server as a persistent child, run with *its* venv."""
    child_env = {k: v for k, v in os.environ.items() if not k.startswith("STELLA_GH_")}
    transport = StdioTransport(
        command=str(STELLA_DIR / ".venv" / "bin" / "python"),
        args=[str(STELLA_DIR / "stella_server.py")],
        cwd=str(STELLA_DIR),
        env=child_env,
        keep_alive=True,
    )
    # The stdio server speaks the classic (2025-xx) handshake only; skip the modern
    # server/discover probe instead of letting it fail and fall back on every session.
    transport.legacy_only = True
    return transport


def build_proxy(auth, allowed_logins: set[str] | None = None, denied_tools: set[str] = frozenset()):
    """Proxy server with policy middleware attached. ``auth=None`` is for in-process
    tests only; ``main()`` always passes a provider."""
    # mode="legacy": never mirror a modern front-connection era onto the 1.x backend.
    proxy = create_proxy(build_transport(), name="stella", auth=auth, mode="legacy")
    if allowed_logins:
        proxy.add_middleware(LoginAllowlist(allowed_logins))
    proxy.add_middleware(ToolDenylist(denied_tools))
    return proxy


def main() -> None:
    from fastmcp.server.auth.providers.github import GitHubProvider

    s = load_settings()
    auth = GitHubProvider(client_id=s["client_id"], client_secret=s["client_secret"],
                          base_url=s["public_url"])
    proxy = build_proxy(auth, s["allowed_logins"], s["denied_tools"])
    print(f"[stella_http] serving {MCP_PATH} on 127.0.0.1:{s['port']} for {s['public_url']} "
          f"(logins: {sorted(s['allowed_logins'])}, denied tools: {sorted(s['denied_tools']) or 'none'})",
          file=sys.stderr, flush=True)
    proxy.run(
        transport="http",
        host="127.0.0.1",
        port=s["port"],
        path=MCP_PATH,
        # Funnel forwards the public Host header; loopback names are for local checks.
        allowed_hosts=[s["public_host"], "127.0.0.1:*", "localhost:*"],
        allowed_origins=[s["public_url"], "http://127.0.0.1:*", "http://localhost:*"],
    )


if __name__ == "__main__":
    main()
