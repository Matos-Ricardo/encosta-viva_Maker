@echo off
REM Encosta Viva - inicia a API + Dashboard com um duplo clique (Windows).
REM Na primeira vez cria o ambiente virtual e instala as dependencias.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Criando ambiente virtual...
    py -m venv .venv
    if errorlevel 1 python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
    echo ERRO: nao foi possivel criar o ambiente virtual. Instale o Python 3.9 ou superior em python.org
    pause
    exit /b 1
)

echo [2/3] Instalando dependencias...
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERRO: falha ao instalar as dependencias. Confira a internet e tente de novo.
    pause
    exit /b 1
)

echo [3/3] Iniciando a API...
".venv\Scripts\python.exe" main.py
pause
