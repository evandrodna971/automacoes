@echo off
title Build ZapFinder Automation
echo ======================================================
echo            ZAPFINDER AUTOMATION - BUILD
echo ======================================================
echo.

REM Verifica Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    pause
    exit /b
)

REM Cria/Ativa ambiente virtual
if not exist "venv" (
    echo [INFO] Criando ambiente virtual...
    python -m venv venv
)
call venv\Scripts\activate

REM Instala dependencias e pyinstaller
echo [INFO] Instalando dependencias e PyInstaller...
pip install -r requirements.txt
pip install pyinstaller

REM Limpa builds anteriores
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del /q *.spec

REM Compila
echo.
echo [INFO] Compilando ZapFinder.exe...
echo Isso pode demorar alguns minutos.
echo.

pyinstaller --noconfirm ^
            --onefile ^
            --windowed ^
            --name "ZapFinder" ^
            --hidden-import "flet" ^
            --hidden-import "selenium" ^
            --icon "NONE" ^
            main.py

echo.
if exist "dist\ZapFinder.exe" (
    echo ======================================================
    echo            BUILD CONCLUIDO COM SUCESSO!
    echo ======================================================
    echo O executavel esta na pasta: dist\ZapFinder.exe
    echo.
) else (
    echo [ERRO] Falha na compilacao. Verifique as mensagens acima.
)

pause
