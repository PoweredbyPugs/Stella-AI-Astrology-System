"""Local entrypoint: Stella's stdio server over a bare WebSocket, for Bulbasaur.

The Obsidian Bulbasaur Chat plugin's "http" transport is a plain WebSocket that
carries the same JSON-RPC frames it would otherwise write to a stdio child. It
sends no headers and speaks no OAuth, so it cannot use stella_http.py (Streamable
HTTP behind GitHub OAuth, the claude.ai endpoint). This process is the bridge:
every connection spawns its own stella_server.py child under the stdio venv, each
text frame becomes one stdin line, each stdout line becomes one frame, and the
child dies when the socket closes.

Reach: bind 127.0.0.1 only. `tailscale serve` publishes the port tailnet-only
(never Funnel) and terminates TLS. The plugin cannot send an Authorization header,
so the shared secret travels as ?token=... in the URL; the tailnet is the outer
wall, the token the inner one.
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import os
import sys
from http import HTTPStatus
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from websockets.asyncio.server import serve as _ws_serve
from websockets.exceptions import ConnectionClosed

STELLA_DIR = Path(__file__).resolve().parent
DEFAULT_PORT = 8812
MCP_PATH = "/mcp"
STDIO_COMMAND = [str(STELLA_DIR / ".venv" / "bin" / "python"), str(STELLA_DIR / "stella_server.py")]
MAX_FRAME = 16 * 1024 * 1024  # tool results carry whole charts; be generous


class ConfigError(RuntimeError):
    pass


def load_settings(env) -> dict:
    token = (env.get("STELLA_WS_TOKEN") or "").strip()
    if not token:
        raise ConfigError("stella_ws: refusing to start, STELLA_WS_TOKEN missing or empty in .env")
    return {
        "token": token,
        "port": int(env.get("STELLA_WS_PORT", DEFAULT_PORT)),
        "path": MCP_PATH,
        "command": STDIO_COMMAND,
    }


def authorized(request_target: str, path: str, token: str) -> bool:
    """True when the request hits `path` with ?token= equal to `token`."""
    if not token:
        return False
    parts = urlsplit(request_target)
    if parts.path != path:
        return False
    presented = parse_qs(parts.query).get("token", [""])[0]
    return hmac.compare_digest(presented.encode(), token.encode())


async def _pump(ws, command: list[str]) -> None:
    """One child per socket; frames <-> lines until either side closes."""
    child_env = {k: v for k, v in os.environ.items() if not k.startswith("STELLA_WS_")}
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=sys.stderr,
        cwd=str(STELLA_DIR),
        env=child_env,
        limit=MAX_FRAME,  # one JSON-RPC line per frame; tools/list alone passes 64 KiB
    )

    async def ws_to_child():
        async for frame in ws:
            if isinstance(frame, bytes):
                frame = frame.decode()
            proc.stdin.write(frame.rstrip("\n").encode() + b"\n")
            await proc.stdin.drain()

    async def child_to_ws():
        while line := await proc.stdout.readline():
            await ws.send(line.rstrip(b"\n").decode())
        await ws.close()  # child went away; tell the client

    pumps = [asyncio.create_task(ws_to_child()), asyncio.create_task(child_to_ws())]
    try:
        # whichever direction finishes first ends the session
        done, pending = await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for t in done:
            if (exc := t.exception()) is not None and not isinstance(exc, ConnectionClosed):
                print(f"[stella_ws] session ended with {exc!r}", file=sys.stderr, flush=True)
    finally:
        if proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), 5)
            except asyncio.TimeoutError:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
                await proc.wait()


def serve(settings: dict):
    """An async context manager running the bridge on 127.0.0.1:port."""

    def gate(connection, request):
        if authorized(request.path, settings["path"], settings["token"]):
            return None
        return connection.respond(HTTPStatus.UNAUTHORIZED, "stella_ws: unauthorized\n")

    async def handler(ws):
        await _pump(ws, settings["command"])

    return _ws_serve(handler, "127.0.0.1", settings["port"], process_request=gate,
                     max_size=MAX_FRAME)


async def _main_async(settings: dict) -> None:
    print(f"[stella_ws] serving {settings['path']} on 127.0.0.1:{settings['port']} "
          f"(child: {' '.join(settings['command'])})", file=sys.stderr, flush=True)
    async with serve(settings):
        await asyncio.Future()


def main() -> None:
    try:
        settings = load_settings(os.environ)
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        sys.exit(78)  # EX_CONFIG
    asyncio.run(_main_async(settings))


if __name__ == "__main__":
    main()
