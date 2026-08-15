import requests
import os
import win32clipboard
from io import BytesIO
from PIL import Image

def baixar_imagem(url, caminho_arquivo):
    """Baixa imagem de uma URL para um arquivo local"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, stream=True, timeout=10, verify=False)
        if response.status_code == 200:
            with open(caminho_arquivo, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        print(f"Erro ao baixar imagem: {e}")
        return False

def copy_image_to_clipboard(image_path):
    """Copia uma imagem para o clipboard do Windows"""
    try:
        image = Image.open(image_path)
        output = BytesIO()
        image.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()
        return True
    except Exception as e:
        print(f"Erro ao copiar imagem para clipboard: {e}")
        return False

def formatar_mensagem_produto(produto, cupom=None):
    """
    Formata o texto de envio para o WhatsApp, exibindo:
    - Preço original riscado (De: ~R$ ...~) quando disponível
    - Preço promocional (Por: *R$ ...* (XX% OFF))
    - Destaque claro de cupom digitável ou aplicado
    """
    titulo = produto.get("titulo", "")
    fonte = produto.get("fonte", "Oferta")
    preco_atual = produto.get("preco", "0.00")
    preco_orig = produto.get("preco_original", "")
    desconto_pct = produto.get("desconto_pct", "")
    link = produto.get("link", "")

    linhas = [
        f"*{titulo}*",
        "",
        f"🛍️ Origem: {fonte}"
    ]

    # Preço anterior (De:)
    try:
        if preco_orig and float(preco_orig) > float(preco_atual):
            linhas.append(f"❌ De: ~R$ {float(preco_orig):.2f}~")
    except:
        pass

    # Preço com Desconto (Por:)
    por_linha = f"🔥 Por: *R$ {float(preco_atual):.2f}*"
    if desconto_pct:
        por_linha += f" ({desconto_pct})"
    linhas.append(por_linha)

    # Se houver cupom digitável real associado
    if cupom:
        code = (cupom.get("code") or "").strip().upper()
        if code and code not in ["CUPOM_SHOPEE", "CUPOM_NO_ANUNCIO"] and not code.startswith("ML_"):
            desc_cupom = cupom.get("discount_text") or cupom.get("title", "")
            linhas.append(f"🏷️ Cupom: *[ {code} ]* ({desc_cupom})")

    linhas.append("")
    linhas.append(f"🛒 Compre aqui: {link}")


    return "\n".join(linhas)


