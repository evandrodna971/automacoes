import sys
import os
import certifi
import urllib3
import flet as ft

# Desativa avisos de SSL/TLS e configura ambiente seguro para PyInstaller executável
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Se estiver rodando como executavel PyInstaller, configura certifi
if getattr(sys, 'frozen', False):
    cert_path = certifi.where()
    if os.path.exists(cert_path):
        os.environ['REQUESTS_CA_BUNDLE'] = cert_path
        os.environ['SSL_CERT_FILE'] = cert_path
    else:
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''

from ui.app import main_app

if __name__ == "__main__":
    ft.app(target=main_app)
