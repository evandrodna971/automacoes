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
if exist "dist_nova" rmdir /s /q dist_nova
if exist "*.spec" del /q *.spec

REM Compila
echo.
echo [INFO] Compilando ZapFinder_Atualizado.exe...
echo Isso pode demorar alguns minutos.
echo.

pyinstaller --noconfirm ^
            --onefile ^
            --windowed ^
            --name "ZapFinder_Atualizado" ^
            --distpath "dist_nova" ^
            --collect-all "flet" ^
            --collect-all "flet_desktop" ^
            --hidden-import "flet" ^
            --hidden-import "flet_desktop" ^
            --hidden-import "selenium" ^
            --icon "NONE" ^
            main.py

echo.
if exist "dist_nova\ZapFinder_Atualizado.exe" (
    echo ======================================================
    echo            BUILD CONCLUIDO COM SUCESSO!
    echo ======================================================
    echo O executavel esta na pasta: dist_nova\ZapFinder_Atualizado.exe
    echo.
) else (
    echo [ERRO] Falha na compilacao. Verifique as mensagens acima.
)

pause
