import streamlit as st

def render_user_card(user: dict, on_login: callable):
    """
    Renderiza um card de usuário para a área de Acesso Rápido.
    :param user: Dicionário contendo dados do usuário do clientes.csv
    :param on_login: Função de callback para efetuar login
    """
    with st.container(border=True):
        st.markdown(f"<h1 style='text-align: center;'>{user['nome'][0].upper()}</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; margin-bottom: 0;'><b>{user['nome']}</b></p>", unsafe_allow_html=True)
        # Como temos apenas cpf_hash no DB, criamos um CPF mascarado genérico para a interface visual
        st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.8em;'>CPF: ***.***.***-**</p>", unsafe_allow_html=True)
        if st.button("Entrar", key=f"login_btn_{user['cpf_hash']}", width='stretch'):
            on_login(user["email"], user["senha"])
