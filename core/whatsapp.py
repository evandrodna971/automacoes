import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

class WhatsAppBot:
    def __init__(self, driver_path=None, session_dir="whatsapp_session"):
        self.driver_path = driver_path
        self.session_dir = os.path.abspath(session_dir)
        self.driver = None

    def log(self, msg):
        print(f"[WhatsApp] {msg}")

    def iniciar_driver(self):
        """Inicializa o Chrome com perfil persistente"""
        try:
            chrome_options = Options()
            chrome_options.add_argument(f"user-data-dir={self.session_dir}")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.log("Iniciando Chrome...")
            
            if self.driver_path and os.path.exists(self.driver_path):
                service = Service(executable_path=self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
                
            self.driver.get("https://web.whatsapp.com")
            return True
        except Exception as e:
            self.log(f"Erro ao iniciar driver: {e}")
            return False

    def aguardar_login(self, timeout=60):
        """Aguardar login no WhatsApp Web"""
        try:
            self.log("Aguardando login...")
            elementos_indicadores = [
                "//div[@data-testid='chat-list']",
                "//div[@role='textbox']", 
                "//div[@contenteditable='true']"
            ]
            
            WebDriverWait(self.driver, timeout).until(
                lambda d: any(d.find_elements(By.XPATH, xp) for xp in elementos_indicadores)
            )
            self.log("Login detectado!")
            return True
        except:
            self.log("Timeout aguardando login")
            return False

    def buscar_grupo(self, nome_grupo):
        """Busca e entra em um grupo"""
        try:
            self.log(f"Buscando grupo: {nome_grupo}")
            
            # 1. Tenta clicar direto se visivel
            try:
                chat = self.driver.find_element(By.XPATH, f"//span[@title='{nome_grupo}']")
                chat.click()
                self.log(f"Grupo {nome_grupo} encontrado na lista.")
                time.sleep(1)
                return True
            except:
                pass
            
            # 2. Usa a busca
            search_box = self.driver.find_element(By.XPATH, "//div[@contenteditable='true'][@data-tab='3']")
            search_box.click()
            search_box.clear()
            search_box.send_keys(nome_grupo)
            time.sleep(2)
            
            chat = self.driver.find_element(By.XPATH, f"//span[@title='{nome_grupo}']")
            chat.click()
            self.log(f"Grupo {nome_grupo} encontrado via busca.")
            return True
            
        except Exception as e:
            self.log(f"Erro ao buscar grupo: {e}")
            return False

    def enviar_imagem(self, image_path, legenda=""):
        """Envia imagem usando input injection e menu"""
        try:
            self.log(f"Enviando imagem: {image_path}")
            
            # Nova Abordagem: Copiar Imagem para Clipboard e Colar
            from core.utils import copy_image_to_clipboard
            import win32clipboard

            # 1. Copia imagem para memória
            if not copy_image_to_clipboard(image_path):
                raise Exception("Falha ao copiar imagem para clipboard")

            # 2. Foca no campo de texto principal
            try:
                # Tenta clicar no campo de mensagem para garantir foco
                box = self.driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='10']")
                box.click()
                time.sleep(0.5)
            except:
                self.log("Aviso: Não consegui focar no chat, tentando colar mesmo assim.")

            # 3. Cola a imagem (Ctrl+V)
            actions = ActionChains(self.driver)
            actions.key_down(Keys.CONTROL)
            actions.send_keys('v')
            actions.key_up(Keys.CONTROL)
            actions.perform()
            
            self.log("Comando colar (Ctrl+V) enviado.")
            
            # 4. Aguarda preview da imagem (campo de legenda aparecer)
            # Substituindo WebDriverWait por sleep fixo curto para agilidade máxima
            # O usuário relatou lentidão, indicando que o Wait estava demorando para achar o elemento.
            time.sleep(0.8) 
            
            # 5. Colar a legenda
            if legenda:
               try:
                   # Copia legenda para clipboard
                   win32clipboard.OpenClipboard()
                   win32clipboard.EmptyClipboard()
                   win32clipboard.SetClipboardText(legenda, win32clipboard.CF_UNICODETEXT)
                   win32clipboard.CloseClipboard()
                   
                   # Cola Legenda (Ctrl+V) assumindo que o foco já está correto (comportamento padrão do WhatsApp)
                   actions = ActionChains(self.driver)
                   actions.key_down(Keys.CONTROL)
                   actions.send_keys('v')
                   actions.key_up(Keys.CONTROL)
                   actions.perform()
                   time.sleep(0.2)
               except Exception as e:
                   self.log(f"Erro ao colar legenda: {e}")
                   # Tenta digitar como último recurso
                   try: 
                        if caption_box:
                            caption_box.send_keys(legenda) 
                   except: pass

            try:
                # Botão de enviar no modal de preview
                send_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send']"))
                )
                send_btn.click()
                self.log("Botão enviar clicado.")
            except Exception as e:
                self.log(f"Erro ao clicar envie: {e}")
                # Fallback Enter
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ENTER).perform()
            
            self.log("Imagem enviada.")
            time.sleep(2)
            return True
            
        except Exception as e:
            self.log(f"Erro ao enviar imagem: {e}")
            return False

    def enviar_mensagem_texto(self, texto):
        """Envia mensagem de texto"""
        try:
            # Encontra campo de texto
            # data-tab=10 é o campo principal de chat
            box = self.driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='10']")
            box.click()
            
            # Envia texto com suporte a quebras de linha (Shift+Enter)
            # Se o texto já vier com \n, podemos tentar enviar direto ou processar
            for linha in texto.split('\n'):
                box.send_keys(linha)
                box.send_keys(Keys.SHIFT + Keys.ENTER)
            
            box.send_keys(Keys.ENTER)
            return True
        except Exception as e:
            self.log(f"Erro ao enviar texto: {e}")
            return False
            
    def fechar(self):
        if self.driver:
            self.driver.quit()
