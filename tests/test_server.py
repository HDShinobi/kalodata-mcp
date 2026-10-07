"""Offline tests: the Kalodata API is mocked, no network or real key needed."""

import json
import os

os.environ.setdefault("KALODATA_SECRET_KEY", "test-key")

import httpx  # noqa: E402
import pytest  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

import server  # noqa: E402


@pytest.fixture
def kalodata(monkeypatch):
    """Route Kalodata HTTP calls to an in-memory handler and record the requests."""
    calls = []
    state = {"status": 200, "body": {"success": True, "data": []}}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(
            {
                "path": request.url.path,
                "headers": request.headers,
                "json": json.loads(request.content),
            }
        )
        return httpx.Response(state["status"], json=state["body"])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(server, "_get_client", lambda: client)
    return calls, state


def test_registers_all_tools():
    names = {t.name for t in server.mcp._tool_manager.list_tools()}
    for entity in ["category", "product", "creator", "video", "shop", "livestream"]:
        assert f"{entity}_rank" in names
        assert f"{entity}_detail" in names
    assert len(names) == 12


async def test_rank_payload_defaults_and_drops_none(kalodata):
    calls, _ = kalodata
    out = await server.product_rank(category_id="123")

    assert json.loads(out) == {"success": True, "data": []}
    call = calls[0]
    assert call["path"] == "/openapi/v1/product/rank"
    assert call["headers"]["secret-key"] == "test-key"
    assert call["json"] == {
        "region": server.DEFAULT_REGION,
        "language": server.DEFAULT_LANGUAGE,
        "currency": server.DEFAULT_CURRENCY,
        "date_range": server.DEFAULT_DATE_RANGE,
        "sort_field": {"field": "revenue", "type": "DESC"},
        "page_number": 1,
        "category_id": "123",
    }


async def test_rank_passes_region_and_page_size(kalodata):
    calls, _ = kalodata
    await server.creator_rank(region="VN", language="vi-VN", currency="VND", page_size=50)
    payload = calls[0]["json"]
    assert payload["region"] == "VN"
    assert payload["language"] == "vi-VN"
    assert payload["currency"] == "VND"
    assert payload["page_size"] == 50
    assert calls[0]["path"] == "/openapi/v1/creator/rank"


async def test_detail_payload(kalodata):
    calls, _ = kalodata
    await server.creator_detail("c1", shop_id="s1")
    assert calls[0]["path"] == "/openapi/v1/creator/detail"
    assert calls[0]["json"]["creator_id"] == "c1"
    assert calls[0]["json"]["shop_id"] == "s1"
    assert "category_id" not in calls[0]["json"]


async def test_http_error_raises_tool_error(kalodata):
    _, state = kalodata
    state["status"] = 403
    state["body"] = {"message": "The key is not allowed"}
    with pytest.raises(server.ToolError, match="HTTP 403"):
        await server.shop_detail("s1")


async def test_kalodata_business_error_raises(kalodata):
    _, state = kalodata
    state["body"] = {"success": False, "code": 1001, "message": "The key is not allowed"}
    with pytest.raises(server.ToolError, match="The key is not allowed"):
        await server.category_rank()


INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1"},
    },
}
MCP_HEADERS = {"Accept": "application/json, text/event-stream"}


@pytest.fixture(autouse=True)
def fresh_session_manager(monkeypatch):
    # The SDK's session manager can only run once; give each HTTP test a new one.
    monkeypatch.setattr(server.mcp, "_session_manager", None)


def test_http_without_auth_token(monkeypatch):
    monkeypatch.setattr(server, "MCP_AUTH_TOKEN", None)
    with TestClient(server.build_http_app()) as client:
        resp = client.post("/mcp", json=INIT, headers=MCP_HEADERS)
    assert resp.status_code == 200
    assert '"serverInfo"' in resp.text


def test_http_bearer_auth(monkeypatch):
    monkeypatch.setattr(server, "MCP_AUTH_TOKEN", "s3cret")
    with TestClient(server.build_http_app()) as client:
        assert client.post("/mcp", json=INIT, headers=MCP_HEADERS).status_code == 401
        bad = {**MCP_HEADERS, "Authorization": "Bearer nope"}
        assert client.post("/mcp", json=INIT, headers=bad).status_code == 401
        good = {**MCP_HEADERS, "Authorization": "Bearer s3cret"}
        resp = client.post("/mcp", json=INIT, headers=good)
    assert resp.status_code == 200
