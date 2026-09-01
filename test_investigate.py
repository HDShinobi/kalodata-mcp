import asyncio, os, json
from dotenv import load_dotenv
load_dotenv()
import sys
sys.path.insert(0, os.path.dirname(__file__))
from server import call_kalodata

base = {'region': 'US', 'language': 'en-US', 'currency': 'USD', 'date_range': 'last7Day'}
sort = {'field': 'revenue', 'type': 'DESC'}

async def t():
    # 1. Investigar paths alternativos para criadores
    print("=" * 55)
    print("  1. Testando variações do endpoint de criadores")
    print("=" * 55)
    creator_paths = [
        '/openapi/v1/crator/rank',
        '/openapi/v1/creator/rank',
        '/openapi/v1/creators/rank',
        '/openapi/v1/influencer/rank',
        '/openapi/v1/influencer/list',
        '/openapi/v2/crator/rank',
        '/openapi/v1/anchor/rank',
    ]
    for p in creator_paths:
        r = await call_kalodata(p, {**base, 'sort_field': sort, 'page_number': 1})
        status = r.get('status_code', 'OK') if r.get('error') else f"success={r.get('success')} code={r.get('code')}"
        print(f"  {p} -> {status}")
        if not r.get('error') and r.get('success'):
            print(f"    >>> FUNCIONA! data={list(r.get('data', [{}])[0].keys()) if r.get('data') else 'vazio'}")

    # 2. Pegar IDs reais do ranking de produtos
    print("\n" + "=" * 55)
    print("  2. Pegando ID real de produto do ranking")
    print("=" * 55)
    r = await call_kalodata('/openapi/v1/product/rank', {**base, 'sort_field': sort, 'page_number': 1})
    if r.get('success') and r.get('data'):
        prod_id = r['data'][0]['product_id']
        prod_name = r['data'][0].get('product_name', '')
        print(f"  Produto #1: ID={prod_id} Nome={prod_name[:60]}")
        
        # Testar product_detail com ID real
        r2 = await call_kalodata('/openapi/v1/product/detail', {**base, 'product_id': prod_id})
        print(f"  product_detail({prod_id}): success={r2.get('success')} msg={r2.get('message')}")
        if r2.get('success') and r2.get('data'):
            print(f"  Chaves: {list(r2['data'].keys())[:10]}")

    # 3. Pegar IDs reais do ranking de videos
    print("\n" + "=" * 55)
    print("  3. Pegando ID real de video do ranking")
    print("=" * 55)
    r = await call_kalodata('/openapi/v1/video/rank', {**base, 'sort_field': sort, 'page_number': 1})
    if r.get('success') and r.get('data'):
        vid_id = r['data'][0]['video_id']
        vid_title = r['data'][0].get('video_title', '')
        print(f"  Video #1: ID={vid_id} Titulo={vid_title[:60]}")
        
        # Testar video_detail com ID real
        r2 = await call_kalodata('/openapi/v1/video/detail', {**base, 'video_id': vid_id})
        print(f"  video_detail({vid_id}): success={r2.get('success')} msg={r2.get('message')}")
        if r2.get('success') and r2.get('data'):
            print(f"  Chaves: {list(r2['data'].keys())[:10]}")
    
    # 4. Pegar creator_id do ranking de videos e testar detail
    print("\n" + "=" * 55)
    print("  4. Testando creator_id extraido de video")
    print("=" * 55)
    r = await call_kalodata('/openapi/v1/video/rank', {**base, 'sort_field': sort, 'page_number': 1})
    if r.get('success') and r.get('data'):
        creator_id = r['data'][0].get('belonged_creator_id')
        print(f"  Creator ID do video #1: {creator_id}")
        
        for p in ['/openapi/v1/crator/detail', '/openapi/v1/creator/detail']:
            r2 = await call_kalodata(p, {**base, 'creator_id': creator_id})
            status = r2.get('status_code', 'OK') if r2.get('error') else f"success={r2.get('success')} msg={r2.get('message')}"
            print(f"  {p}: {status}")
            if not r2.get('error') and r2.get('success'):
                print(f"    >>> FUNCIONA! Chaves: {list(r2.get('data', {}).keys())[:10]}")

asyncio.run(t())
