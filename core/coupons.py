import re
from datetime import datetime
from database.db import salvar_cupons, obter_cupons_validos, limpar_cupons_expirados
from core.shopee import buscar_cupons_shopee_api
from core.mercadolivre import buscar_cupons_ml_central

# Dicionário de taxonomias e palavras-chave para correspondência semântica de nicho
TAXONOMIA_NICHOS = {
    "tecnologia": [
        "celular", "smartphone", "iphone", "samsung", "xiaomi", "redmi", "motorola",
        "fone", "headphone", "headset", "bluetooth", "tws", "earphone", "airpods",
        "notebook", "laptop", "computador", "pc", "gamer", "teclado", "mouse", "pad",
        "monitor", "gabinete", "placa", "ssd", "ram", "memoria", "hd", "pendrive",
        "cabo", "carregador", "powerbank", "usb", "tipo-c", "adaptador", "fonte",
        "smartwatch", "smartband", "relogio inteligente", "tablet", "ipad", "kindle",
        "camera", "webcam", "microfone", "caixa de som", "alexa", "echo", "tv", "smart tv"
    ],
    "moda": [
        "calca", "calça", "jeans", "camisa", "camiseta", "regata", "blusa", "cropped",
        "vestido", "saia", "shorts", "bermuda", "jaqueta", "casaco", "moletom", "sueter",
        "tenis", "tênis", "sapato", "sandalia", "sandália", "chinelo", "bota", "salto",
        "bolsa", "mochila", "carteira", "cinto", "bone", "boné", "chapeu", "oculos",
        "relogio", "relógio", "cueca", "calcinha", "sutia", "sutiã", "meia", "pijama"
    ],
    "casa": [
        "panela", "frigideira", "airfryer", "fritadeira", "liquidificador", "batedeira",
        "aspirador", "vassoura", "mop", "microondas", "fogao", "geladeira", "cafeteira",
        "copo", "prato", "talher", "faca", "garrafa", "termica", "pote", "organizador",
        "lencol", "lençol", "travesseiro", "cobertor", "edredom", "toalha", "cortina",
        "tapete", "almofada", "sofa", "sofá", "mesa", "cadeira", "estante", "lampada", "luminaria"
    ],
    "beleza": [
        "perfume", "colonia", "batom", "maquiagem", "base", "corretivo", "rimel",
        "shampoo", "condicionador", "mascara capilar", "hidratante", "creme", "serum",
        "protetor solar", "anti-idade", "secador", "chapinha", "babyliss", "barbeador",
        "depilador", "esmalte", "unha", "skincare", "sabonete facial", "oleo corporal"
    ],
    "saude": [
        "suplemento", "creatina", "whey", "protein", "bcaa", "glutamina", "vitamina",
        "omega 3", "termogenico", "pre treino", "pre-treino", "colageno", "magnesio"
    ],
    "ferramentas": [
        "furadeira", "parafusadeira", "martelete", "esmerilhadeira", "serra", "trena",
        "alicate", "chave", "jogo de ferramentas", "maleta", "solda", "compressor",
        "pneu", "oleo motor", "automotivo", "som automotivo", "palheta"
    ]
}


