import sys
import time
from core.whatsapp import WhatsAppBot

bot = WhatsAppBot()
print("Iniciando driver...")
bot.iniciar_driver()

print("Aguardando login...")
if not bot.aguardar_login(30):
    print("Falha ao logar")
    bot.fechar()
    sys.exit(1)

print("Buscando grupo Achadinhos da Joice para testar...")
if bot.buscar_grupo("Achadinhos da Joice"):
    print("SUCESSO: Grupo aberto com sucesso.")
    # Não vamos enviar mensagem real para não poluir o grupo
    # Apenas validamos se a pesquisa funciona
else:
    print("FALHA na busca do grupo.")

time.sleep(3)
bot.fechar()
