import streamlit as st
from components.metric_card import render_metric_cards
from components.chat_modal import render_chat_modal
from styles.theme import inject_styles

st.set_page_config(
    page_title="Banco Ágil — Dashboard",
    page_icon="🏦",
    layout="wide"
)

inject_styles()

if not st.session_state.get("access_token") or not st.session_state.get("logged_user"):
    st.switch_page("app.py")

user = st.session_state["logged_user"]

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏦 Banco Ágil")
    st.write(f"**Usuário:** {user['nome']}")
    st.divider()
    if st.button("Sair", width='stretch'):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("app.py")

# ─── Área Principal ───────────────────────────────────────────────────────────
st.header(f"Olá, {user['nome']}!")
st.write("Acompanhe seus dados financeiros abaixo:")

# Métricas (Mock based on the user object)
# Em um sistema real, buscaríamos da API usando o access_token.
# Aqui vamos ler o dado mais atualizado do clientes.csv para refletir as mudanças do LLM.
import os
import csv

clientes_path = os.path.join(os.path.dirname(__file__), "../../backend/data/clientes.csv")
limite_mock = float(user.get("limite_atual", 0))
score_mock = int(user.get("score", 0))

if os.path.exists(clientes_path):
    try:
        with open(clientes_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("cpf_hash") == user.get("cpf_hash"):
                    limite_mock = float(row.get("limite_atual", 0))
                    score_mock = int(row.get("score", 0))
                    
                    # Atualiza o estado da sessão para manter sincronizado com o DB
                    st.session_state["logged_user"]["limite_atual"] = row.get("limite_atual", 0)
                    st.session_state["logged_user"]["score"] = row.get("score", 0)
                    break
    except Exception as e:
        st.error(f"Erro ao ler os dados atualizados do cliente: {e}")

render_metric_cards(
    cpf=user.get("cpf_mask", "XXX.XXX.XXX-XX"),
    score=score_mock,
    limite=limite_mock,
    status="Ativo 🟢"
)

st.divider()

st.subheader("Histórico de Solicitações")
from datetime import datetime
import pandas as pd

csv_path = os.path.join(os.path.dirname(__file__), "../../backend/data/solicitacoes_aumento_limite.csv")
history = []

if os.path.exists(csv_path) and os.path.getsize(csv_path) > 0:
    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("cpf_cliente") == user.get("cpf_hash"):
                    try:
                        dt = datetime.fromisoformat(row["data_hora_solicitacao"])
                        data_str = dt.strftime("%d/%m/%Y %H:%M")
                    except Exception:
                        data_str = row.get("data_hora_solicitacao", "")
                        
                    try:
                        val = float(row.get("novo_limite_solicitado", 0))
                        limite_fmt = f"R$ {val:,.2f}"
                    except Exception:
                        limite_fmt = row.get("novo_limite_solicitado", "")
                    
                    status_raw = row.get("status_pedido", "")
                    
                    history.append({
                        "Data": data_str,
                        "Limite Solicitado": limite_fmt,
                        "Status": status_raw.capitalize()
                    })
    except Exception as e:
        st.error(f"Erro ao ler histórico: {e}")

df = pd.DataFrame(history, columns=["Data", "Limite Solicitado", "Status"])
if df.empty:
    st.info("Nenhuma solicitação de aumento de limite encontrada.")
else:
    st.dataframe(df, width='stretch', hide_index=True)

# ─── Chat Flutuante ───────────────────────────────────────────────────────────
render_chat_modal()
