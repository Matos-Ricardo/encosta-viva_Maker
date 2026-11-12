#!/usr/bin/env bash
# Encosta Viva - inicia a API + Dashboard (macOS / Linux).
# Na primeira vez cria o ambiente virtual e instala as dependências.
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "[1/3] Criando ambiente virtual..."
    python3 -m venv .venv
fi

echo "[2/3] Instalando dependências..."
.venv/bin/python -m pip install -q -r requirements.txt

echo "[3/3] Iniciando a API..."
exec .venv/bin/python main.py
