import time
import json
import hashlib
import requests
import re

API_URL = "https://open-api.affiliate.shopee.com.br/graphql"

def gerar_assinatura(appid, secret, payload_json):
    """Gera assinatura SHA256 conforme documentação"""
    timestamp = str(int(time.time()))
    fator = appid + timestamp + payload_json + secret
    signature = hashlib.sha256(fator.encode('utf-8')).hexdigest()
    return timestamp, signature

def processar_oferta_individual(oferta, indice):
    """Processa uma oferta individual com tratamento robusto de erros"""
    try:
        # Extrai dados COM VALORES PADRÃO
        nome = oferta.get("productName", f"Produto {indice}")
        preco_str = oferta.get("price", "0")
        rating_str = oferta.get("ratingStar", "4.5")
        link = oferta.get("offerLink", "")
        imagem_url = oferta.get("imageUrl", "")
        
        # Converte preço
        try:
            preco = float(preco_str)
        except:
            preco = 99.99
        
        # Converte rating
        try:
            rating = float(rating_str)
        except:
            rating = 4.5
        
        # Limpa nome (SEM CORTAR)
        nome_limpo = re.sub(r'[^\w\s\-\.,!?]', '', str(nome))
        
        return {
            "titulo": nome_limpo,
            "preco": f"{preco:.2f}",
            "avaliacao": f"{rating:.1f}",
            "link": link if link else "https://shopee.com.br",
            "afiliado": link if link else "https://shopee.com.br",
            "fonte": "Shopee",
            "imagem_url": imagem_url
        }
        
    except Exception as e:
        print(f"   ⚠️ Erro no produto {indice}: {str(e)[:80]}")
        return None

def buscar_ofertas_shopee_reais(appid, secret, limit=5):
    """Busca ofertas reais da API Shopee"""
    produtos = []
    
    if not appid or not secret or len(secret) != 32:
        print("⚠️ Credenciais inválidas")
        return produtos
    
    try:
        print(f"\n🛍️  Buscando ofertas na API Shopee (Limit: {limit})...")
        
        query = """{
  productOfferV2(limit: 10) {
    nodes {
      productName
      price
      ratingStar
      offerLink
      imageUrl
    }
  }
}"""
        
        payload_dict = {"query": query}
        payload_json = json.dumps(payload_dict, separators=(',', ':'))
        
        timestamp, signature = gerar_assinatura(appid, secret, payload_json)
        
        auth_header = f"SHA256 Credential={appid}, Timestamp={timestamp}, Signature={signature}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": auth_header,
            "User-Agent": "Mozilla/5.0"
        }
        
        print(f"Requesting {API_URL}...")
        response = requests.post(API_URL, headers=headers, data=payload_json, timeout=25)
        
        if response.status_code != 200:
            print(f"⚠️ HTTP {response.status_code} da API")
            return produtos
        
        resposta = response.json()
        
        # Verificação passo a passo da estrutura
        if "data" not in resposta:
            print("❌ Resposta não contém 'data'")
            return produtos
            
        if "productOfferV2" not in resposta["data"]:
            print("❌ Resposta não contém 'productOfferV2'")
            return produtos
            
        if "nodes" not in resposta["data"]["productOfferV2"]:
            print("❌ Resposta não contém 'nodes'")
            return produtos
        
        ofertas = resposta["data"]["productOfferV2"]["nodes"]
        
        print(f"✅ API retornou {len(ofertas)} ofertas!")
        
        for i, oferta in enumerate(ofertas[:limit]):
            produto_processado = processar_oferta_individual(oferta, i+1)
            if produto_processado:
                produtos.append(produto_processado)
        
        print(f"✅ {len(produtos)} produtos processados com sucesso")
        
    except Exception as e:
        print(f"❌ Erro geral na API: {str(e)[:100]}")
    
    return produtos
