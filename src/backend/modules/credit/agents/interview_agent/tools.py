from langchain_core.tools import tool

@tool
def transfer_to_triage() -> str:
    """
    Transfere o atendimento de volta para a triagem geral (router) se o cliente quiser falar de outro assunto ou encerrar a conversa.
    """
    return "handoff_triage"
