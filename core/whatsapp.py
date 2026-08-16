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

    def fechar_popups_aviso(self):
        """Fecha qualquer modal ou popup de aviso de atualização/boas-vindas do WhatsApp"""
        try:
            botoes = self.driver.find_elements(By.XPATH, "//button[contains(., 'Continuar') or contains(., 'Fechar') or contains(., 'Entendi') or contains(., 'OK')] | //div[@role='button'][contains(., 'Continuar') or contains(., 'Fechar') or contains(., 'Entendi')] | //span[@data-icon='x']")
            for btn in botoes:
                if btn.is_displayed():
                    btn.click()
                    self.log("Aviso/popup inicial do WhatsApp fechado com sucesso.")
                    time.sleep(1)
        except:
            pass

    def aguardar_login(self, timeout=120):
        """Aguardar login no WhatsApp Web"""
        try:
            self.log("Aguardando login...")
            elementos_indicadores = [
                "//div[@id='pane-side']",
                "//div[@data-testid='chat-list']",
                "//span[@data-icon='menu']",
                "//span[@data-icon='chat']"
            ]
            
            WebDriverWait(self.driver, timeout).until(
                lambda d: any(d.find_elements(By.XPATH, xp) for xp in elementos_indicadores)
            )
            self.log("Login detectado!")
            time.sleep(2)
            self.fechar_popups_aviso()
            return True
        except:
            self.log("Timeout aguardando login")
            return False

    def buscar_grupo(self, nome_grupo):
        """Busca e entra em um grupo"""
        try:
            self.fechar_popups_aviso()
            self.log(f"Buscando grupo: {nome_grupo}")
            
            # 1. Tenta clicar direto se visível na lista
            try:
                chat = self.driver.find_element(By.XPATH, f"//span[@title='{nome_grupo}']")
                chat.click()
                self.log(f"Grupo {nome_grupo} encontrado na lista.")
                time.sleep(1.5)
                return True
            except:
                pass
            
            # 2. Usa o campo de busca do WhatsApp
            search_box = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Pesquisar') or contains(@placeholder, 'nova') or contains(@placeholder, 'Search')] | //div[@id='side']//input")
            search_box.click()
            search_box.clear()
            search_box.send_keys(nome_grupo)
            time.sleep(2)
            
            chat = self.driver.find_element(By.XPATH, f"//span[@title='{nome_grupo}']")
            chat.click()
            self.log(f"Grupo {nome_grupo} encontrado via busca.")
            time.sleep(1.5)
            return True
            
        except Exception as e:
            self.log(f"Erro ao buscar grupo: {e}")
            return False

    def enviar_imagem(self, image_path, legenda=""):
        """Envia imagem copiando para o clipboard e colando com tempo de espera ampliado para a legenda"""
        try:
            self.log(f"Enviando imagem: {image_path}")
            
            from core.utils import copy_image_to_clipboard
            import win32clipboard

            # 1. Copia imagem para memória
            if not copy_image_to_clipboard(image_path):
                raise Exception("Falha ao copiar imagem para clipboard")

            # 2. Foca no campo de texto principal do chat
            try:
                box = self.driver.find_element(By.XPATH, "//footer//div[@contenteditable='true'] | //div[@contenteditable='true'][@data-tab='10']")
                box.click()
                time.sleep(0.5)
            except:
                self.log("Aviso: Tentando colar imagem diretamente no chat.")

            # 3. Cola a imagem (Ctrl+V)
            actions = ActionChains(self.driver)
            actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            self.log("Imagem colada (Ctrl+V). Aguardando carregamento do preview...")
            
            # 4. Tempo de espera ampliado para a imagem carregar totalmente no modal de preview
            time.sleep(2.5) 
            
            # 5. Colar a legenda
            if legenda:
                try:
                    # Copia legenda para clipboard
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(legenda, win32clipboard.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                    time.sleep(0.3)
                    
                    # Cola Legenda (Ctrl+V) no modal de preview que já está focado
                    actions = ActionChains(self.driver)
                    actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                    self.log("Legenda colada (Ctrl+V).")
                    time.sleep(1.0)
                except Exception as e:
                    self.log(f"Erro ao colar legenda: {e}")

            # 6. Clicar no botão Enviar (ou Enter)
            try:
                send_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send'] | //div[@aria-label='Enviar' or @aria-label='Send']"))
                )
                send_btn.click()
                self.log("Botão enviar clicado.")
            except Exception as e:
                self.log(f"Erro ao clicar enviar: {e}. Tentando Enter...")
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ENTER).perform()
            
            self.log("Imagem e legenda enviadas com sucesso.")
            time.sleep(2.5)
            return True
            
        except Exception as e:
            self.log(f"Erro ao enviar imagem: {e}")
            return False

    def enviar_mensagem_texto(self, texto):
        """Envia mensagem de texto via clipboard e Ctrl+V com tempos seguros e clique no botão de envio"""
        try:
            if not texto or not texto.strip():
                return False
                
            self.fechar_popups_aviso()
            self.log("Preparando envio de mensagem de texto...")
            
            import win32clipboard

            # 1. Copia texto completo para o clipboard
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(texto.strip(), win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            except Exception as clip_err:
                self.log(f"Aviso no clipboard de texto: {clip_err}")
                
            time.sleep(0.3)

            # 2. Localiza e foca no campo de mensagem do chat
            box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//footer//div[@contenteditable='true'] | //div[@contenteditable='true'][@data-tab='10']"))
            )
            box.click()
            time.sleep(0.5)

            # 3. Cola o texto completo instantaneamente (Ctrl+V)
            actions = ActionChains(self.driver)
            actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            self.log("Texto colado no campo de mensagem (Ctrl+V).")
            
            # 4. Aguarda tempo seguro para o WhatsApp processar o texto e liberar o botão de envio
            time.sleep(1.5)

            # 5. Clica no botão de envio
            try:
                send_btn = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@data-icon='send'] | //div[@aria-label='Enviar' or @aria-label='Send'] | //button[contains(@aria-label, 'Enviar')]"))
                )
                send_btn.click()
                self.log("Botão de envio clicado com sucesso.")
            except Exception as ex_btn:
                self.log(f"Botão não clicável, enviando ENTER: {ex_btn}")
                actions = ActionChains(self.driver)
                actions.send_keys(Keys.ENTER).perform()

            # 6. Tempo de espera seguro pós-envio para garantir que o WhatsApp transmita a mensagem antes de fechar o driver
            time.sleep(3.0)
            self.log("Mensagem de texto enviada e transmitida com sucesso!")
            return True
        except Exception as e:
            self.log(f"Erro ao enviar texto: {e}")
            return False
            
    def fechar(self):
        if self.driver:
            self.driver.quit()
