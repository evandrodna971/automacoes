# Automação ZapFinder v2.0

Ferramenta moderna de automação para formatar e enviar produtos da Shopee para grupos de WhatsApp.

## 🚀 Funcionalidades
- **Interface Moderna**: Painel em modo escuro construído com Flet.
- **Envio Automatizado**: Busca produtos da API Shopee, baixa imagens e envia via WhatsApp Web.
- **Motor Selenium**: Automação robusta e confiável.
- **Envio de Imagem via Clipboard**: Evita janelas de diálogo do sistema, colando imagens diretamente no chat.
- **Agendamento**: Configure horários específicos para execução automática.
- **Histórico**: Mantém o registro de todos os produtos enviados.
- **Executável Portátil**: Pode ser compilado em um arquivo `.exe` único.

## 📋 Pré-requisitos
Antes de começar, certifique-se de ter:
1. **Google Chrome** instalado e atualizado.
2. **Python 3.10+** instalado (apenas se for rodar pelo código fonte).
3. **Conta no WhatsApp** ativa e acessível via Web.

## ⚙️ Instalação e Configuração

### Opção 1: Rodando pelo Código Fonte (Desenvolvedores)
1. Instale o Python: [python.org](https://www.python.org/downloads/)
2. Clone este repositório ou baixe os arquivos.
3. Execute o arquivo **`setup.bat`**.
   - Isso criará um ambiente virtual e instalará todas as dependências necessárias automaticamente.
4. Para iniciar o programa, execute **`run.bat`**.

### Opção 2: Usando o Executável (.exe)
Se você gerou ou baixou o executável:
1. Basta executar o arquivo **`ZapFinder.exe`**.
2. Não é necessário instalar Python.

---

## 🏗️ Como Criar o Executável (Build)
Para transformar o código Python em um executável `.exe` que pode ser enviado para outros computadores:

1. Certifique-se de ter rodado o `setup.bat` pelo menos uma vez.
2. Execute o arquivo **`build.bat`**.
3. Aguarde o processo terminar (pode levar alguns minutos).
4. O arquivo final estará na pasta **`dist/ZapFinder.exe`**.

> **Nota**: A pasta `dist` pode ser movida para qualquer lugar, mas o computador destino precisa ter o Google Chrome instalado.

---

## 📖 Como Usar
1. **Configuração Inicial**:
   - Abra o programa.
   - Vá para a aba **Configurações**.
   - Preencha seu **Shopee App ID** e **Secret Key**.
   - Digite o **Nome do Grupo WhatsApp** exato onde as ofertas serão postadas.
   - Ajuste a **Quantidade de Produtos** por envio.
   - Clique em "Salvar Configurações".

2. **Execução Manual**:
   - No **Dashboard**, clique em "Iniciar Envio Shopee".
   - O Chrome abrirá automaticamente. Escaneie o QR Code do WhatsApp se solicitado.
   - O robô buscará as ofertas e enviará para o grupo configurado.

3. **Agendamento**:
   - Vá para a aba **Agendamento**.
   - Adicione os horários desejados (ex: `09:00`, `14:00`, `18:00`).
   - Clique em "Iniciar Agendamento".
   - **Mantenha o programa aberto**. Ele executará automaticamente nos horários definidos.

## 🛠️ Solução de Problemas
- **Erro ao abrir o Chrome**: Verifique se seu Google Chrome está atualizado.
- **Não envia a imagem**: O sistema usa a área de transferência (Clipboard). Evite usar o computador (copiar/colar outras coisas) enquanto o robô está enviando.
- **Janela não maximiza**: O programa tenta maximizar automaticamente. Se falhar, você pode maximizar manualmente.
- **Login WhatsApp**: O robô aguarda você escanear o QR Code. Se demorar muito, ele pode dar timeout e você precisará reiniciar.

## 📁 Estrutura de Arquivos Importantes
- `run.bat`: Inicia o programa (código fonte).
- `setup.bat`: Instala dependências.
- `build.bat`: Gera o executável.
- `config.json`: Salva suas configurações locais.
- `zapfinder.db`: Banco de dados do histórico.
