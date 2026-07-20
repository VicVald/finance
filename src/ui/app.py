"""
Interface Streamlit do Banco Ágil.

Entrypoint Principal (Tela de Login).
"""
import uuid
import requests
import streamlit as st

from styles.theme import inject_styles
from components.user_card import render_user_card

# ─── Config ───────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"
AUTH_LOGIN = f"{API_BASE}/auth/login"

st.set_page_config(
    page_title="Banco Ágil — Login",
    page_icon="🏦",
    layout="centered",
)

inject_styles()

# ─── Session State Init ────────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "access_token": None,
        "refresh_token": None,
        "thread_id": None,
        "logged_user": None,
        "messages": [],
        "awaiting_interrupt": False,
        "interrupt_message": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_session()

# Se já tem token, vai pro dashboard
if st.session_state.access_token and st.session_state.logged_user:
    st.switch_page("pages/dashboard.py")

# ─── API Calls ────────────────────────────────────────────────────────────────
def _login(email: str, senha: str, user_data: dict = None) -> bool:
    resp = requests.post(AUTH_LOGIN, json={"email": email, "senha": senha})
    if resp.status_code == 200:
        data = resp.json()
        st.session_state.access_token = data["access_token"]
        st.session_state.refresh_token = data["refresh_token"]
        st.session_state.thread_id = str(uuid.uuid4())
        
        # Guarda os dados do usuário na sessão para exibir no dashboard
        if user_data:
            st.session_state.logged_user = user_data
        else:
            # Caso o login manual não passe o dicionário completo, buscamos no csv
            csv_path = os.path.join(os.path.dirname(__file__), "../backend/data/clientes.csv")
            found_user = None
            if os.path.exists(csv_path):
                import csv
                try:
                    with open(csv_path, mode="r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            if row.get("email") == email:
                                found_user = row
                                break
                except Exception:
                    pass
            
            if found_user:
                st.session_state.logged_user = found_user
            else:
                st.session_state.logged_user = {"nome": email.split("@")[0].title()}
                
        return True
    return False

# ─── UI ───────────────────────────────────────────────────────────────────────
st.title("🏦 Banco Ágil")
st.subheader("Acesso ao Atendimento")

st.write("### Acesso Rápido (Demo)")

import os
import csv
users = []
csv_path = os.path.join(os.path.dirname(__file__), "../backend/data/clientes.csv")
try:
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users.append(row)
except Exception as e:
    st.error(f"Erro ao ler base de clientes: {e}")

if users:
    cols = st.columns(4)
    for i, user in enumerate(users[:4]):
        with cols[i]:
            def on_login(email=user["email"], senha=user["senha"], u=user):
                with st.spinner("Autenticando..."):
                    if _login(email, senha, u):
                        st.switch_page("pages/dashboard.py")
                    else:
                        st.error("Erro no login rápido.")
            render_user_card(user, on_login)

st.divider()

st.write("### Login Manual")
with st.form("login_form"):
    email = st.text_input("E-mail", placeholder="seu@email.com")
    senha = st.text_input("Senha", type="password")
    submit = st.form_submit_button("Entrar", width='stretch')

if submit:
    with st.spinner("Autenticando..."):
        ok = _login(email, senha)
    if ok:
        st.switch_page("pages/dashboard.py")
    else:
        st.error("E-mail ou senha incorretos.")

st.write("")
st.page_link("pages/register.py", label="Ainda não tem conta? **Cadastre-se**")
