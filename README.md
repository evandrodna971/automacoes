# Automação ZapFinder v2.0

Ferramenta moderna de automação para formatar e enviar produtos da Shopee para grupos de WhatsApp.

## Funcionalidades
- **Interface Moderna**: Painel em modo escuro construído com Flet.
- **Envio Automatizado**: Busca produtos da API Shopee, baixa imagens e envia via WhatsApp Web.
- **Motor Selenium**: Automação robusta e confiável (sem problemas de movimento do mouse).
- **Agendamento**: Configure e esqueça! Executa automaticamente em intervalos definidos.
- **Histórico**: Mantém o registro de todos os produtos enviados.

## Instalação
1. Certifique-se de ter o Python 3.10 ou superior instalado.
2. Execute o arquivo `setup.bat` para instalar as dependências.

## Como Usar
1. Execute o arquivo `run.bat` para iniciar o aplicativo.
2. Vá para a aba **Configurações**:
   - Digite seu **Shopee App ID** e **Secret Key**.
   - Digite o **Nome do Grupo WhatsApp** exato.
   - Clique em "Salvar Configurações".
3. Vá para o **Dashboard** e clique em "Iniciar Envio Shopee" para rodar uma vez.
   - OU
4. Vá para **Agendamento** para configurar uma tarefa recorrente (ex: a cada 60 minutos).

## Solução de Problemas
- **Login WhatsApp**: Na primeira execução, você precisará escanear o QR code.
- **Navegador**: O Google Chrome deve estar instalado.
- **Parar**: O botão "Parar" na interface para o *agendador*, mas pode não fechar imediatamente um processo Selenium ativo. Feche a janela do terminal para forçar o encerramento, se necessário.
# automacoes  
