"""Kalodata MCP server: exposes the Kalodata Open API (TikTok Shop analytics) as MCP tools."""

import hmac
import json
import os
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

# Load environment variables from a local .env file (no-op in production).
load_dotenv()

KALODATA_SECRET_KEY = os.getenv("KALODATA_SECRET_KEY")
KALODATA_BASE_URL = os.getenv("KALODATA_BASE_URL", "https://staging.kalodata.com").rstrip("/")
KALODATA_TIMEOUT = float(os.getenv("KALODATA_TIMEOUT", "30"))

# Defaults applied when the client does not pass region/language/currency/date_range.
DEFAULT_REGION = os.getenv("KALODATA_DEFAULT_REGION", "US")
DEFAULT_LANGUAGE = os.getenv("KALODATA_DEFAULT_LANGUAGE", "en-US")
DEFAULT_CURRENCY = os.getenv("KALODATA_DEFAULT_CURRENCY", "USD")
DEFAULT_DATE_RANGE = os.getenv("KALODATA_DEFAULT_DATE_RANGE", "last7Day")

# Optional shared secret protecting the public /mcp endpoint (HTTP transport only).
MCP_AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN") or None
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

if not KALODATA_SECRET_KEY:
    raise ValueError(
        "KALODATA_SECRET_KEY is not set. "
        "Define it in your .env file or in your hosting provider's dashboard."
    )

DEFAULT_SORT = {"field": "revenue", "type": "DESC"}

_http_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    """Return a shared HTTP client so connections are reused across tool calls."""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=KALODATA_TIMEOUT)
    return _http_client


async def call_kalodata(path: str, payload: dict) -> dict:
    """
    Send a POST request to the Kalodata Open API.
    Adds the auth headers and converts network/HTTP failures into an error dict.
    """
    url = f"{KALODATA_BASE_URL}{path}"
    headers = {
        "secret-key": KALODATA_SECRET_KEY,
        "content-type": "application/json;charset=utf-8",
    }

    try:
        response = await _get_client().post(url, json=payload, headers=headers)
    except httpx.TimeoutException:
        return {
            "error": True,
            "status_code": 408,
            "message": f"Timed out after {KALODATA_TIMEOUT:g}s while calling the Kalodata API.",
        }
    except httpx.RequestError as exc:
        return {
            "error": True,
            "status_code": 502,
            "message": f"Could not reach the Kalodata API: {exc}",
        }

    if response.status_code >= 400:
        return {
            "error": True,
            "status_code": response.status_code,
            "message": f"Kalodata API request failed (HTTP {response.status_code}): {response.text}",
        }
    try:
        return response.json()
    except ValueError:
        return {
            "error": True,
            "status_code": response.status_code,
            "message": f"Kalodata API returned a non-JSON response: {response.text[:500]}",
        }


def _clean_payload(base_params: dict, extra_params: dict) -> dict:
    """Merge optional parameters into the payload, dropping the ones that are None."""
    payload = {**base_params}
    for k, v in extra_params.items():
        if v is not None:
            payload[k] = v
    return payload


def _common(
    region: Optional[str],
    language: Optional[str],
    currency: Optional[str],
    date_range: Optional[str],
) -> dict:
    """Build the market/time parameters shared by every endpoint, applying env defaults."""
    return {
        "region": region or DEFAULT_REGION,
        "language": language or DEFAULT_LANGUAGE,
        "currency": currency or DEFAULT_CURRENCY,
        "date_range": date_range or DEFAULT_DATE_RANGE,
    }


async def _rank(path: str, common: dict, sort_field, page_number, page_size, filters: dict) -> str:
    base = {**common, "sort_field": sort_field or DEFAULT_SORT, "page_number": page_number}
    payload = _clean_payload(base, {"page_size": page_size, **filters})
    return _dump(await call_kalodata(path, payload))


async def _detail(path: str, common: dict, ids: dict) -> str:
    payload = _clean_payload(common, ids)
    return _dump(await call_kalodata(path, payload))


def _dump(result: dict) -> str:
    # Surface failures as MCP tool errors (isError=true) instead of a "successful" payload.
    if result.get("error") or result.get("success") is False:
        raise ToolError(json.dumps(result, ensure_ascii=False))
    # Compact JSON keeps large rank responses cheaper in the model's context.
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


SERVER_INSTRUCTIONS = """\
Kalodata TikTok Shop analytics. Typical workflow: use a *_rank tool to discover
categories, products, creators, videos, shops or livestreams, then pass an ID from the
result to the matching *_detail tool.
Common parameters: region (market code, e.g. US, VN, ID, TH, MY, PH, GB),
language (e.g. en-US, vi-VN), currency (e.g. USD, VND), date_range (e.g. last7Day).
Rank tools sort by {"field": "revenue", "type": "DESC"} unless sort_field is given,
and are paginated with page_number (and optional page_size).
"""

