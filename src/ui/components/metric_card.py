import streamlit as st

def render_metric_cards(cpf: str, score: int, limite: float, status: str):
    """
    Renderiza uma linha de métricas financeiras do usuário.
    """
    cols = st.columns(4)
    
    with cols[0]:
        st.metric(label="CPF", value=cpf)
        
    with cols[1]:
        # Mostra o score numérico. A barra de progresso pode ser adicionada como progress bar do Streamlit.
        st.metric(label="Score de Crédito", value=score)
        st.progress(min(score / 1000.0, 1.0))
        
    with cols[2]:
        st.metric(label="Limite Atual", value=f"R$ {limite:,.2f}")
        
    with cols[3]:
        st.metric(label="Status da Conta", value=status)
