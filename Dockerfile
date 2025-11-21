# Usa uma imagem oficial do Python para performance
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o requirements.txt primeiro para cachear a instalação
COPY src/requirements.txt .

# Instala as dependências (incluindo uvicorn, fastapi, streamlit e google-genai)
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código fonte para o WORKDIR /app
COPY src/ .

# Exposição das portas: a API (8000) e o Streamlit (8501 - porta padrão)
# Nota: A porta 8000 é usada pelo uvicorn, 8501 pelo streamlit.
EXPOSE 8000
EXPOSE 8501

# Comando de execução. 
# Importante: Como são duas aplicações separadas (API e UI), 
# é mais fácil fazer o deploy do Streamlit e a UI do Streamlit 
# fazer a chamada HTTP para a API rodando separadamente.
# Para este Case, vamos simplificar para rodar APENAS o Streamlit, 
# pois ele fará o deploy mais fácil.

# Este CMD executa APENAS o Streamlit.
# A API (FastAPI) será chamada pelo app_ui.py. 
# IMPORTANTE: Se o deploy for feito no Streamlit Cloud, 
# ele só consegue rodar UMA aplicação (Streamlit).

CMD ["streamlit", "run", "app_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]

# Se você fizer o deploy em um serviço como Railway ou Render que 
# permite múltiplos serviços ou processos (via script bash), 
# a configuração seria mais complexa. Para o Streamlit Cloud,
# este CMD é o ideal.
