"""The WebSocket-to-stdio bridge that Bulbasaur's "http" transport talks to."""

import asyncio
import json
import os
import signal
import sys
from pathlib import Path

import pytest

websockets = pytest.importorskip("websockets")

from websockets.asyncio.client import connect  # noqa: E402
from websockets.exceptions import InvalidStatus  # noqa: E402

STELLA_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STELLA_DIR))

from stella_ws import ConfigError, authorized, load_settings, serve  # noqa: E402

FAKE_CHILD = [sys.executable, str(STELLA_DIR / "tests" / "fake_stdio_server.py")]
TOKEN = "s3cret-token-for-tests"


# ── settings ────────────────────────────────────────────────────────────────

def test_settings_require_a_token():
    with pytest.raises(ConfigError, match="STELLA_WS_TOKEN"):
        load_settings({})
    with pytest.raises(ConfigError, match="STELLA_WS_TOKEN"):
        load_settings({"STELLA_WS_TOKEN": "   "})


def test_settings_default_port_and_path():
    s = load_settings({"STELLA_WS_TOKEN": TOKEN})
    assert s["token"] == TOKEN
    assert s["port"] == 8812
    assert s["path"] == "/mcp"


def test_settings_port_from_env():
    assert load_settings({"STELLA_WS_TOKEN": TOKEN, "STELLA_WS_PORT": "9001"})["port"] == 9001


# ── token check ─────────────────────────────────────────────────────────────

def test_authorized_only_with_matching_token_on_the_mcp_path():
    assert authorized("/mcp?token=" + TOKEN, "/mcp", TOKEN)
    assert not authorized("/mcp?token=wrong", "/mcp", TOKEN)
    assert not authorized("/mcp", "/mcp", TOKEN)
    assert not authorized("/other?token=" + TOKEN, "/mcp", TOKEN)
    assert not authorized("/mcp?token=", "/mcp", "")


# ── live bridge ─────────────────────────────────────────────────────────────

async def _run(coro):
    settings = {"token": TOKEN, "port": 0, "path": "/mcp", "command": FAKE_CHILD}
    async with serve(settings) as server:
        port = server.sockets[0].getsockname()[1]
        return await coro(f"ws://127.0.0.1:{port}/mcp")


def test_rejects_wrong_token_with_401():
    async def scenario(base):
        with pytest.raises(InvalidStatus) as exc:
            async with connect(base + "?token=nope"):
                pass
        return exc.value.response.status_code

    assert asyncio.run(_run(scenario)) == 401


def test_bridges_a_jsonrpc_frame_to_the_child_and_back():
    async def scenario(base):
        async with connect(base + "?token=" + TOKEN) as ws:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 7, "method": "initialize", "params": {}}))
            return json.loads(await asyncio.wait_for(ws.recv(), 10))

    reply = asyncio.run(_run(scenario))
    assert reply["id"] == 7
    assert reply["result"]["echo"] == "initialize"


def test_frames_larger_than_64k_survive_the_round_trip():
    async def scenario(base):
        async with connect(base + "?token=" + TOKEN, max_size=None) as ws:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "big"}))
            return json.loads(await asyncio.wait_for(ws.recv(), 10))

    reply = asyncio.run(_run(scenario))
    assert len(reply["result"]["pad"]) == 300_000


def test_each_connection_gets_its_own_child_that_dies_with_the_socket():
    async def scenario(base):
        pids = []
        for i in range(2):
            async with connect(base + "?token=" + TOKEN) as ws:
                await ws.send(json.dumps({"jsonrpc": "2.0", "id": i, "method": "ping"}))
                pids.append(json.loads(await asyncio.wait_for(ws.recv(), 10))["result"]["pid"])
        # give the bridge a moment to reap
        for _ in range(50):
            alive = [p for p in pids if _alive(p)]
            if not alive:
                break
            await asyncio.sleep(0.1)
        return pids, alive

    pids, alive = asyncio.run(_run(scenario))
    assert len(set(pids)) == 2, "two connections must not share one child"
    assert alive == [], f"children still running after their sockets closed: {alive}"


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # zombie still counts as "gone" once reaped; check state
    try:
        _, status = os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
