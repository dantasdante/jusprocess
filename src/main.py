import os
import json
from typing import List, Dict

# --- Dependências da API ---
from fastapi import FastAPI, HTTPException
from uvicorn import run as uvicorn_run

# --- Dependências do Módulo de Verificação LLM ---
from pydantic import BaseModel, Field
from google import genai
from google.genai import types


# ==============================================================================
# 1. CONTRATOS DE DADOS (Pydantic Schemas)
# ==============================================================================

# CONTRATO DE SAÍDA OBRIGATÓRIO (para o LLM e para a API)
class DecisaoProcesso(BaseModel):
    """Esquema de saída obrigatório para o LLM."""
    
    decision: str = Field(
        ..., 
        description="A decisão final sobre o processo. Deve ser 'approved', 'rejected' ou 'incomplete'."
    )
    rationale: str = Field(
        ..., 
        description="A justificativa clara e concisa para a decisão, baseada estritamente nas regras da Política (POL-X)."
    )
    citacoes: List[str] = Field(
        ..., 
        description="Lista dos IDs das regras da Política (ex: 'POL-1', 'POL-4') que foram aplicadas."
    )

# CONTRATO DE ENTRADA (para a API)
class ProcessoJudicial(BaseModel):
    """Estrutura dos dados de entrada do processo judicial para análise."""
    
    numeroProcesso: str
    esfera: str = Field(description="Ex: Federal, Estadual, Trabalhista.")
    valorCondenacao: float = Field(description="O valor da condenação em Reais.")
    documentos_faltando: bool = Field(description="True se faltar documento essencial (p/ POL-8).")
    transitou_julgado: bool = Field(description="True se o trânsito em julgado estiver comprovado (p/ POL-1).")
    substabelecimento_sem_reserva: bool = Field(description="True se houver substabelecimento sem reserva (p/ POL-6).")
    obito_autor: bool = Field(description="True se houver óbito do autor sem habilitação (p/ POL-5).")


# ==============================================================================
# 2. POLÍTICA E LLM (Lógica de Negócio)
# ==============================================================================

# Variável global para armazenar a chave de API, lida do ambiente.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

POLITICA_JUSCASH = """
Regra-base (elegibilidade)
POL-1: Só compramos crédito de processos transitados em julgado e em fase de execução.
POL-2: Exigir valor de condenação informado.

Quando NÃO compramos o crédito (Rejeitar - rejected)
POL-3: Valor de condenação < R$ 1.000,00 não compra (REJEITAR).
POL-4: Condenações na esfera trabalhista não compra (REJEITAR).
POL-5: Óbito do autor sem habilitação no inventário não compra (REJEITAR).
POL-6: Substabelecimento sem reserva de poderes não compra (REJEITAR).

Saídas e qualidade (Incompleto - incomplete)
POL-8: Se faltar documento essencial (ex.: trânsito em julgado não comprovado) INCOMPLETE.
"""

def verificar_processo_llm_gemini(processo: ProcessoJudicial) -> DecisaoProcesso:
    """
    Usa o Gemini para verificar a conformidade do processo com a Política, 
    forçando a saída estruturada pelo Pydantic Schema.
    """
    global GEMINI_API_KEY
    
    # 1. Verificação da Chave
    if not GEMINI_API_KEY:
        raise ConnectionError("Chave GEMINI_API_KEY não configurada no ambiente.")

    # 2. Inicialização do Cliente (Passando a chave diretamente, a solução robusta)
    # No seu src/main.py, dentro da função verificar_processo_llm_gemini

# 2. Inicialização do Cliente Gemini COM HttpOptions para Timeout
try:
    # Define o timeout na configuração HTTP (60 segundos)
    http_options = types.HttpOptions(
        timeout=300 
    )
    
    # O cliente é inicializado com a chave E a configuração de HTTP/Timeout
    client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=http_options
    )
