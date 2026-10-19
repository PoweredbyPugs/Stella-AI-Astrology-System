"""Policy tests for the remote (Streamable HTTP) Stella endpoint.

Runs only under the HTTP venv: .venv-http/bin/python -m pytest tests/test_stella_http.py
Under the main venv `fastmcp` is absent and the module is skipped.
"""
import asyncio
import sys
from pathlib import Path

import pytest

fastmcp = pytest.importorskip("fastmcp")

from fastmcp import Client, FastMCP  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402
from fastmcp.server.auth import AccessToken  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from stella_http_policy import LoginAllowlist, ToolDenylist  # noqa: E402


def _server() -> FastMCP:
    srv = FastMCP("policy-test")

    @srv.tool
    def hello() -> str:
        return "hi"

    @srv.tool
    def graph_cypher(q: str) -> str:
        return "unsafe"

    return srv


def _token(login):
    return AccessToken(token="t", client_id="c", scopes=[], claims={"login": login})


def _run(coro):
    return asyncio.run(coro)


async def _names(server):
    async with Client(server) as c:
        return sorted(t.name for t in await c.list_tools())


# ── login allowlist ────────────────────────────────────────────────────────

def test_allowed_login_passes():
    srv = _server()
    srv.add_middleware(LoginAllowlist({"PoweredbyPugs"}, token_getter=lambda: _token("PoweredbyPugs")))
    assert _run(_names(srv)) == ["graph_cypher", "hello"]


def test_other_login_is_rejected():
    srv = _server()
    srv.add_middleware(LoginAllowlist({"PoweredbyPugs"}, token_getter=lambda: _token("someone-else")))
    with pytest.raises(Exception, match="not allowed"):
        _run(_names(srv))


def test_missing_token_is_rejected():
    srv = _server()
    srv.add_middleware(LoginAllowlist({"PoweredbyPugs"}, token_getter=lambda: None))
    with pytest.raises(Exception, match="not allowed"):
        _run(_names(srv))


def test_empty_allowlist_refused_at_construction():
    with pytest.raises(ValueError):
        LoginAllowlist(set())


# ── tool denylist ──────────────────────────────────────────────────────────

def test_denylist_hides_and_blocks():
    srv = _server()
    srv.add_middleware(ToolDenylist({"graph_cypher"}))
    assert _run(_names(srv)) == ["hello"]

    async def call():
        async with Client(srv) as c:
            await c.call_tool("graph_cypher", {"q": "MATCH (n) DETACH DELETE n"})

    with pytest.raises(ToolError, match="disabled"):
        _run(call())


def test_empty_denylist_passes_everything():
    srv = _server()
    srv.add_middleware(ToolDenylist(set()))
    assert _run(_names(srv)) == ["graph_cypher", "hello"]


def test_denylist_parses_env_string():
    assert ToolDenylist.from_env_value(" graph_cypher, delete_chart ,") == {"graph_cypher", "delete_chart"}
    assert ToolDenylist.from_env_value("") == set()
    assert ToolDenylist.from_env_value(None) == set()


# ── integration: proxy over the real stdio server (slow) ───────────────────

def test_proxy_discovers_real_tools_and_reports_build():
    from stella_http import build_proxy

    proxy = build_proxy(auth=None)

    async def go():
        async with Client(proxy) as c:
            names = {t.name for t in await c.list_tools()}
            assert "get_convergence_ki_now" in names
            assert len(names) > 80, len(names)
            res = await c.call_tool("get_convergence_ki_now", {"target_date": "2026-10-19"})
            text = res.content[0].text
            assert '"build"' in text and '"git"' in text

    _run(go())


# ── settings: never start open ─────────────────────────────────────────────

GOOD_ENV = {
    "STELLA_GH_CLIENT_ID": "id", "STELLA_GH_CLIENT_SECRET": "sec",
    "STELLA_PUBLIC_URL": "https://punkrecords.tail4a61d3.ts.net:10000/",
    "STELLA_ALLOWED_GH_LOGINS": "PoweredbyPugs, second",
    "STELLA_HTTP_DENY_TOOLS": "graph_cypher",
}


def test_settings_parse_and_normalise():
    from stella_http import load_settings

    s = load_settings(GOOD_ENV)
    assert s["public_url"] == "https://punkrecords.tail4a61d3.ts.net:10000"  # trailing slash dropped
    assert s["public_host"] == "punkrecords.tail4a61d3.ts.net:10000"
    assert s["allowed_logins"] == {"PoweredbyPugs", "second"}
    assert s["denied_tools"] == {"graph_cypher"}
    assert s["port"] == 8811


@pytest.mark.parametrize("missing", ["STELLA_GH_CLIENT_ID", "STELLA_GH_CLIENT_SECRET",
                                     "STELLA_PUBLIC_URL", "STELLA_ALLOWED_GH_LOGINS"])
def test_settings_refuse_missing_auth(missing):
    from stella_http import ConfigError, load_settings

    env = {**GOOD_ENV, missing: ""}
    with pytest.raises(ConfigError, match=missing):
        load_settings(env)


def test_settings_refuse_non_https_public_url():
    from stella_http import ConfigError, load_settings

    with pytest.raises(ConfigError, match="https"):
        load_settings({**GOOD_ENV, "STELLA_PUBLIC_URL": "http://punkrecords.tail4a61d3.ts.net:10000"})
