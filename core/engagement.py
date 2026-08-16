import random
import datetime
import re
from core.ai_gemini import GeminiCopywriter
from database.db import (
    obter_cupons_validos,
    salvar_historico_engajamento,
    obter_ultimos_envios_engajamento
)

# Acervo nativo de fallback com rotação inteligente pelo dia do ano para evitar repetições
MENSAGENS_FALLBACK = {
    "versiculo": [
        "📖 *Versículo do Dia*\n\n\"O Senhor é o meu pastor; de nada terei falta.\" - *Salmos 23:1*\n\nQue o seu dia seja repleto de bênçãos, paz e prosperidade! 🙏✨",
        "📖 *Versículo do Dia*\n\n\"Entregue o seu caminho ao Senhor; confie nele, e ele agirá.\" - *Salmos 37:5*\n\nUm dia abençoado e cheio de vitórias para todos nós! 🙌☀️",
        "📖 *Versículo do Dia*\n\n\"Tudo posso naquele que me fortalece.\" - *Filipenses 4:13*\n\nQue a sua jornada hoje seja guiada por fé, coragem e muitas conquistas! 🌟🙏",
        "📖 *Versículo do Dia*\n\n\"O Senhor te abençoe e te guarde; o Senhor faça resplandecer o seu rosto sobre ti.\" - *Números 6:24-25*\n\nTenha uma manhã extraordinária e abençoada! 🕊️✨",
        "📖 *Versículo do Dia*\n\n\"Mas os que esperam no Senhor renovarão as suas forças. Subirão com asas como águias.\" - *Isaías 40:31*\n\nQue você renove suas forças e tenha um dia produtivo e vitorioso! 🦅💪",
        "📖 *Versículo do Dia*\n\n\"Confie no Senhor de todo o seu coração e não se apoie em seu próprio entendimento.\" - *Provérbios 3:5*\n\nQue a sabedoria divina guie cada uma das suas decisões hoje! 💡🙏",
        "📖 *Versículo do Dia*\n\n\"Não fui eu que lhe ordenei? Seja forte e corajoso! Não se apavore nem desanime, pois o Senhor estará com você.\" - *Josué 1:9*\n\nMuita coragem e determinação para vencer todos os desafios de hoje! 🛡️🔥",
        "📖 *Versículo do Dia*\n\n\"O Senhor é a minha luz e a minha salvação; de quem terei temor?\" - *Salmos 27:1*\n\nQue a luz e a paz estejam presentes em seu lar hoje e sempre! ☀️💛",
        "📖 *Versículo do Dia*\n\n\"Sabemos que Deus age em todas as coisas para o bem daqueles que o amam.\" - *Romanos 8:28*\n\nConfie nos planos que estão sendo preparados para sua vida! 🌈✨",
        "📖 *Versículo do Dia*\n\n\"O amor é paciente, o amor é bondoso. Não inveja, não se vangloria, não se orgulha.\" - *1 Coríntios 13:4*\n\nQue o seu dia seja repleto de amor, carinho e união! ❤️🕊️"
    ],
    "dica": [
        "💡 *Dica de Economia do Dia*\n\nAntes de finalizar qualquer compra online, lembre-se sempre de:\n1. Conferir se há cupons de frete grátis ativos no app.\n2. Aproveitar pagamentos via Pix que costumam ter de 5% a 15% de desconto imediato!\n\nBoas compras e economize sempre! 🛒💰",
        "💡 *Dica de Economia do Dia*\n\nColoque os produtos de seu interesse no carrinho com antecedência. Quando houver redução de preço ou liberação de novos cupons relâmpago, você será notificado primeiro e garante o menor valor! ⚡🛍️",
        "💡 *Dica de Economia do Dia*\n\nAcompanhe nossos achadinhos diários! Nós garimpamos manualmente as melhores oportunidades para que você não perca tempo e compre com segurança pelo melhor preço do mercado. 🚀🎯",
        "💡 *Dica de Economia do Dia*\n\nSempre confira o preço por unidade, grama ou litro ao comprar pacotes ou kits! Muitas vezes o kit com 3 unidades sai 30% mais barato do que comprar itens individuais. 📊🏷️",
        "💡 *Dica de Economia do Dia*\n\nAntes de comprar, dê uma olhada rápida nas avaliações com fotos e vídeos de outros compradores. Isso garante que você está adquirindo um item de alta qualidade e evita devoluções desnecessárias! 📸⭐",
        "💡 *Dica de Economia do Dia*\n\nAtive as notificações do grupo! As promoções com descontos acima de 50% ou erros de precificação costumam esgotar em menos de 15 minutos. Quem chega primeiro, economiza mais! ⏰🔥"
    ]
}

def extrair_resumo_curto(texto, tipo):
    """Extrai um resumo de identificação (ex: nome do versículo ou tema da dica) para o banco de dados"""
    if not texto:
        return tipo
    # Tenta achar referência bíblica (ex: Salmos 23:1, Isaías 40:31, etc.)
    match = re.search(r'\*?([1-3]?\s?[A-Za-zÀ-ú]+\s\d+:\d+(?:-\d+)?)\*?', texto)
    if match:
        return match.group(1).strip()
    
    # Pega primeira linha ou primeiras palavras
    linhas = [l.strip() for l in texto.split('\n') if l.strip()]
    if linhas:
        primeira = re.sub(r'[*_#]', '', linhas[0])
        return primeira[:40]
    return tipo

