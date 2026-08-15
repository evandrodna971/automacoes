import time
import json
import hashlib
import requests
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def buscar_ofertas_shopee_reais(appid, secret, limit=5, ignore_list=None, log_func=print):
    """Busca ofertas reais da API Shopee paginando até atingir o limite de produtos únicos"""
    produtos = []
    
    if not appid or not secret or len(secret) != 32:
        log_func("⚠️ Credenciais inválidas")
        return produtos
        
    if ignore_list is None:
        ignore_list = set()
    else:
        ignore_list = set(ignore_list)
        
    page = 1
    max_pages = 10  # Limite de segurança para não entrar em loop infinito
    
    try:
        log_func(f"🛍️ Buscando ofertas Shopee (Meta: {limit}, ignorando {len(ignore_list)} enviados)...")
        
        while len(produtos) < limit and page <= max_pages:
            log_func(f"📡 Buscando página {page} na API Shopee...")
            
            query = f"""{{
  productOfferV2(limit: 20, page: {page}, sortType: 1) {{
    nodes {{
      productName
      price
      ratingStar
      offerLink
      imageUrl
    }}
  }}
}}"""
            
            payload_dict = {"query": query}
            payload_json = json.dumps(payload_dict, separators=(',', ':'))
            
            timestamp, signature = gerar_assinatura(appid, secret, payload_json)
            
            auth_header = f"SHA256 Credential={appid}, Timestamp={timestamp}, Signature={signature}"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": auth_header,
                "User-Agent": "Mozilla/5.0"
            }
            
            response = requests.post(API_URL, headers=headers, data=payload_json, timeout=25, verify=False)
            
            if response.status_code != 200:
                log_func(f"⚠️ Erro HTTP {response.status_code} na página {page}")
                break
            
            resposta = response.json()
            
            # Verificação passo a passo da estrutura
            if "data" not in resposta or "productOfferV2" not in resposta["data"] or "nodes" not in resposta["data"]["productOfferV2"]:
                log_func(f"❌ Resposta inválida da API Shopee na página {page}: {list(resposta.keys()) if isinstance(resposta, dict) else 'Não é objeto'}")
                break
            
            ofertas = resposta["data"]["productOfferV2"]["nodes"]
            if not ofertas:
                log_func(f"ℹ️ Sem mais ofertas retornadas na página {page}")
                break
            
            log_func(f"✅ Página {page} retornou {len(ofertas)} ofertas.")
            
            novos_adicionados = 0
            for i, oferta in enumerate(ofertas):
                produto_processado = processar_oferta_individual(oferta, len(produtos) + 1)
                if produto_processado:
                    titulo = produto_processado["titulo"]
                    if titulo in ignore_list:
                        continue
                    
                    produtos.append(produto_processado)
                    ignore_list.add(titulo) # Evita duplicados dentro da mesma busca
                    novos_adicionados += 1
                    
                    if len(produtos) >= limit:
                        break
            
            log_func(f"📊 Adicionados {novos_adicionados} novos produtos nesta página. Total acumulado: {len(produtos)}/{limit}")
            page += 1
            time.sleep(1) # Intervalo respeitoso entre requisições
            
        log_func(f"✅ Processo de busca concluído com {len(produtos)} produtos.")
        
    except Exception as e:
        log_func(f"❌ Erro geral na API: {str(e)[:100]}")
    
    return produtos[:limit]

