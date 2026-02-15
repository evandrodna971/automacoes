@echo off
title Instalação do ZapFinder Automation
echo ======================================================
echo            ZAPFINDER AUTOMATION - SETUP
echo ======================================================
echo.

REM Verifica Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale o Python 3.10+ e adicione ao PATH.
    echo Baixe em: https://www.python.org/downloads/
    pause
    exit /b
)

echo [INFO] Python encontrado.
echo.

REM Cria ambiente virtual (opcional mas recomendado)
if not exist "venv" (
    echo [INFO] Criando ambiente virtual...
    python -m venv venv
) else (
    echo [INFO] Ambiente virtual ja existe.
)

REM Ativa ambiente e instala dependencias
echo [INFO] Instalando dependencias...
call venv\Scripts\activate
pip install --upgrade pip
if exist "requirements.txt" (
    pip install -r requirements.txt
    echo.
    echo [SUCESSO] Dependencias instaladas!
) else (
    echo [ERRO] Arquivo requirements.txt nao encontrado!
)

echo.
echo ======================================================
echo            INSTALACAO CONCLUIDA
echo ======================================================
echo Para iniciar o programa, execute o arquivo 'run.bat'.
echo.
pause