mcp = FastMCP(
    "kalodata",
    instructions=SERVER_INSTRUCTIONS,
    host=HOST,
    port=PORT,
    # Stateless mode: no server-side sessions, so restarts/scale-to-zero don't break clients.
    stateless_http=os.getenv("MCP_STATELESS_HTTP", "true").lower() == "true",
)


# --------------------------------------------------------------------------- category


@mcp.tool()
async def category_rank(
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
    category_id: Optional[str] = None,
    category_level: Optional[int] = None,
    revenue_range: Optional[Dict[str, Any]] = None,
    sort_field: Optional[Dict[str, str]] = None,
    page_number: int = 1,
    page_size: Optional[int] = None,
) -> str:
    """
    Rank TikTok Shop product categories by revenue.
    Use it to find which niches/categories generate the most sales.
    """
    return await _rank(
        "/openapi/v1/category/rank",
        _common(region, language, currency, date_range),
        sort_field,
        page_number,
        page_size,
        {
            "category_id": category_id,
            "category_level": category_level,
            "revenue_range": revenue_range,
        },
    )


@mcp.tool()
async def category_detail(
    category_id: str,
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
) -> str:
    """
    Get full details for one TikTok Shop category by its ID.
    Returns in-depth sales metrics, growth rate and category behavior.
    """
    return await _detail(
        "/openapi/v1/category/detail",
        _common(region, language, currency, date_range),
        {"category_id": category_id},
    )


# --------------------------------------------------------------------------- product


@mcp.tool()
async def product_rank(
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
    category_id: Optional[str] = None,
    shop_id: Optional[str] = None,
    creator_id: Optional[str] = None,
    video_id: Optional[str] = None,
    revenue_range: Optional[Dict[str, Any]] = None,
    is_affiliate: Optional[str] = None,
    commission_rate: Optional[Dict[str, Any]] = None,
    unit_price_range: Optional[Dict[str, Any]] = None,
    sort_field: Optional[Dict[str, str]] = None,
    page_number: int = 1,
    page_size: Optional[int] = None,
) -> str:
    """
    Rank the best-selling TikTok Shop products.
    Filter by category, shop, creator, video, commission rate and unit price.
    Useful for finding winning products.
    """
    return await _rank(
        "/openapi/v1/product/rank",
        _common(region, language, currency, date_range),
        sort_field,
        page_number,
        page_size,
        {
            "category_id": category_id,
            "shop_id": shop_id,
            "creator_id": creator_id,
            "video_id": video_id,
            "revenue_range": revenue_range,
            "is_affiliate": is_affiliate,
            "commission_rate": commission_rate,
            "unit_price_range": unit_price_range,
        },
    )


@mcp.tool()
async def product_detail(
    product_id: str,
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
) -> str:
    """
    Get detailed data for one TikTok Shop product by its ID.
    Returns sales, affiliate commission, owning shop and promotional video/live stats.
    """
    return await _detail(
        "/openapi/v1/product/detail",
        _common(region, language, currency, date_range),
        {"product_id": product_id},
    )


# --------------------------------------------------------------------------- creator


@mcp.tool()
async def creator_rank(
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
    category_id: Optional[str] = None,
    shop_id: Optional[str] = None,
    revenue_range: Optional[Dict[str, Any]] = None,
    creator_type: Optional[str] = None,
    followers_range: Optional[str] = None,
    engagement_rate: Optional[str] = None,
    sort_field: Optional[Dict[str, str]] = None,
    page_number: int = 1,
    page_size: Optional[int] = None,
) -> str:
    """
    Rank TikTok Shop creators/influencers by the revenue they generate.
    Filter by creator type, follower count and engagement rate to find partners.
    """
    return await _rank(
        "/openapi/v1/creator/rank",
        _common(region, language, currency, date_range),
        sort_field,
        page_number,
        page_size,
        {
            "category_id": category_id,
            "shop_id": shop_id,
            "revenue_range": revenue_range,
            "creator_type": creator_type,
            "followers_range": followers_range,
            "engagement_rate": engagement_rate,
        },
    )


@mcp.tool()
async def creator_detail(
    creator_id: str,
    shop_id: Optional[str] = None,
    category_id: Optional[str] = None,
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
) -> str:
    """
    Get detailed stats for one TikTok Shop creator by their ID.
    Returns accumulated sales, video engagement and performance history.
    """
    return await _detail(
        "/openapi/v1/creator/detail",
        _common(region, language, currency, date_range),
        {"creator_id": creator_id, "shop_id": shop_id, "category_id": category_id},
    )


# --------------------------------------------------------------------------- video


