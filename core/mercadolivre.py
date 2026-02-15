import requests
import re

def buscar_ofertas_ml(links, limit=5):
    """Busca ofertas Mercado Livre"""
    produtos = []
    
    # Se links for uma string única (não lista), converte
    if isinstance(links, str):
        links = [links]
    
    for i, link in enumerate(links[:limit]):
        if not link or not link.strip():
            continue
        
        try:
            print(f"📡 Processando: {link[:50]}...")
            
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(link, headers=headers, timeout=20)
            
            if response.status_code == 200:
                html = response.text
                
                # Extrai título
                titulo = "Produto Mercado Livre"
                titulo_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE)
                if titulo_match:
                    titulo = titulo_match.group(1)
                    titulo = titulo.split('|')[0].split('-')[0].strip()
                    titulo = re.sub(r'\s+', ' ', titulo)
                    titulo = re.sub(r'[^\w\s\-\.,!?]', '', titulo)  # Não cortamos
                
                # Extrai preço
                preco = 99.99
                padroes_preco = [
                    r'"price":\s*"(\d+\.?\d*)"',
                    r'"price":\s*(\d+\.?\d*)',
                    r'R\$\s*[\d\.]+,\d+',
                ]
                
                for padrao in padroes_preco:
                    match = re.search(padrao, html)
                    if match:
                        try:
                            preco_text = match.group(1) if match.groups() else match.group(0)
                            preco_text = re.sub(r'[^\d,]', '', preco_text)
                            preco = float(preco_text.replace(',', '.'))
                            break
                        except:
                            continue
                
                # Tenta extrair imagem
                imagem_url = ""
                padroes_imagem = [
                    r'"picture":"([^"]+)"',
                    r'data-src="([^"]+)"',
                    r'src="([^"]+\.(jpg|jpeg|png|gif))"',
                ]
                
                for padrao in padroes_imagem:
                    match = re.search(padrao, html)
                    if match:
                        imagem_url = match.group(1)
                        if not imagem_url.startswith('http'):
                            imagem_url = "https:" + imagem_url
                        break
                
                produtos.append({
                    "titulo": titulo,
                    "preco": f"{preco:.2f}",
                    "avaliacao": "4.5",
                    "link": link,
                    "afiliado": link,
                    "fonte": "Mercado Livre",
                    "imagem_url": imagem_url
                })
                
                print(f"   ✅ {titulo[:40]}... - R$ {preco:.2f}")
            else:
                print(f"   ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Erro: {e}")
    
    return produtos
