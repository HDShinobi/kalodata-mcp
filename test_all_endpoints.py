import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import asyncio
import json
import os

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))
from server import call_kalodata

def ok(resp): return resp.get("success") is True
def status(resp): return "✅ SUCESSO" if ok(resp) else f"❌ ERRO: {resp.get('message', resp.get('error'))}"

async def test_all():
    print("=" * 60)
    print("  TESTE COMPLETO - Kalodata Open API (todos os 8 endpoints)")
    print("=" * 60)
    
    base_common = {
        "region": "US", "language": "en-US", "currency": "USD",
        "date_range": "last7Day"
    }
    sort_revenue = {"field": "revenue", "type": "DESC"}

    tests = [
        ("/openapi/v1/category/rank", {**base_common, "sort_field": sort_revenue, "page_number": 1}),
        ("/openapi/v1/category/detail", {**base_common, "category_id": "601450"}),
        ("/openapi/v1/product/rank", {**base_common, "sort_field": sort_revenue, "page_number": 1}),
        ("/openapi/v1/product/detail", {**base_common, "product_id": "1730327988167836895"}),
        ("/openapi/v1/crator/rank", {**base_common, "sort_field": sort_revenue, "page_number": 1}),
        ("/openapi/v1/crator/detail", {**base_common, "creator_id": "7183975715938869253"}),
        ("/openapi/v1/video/rank", {**base_common, "sort_field": sort_revenue, "page_number": 1}),
        ("/openapi/v1/video/detail", {**base_common, "video_id": "7415765399989948698"}),
    ]

    results = {}
    for path, payload in tests:
        print(f"\n>> Testando: {path}")
        resp = await call_kalodata(path, payload)
        s = status(resp)
        results[path] = {"status": s, "response": resp}
        print(f"  {s}")
        
        # Show sample data
        if ok(resp):
            data = resp.get("data")
            if isinstance(data, list) and data:
                print(f"  Primeira entrada: {json.dumps(data[0], ensure_ascii=False, indent=4)[:500]}")
            elif isinstance(data, dict):
                keys = list(data.keys())
                print(f"  Chaves retornadas: {keys}")
        else:
            print(f"  Resposta completa: {json.dumps(resp, ensure_ascii=False)}")

    print("\n" + "=" * 60)
    print("  RESUMO DOS TESTES")
    print("=" * 60)
    for path, r in results.items():
        print(f"  {r['status']}  {path}")
    print("=" * 60)

asyncio.run(test_all())
