import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

def buscar_ofertas_ml_reais(termo="ofertas", tag_afiliado="", limit=5, ignore_list=None, log_func=print):
    """
    Busca ofertas reais da página oficial de ofertas do Mercado Livre Brasil.
    Retorna uma lista de dicionários padronizada com o atributo "fonte": "Mercado Livre".
    """
    produtos = []
    
    if ignore_list is None:
        ignore_list = set()
    else:
        ignore_list = set(ignore_list)

    def safe_log(msg):
        try:
            log_func(msg)
        except Exception:
            try:
                clean_msg = msg.encode('ascii', errors='ignore').decode('ascii')
                log_func(clean_msg)
            except Exception:
                pass

    try:
        if termo and termo.strip() and termo.strip().lower() != "ofertas":
            url = f"https://www.mercadolivre.com.br/ofertas?q={urllib.parse.quote(termo.strip())}"
        else:
            url = "https://www.mercadolivre.com.br/ofertas"

        safe_log(f"[Mercado Livre] Buscando ofertas (Termo: '{termo}', Meta: {limit})...")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            safe_log(f"[Mercado Livre] Status HTTP {response.status_code} na busca de ofertas.")
            return produtos

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select(".promotion-item, .poly-card, .ui-search-result, li.ui-search-layout__item")
        safe_log(f"[Mercado Livre] Encontrados {len(items)} itens em destaque.")

        for item in items:
            if len(produtos) >= limit:
                break
                
            # Extrai título
            title_el = item.select_one(".promotion-item__title, .poly-component__title, p.poly-box, a.poly-component__title")
            titulo_raw = title_el.get_text(strip=True) if title_el else ""
            
            if not titulo_raw:
                img_el = item.select_one("img")
                if img_el and img_el.get("alt"):
                    titulo_raw = img_el.get("alt")

            if not titulo_raw:
                continue

            # Limpa o título
            titulo_limpo = re.sub(r'[^\w\s\-\.,!?]', '', str(titulo_raw)).strip()
            
            # Verifica se já foi enviado
            if titulo_limpo in ignore_list or titulo_raw in ignore_list:
                continue

            # Extrai Preço
            price_el = item.select_one(".andes-money-amount__fraction, .promotion-item__price")
            preco_str = price_el.get_text(strip=True) if price_el else "0"
            preco_str = re.sub(r'[^\d]', '', preco_str)
            try:
                preco_num = float(preco_str)
            except:
                preco_num = 0.0

            # Extrai Link
            link_el = item.select_one("a.promotion-item__link-container, a.poly-component__title, a")
            permalink = link_el["href"] if link_el and link_el.has_attr("href") else ""
            if not permalink:
                continue
                
            # Corta parâmetros de rastreamento pesados do link original
            permalink_clean = permalink.split("#")[0]

            # Anexa Tag de Afiliado se fornecida
            link_afiliado = permalink_clean
            if tag_afiliado and tag_afiliado.strip():
                tag_clean = tag_afiliado.strip()
                sep = "&" if "?" in link_afiliado else "?"
                link_afiliado += f"{sep}matt_tool={tag_clean}"

            # Extrai Imagem
            img_el = item.select_one("img")
            imagem_url = ""
            if img_el:
                imagem_url = img_el.get("data-src") or img_el.get("src") or ""
                # Garantir boa resolução
                if imagem_url and "-I.jpg" in imagem_url:
                    imagem_url = imagem_url.replace("-I.jpg", "-O.jpg")
                if imagem_url and not imagem_url.startswith("http"):
                    imagem_url = "https:" + imagem_url

            produtos.append({
                "titulo": titulo_limpo,
                "preco": f"{preco_num:.2f}",
                "avaliacao": "4.8",
                "link": link_afiliado,
                "afiliado": link_afiliado,
                "fonte": "Mercado Livre",
                "imagem_url": imagem_url
            })

        safe_log(f"[Mercado Livre] Sucesso: {len(produtos)} produtos válidos extraídos.")

    except Exception as e:
        safe_log(f"[Mercado Livre] Erro ao buscar ofertas: {e}")

    return produtos


if __name__ == "__main__":
    def test_log(msg):
        print(f"[TEST] {msg}")

    print("Testando busca no Mercado Livre...")
    prods = buscar_ofertas_ml_reais("fone", tag_afiliado="123456", limit=3, log_func=test_log)
    for p in prods:
        print(f"-> {p['fonte']} | {p['titulo'][:40]} | R$ {p['preco']} | {p['link'][:60]}")