def mapear_categoria_shopee(nome_oferta):
    """Mapeia nomes de ofertas da Shopee para tags semânticas em português"""
    nome = (nome_oferta or "").lower()
    tags = []
    
    if any(k in nome for k in ["health", "saude", "suplement"]):
        tags.extend(["saude", "suplementos", "beleza", "cuidados"])
    if any(k in nome for k in ["fashion", "accessories", "moda", "acessorios", "joias"]):
        tags.extend(["moda", "acessorios", "relogios", "oculos"])
    if any(k in nome for k in ["home", "appliance", "kitchen", "casa", "cozinha", "eletro"]):
        tags.extend(["casa", "eletrodomesticos", "cozinha", "utilidades"])
    if any(k in nome for k in ["clothes", "roupa", "vestuario", "shirt", "pant"]):
        tags.extend(["moda", "roupas", "vestuario"])
    if any(k in nome for k in ["shoe", "calcado", "tenis", "sapato", "sandalia"]):
        tags.extend(["moda", "calcados", "tenis", "sapatos"])
    if any(k in nome for k in ["computer", "electronic", "tech", "tecnologia", "celular", "gamer"]):
        tags.extend(["tecnologia", "informatica", "eletronicos", "gamer"])
    if any(k in nome for k in ["beauty", "beleza", "makeup", "perfum"]):
        tags.extend(["beleza", "maquiagem", "perfumes", "estetica"])
    if any(k in nome for k in ["sport", "esporte", "fitness", "academia"]):
        tags.extend(["esporte", "fitness", "academia"])
    if any(k in nome for k in ["baby", "kids", "toy", "brinquedo", "infantil"]):
        tags.extend(["bebe", "infantil", "brinquedos", "criancas"])
    if any(k in nome for k in ["free shipping", "frete gratis", "voucher", "cupom", "bau"]):
        tags.append("geral")
        
    if not tags:
        tags.append("geral")
        
    return ",".join(sorted(list(set(tags))))

def buscar_cupons_shopee_api(appid, secret, limit=20, log_func=print):
    """Busca campanhas de cupons e vouchers oficiais de afiliados na API Shopee GraphQL"""
    cupons = []
    
    if not appid or not secret or len(secret) != 32:
        log_func("⚠️ Credenciais da Shopee ausentes ou inválidas para busca de cupons.")
        return cupons
        
    try:
        log_func("🎟️ Consultando campanhas e cupons de afiliados na Shopee API...")
        query = f"""{{
  shopeeOfferV2(limit: {limit}, page: 1) {{
    nodes {{
      offerName
      offerLink
      imageUrl
      periodStartTime
      periodEndTime
    }}
  }}
}}"""
        payload_dict = {"query": query}
        payload_json = json.dumps(payload_dict, separators=(',', ':'))
        timestamp, signature = gerar_assinatura(appid, secret, payload_json)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"SHA256 Credential={appid}, Timestamp={timestamp}, Signature={signature}",
            "User-Agent": "Mozilla/5.0"
        }
        
        response = requests.post(API_URL, headers=headers, data=payload_json, timeout=20, verify=False)
        if response.status_code != 200:
            log_func(f"⚠️ Erro HTTP {response.status_code} ao buscar cupons na Shopee.")
            return cupons
            
        dados = response.json()
        nodes = dados.get("data", {}).get("shopeeOfferV2", {}).get("nodes", [])
        
        for node in nodes:
            nome = node.get("offerName", "")
            link = node.get("offerLink", "")
            end_timestamp = node.get("periodEndTime", 0)
            
            # Formata data de expiração se timestamp válido
            expires_at = ""
            if end_timestamp and end_timestamp < 30000000000: # Evita timestamps infinitos no futuro distante
                try:
                    expires_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_timestamp))
                except:
                    expires_at = ""
            
            tags = mapear_categoria_shopee(nome)
            
            # Limpa e enxuga o título
            titulo_limpo = re.sub(r'^(New\s+)?(BAU\s+)?(Comm\s*-\s*)?', '', nome, flags=re.IGNORECASE).strip()
            
            cupons.append({
                "code": "CUPOM_SHOPEE",
                "marketplace": "Shopee",
                "title": f"Campanha Shopee: {titulo_limpo}",
                "discount_text": "Cupom & Oferta Oficial Shopee",
                "min_value": 0.0,
                "category_tags": tags,
                "link": link,
                "expires_at": expires_at
            })
            
        log_func(f"✅ {len(cupons)} campanhas/cupons de afiliados Shopee carregados com sucesso.")
    except Exception as e:
        log_func(f"❌ Erro ao buscar cupons Shopee via API: {e}")
        
    return cupons

