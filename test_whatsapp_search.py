import sys
import time
from core.whatsapp import WhatsAppBot
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

bot = WhatsAppBot()
print("Iniciando driver...")
bot.iniciar_driver()

time.sleep(15) 

try:
    print("Buscando input de pesquisa...")
    search_box = bot.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Pesquisar') or contains(@placeholder, 'Search') or contains(@placeholder, 'nova')]")
    search_box.click()
    search_box.send_keys("Ronaldo Clamed")
    time.sleep(2)
    
    chat = bot.driver.find_element(By.XPATH, "//span[@title='Ronaldo Clamed']")
    chat.click()
    print("Chat clicado!")
    time.sleep(3)
    
    print("Inputs/Editables apos abrir chat:")
    els = bot.driver.find_elements(By.XPATH, "//*[@contenteditable='true'] | //input | //p[@contenteditable='true']")
    for e in els:
        print(f"Tag: {e.tag_name}, Class: {e.get_attribute('class')}, Title: {e.get_attribute('title')}, Placeholder: {e.get_attribute('placeholder')}")
        
except Exception as e:
    print("Erro durante execucao:", e)

bot.driver.save_screenshot("screenshot_chat.png")
bot.fechar()
