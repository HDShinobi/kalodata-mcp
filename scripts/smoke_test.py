"""
Live smoke test against the real Kalodata Open API (needs KALODATA_SECRET_KEY in .env).

Calls every rank endpoint, then feeds the first ID it returns into the matching
detail endpoint. Usage:

    python scripts/smoke_test.py            # uses KALODATA_DEFAULT_* or US/en-US/USD
    python scripts/smoke_test.py VN vi-VN VND
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import server  # noqa: E402

# (name, rank path, detail path, id field in rank rows, id param for detail)
ENTITIES = [
    ("category", "/openapi/v1/category/rank", "/openapi/v1/category/detail", "category_id"),
    ("product", "/openapi/v1/product/rank", "/openapi/v1/product/detail", "product_id"),
    ("creator", "/openapi/v1/creator/rank", "/openapi/v1/creator/detail", "creator_id"),
    ("video", "/openapi/v1/video/rank", "/openapi/v1/video/detail", "video_id"),
    ("shop", "/openapi/v1/shop/rank", "/openapi/v1/shop/detail", "shop_id"),
    ("livestream", "/openapi/v1/livestream/rank", "/openapi/v1/livestream/detail", "livestream_id"),
]


def _status(resp: dict) -> str:
    if resp.get("success") is True:
        return "OK"
    return f"FAIL: {resp.get('message') or resp}"


async def main(region=None, language=None, currency=None) -> int:
    common = server._common(region, language, currency, None)
    print(f"Base URL: {server.KALODATA_BASE_URL}")
    print(f"Params:   {common}\n")

    failures = 0
    for name, rank_path, detail_path, id_field in ENTITIES:
        rank = await server.call_kalodata(
            rank_path, {**common, "sort_field": server.DEFAULT_SORT, "page_number": 1}
        )
        status = _status(rank)
        failures += status != "OK"
        print(f"[{status}] {name}_rank")

        rows = rank.get("data") if isinstance(rank.get("data"), list) else []
        if not rows:
            print(f"        (no rows, skipping {name}_detail)")
            continue
        print(f"        first row keys: {sorted(rows[0].keys())}")

        entity_id = rows[0].get(id_field)
        if not entity_id:
            print(f"        (row has no '{id_field}', skipping {name}_detail)")
            failures += 1
            continue
        detail = await server.call_kalodata(detail_path, {**common, id_field: entity_id})
        status = _status(detail)
        failures += status != "OK"
        print(f"[{status}] {name}_detail({entity_id})")
        if isinstance(detail.get("data"), dict):
            print(f"        keys: {json.dumps(sorted(detail['data'].keys()))[:300]}")

    print(f"\n{'All endpoints OK' if not failures else f'{failures} failure(s)'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(*sys.argv[1:4])))