@mcp.tool()
async def video_rank(
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
    category_id: Optional[str] = None,
    shop_id: Optional[str] = None,
    creator_id: Optional[str] = None,
    product_id: Optional[str] = None,
    revenue_range: Optional[Dict[str, Any]] = None,
    followers_range: Optional[str] = None,
    ads_roas: Optional[Dict[str, Any]] = None,
    sort_field: Optional[Dict[str, str]] = None,
    page_number: int = 1,
    page_size: Optional[int] = None,
) -> str:
    """
    Rank the top-selling viral videos on TikTok Shop.
    Useful for researching high-converting creatives, hooks and ad ROAS.
    """
    return await _rank(
        "/openapi/v1/video/rank",
        _common(region, language, currency, date_range),
        sort_field,
        page_number,
        page_size,
        {
            "category_id": category_id,
            "shop_id": shop_id,
            "creator_id": creator_id,
            "product_id": product_id,
            "revenue_range": revenue_range,
            "followers_range": followers_range,
            "ads_roas": ads_roas,
        },
    )


@mcp.tool()
async def video_detail(
    video_id: str,
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
) -> str:
    """
    Get full performance metrics for one TikTok Shop video by its ID.
    Returns revenue, views, likes and the products linked to the video.
    """
    return await _detail(
        "/openapi/v1/video/detail",
        _common(region, language, currency, date_range),
        {"video_id": video_id},
    )


# --------------------------------------------------------------------------- shop


@mcp.tool()
async def shop_rank(
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
    category_id: Optional[str] = None,
    revenue_range: Optional[Dict[str, Any]] = None,
    shop_type: Optional[str] = None,
    sort_field: Optional[Dict[str, str]] = None,
    page_number: int = 1,
    page_size: Optional[int] = None,
) -> str:
    """
    Rank TikTok Shop stores by revenue.
    Filter by product category, revenue range and shop type.
    """
    return await _rank(
        "/openapi/v1/shop/rank",
        _common(region, language, currency, date_range),
        sort_field,
        page_number,
        page_size,
        {
            "category_id": category_id,
            "revenue_range": revenue_range,
            "shop_type": shop_type,
        },
    )


@mcp.tool()
async def shop_detail(
    shop_id: str,
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
) -> str:
    """
    Get performance details for one TikTok Shop store by its ID.
    Returns total sales, best-selling products, affiliate channel and revenue split.
    """
    return await _detail(
        "/openapi/v1/shop/detail",
        _common(region, language, currency, date_range),
        {"shop_id": shop_id},
    )


# --------------------------------------------------------------------------- livestream


@mcp.tool()
async def livestream_rank(
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
    category_id: Optional[str] = None,
    shop_id: Optional[str] = None,
    creator_id: Optional[str] = None,
    revenue_range: Optional[Dict[str, Any]] = None,
    sort_field: Optional[Dict[str, str]] = None,
    page_number: int = 1,
    page_size: Optional[int] = None,
) -> str:
    """
    Rank TikTok Shop livestreams by revenue.
    Useful for seeing which lives earned the most, their peak viewers and promoted products.
    """
    return await _rank(
        "/openapi/v1/livestream/rank",
        _common(region, language, currency, date_range),
        sort_field,
        page_number,
        page_size,
        {
            "category_id": category_id,
            "shop_id": shop_id,
            "creator_id": creator_id,
            "revenue_range": revenue_range,
        },
    )


@mcp.tool()
async def livestream_detail(
    livestream_id: str,
    region: Optional[str] = None,
    language: Optional[str] = None,
    currency: Optional[str] = None,
    date_range: Optional[str] = None,
) -> str:
    """
    Get full stats for one TikTok Shop livestream by its ID.
    Returns audience metrics, duration, total revenue, GPM and products sold.
    """
    return await _detail(
        "/openapi/v1/livestream/detail",
        _common(region, language, currency, date_range),
        {"livestream_id": livestream_id},
    )


# --------------------------------------------------------------------------- HTTP app


class BearerAuthMiddleware:
    """Reject HTTP requests that lack `Authorization: Bearer <MCP_AUTH_TOKEN>`."""

    def __init__(self, app, token: str):
        self.app = app
        self.expected = f"Bearer {token}".encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers") or [])
            provided = headers.get(b"authorization", b"")
            if not hmac.compare_digest(provided, self.expected):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"www-authenticate", b"Bearer"),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
                return
        await self.app(scope, receive, send)


def build_http_app():
    """Build the Streamable HTTP ASGI app, wrapped with bearer auth when configured."""
    app = mcp.streamable_http_app()
    if MCP_AUTH_TOKEN:
        return BearerAuthMiddleware(app, MCP_AUTH_TOKEN)
    return app


if __name__ == "__main__":
    tool_count = len(mcp._tool_manager.list_tools())
    if MCP_TRANSPORT == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn

        print(f"[kalodata-mcp] Starting server at http://{HOST}:{PORT}/mcp")
        print(
            f"[kalodata-mcp] Transport: streamable-http | {tool_count} tools registered | "
            f"auth: {'bearer token' if MCP_AUTH_TOKEN else 'NONE (set MCP_AUTH_TOKEN)'}"
        )
        uvicorn.run(build_http_app(), host=HOST, port=PORT)
