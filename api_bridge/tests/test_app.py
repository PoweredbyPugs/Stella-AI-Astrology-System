import asyncio
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import DENIED_TOOLS, SNAPSHOT_TOOLS, create_app


class TextBlock:
    def __init__(self, text: str):
        self.text = text


class MockGateway:
    def __init__(self):
        self.started = 0
        self.stopped = 0
        self.calls = []
        self.active_calls = 0
        self.max_active_calls = 0
        names = [
            "get_current_moon",
            "get_planet_positions",
            "get_planet_aspects",
            "get_current_dignities",
            "echo",
            *sorted(DENIED_TOOLS),
        ]
        self.tools = [
            SimpleNamespace(
                name=name,
                description=f"Description for {name}",
                inputSchema={"type": "object"},
            )
            for name in names
        ]
        self.failures = set()

    async def start(self):
        self.started += 1

    async def stop(self):
        self.stopped += 1

    async def list_tools(self):
        return SimpleNamespace(tools=self.tools)

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        self.active_calls += 1
        self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            await asyncio.sleep(0.01)
            if name in self.failures:
                raise RuntimeError(f"{name} unavailable")
            return SimpleNamespace(
                content=[TextBlock('{"name": "%s", "ok": true}' % name)],
                isError=False,
                structuredContent=None,
            )
        finally:
            self.active_calls -= 1


@pytest.fixture
def gateway():
    return MockGateway()


@pytest.fixture
def app(monkeypatch, gateway):
    monkeypatch.setenv("STELLA_API_HOST", "127.0.0.1")
    monkeypatch.setenv("STELLA_API_TOKEN", "test-token")
    return create_app(lambda: gateway)


def test_lifespan_starts_and_stops_one_gateway(app, gateway):
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok", "mcp": "connected"}
        assert gateway.started == 1
    assert gateway.stopped == 1


def test_bearer_auth_protects_v1_routes(app):
    with TestClient(app) as client:
        response = client.get("/v1/tools")
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

        response = client.get(
            "/v1/tools", headers={"Authorization": "Bearer wrong-token"}
        )
        assert response.status_code == 401

        response = client.get(
            "/v1/tools", headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200


def test_token_is_optional_on_loopback(monkeypatch, gateway):
    monkeypatch.setenv("STELLA_API_HOST", "localhost")
    monkeypatch.delenv("STELLA_API_TOKEN", raising=False)
    with TestClient(create_app(lambda: gateway)) as client:
        assert client.get("/v1/tools").status_code == 200


def test_non_loopback_bind_requires_token(monkeypatch, gateway):
    monkeypatch.setenv("STELLA_API_HOST", "0.0.0.0")
    monkeypatch.delenv("STELLA_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="STELLA_API_TOKEN is required"):
        with TestClient(create_app(lambda: gateway)):
            pass
    assert gateway.started == 0


def test_tool_listing_filters_explicit_denylist(app):
    with TestClient(app) as client:
        response = client.get(
            "/v1/tools", headers={"Authorization": "Bearer test-token"}
        )
    assert response.status_code == 200
    names = {tool["name"] for tool in response.json()["tools"]}
    assert "echo" in names
    assert not names.intersection(DENIED_TOOLS)
    assert response.json()["count"] == len(names)


def test_tool_call_forwards_arguments_and_decodes_json(app, gateway):
    with TestClient(app) as client:
        response = client.post(
            "/v1/tools/echo",
            headers={"Authorization": "Bearer test-token"},
            json={"message": "hello"},
        )
    assert response.status_code == 200
    assert response.json() == {
        "tool": "echo",
        "isError": False,
        "result": {"name": "echo", "ok": True},
    }
    assert gateway.calls == [("echo", {"message": "hello"})]


@pytest.mark.parametrize("name", sorted(DENIED_TOOLS))
def test_denied_tools_cannot_be_called(app, gateway, name):
    with TestClient(app) as client:
        response = client.post(
            f"/v1/tools/{name}",
            headers={"Authorization": "Bearer test-token"},
            json={},
        )
    assert response.status_code == 403
    assert gateway.calls == []


def test_unknown_tool_returns_404(app):
    with TestClient(app) as client:
        response = client.post(
            "/v1/tools/not_a_tool",
            headers={"Authorization": "Bearer test-token"},
            json={},
        )
    assert response.status_code == 404


def test_snapshot_calls_all_tools_concurrently_and_reports_partial_errors(app, gateway):
    gateway.failures.add("get_planet_aspects")
    with TestClient(app) as client:
        response = client.get(
            "/v1/snapshot", headers={"Authorization": "Bearer test-token"}
        )
    assert response.status_code == 200
    body = response.json()
    assert body["partial"] is True
    assert set(body["data"]) == {"moon", "planets", "dignities"}
    assert body["errors"] == {"aspects": "get_planet_aspects unavailable"}
    assert {name for name, arguments in gateway.calls} == set(SNAPSHOT_TOOLS.values())
    assert all(arguments == {} for name, arguments in gateway.calls)
    assert gateway.max_active_calls == 4


def test_structured_content_takes_precedence(app, gateway):
    async def structured_call(name, arguments):
        return SimpleNamespace(
            content=[TextBlock("ignored")],
            isError=False,
            structuredContent={"answer": 42},
        )

    gateway.call_tool = structured_call
    with TestClient(app) as client:
        response = client.post(
            "/v1/tools/echo",
            headers={"Authorization": "Bearer test-token"},
            json={},
        )
    assert response.json()["result"] == {"answer": 42}


def test_fastmcp_result_wrapper_is_unwrapped(app, gateway):
    async def structured_call(name, arguments):
        return SimpleNamespace(
            content=[TextBlock("ignored")],
            isError=False,
            structuredContent={"result": {"sign": "Taurus"}},
        )

    gateway.call_tool = structured_call
    with TestClient(app) as client:
        response = client.post(
            "/v1/tools/echo",
            headers={"Authorization": "Bearer test-token"},
            json={},
        )
    assert response.json()["result"] == {"sign": "Taurus"}


def test_fastmcp_json_string_result_is_decoded(app, gateway):
    async def structured_call(name, arguments):
        return SimpleNamespace(
            content=[TextBlock("ignored")],
            isError=False,
            structuredContent={"result": '{"phase": "Full Moon"}'},
        )

    gateway.call_tool = structured_call
    with TestClient(app) as client:
        response = client.post(
            "/v1/tools/echo",
            headers={"Authorization": "Bearer test-token"},
            json={},
        )
    assert response.json()["result"] == {"phase": "Full Moon"}
