import os
import re
import requests
import json
from core.utils import formatar_mensagem_produto, limpar_titulo_inteligente

class GeminiCopywriter:
    """
    Motor de Inteligência Artificial para geração de copys persuasivas de vendas
    e mensagens de engajamento utilizando a API do Google Gemini com fallback resiliente.
    """

    MODELOS_DISPONIVEIS = [
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite-preview",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.7-flash"
    ]

    @classmethod
    def gerar_copy_produto(cls, produto, cupom=None, tom="achadinho", api_key="", log_func=print):
        """
        Gera uma mensagem de WhatsApp persuasiva para o produto usando o Gemini.
        Se a API Key não for fornecida ou falhar, recorre instantaneamente ao fallback padrão.
        """
        api_key_clean = (api_key or "").strip()
        
        # Se tom for desativado ou chave não informada, usa fallback direto
        if tom == "desativado" or not api_key_clean:
            return formatar_mensagem_produto(produto, cupom)

        titulo_original = limpar_titulo_inteligente(produto.get("titulo", ""))
        fonte = produto.get("fonte", "Oferta")
        preco_atual = produto.get("preco", "0.00")
        preco_orig = produto.get("preco_original", "")
        desconto_pct = produto.get("desconto_pct", "")
        link = produto.get("link", "")
        
        info_cupom = ""
        if cupom:
            code = (cupom.get("code") or "").strip().upper()
            if code and code not in ["CUPOM_SHOPEE", "CUPOM_NO_ANUNCIO"] and not code.startswith("ML_"):
                desc_cupom = cupom.get("discount_text") or cupom.get("title", "")
                info_cupom = f"CUPOM DIGITÁVEL NO CARRINHO: {code} ({desc_cupom})"

        instrucao_tom = {
            "achadinho": "Crie um post amigável, entusiasmado e acolhedor de grupo de achadinhos/descontos. Destaque que é uma super oportunidade.",
            "urgencia": "Crie um post com tom de alerta de oferta relâmpago, imperdível, estilo 'Corre antes que acabe o estoque ou mude o preço'.",
            "direto": "Crie um post direto, profissional, destacando os 2 principais benefícios do item de forma limpa."
        }.get(tom, "Crie um post atraente e persuasivo para grupo de ofertas do WhatsApp.")

        prompt = f"""Você é um copywriter especialista em grupos de ofertas e achadinhos no WhatsApp no Brasil.
Seu objetivo é transformar os dados deste produto em uma mensagem completa de vendas no WhatsApp.

DADOS DO PRODUTO:
- Nome/Título Bruto: {titulo_original}
- Loja/Origem: {fonte}
- Preço Promocional: R$ {float(preco_atual):.2f}
{f'- Preço Anterior (De): R$ {float(preco_orig):.2f}' if preco_orig else ''}
{f'- Desconto: {desconto_pct}' if desconto_pct else ''}
{f'- {info_cupom}' if info_cupom else ''}
- Link de Compra: {link}

ESTRUTURA OBRIGATÓRIA DA MENSAGEM:
1. Linha 1: *Título Limpo e Atraente em Negrito*
2. Linha 2: Frase curta com gancho/benefício ({instrucao_tom})
3. Linha 3: 🛍️ Origem: {fonte}
4. Linha 4 (se houver preço anterior): ❌ De: ~R$ {float(preco_orig):.2f}~
5. Linha 5: 🔥 Por: *R$ {float(preco_atual):.2f}*{f' ({desconto_pct})' if desconto_pct else ''}
{f'6. Linha 6: 🏷️ Cupom: *[ {code} ]* ({desc_cupom})' if info_cupom else ''}
7. Linha final: 🛒 Compre aqui: {link}

Use apenas formatação de WhatsApp (*negrito*, ~riscado~). Retorne a mensagem COMPLETA sem cortar.
"""

        try:
            resposta_ia = cls._chamar_gemini_api(prompt, api_key_clean)
            if resposta_ia and len(resposta_ia.strip()) > 30:
                texto_final = resposta_ia.strip()
                if link and link not in texto_final:
                    texto_final += f"\n\n🛒 Compre aqui: {link}"
                return texto_final
            else:
                log_func("⚠️ Resposta da IA vazia. Usando template padrão.")
                return formatar_mensagem_produto(produto, cupom)
        except Exception as e:
            log_func(f"⚠️ Erro ao chamar IA Gemini ({e}). Usando fallback padrão.")
            return formatar_mensagem_produto(produto, cupom)

    @classmethod
    def gerar_versiculo_biblico_inedito(cls, ja_usados=None, api_key="", log_func=print):
        """
        Gera um versículo bíblico com reflexão 100% inédito, proibindo os versículos já enviados recentemente.
        """
        import random
        import datetime
        
        api_key_clean = (api_key or "").strip()
        if not api_key_clean:
            return None

        livros_sugeridos = [
            "Provérbios", "Salmos", "Isaías", "Jeremias", "Mateus", "Lucas", "João", 
            "Romanos", "1 Coríntios", "2 Coríntios", "Gálatas", "Efésios", "Filipenses", 
            "Colossenses", "1 Tessalonicenses", "Josué", "Tiago", "1 Pedro", "Hebreus", "Eclesiastes"
        ]
        temas_sugeridos = [
            "Paz e Esperança", "Sabedoria nas Decisões", "Força e Vitória", "Gratidão e Família",
            "Trabalho e Prosperidade", "Paciência e Confiança", "Recomeço e Fé", "Alegria e Superação"
        ]
        
        livro_foco = random.choice(livros_sugeridos)
        tema_foco = random.choice(temas_sugeridos)
        
        lista_bloqueados = ""
        if ja_usados:
            lista_bloqueados = "\n".join([f"- {u}" for u in ja_usados[:25]])
        else:
            lista_bloqueados = "- (Nenhum registro anterior)"

        prompt = f"""Você é o administrador de um grupo VIP de ofertas e achadinhos no WhatsApp no Brasil.
Seu objetivo é gerar a Mensagem do Versículo Bíblico do Dia para abençoar e acolher os membros.

DIRETRIZES DESTA GERAÇÃO:
- Foco temático de hoje: {tema_foco}
- Livro bíblico sugerido: {livro_foco}

⛔ VERSÍCULOS / REFERÊNCIAS JÁ UTILIZADOS RECENTEMENTE (PROIBIDO REPETIR QUALQUER UM DESTES):
{lista_bloqueados}

REGRAS ESTRITAS:
1. Escolha um versículo DIFERENTE e INÉDITO, que NÃO esteja na lista acima.
2. Inicie com um cabeçalho bonito (ex: 📖 *PALAVRA DO DIA* ou 🌟 *VERSÍCULO DO DIA*).
3. Coloque o versículo bíblico completo entre aspas em _itálico_ com a referência bíblica destacada em *negrito* (ex: *Isaías 40:31*).
4. Escreva uma reflexão calorosa, motivadora e acolhedora de 2 parágrafos curtos, desejando um dia de paz, vitórias e boas conquistas para todos os membros do grupo.
5. Use formatação nativa do WhatsApp (*negrito*, _itálico_) e emojis acolhedores bem distribuídos.
6. Retorne APENAS o texto pronto para envio no WhatsApp, sem introduções ou comentários.
"""
        try:
            resp = cls._chamar_gemini_api(prompt, api_key_clean)
            if resp and len(resp.strip()) > 30:
                return resp.strip()
        except Exception as e:
            log_func(f"⚠️ Erro ao gerar versículo inédito: {e}")
        return None

    @classmethod
    def gerar_dica_economia_inedita(cls, ja_usados=None, api_key="", log_func=print):
        """
        Gera uma dica de economia e compras inteligentes 100% inédita, proibindo dicas já dadas.
        """
        import random
        api_key_clean = (api_key or "").strip()
        if not api_key_clean:
            return None

        topicos_dica = [
            "Cashback e carteiras digitais que devolvem dinheiro de verdade",
            "Alertas de queda de preço e históricos para não cair em falsas promoções",
            "Estratégia de acumular cupons de loja com cupons de frete grátis da plataforma",
            "Comparação do preço por grama / ml / unidade em produtos de mercado e higiene",
            "Dicas de segurança para verificar reputação de vendedores e fotos reais nos comentários",
            "Como funciona a garantia estendida e o direito de devolução grátis em 7 dias",
            "Criar lista de desejos e monitorar horários de virada de ofertas relâmpago (00:00, 12:00)",
            "Vantagens de pagamentos instantâneos (Pix) que concedem descontos adicionais",
            "Como evitar compras por impulso usando a regra dos 2 dias de reflexão",
            "Aproveitar combos 'Leve Mais por Menos' e cupons progressivos com sabedoria"
        ]
        
        topico_foco = random.choice(topicos_dica)
        lista_bloqueados = ""
        if ja_usados:
            lista_bloqueados = "\n".join([f"- {u}" for u in ja_usados[:25]])
        else:
            lista_bloqueados = "- (Nenhum registro anterior)"

        prompt = f"""Você é o administrador de um grupo VIP de ofertas e achadinhos no WhatsApp no Brasil.
Seu objetivo é gerar a Dica de Economia & Compras Inteligentes do Dia para ajudar os membros a economizarem de verdade.

DIRETRIZES DESTA GERAÇÃO:
- Tópico sugerido de hoje: {topico_foco}

⛔ DICAS JÁ DADAS RECENTEMENTE (PROIBIDO REPETIR O MESMO TEMA/ASSUNTO):
{lista_bloqueados}

REGRAS ESTRITAS:
1. Crie uma dica NOVA, PRÁTICA e CRIATIVA sobre o tópico sugerido.
2. Inicie com um título atraente (ex: 💡 *DICA DE ECONOMIA DO ADM* ou 🎯 *SEGREDO PARA COMPRAR MAIS BARATO*).
3. Explique em 2 ou 3 passos simples como aplicar a dica na prática (na Shopee, Mercado Livre ou compras online em geral).
4. Tom amigável, parceiro e experiente, com emojis bem distribuídos e formatação do WhatsApp (*negrito*, _itálico_).
5. Retorne APENAS o texto pronto para envio no WhatsApp.
"""
        try:
            resp = cls._chamar_gemini_api(prompt, api_key_clean)
            if resp and len(resp.strip()) > 30:
                return resp.strip()
        except Exception as e:
            log_func(f"⚠️ Erro ao gerar dica inédita: {e}")
        return None

    @classmethod
    def gerar_mensagem_engajamento(cls, tema_ou_prompt, api_key="", log_func=print):
        """
        Gera uma mensagem de engajamento genérica ou personalizada.
        """
        api_key_clean = (api_key or "").strip()
        if not api_key_clean:
            return f"✨ *Mensagem do Dia*\n\n{tema_ou_prompt}\n\nTenham todos um excelente dia!"

        prompt = f"""Você é o administrador de um grupo VIP de ofertas e achadinhos no WhatsApp no Brasil.
Crie uma mensagem especial de engajamento e acolhimento para os membros do grupo.

TEMA OU PEDIDO:
{tema_ou_prompt}

REGRAS:
1. Mensagem calorosa, inspiradora e relevante.
2. Use formatação nativa do WhatsApp (*negrito*, _itálico_).
3. Use emojis bem distribuídos.
4. Não seja excessivamente longo (2 a 4 parágrafos curtos).
5. Retorne APENAS o texto pronto para envio.
"""
        try:
            resp = cls._chamar_gemini_api(prompt, api_key_clean)
            if resp and len(resp.strip()) > 10:
                return resp.strip()
        except Exception as e:
            log_func(f"⚠️ Erro na IA de engajamento: {e}")

        return f"✨ *Mensagem Especial*\n\n{tema_ou_prompt}\n\n🙏 Desejamos a todos um dia abençoado e cheio de boas oportunidades!"

    @classmethod
    def _chamar_gemini_api(cls, prompt_texto, api_key):
        """
        Executa a chamada HTTP direta para a API do Google Gemini com suporte a múltiplos modelos e alta variabilidade.
        """
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [{"text": prompt_texto}]
            }],
            "generationConfig": {
                "temperature": 0.85,
                "topP": 0.95,
                "maxOutputTokens": 1000,
            }
        }

        # Tenta os modelos mais recentes em ordem de velocidade/relevância
        for modelo in cls.MODELOS_DISPONIVEIS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=8, verify=False)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
                elif resp.status_code in [400, 403]:
                    break
            except requests.exceptions.RequestException:
                continue

        # Tenta via SDK oficial google-genai se a requisição REST não responder
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_texto,
            )
            if response and response.text:
                return response.text
        except Exception:
            pass

        return None