class SmartCouponMatcher:
    """Motor de correspondência e validação estrita de cupons para produtos"""

    @staticmethod
    def normalizar_texto(texto):
        if not texto:
            return ""
        import unicodedata
        # Remove acentos
        nfkd = unicodedata.normalize('NFKD', texto.lower())
        sem_acento = u"".join([c for c in nfkd if not unicodedata.combining(c)])
        return re.sub(r'[^\w\s]', ' ', sem_acento)

    @classmethod
    def detectar_categorias_produto(cls, titulo_produto):
        """Identifica os nichos semânticos do produto com base no título, suportando plural e singular"""
        texto_norm = cls.normalizar_texto(titulo_produto)
        categorias = set()

        for categoria, palavras in TAXONOMIA_NICHOS.items():
            for kw in palavras:
                kw_norm = cls.normalizar_texto(kw).strip()
                if not kw_norm:
                    continue
                # Suporta palavras compostas e plurais comuns (s, es)
                padrao = rf"\b{re.escape(kw_norm)}(?:s|es)?\b"
                if re.search(padrao, texto_norm):
                    categorias.add(categoria)
                    break

        return categorias


    @classmethod
    def validar_cupom_para_produto(cls, cupom, produto):
        """
        Valida rigorosamente se um cupom pode ser associado a determinado produto.
        Retorna (True, motivo) ou (False, motivo).
        """
        # 1. Validação de Marketplace
        fonte_prod = produto.get("fonte", "")
        mkt_cupom = cupom.get("marketplace", "")
        if fonte_prod and mkt_cupom and fonte_prod.lower() != mkt_cupom.lower():
            return False, "Marketplace divergente"

        # 2. Validação de Data/Hora de Expiração
        expires_at = cupom.get("expires_at", "")
        if expires_at:
            try:
                dt_exp = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
                if dt_exp < datetime.now():
                    return False, "Cupom expirado"
            except:
                pass

        # 3. Validação de Preço Mínimo
        try:
            preco_prod = float(produto.get("preco", 0.0))
        except:
            preco_prod = 0.0

        min_val = float(cupom.get("min_value", 0.0))
        if min_val > 0 and preco_prod < min_val:
            return False, f"Preço do produto (R$ {preco_prod:.2f}) abaixo do mínimo exigido (R$ {min_val:.2f})"

        # 4. Validação Estrita de Nicho/Categoria
        tags_cupom_raw = cupom.get("category_tags", "geral").lower()
        tags_cupom = [t.strip() for t in tags_cupom_raw.split(",") if t.strip()]

        # Se for cupom geral (válido em todo o site), permite qualquer produto que atenda ao valor
        if "geral" in tags_cupom:
            return True, "Cupom geral válido"

        # Se o cupom é restrito a categorias específicas:
        categorias_produto = cls.detectar_categorias_produto(produto.get("titulo", ""))
        
        # Verifica se há interseção de categorias
        intersecao = set(tags_cupom).intersection(categorias_produto)
        if not intersecao:
            return False, f"Nicho incompatível (Cupom: {tags_cupom}, Produto: {list(categorias_produto)})"

        return True, "Cupom estritamente compatível"

    @classmethod
    def match(cls, produto, cupons_disponiveis=None):
        """
        Encontra o melhor cupom compatível para o produto.
        Retorna o dicionário do cupom ou None.
        """
        # Se o produto já possui uma tag de cupom direta do card (ex: Mercado Livre)
        cupom_tag_direta = produto.get("cupom_tag", "")
        if cupom_tag_direta:
            return {
                "code": "CUPOM_NO_ANUNCIO",
                "marketplace": produto.get("fonte", "Mercado Livre"),
                "title": cupom_tag_direta,
                "discount_text": cupom_tag_direta,
                "min_value": 0.0,
                "category_tags": "geral",
                "link": produto.get("link", ""),
                "expires_at": ""
            }

        # Consulta cupons disponíveis
        if cupons_disponiveis is None:
            cupons_disponiveis = obter_cupons_validos(marketplace=produto.get("fonte"))

        if not cupons_disponiveis:
            return None

        # Avalia cada cupom
        candidatos = []
        for cupom in cupons_disponiveis:
            valido, motivo = cls.validar_cupom_para_produto(cupom, produto)
            if valido:
                candidatos.append(cupom)

        if not candidatos:
            return None

        # Prioriza cupom específico de categoria sobre cupom genérico
        def score_cupom(c):
            tags = c.get("category_tags", "").lower()
            is_generic = "geral" in tags
            return 0 if is_generic else 1

        candidatos.sort(key=score_cupom, reverse=True)
        return candidatos[0]


def sincronizar_todos_os_cupons(appid="", secret="", tag_ml="", matt_word="", log_func=print):
    """
    Sincroniza cupons de todas as plataformas conectadas (API Shopee + Mercado Livre),
    armazena no banco e remove expirados.
    """
    log_func("🔄 Iniciando sincronização centralizada de cupons...")
    todos_cupons = []

    # 1. Shopee (via API Oficial)
    if appid and secret:
        try:
            cupons_shopee = buscar_cupons_shopee_api(appid, secret, log_func=log_func)
            todos_cupons.extend(cupons_shopee)
        except Exception as e:
            log_func(f"⚠️ Erro ao sincronizar cupons Shopee: {e}")
    else:
        log_func("ℹ️ Credenciais Shopee ausentes. Pulando busca de cupons Shopee API.")

    # 2. Mercado Livre
    try:
        cupons_ml = buscar_cupons_ml_central(tag_afiliado=tag_ml, matt_word=matt_word, log_func=log_func)
        todos_cupons.extend(cupons_ml)
    except Exception as e:
        log_func(f"⚠️ Erro ao sincronizar cupons Mercado Livre: {e}")

    # 3. Salvar no banco
    if todos_cupons:
        total_salvos = salvar_cupons(todos_cupons)
        log_func(f"💾 {total_salvos} cupons registrados/atualizados no banco de dados.")
    else:
        log_func("ℹ️ Nenhum novo cupom identificado nesta varredura.")

    # 4. Limpar expirados
    removidos = limpar_cupons_expirados()
    if removidos > 0:
        log_func(f"🧹 {removidos} cupons expirados foram removidos do histórico ativo.")

    cupons_ativos = obter_cupons_validos()
    log_func(f"✅ Sincronização concluída. Total de cupons ativos disponíveis: {len(cupons_ativos)}.")
    return cupons_ativos
