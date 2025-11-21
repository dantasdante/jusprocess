# Usa uma imagem oficial do Python
FROM python:3.11-slim

WORKDIR /app

# Copia e instala dependências
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código fonte e o script de inicialização
COPY src/ .

# Torna o script de inicialização executável
RUN chmod +x start.sh

# A porta 8501 é a porta do Streamlit que o serviço de hosting deve expor (front-end)
# A porta 8000 é usada internamente para a comunicação UI <-> API
EXPOSE 8000
EXPOSE 8501

# Comando de execução:
# Define a variável de ambiente (GEMINI_API_KEY) que deve ser passada pelo Docker/Cloud
# E executa o script que inicia os dois apps.
CMD ["./start.sh"]
