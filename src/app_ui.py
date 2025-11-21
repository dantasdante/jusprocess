import streamlit as st
import requests
import json
import os

# --- CONFIGURAÇÃO ---
# Lê a variável de ambiente, se não existir, usa 'http://localhost:8000' (para testes locais)
# No deploy final (Docker/Railway), esta variável garantirá o URL correto.
API_URL_BASE = os.getenv("JUSCASH_API_BASE_URL", "http://localhost:8000") 
API_VERIFY_URL = f"{API_URL_BASE}/verificar"

st.set_page_config(
    page_title="JusCash LLM Verificador",
    layout="wide",
)

st.title("🛡️ Verificador de Processos Judiciais (JusCash LLM)")
st.caption("UI para testes manuais. Chama o endpoint da API FastAPI/Gemini.")

# ==============================================================================
# 1. FORMULÁRIO DE ENTRADA (Simula o objeto ProcessoJudicial)
# ==============================================================================

with st.form(key='verification_form'):
    st.subheader("Dados do Processo para Análise")
    
    # Colunas para organização do layout
    col1, col2 = st.columns(2)

    with col1:
        numero = st.text_input("Número do Processo", value="0100000-00.2024.4.01.0000")
        esfera = st.selectbox("Esfera Judicial (POL-4)", ["Federal", "Estadual", "Trabalhista"])
        valor = st.number_input("Valor da Condenação (R$) (POL-3)", value=15000.00, min_value=0.0)
        
    with col2:
        st.markdown("##### Verificações de Documentação e Status")
        transitou = st.checkbox("1. Trânsito em Julgado Comprovado? (POL-1)", value=True)
        doc_falta = st.checkbox("2. Faltam Documentos Essenciais? (POL-8)", value=False)
        substabelecimento = st.checkbox("3. Substabelecimento sem Reserva de Poderes? (POL-6)", value=False)
        obito = st.checkbox("4. Óbito do Autor sem Habilitação? (POL-5)", value=False)

    # Botão de submissão
    submit_button = st.form_submit_button(label='🚀 Verificar Conformidade com LLM')

# ==============================================================================
# 2. LÓGICA DE CHAMADA DA API E EXIBIÇÃO
# ==============================================================================

if submit_button:
    # 2.1. Monta a carga de dados (Payload) que corresponde ao Pydantic Schema
    payload = {
        "numeroProcesso": numero,
        "esfera": esfera,
        "valorCondenacao": valor,
        "documentos_faltando": doc_falta,
        "transitou_julgado": transitou,
        "substabelecimento_sem_reserva": substabelecimento,
        "obito_autor": obito
    }
    
    st.info(f"Aguardando resposta da API LLM em: **{API_VERIFY_URL}**") # Mostra o URL
    
    try:
        # 2.2. Chama o endpoint POST da sua API FastAPI
        # ATENÇÃO: Mudança para API_VERIFY_URL
        response = requests.post(API_VERIFY_URL, json=payload, timeout=40)
        
        # 2.3. Processamento da Resposta
        if response.status_code == 200:
            # Sucesso na verificação
            result = response.json()
            
            # Formatação visual da Decisão
            decision_map = {
                "approved": ("✅ APROVADO", "success"),
                "rejected": ("❌ REJEITADO", "error"),
                "incomplete": ("⚠️ INCOMPLETO", "warning")
            }
            display_text, color = decision_map.get(result.get('decision', 'error'), ("❓ ERRO", "error"))
            
            st.markdown("---")
            st.metric(label="DECISÃO FINAL", value=display_text)
            
            st.markdown(f"#### Justificativa (Rationale)")
            st.code(result.get('rationale'))
            
            st.markdown(f"#### Regras Aplicadas (Citações)")
            st.write(f"**IDs:** `{', '.join(result.get('citacoes', ['Nenhuma']))}`")
            
            st.markdown("---")
            st.markdown("##### JSON Retornado pela API")
            st.json(result)
            
        elif response.status_code == 422:
            # Erro de validação do Pydantic (FastAPI)
            st.error("Erro de Validação: O JSON enviado não corresponde ao schema esperado. Verifique os tipos de dados.")
            st.json(response.json())

        else:
            # Outros erros da API (500, 503, etc.)
            error_detail = response.json().get('detail', 'Nenhuma mensagem de erro fornecida.')
            st.error(f"Erro na API (Código {response.status_code}): {error_detail}")
            
    except requests.exceptions.ConnectionError:
        st.error(f"ERRO DE CONEXÃO: A API FastAPI não está rodando em {API_URL_BASE}.")
        st.warning("Verifique se o seu container Docker/Serviço Cloud está a correr corretamente.")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")