except Exception as e:
    raise ConnectionError(f"Erro ao inicializar o cliente Gemini: {e}")

    # 3. Instrução (Prompt)
    prompt = f"""
    Você é o Analista de Machine Learning da JusCash. Aplique as regras da Política JusCash
    abaixo nos dados do processo e retorne a sua análise no formato JSON exigido.

    # Regras da Política JusCash:
    {POLITICA_JUSCASH}

    # Dados do Processo:
    {json.dumps(processo.model_dump(), indent=2)}

    Determine a decisão ('approved', 'rejected', 'incomplete') e cite as regras (POL-X) que a justificam.
    """

    # 4. Configuração de Geração com Structured Output
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=DecisaoProcesso, 
    )

    # 5. Chamada à API
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt],
            config=config,
            
        )
        
        # 6. Verificação de Conteúdo Vazio ou Erro
    if not response.text:
        # Se a resposta estiver vazia (a causa do erro JSON)
        raise RuntimeError("O LLM Gemini não retornou nenhum texto (Resposta vazia). Verifique a chave e limites de uso.")

    # 7. Verificação de Bloqueio de Segurança
    if response.prompt_feedback.block_reason != 0:
        # Se o Gemini bloquear o prompt por segurança (BlockReason.SAFETY)
        raise RuntimeError(f"O Prompt foi bloqueado por motivo de segurança: {response.prompt_feedback.block_reason.name}")

    # 8. Retorno do Objeto Pydantic (Só acontece se o texto não for vazio)
    return DecisaoProcesso.model_validate_json(response.text)

except Exception as e:
    # Captura o erro e repassa para a API
    raise RuntimeError(f"Erro na chamada do modelo Gemini: {e}")


# ==============================================================================
# 3. API ENDPOINTS (FastAPI)
# ==============================================================================

app = FastAPI(
    title="JusCash LLM Verifier API",
    description="API para validação de processos judiciais usando Gemini e Pydantic.",
    version="1.0.0",
)

# Endpoint de Saúde (Obrigatório: /health)
@app.get("/health", summary="Verificação de saúde da API")
def health_check():
    """Retorna o status 'ok' para indicar que a API está rodando."""
    return {"status": "ok", "message": "API operacional"}

# Endpoint Principal (para verificar o processo)
@app.post("/verificar", response_model=DecisaoProcesso, summary="Analisa o processo e retorna a decisão estruturada")
def verificar_processo(processo: ProcessoJudicial):
    """
    Recebe os dados de um processo judicial e retorna uma decisão estruturada
    (approved, rejected, incomplete) com justificativa e citações.
    """
    try:
        # Chama a lógica principal de verificação LLM
        decisao = verificar_processo_llm_gemini(processo)
        return decisao
    
    except ConnectionError as e:
        # Erros de configuração (Chave API ausente/inválida)
        raise HTTPException(
            status_code=500, detail=f"Erro de Configuração: {e}"
        )
    except RuntimeError as e:
        # Erros durante a execução do LLM
        raise HTTPException(
            status_code=503, detail=f"Erro no Serviço LLM: {e}"
        )
    except Exception as e:
        # Erros inesperados
        raise HTTPException(
            status_code=500, detail=f"Erro Interno Inesperado: {e}"
        )

# ==============================================================================
# 4. INSTRUÇÕES DE EXECUÇÃO
# ==============================================================================
# Para rodar a API localmente, execute o comando:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Exemplo de uso (Não é necessário rodar no Colab/notebook, mas mantém a estrutura)
'''
if __name__ == "__main__":
    print(f"Chave de API carregada? {'Sim' if GEMINI_API_KEY else 'Não'}")
    print("Iniciando API com Uvicorn (Acesse http://127.0.0.1:8000/docs)")
    # uvicorn_run(app, host="0.0.0.0", port=8000) 
    # Linha comentada pois este ambiente não suporta uvicorn_run
'''
