import asyncio
import json
import os
from dotenv import load_dotenv

# Garantir que as variáveis de ambiente sejam carregadas do .env local
load_dotenv()

from server import call_kalodata

async def main():
    print("==================================================")
    print("  Teste de Conexão Local - Kalodata Open API")
    print("==================================================")
    
    secret_key = os.getenv("KALODATA_SECRET_KEY")
    base_url = os.getenv("KALODATA_BASE_URL", "https://staging.kalodata.com")
    
    print(f"Base URL: {base_url}")
    print(f"Secret Key: {secret_key[:6]}...{secret_key[-4:] if secret_key else 'NÃO DEFINIDA'}\n")
    
    if not secret_key:
        print("[ERRO] KALODATA_SECRET_KEY não encontrada no arquivo .env!")
        return

    # Payload de teste para o endpoint de ranking de categorias
    payload = {
        "region": "US",
        "language": "en-US",
        "currency": "USD",
        "date_range": "last7Day",
        "sort_field": {
            "field": "revenue",
            "type": "DESC"
        },
        "page_number": 1
    }
    
    endpoint = "/openapi/v1/category/rank"
    print(f"Enviando requisição POST para: {base_url}{endpoint}")
    print(f"Payload: {json.dumps(payload, indent=2)}\n")
    
    resposta = await call_kalodata(endpoint, payload)
    
    print("---------------- Resposta da API ----------------")
    print(json.dumps(resposta, indent=2, ensure_ascii=False))
    print("-------------------------------------------------")
    
    if resposta.get("error"):
        print("\n[FALHA HTTP] A requisição retornou um erro HTTP ou de rede.")
    elif resposta.get("success") is False:
        print(f"\n[RETORNO KALODATA] A API respondeu com código {resposta.get('code')}: {resposta.get('message')}")
        print("DICA: Se a resposta for 'The key is not allowed', verifique se sua chave é de Produção (ajuste KALODATA_BASE_URL no .env para o host informado no e-mail de ativação da Kalodata).")
    else:
        print("\n[SUCESSO] Conexão e autenticação com a Kalodata Open API validadas com sucesso!")

if __name__ == "__main__":
    asyncio.run(main())
