#!/bin/bash
# Script para iniciar a API FastAPI e a UI Streamlit

echo "Iniciando a API FastAPI em background na porta 8000..."
# Inicia a API Uvicorn (FastAPI) e envia para o background (&)
# --host 0.0.0.0 é crucial para ambientes de container
# Não use --reload em produção!
uvicorn main:app --host 0.0.0.0 --port 8000 &

echo "Aguardando 5 segundos para a API iniciar..."
sleep 5

# Define a variável de ambiente para que a UI saiba onde está a API.
# Como a API está a correr no mesmo container, o endereço é localhost.
export JUSCASH_API_BASE_URL="http://localhost:8000"

echo "Iniciando a Interface Visual (Streamlit) na porta 8501..."
# Inicia a UI Streamlit (em foreground)
streamlit run app_ui.py --server.port 8501 --server.address 0.0.0.0