def gerar_mensagem_engajamento_completa(tipo="versiculo", prompt_custom="", api_key="", log_func=print):
    """
    Gera o texto completo formatado para WhatsApp conforme o tipo de mensagem de engajamento,
    garantindo que NUNCA repita versículos ou dicas através de histórico no banco de dados e IA Gemini.
    """
    api_key_clean = (api_key or "").strip()
    
    # 1. Resumo Consolidado de Cupons do Dia
    if tipo == "resumo_cupons":
        cupons = obter_cupons_validos()
        if not cupons:
            return "🏷️ *Resumo de Cupons do Dia*\n\nEstamos atualizando as melhores ofertas e cupons da Shopee e Mercado Livre para hoje. Fiquem ligados nas próximas postagens! 🚀✨"
            
        linhas = [
            "🏷️ *RESUMO DOS MELHORES CUPONS DO DIA*",
            "Aproveite para aplicar em suas compras de hoje:\n"
        ]
        
        # Filtra cupons com código real digitável
        cupons_validos = [c for c in cupons if c.get("code") and not c["code"].startswith("ML_") and c["code"] not in ["CUPOM_SHOPEE", "CUPOM_NO_ANUNCIO"]]
        if not cupons_validos:
            cupons_validos = cupons[:5]
            
        for c in cupons_validos[:6]:
            code = c.get("code", "")
            loja = c.get("marketplace", "Geral")
            desc = c.get("discount_text") or c.get("title", "Desconto Especial")
            linhas.append(f"🔹 *[{loja}]* Cupom: *{code}* - {desc}")
            
        linhas.append("\n🛒 *Dica:* Copie o código e cole no carrinho antes de pagar!")
        return "\n".join(linhas)

    # 2. Versículo Bíblico do Dia (Anti-duplicação garantida com Gemini)
    elif tipo == "versiculo":
        ja_usados = obter_ultimos_envios_engajamento("versiculo", limit=40)
        
        if api_key_clean:
            log_func(f"🤖 Gerando versículo inédito com Gemini (bloqueando {len(ja_usados)} já enviados)...")
            res = GeminiCopywriter.gerar_versiculo_biblico_inedito(ja_usados=ja_usados, api_key=api_key_clean, log_func=log_func)
            if res and len(res.strip()) > 30:
                texto_gerado = res.strip()
                resumo = extrair_resumo_curto(texto_gerado, "versiculo")
                salvar_historico_engajamento("versiculo", resumo, texto_gerado)
                log_func(f"✅ Versículo inédito gerado: {resumo}")
                return texto_gerado

        # Fallback inteligente com rotação por dia do ano
        dia_ano = datetime.datetime.now().timetuple().tm_yday
        idx = dia_ano % len(MENSAGENS_FALLBACK["versiculo"])
        texto_fb = MENSAGENS_FALLBACK["versiculo"][idx]
        resumo_fb = extrair_resumo_curto(texto_fb, "versiculo")
        salvar_historico_engajamento("versiculo", resumo_fb, texto_fb)
        return texto_fb

    # 3. Dica de Economia / Compras (Anti-duplicação garantida com Gemini)
    elif tipo == "dica":
        ja_usados = obter_ultimos_envios_engajamento("dica", limit=40)
        
        if api_key_clean:
            log_func(f"🤖 Gerando dica de economia inédita com Gemini (bloqueando {len(ja_usados)} já enviadas)...")
            res = GeminiCopywriter.gerar_dica_economia_inedita(ja_usados=ja_usados, api_key=api_key_clean, log_func=log_func)
            if res and len(res.strip()) > 30:
                texto_gerado = res.strip()
                resumo = extrair_resumo_curto(texto_gerado, "dica")
                salvar_historico_engajamento("dica", resumo, texto_gerado)
                log_func(f"✅ Dica inédita gerada: {resumo}")
                return texto_gerado

        # Fallback inteligente com rotação por dia do ano
        dia_ano = datetime.datetime.now().timetuple().tm_yday
        idx = dia_ano % len(MENSAGENS_FALLBACK["dica"])
        texto_fb = MENSAGENS_FALLBACK["dica"][idx]
        resumo_fb = extrair_resumo_curto(texto_fb, "dica")
        salvar_historico_engajamento("dica", resumo_fb, texto_fb)
        return texto_fb

    # 4. Mensagem Personalizada pelo Usuário
    elif tipo == "custom":
        p = prompt_custom.strip() if prompt_custom else "Uma mensagem especial de bom dia e boas compras para o grupo."
        if api_key_clean:
            try:
                res = GeminiCopywriter.gerar_mensagem_engajamento(p, api_key=api_key_clean, log_func=log_func)
                if res and len(res.strip()) > 20:
                    return res.strip()
            except Exception as e:
                log_func(f"Aviso no Gemini (Custom): {e}")
                
        return f"✨ *Mensagem Especial*\n\n{p}\n\n🙏 Tenham todos um excelente dia!"

    return "✨ *Tenham todos um excelente dia repleto de bênçãos e boas oportunidades!* 🙏☀️"
