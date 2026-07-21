import streamlit as st
import uuid
import json
import requests
import os

API_BASE = os.getenv("BACKEND_URL", "http://localhost:8000")
AUTH_REFRESH = f"{API_BASE}/auth/refresh"
AGENT_STREAM = f"{API_BASE}/api/v1/agent/stream"
AGENT_RESUME = f"{API_BASE}/api/v1/agent/resume"

def _auth_headers() -> dict:
    return {"Authorization": f"Bearer {st.session_state.access_token}"}

def _try_refresh() -> bool:
    resp = requests.post(AUTH_REFRESH, json={"refresh_token": st.session_state.refresh_token})
    if resp.status_code == 200:
        data = resp.json()
        st.session_state.access_token = data["access_token"]
        st.session_state.refresh_token = data["refresh_token"]
        return True
    return False

def _resume_interview(aceite: bool) -> str:
    payload = {
        "thread_id": st.session_state.thread_id,
        "resume_value": aceite,
    }
    headers = {**_auth_headers(), "Accept": "text/event-stream"}
    resp = requests.post(AGENT_RESUME, json=payload, headers=headers, stream=True)
    if resp.status_code == 401 and _try_refresh():
        headers.update(_auth_headers())
        resp = requests.post(AGENT_RESUME, json=payload, headers=headers, stream=True)

    if not resp.ok:
        return "Erro ao processar resposta."

    full_text = ""
    for line in resp.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8") if isinstance(line, bytes) else line
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("data:"):
            raw = line[5:].strip()
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if event_type == "token":
                full_text += data.get("content", "")
            elif event_type in ("done", "error"):
                if event_type == "done":
                    st.session_state.is_conversation_ended = data.get("is_conversation_ended", False)
                break

    return full_text

def render_chat_modal():
    """Renderiza o modal flutuante de chat (FAB)."""
    # Popover acts as the modal. We styled its button to look like a FAB in theme.py.
    with st.popover("💬", width='content'):
        st.markdown("### Atendimento Banco Ágil")
        
        # Botão para reiniciar conversa (limpa mensagens e gera novo thread_id)
        if st.button("Reiniciar Conversa", key="restart_chat_btn", width='stretch'):
            st.session_state.messages = []
            st.session_state.thread_id = str(uuid.uuid4())
            st.session_state.awaiting_interrupt = False
            st.session_state.is_conversation_ended = False
            st.rerun()

        # Se a lista de mensagens estiver vazia, adicionamos a mensagem de boas-vindas padrão
        if not st.session_state.messages:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Olá! Seja bem-vindo ao atendimento do Banco Ágil. Para iniciar, por favor informe o seu CPF e sua data de nascimento para realizar a autenticação."
            })

        # Usamos um container com altura fixa para simular um modal scrollável
        chat_container = st.container(height=400)
        
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if st.session_state.awaiting_interrupt:
                with st.chat_message("assistant"):
                    st.markdown(st.session_state.interrupt_message)
                    col_sim, col_nao = st.columns(2)
                    with col_sim:
                        if st.button("✅ Gostaria de fazer a entrevista", key="btn_aceitar", width='stretch'):
                            st.session_state.messages.append({
                                "role": "user",
                                "content": "Sim, quero fazer a entrevista de crédito."
                            })
                            st.session_state.awaiting_interrupt = False
                            with st.chat_message("assistant"):
                                with st.spinner(""):
                                    resposta = _resume_interview(aceite=True)
                            st.session_state.messages.append({"role": "assistant", "content": resposta})
                            st.rerun()
                    with col_nao:
                        if st.button("❌ Mais tarde", key="btn_recusar", width='stretch'):
                            st.session_state.messages.append({
                                "role": "user",
                                "content": "Não, obrigado."
                            })
                            st.session_state.awaiting_interrupt = False
                            with st.chat_message("assistant"):
                                with st.spinner(""):
                                    resposta = _resume_interview(aceite=False)
                            st.session_state.messages.append({"role": "assistant", "content": resposta})
                            st.rerun()
                # Interrompe o fluxo para não renderizar input se estamos aguardando
                return

        # Input do chat (fora do container com scroll)
        is_ended = st.session_state.get("is_conversation_ended", False)
        if prompt := st.chat_input("Digite sua mensagem...", disabled=is_ended):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    accumulated = ""
                    
                    payload = {"message": prompt, "thread_id": st.session_state.thread_id}
                    headers = {**_auth_headers(), "Accept": "text/event-stream"}
                    interrupt_data = None
                    event_type = ""

                    try:
                        resp = requests.post(AGENT_STREAM, json=payload, headers=headers, stream=True)
                        if resp.status_code == 401 and _try_refresh():
                            headers.update(_auth_headers())
                            resp = requests.post(AGENT_STREAM, json=payload, headers=headers, stream=True)

                        with resp:
                            for line in resp.iter_lines():
                                if not line:
                                    continue
                                line = line.decode("utf-8") if isinstance(line, bytes) else line

                                if line.startswith("event:"):
                                    event_type = line[6:].strip()
                                elif line.startswith("data:"):
                                    raw = line[5:].strip()
                                    try:
                                        data = json.loads(raw)
                                    except Exception:
                                        continue

                                    if event_type == "token":
                                        accumulated += data.get("content", "")
                                        display_text = accumulated.replace("[HANDOFF:credit]", "").replace("[HANDOFF:exchange]", "").replace("[HANDOFF:interview]", "").replace("[INTERVIEW_DONE]", "").replace("[RETURN_TRIAGE]", "")
                                        placeholder.markdown(display_text + "▌")
                                    elif event_type == "interrupt":
                                        interrupt_data = data
                                    elif event_type in ("done", "error"):
                                        if event_type == "done":
                                            st.session_state.is_conversation_ended = data.get("is_conversation_ended", False)
                                        break
                    except requests.exceptions.RequestException as e:
                        accumulated = "Erro de conexão com o servidor de IA."

                    placeholder.markdown(accumulated)

            if accumulated:
                clean_accumulated = accumulated.replace("[HANDOFF:credit]", "").replace("[HANDOFF:exchange]", "").replace("[HANDOFF:interview]", "").replace("[INTERVIEW_DONE]", "").replace("[RETURN_TRIAGE]", "").strip()
                if clean_accumulated:
                    st.session_state.messages.append({"role": "assistant", "content": clean_accumulated})

            if interrupt_data:
                st.session_state.awaiting_interrupt = True
                st.session_state.interrupt_message = interrupt_data.get("message", "")
            
            st.rerun()
