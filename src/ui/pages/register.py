import streamlit as st
import requests
import re
import os
from datetime import datetime
from styles.theme import inject_styles

st.set_page_config(
    page_title="Banco Ágil — Cadastro",
    page_icon="🏦",
    layout="centered"
)

inject_styles()

st.title("🏦 Banco Ágil")
st.subheader("Cadastro de Novo Cliente")

API_BASE = os.getenv("BACKEND_URL", "http://localhost:8000")
API_REGISTER = f"{API_BASE}/auth/register"

def validate_cpf(cpf: str) -> bool:
    cpf_clean = re.sub(r"\D", "", cpf)
    return len(cpf_clean) == 11

def validate_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email))

def validate_data(data: str) -> bool:
    try:
        datetime.strptime(data, "%d/%m/%Y")
        return True
    except ValueError:
        return False

with st.form("register_form"):
    nome = st.text_input("Nome Completo")
    cpf = st.text_input("CPF (com ou sem pontuação)")
    data_nasc = st.text_input("Data de Nascimento (DD/MM/AAAA)")
    email = st.text_input("E-mail")
    senha = st.text_input("Senha", type="password")
    submit = st.form_submit_button("Cadastrar", width="stretch")

if submit:
    erros = []
    if not nome or not senha:
        erros.append("Nome e senha são obrigatórios.")
    if not validate_cpf(cpf):
        erros.append("CPF inválido. Deve conter 11 dígitos.")
    if not validate_email(email):
        erros.append("E-mail com formato inválido.")
    if not validate_data(data_nasc):
        erros.append("Data de nascimento inválida. Use o formato DD/MM/AAAA.")
        
    if erros:
        for erro in erros:
            st.error(erro)
    else:
        with st.spinner("Realizando cadastro..."):
            cpf_clean = re.sub(r"\D", "", cpf)
            payload = {
                "nome": nome.strip(),
                "cpf": cpf_clean,
                "data_nascimento": data_nasc,
                "email": email.strip(),
                "senha": senha
            }
            try:
                resp = requests.post(API_REGISTER, json=payload)
                if resp.status_code == 201:
                    st.success("Cadastro realizado com sucesso!")
                    # Utilizando experimental_rerun ou switch page diretamente
                    st.switch_page("app.py")
                else:
                    detail = resp.json().get("detail", "Erro ao cadastrar.")
                    st.error(detail)
            except Exception as e:
                st.error(f"Erro de conexão com a API: {e}")

st.divider()
if st.button("Voltar ao Login", width="stretch"):
    st.switch_page("app.py")
