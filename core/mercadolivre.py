import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def encurtar_link_ml(url):
    """
    Limpa e encurta URLs do Mercado Livre removendo o texto do título (slug) e filtros desnecessários,
    preservando apenas a estrutura enxuta do produto com seu ID único (MLB).
    """
    if not url:
        return ""
        
    # Remove fragmentos (#...)
    clean_url = url.split('#')[0]
    
    # Padrão 1: Produto de Catálogo (/p/MLB12345678)
    match_p = re.search(r'(/p/MLB\d+)', clean_url)
    if match_p:
        return f"https://www.mercadolivre.com.br{match_p.group(1)}"
        
    # Padrão 2: Anúncio Individual (MLB-1234567890 ou MLB1234567890)
    match_mlb = re.search(r'(MLB-?\d+)', clean_url)
    if match_mlb:
        mlb_id = match_mlb.group(1)
        if not mlb_id.startswith("MLB-"):
            mlb_id = mlb_id.replace("MLB", "MLB-")
        return f"https://produto.mercadolivre.com.br/{mlb_id}"
        
    # Fallback: remove query parameters (?...)
    return clean_url.split('?')[0]


def buscar_ofertas_ml_reais(termo="ofertas", tag_afiliado="", matt_word="", limit=5, ignore_list=None, log_func=print):
    """
    Busca ofertas reais da página oficial de ofertas do Mercado Livre Brasil.
    Retorna uma lista de dicionários padronizada com o atributo "fonte": "Mercado Livre".
    Anexa os parâmetros de rastreamento matt_tool e matt_word do programa de afiliados/criadores ML em URLs curtas.
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
        
        response = requests.get(url, headers=headers, timeout=15, verify=False)
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

            # 1. Extrai Preço Anterior (De:) se houver
            prev_box = item.select_one('.poly-price__labels s, s.andes-money-amount--previous, .promotion-item__old-price')
            preco_original_str = ""
            if prev_box:
                frac = prev_box.select_one('.andes-money-amount__fraction')
                cents = prev_box.select_one('.andes-money-amount__cents')
                if frac:
                    f_txt = re.sub(r'[^\d]', '', frac.get_text(strip=True))
                    c_txt = re.sub(r'[^\d]', '', cents.get_text(strip=True)) if cents else "00"
                    try:
                        preco_orig_num = float(f"{f_txt}.{c_txt}")
                        preco_original_str = f"{preco_orig_num:.2f}"
                    except:
                        preco_original_str = ""

            # 2. Extrai Preço Atual Promocional (Por:)
            curr_box = item.select_one('.poly-price__current, .promotion-item__price')
            preco_atual_num = 0.0
            if curr_box:
                frac = curr_box.select_one('.andes-money-amount__fraction')
                cents = curr_box.select_one('.andes-money-amount__cents')
                if frac:
                    f_txt = re.sub(r'[^\d]', '', frac.get_text(strip=True))
                    c_txt = re.sub(r'[^\d]', '', cents.get_text(strip=True)) if cents else "00"
                    try:
                        preco_atual_num = float(f"{f_txt}.{c_txt}")
                    except:
                        preco_atual_num = 0.0
            else:
                # Fallback se a estrutura for diferente
                price_el = item.select_one(".andes-money-amount__fraction")
                if price_el:
                    try:
                        preco_atual_num = float(re.sub(r'[^\d]', '', price_el.get_text(strip=True)))
                    except:
                        preco_atual_num = 0.0

            # 3. Extrai Desconto Percentual (% OFF)
            disc_el = item.select_one('.poly-price__discount-polylabel, .polylabel-pill, .andes-money-amount__discount, .promotion-item__discount')
            desconto_txt = disc_el.get_text(strip=True) if disc_el else ""

            # Extrai e Encurta o Link
            link_el = item.select_one("a.promotion-item__link-container, a.poly-component__title, a")
            permalink = link_el["href"] if link_el and link_el.has_attr("href") else ""
            if not permalink:
                continue
                
            # Encurta a URL base do produto
            permalink_curto = encurtar_link_ml(permalink)

            # Anexa Parâmetros de Afiliado (matt_tool e matt_word)
            link_afiliado = permalink_curto
            tracking_params = []
            
            if tag_afiliado and str(tag_afiliado).strip():
                tracking_params.append(f"matt_tool={str(tag_afiliado).strip()}")
            if matt_word and str(matt_word).strip():
                tracking_params.append(f"matt_word={str(matt_word).strip()}")
                
            if tracking_params:
                sep = "&" if "?" in link_afiliado else "?"
                link_afiliado += f"{sep}" + "&".join(tracking_params)

            # Extrai Imagem em alta resolução
            img_el = item.select_one("img")
            imagem_url = ""
            if img_el:
                imagem_url = img_el.get("data-src") or img_el.get("src") or ""
                if imagem_url and "-I.jpg" in imagem_url:
                    imagem_url = imagem_url.replace("-I.jpg", "-O.jpg")
                if imagem_url and not imagem_url.startswith("http"):
                    imagem_url = "https:" + imagem_url

            # Extrai tag de Cupom no Card do Mercado Livre se houver
            coupon_el = item.select_one(".poly-component__coupons, .poly-coupons__wrapper, .poly-coupons__pill, [class*='coupon']")
            cupom_tag = coupon_el.get_text(strip=True) if coupon_el else ""

            produtos.append({
                "titulo": titulo_limpo,
                "preco": f"{preco_atual_num:.2f}",
                "preco_original": preco_original_str,
                "desconto_pct": desconto_txt,
                "avaliacao": "4.8",
                "link": link_afiliado,
                "afiliado": link_afiliado,
                "fonte": "Mercado Livre",
                "imagem_url": imagem_url,
                "cupom_tag": cupom_tag
            })

        safe_log(f"[Mercado Livre] Sucesso: {len(produtos)} produtos válidos extraídos.")

    except Exception as e:
        safe_log(f"[Mercado Livre] Erro ao buscar ofertas: {e}")


    return produtos


def mapear_categoria_ml(texto_cupom):
    """Mapeia o texto ou descrição do cupom do ML para tags semânticas"""
    txt = (texto_cupom or "").lower()
    tags = []
    
    if any(k in txt for k in ["celular", "smartphone", "notebook", "fone", "tech", "tecnologia", "informatica", "gamer", "tv", "audio"]):
        tags.extend(["tecnologia", "informatica", "eletronicos", "gamer"])
    if any(k in txt for k in ["eletro", "geladeira", "fogao", "microondas", "lavadora", "cozinha", "casa"]):
        tags.extend(["casa", "eletrodomesticos", "cozinha", "utilidades"])
    if any(k in txt for k in ["moda", "roupa", "tenis", "calcado", "vestuario", "acessorios"]):
        tags.extend(["moda", "calcados", "roupas", "acessorios"])
    if any(k in txt for k in ["beleza", "perfum", "cabelo", "maquiagem", "saude", "suplement"]):
        tags.extend(["beleza", "perfumes", "saude", "suplementos"])
    if any(k in txt for k in ["ferramenta", "construcao", "furadeira", "automotivo", "pneu"]):
        tags.extend(["ferramentas", "automotivo", "construcao"])
    if any(k in txt for k in ["livro", "papelaria", "escritorio"]):
        tags.extend(["livros", "papelaria"])
    if any(k in txt for k in ["primeira compra", "site todo", "geral", "frete", "todos os produtos"]):
        tags.append("geral")
        
    if not tags:
        tags.append("geral")
        
    return ",".join(sorted(list(set(tags))))


def buscar_cupons_ml_central(tag_afiliado="", matt_word="", log_func=print):
    """Busca cupons e destaques promocionais vigentes no Mercado Livre"""
    cupons = []
    
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
        safe_log("[Mercado Livre] Consultando página de ofertas e cupons do Mercado Livre...")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
        
        url_ofertas = "https://www.mercadolivre.com.br/ofertas"
        resp = requests.get(url_ofertas, headers=headers, timeout=15, verify=False)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # 1. Procura cupons em pílulas e banners de cupons
            pills = soup.select(".poly-component__coupons, .poly-coupons__wrapper, .poly-coupons__pill, [class*='coupon']")
            vistos = set()
            
            for p in pills:
                txt = p.get_text(strip=True)
                if not txt or txt in vistos or len(txt) > 80:
                    continue
                vistos.add(txt)
                
                # Extrai valor de desconto se presente (ex: R$30OFF ou 15%OFF)
                desc_match = re.search(r'(R\$\s*\d+|\d+%)', txt, re.IGNORECASE)
                desc_val = desc_match.group(1) if desc_match else "Desconto Especial"
                
                # Extrai valor mínimo se presente
                min_match = re.search(r'acima de R\$\s*(\d+)', txt, re.IGNORECASE)
                min_val = float(min_match.group(1)) if min_match else 0.0
                
                tags = mapear_categoria_ml(txt)
                
                # Gera link com afiliado se fornecido
                link_cupom = "https://www.mercadolivre.com.br/ofertas"
                if tag_afiliado or matt_word:
                    tracking = []
                    if tag_afiliado:
                        tracking.append(f"matt_tool={tag_afiliado}")
                    if matt_word:
                        tracking.append(f"matt_word={matt_word}")
                    link_cupom += "?" + "&".join(tracking)
                    
                cupons.append({
                    "code": f"ML_{desc_val.replace(' ', '').replace('$', '')}",
                    "marketplace": "Mercado Livre",
                    "title": f"Cupom Mercado Livre: {txt}",
                    "discount_text": txt,
                    "min_value": min_val,
                    "category_tags": tags,
                    "link": link_cupom,
                    "expires_at": ""
                })
                
        safe_log(f"[Mercado Livre] {len(cupons)} cupons/destaques promocionais identificados.")
    except Exception as e:
        safe_log(f"[Mercado Livre] Erro ao extrair cupons: {e}")
        
    return cupons


if __name__ == "__main__":
    def test_log(msg):
        print(f"[TEST] {msg}")

    print("Testando encurtamento de links e busca no Mercado Livre...")
    prods = buscar_ofertas_ml_reais("fone", tag_afiliado="38835395", matt_word="joicemagalhes", limit=3, log_func=test_log)
    for p in prods:
        print(f"-> {p['fonte']} | {p['titulo'][:30]} | R$ {p['preco']}")
        print(f"   Link Encurtado: {p['link']}")
