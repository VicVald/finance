# ADR-009: Ajustes de Triagem, Logs e Rastreabilidade

**Status:** Aceito  
**Data:** 2026-07-19  
**Decididores:** Antigravity (AI Agent), Victor  

---

## Contexto

Durante o uso da aplicação Banco Ágil, foram identificados alguns problemas na experiência de triagem e no monitoramento do sistema:
1. **Falha de Correlação do CPF**: O assistente virtual não validava se o CPF inserido no chat correspondia ao cliente atualmente logado no dashboard, permitindo possíveis inconsistências de segurança ou conflitos de dados.
2. **Ausência de Logs na UI**: O usuário não conseguia inspecionar os logs de execução em tempo real na interface Streamlit.
3. **Mapeamento Incompleto do LangSmith**: As variáveis de ambiente do LangSmith não eram exportadas corretamente para as variáveis com prefixo `LANGCHAIN_` consumidas internamente pela biblioteca LangChain/LangGraph, resultando na ausência de rastreabilidade do fluxo e do estado geral nos traces do LangSmith.
4. **Fechamento Abrupto do Chat**: No caso de exceder 3 tentativas de autenticação, o grafo encerrava sem enviar uma mensagem amigável de erro e sem desabilitar a entrada de texto do chat no Streamlit.

---

## Decisão

### 1. Validação de CPF Cruzada
Adicionar o campo `current_user_cpf_hash` no `RouterState` do LangGraph. Este campo é inicializado no endpoint `/stream` com o hash do CPF do usuário logado obtido a partir da dependência `get_current_user` do FastAPI.
Durante a chamada de `authenticate_client` no `triage_node`, o sistema valida se o hash do CPF fornecido pelo usuário corresponde ao hash do usuário ativo:
```python
if result.get("authenticated") and result.get("cpf_hash") == state.current_user_cpf_hash:
    # Autenticado com sucesso
else:
    # Tratado como falha de autenticação
```

### 2. Monitoramento de Logs
Habilitar a gravação de logs no backend utilizando `logging.basicConfig` configurado com `level=logging.DEBUG`.
O frontend Streamlit lerá as últimas linhas deste arquivo e as renderizará dinamicamente em um expander de logs na barra lateral (sidebar) para visualização imediata do desenvolvedor/usuário.

### 3. Mapeamento de Variáveis do LangSmith
Se `LANGSMITH_TRACING` estiver ativo, o `core/config.py` exportará dinamicamente as variáveis `LANGSMITH_*` para o `os.environ` como `LANGCHAIN_*`, garantindo que o ciclo de vida completo do grafo, transição de nós e o estado geral apareçam nos traces do LangSmith.

### 4. Encerramento Gentil e Controle do Input
- Se o usuário falhar na 3ª tentativa, o `triage_node` insere uma `AIMessage` explicativa ("Acesso bloqueado...") no estado antes de encerrar o grafo.
- O endpoint SSE retorna a propriedade `is_conversation_ended` ao finalizar o stream.
- O Streamlit desabilita o campo `st.chat_input` quando `is_conversation_ended` for True, e insere uma mensagem amigável inicial ao abrir a conversa pela primeira vez.

---

## Consequências

**Positivas:**
- Aumento da segurança, impedindo autenticação de CPF de terceiros no chat do usuário logado.
- Observabilidade aprimorada com exibição de logs na UI e rastreamento robusto e completo do LangGraph no LangSmith.
- Melhor experiência do usuário (UX) com mensagens claras de erro, boas-vindas padrão e bloqueio visual do input do chat ao final do atendimento.
