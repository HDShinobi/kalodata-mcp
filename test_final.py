import asyncio, os, json, sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))
from server import call_kalodata

base = {'region': 'US', 'language': 'en-US', 'currency': 'USD', 'date_range': 'last7Day'}
sort = {'field': 'revenue', 'type': 'DESC'}

async def t():
    results = {}
    
    # 1. category/rank
    r = await call_kalodata('/openapi/v1/category/rank', {**base, 'sort_field': sort, 'page_number': 1})
    results['category_rank'] = ('OK' if r.get('success') else r.get('message'), r.get('data', [{}])[0] if r.get('data') else None)
    
    # 2. category/detail  
    cat_id = r['data'][0]['category_id'] if r.get('data') else '601450'
    r2 = await call_kalodata('/openapi/v1/category/detail', {**base, 'category_id': cat_id})
    results['category_detail'] = ('OK' if r2.get('success') else r2.get('message'), list(r2.get('data', {}).keys()) if r2.get('data') else None)

    # 3. product/rank -> pegar ID real
    rp = await call_kalodata('/openapi/v1/product/rank', {**base, 'sort_field': sort, 'page_number': 1})
    results['product_rank'] = ('OK' if rp.get('success') else rp.get('message'), rp.get('data', [{}])[0] if rp.get('data') else None)
    
    # 4. product/detail com ID real
    prod_id = rp['data'][0]['product_id'] if rp.get('data') else None
    if prod_id:
        rpd = await call_kalodata('/openapi/v1/product/detail', {**base, 'product_id': prod_id})
        results['product_detail'] = ('OK' if rpd.get('success') else rpd.get('message'), list(rpd.get('data', {}).keys()) if rpd.get('data') else None)

    # 5. creator/rank (CORRIGIDO)
    rc = await call_kalodata('/openapi/v1/creator/rank', {**base, 'sort_field': sort, 'page_number': 1})
    results['creator_rank'] = ('OK' if rc.get('success') else rc.get('message'), rc.get('data', [{}])[0] if rc.get('data') else None)

    # 6. creator/detail com ID real do ranking
    creator_id = rc['data'][0]['creator_id'] if rc.get('data') else None
    if creator_id:
        rcd = await call_kalodata('/openapi/v1/creator/detail', {**base, 'creator_id': creator_id})
        results['creator_detail'] = ('OK' if rcd.get('success') else rcd.get('message'), list(rcd.get('data', {}).keys())[:8] if rcd.get('data') else None)
    
    # 7. video/rank -> pegar ID real
    rv = await call_kalodata('/openapi/v1/video/rank', {**base, 'sort_field': sort, 'page_number': 1})
    results['video_rank'] = ('OK' if rv.get('success') else rv.get('message'), rv.get('data', [{}])[0] if rv.get('data') else None)

    # 8. video/detail com ID real
    vid_id = rv['data'][0]['video_id'] if rv.get('data') else None
    if vid_id:
        rvd = await call_kalodata('/openapi/v1/video/detail', {**base, 'video_id': vid_id})
        results['video_detail'] = ('OK' if rvd.get('success') else rvd.get('message'), list(rvd.get('data', {}).keys())[:8] if rvd.get('data') else None)

    print("\n" + "=" * 60)
    print("  RESULTADO FINAL - TODOS OS 8 ENDPOINTS")
    print("=" * 60)
    for name, (status, data) in results.items():
        icon = "OK" if status == "OK" else "FALHA"
        print(f"\n  [{icon}] {name}")
        if status != "OK":
            print(f"        Erro: {status}")
        else:
            print(f"        Dados: {json.dumps(data, ensure_ascii=False)[:200]}")

asyncio.run(t())
