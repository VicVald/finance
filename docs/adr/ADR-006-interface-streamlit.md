# ADR-006: Interface Streamlit do Banco Ágil

**Status:** Aceito  
**Data:** 2026-07-19  
**Decididores:** Victor  

---

## Contexto

O desafio requer uma UI de testes para simular atendimento bancário completo. A interface deve ter identidade visual do **Banco Ágil** com a paleta definida, telas de login/registro, dashboard de dados do cliente e um chat integrado ao router LangGraph.

---

## Decisão

### Paleta de Cores

| Nome | Hex | Uso |
|------|-----|-----|
| Dusty Denim | `#6290C3` | Cor primária, botões principais, links |
| Frozen Water | `#C2E7DA` | Fundos de cards, badges de status |
| Honeydew | `#F1FFE7` | Background geral da aplicação |
| Space Indigo | `#1A1B41` | Textos principais, sidebar, headers |
| Chartreuse | `#BAFF29` | CTAs de destaque, badges ativos, indicadores |

### Estrutura de Páginas

```
src/ui/
├── app.py                  # Entrypoint principal
├── pages/
│   ├── login.py            # Tela de login com 4 cards de usuário
│   ├── dashboard.py        # Tela principal após login
│   └── register.py         # Tela de cadastro (fluxo opcional)
├── components/
│   ├── chat_modal.py       # Modal do chat flutuante
│   ├── user_card.py        # Card de usuário pré-definido
│   └── metric_card.py      # Card de métricas do dashboard
└── styles/
    └── theme.py            # Injeção de CSS customizado via st.markdown
```

### Tela de Login

**Layout:** Centralizado, com logo do Banco Ágil e título.

**4 Cards de Usuário Pré-Definidos:**
- Exibidos em grade 2×2 ou linha de 4
- Cada card contém: avatar (inicial do nome), nome do cliente, CPF mascarado
- 1 clique → login direto (entra no dashboard sem novo formulário)
- Os 4 usuários são idênticos aos registros do `clientes.csv` (populados automaticamente na inicialização da app)

**Fluxo de Clique no Card:**
```
1. Clique no card → st.session_state["logged_user"] = {nome, cpf_hash, ...}
2. Streamlit rerun → redireciona para dashboard.py
```

**Formulário de Login Manual:** Campo CPF + campo senha (alternativa aos cards)

**Link para Registro:** Direciona para `register.py`

### Tela de Dashboard

**Layout:** Sidebar + área principal

**Sidebar:**
- Nome do banco ("Banco Ágil") com logo
- Nome do usuário logado
- Botão "Sair" (limpa `st.session_state` e redireciona para login)

**Área Principal:**
- Cabeçalho: "Olá, {Nome}!"
- **Cards de métricas (linha horizontal):**
  - CPF: mascarado (`123.***.***-09`)
  - Score de crédito: valor atual (0-1000) com barra de progresso colorida
  - Limite de crédito atual: valor em BRL formatado
  - Status da conta: Ativo/Inativo com badge colorido
- **Tabela de histórico de solicitações:**
  - Lê de `solicitacoes_aumento_limite.csv` filtrando pelo `cpf_hash` do usuário logado
  - Colunas: Data, Limite Solicitado, Status (com cores: verde/aprovado, vermelho/rejeitado, amarelo/pendente)

### Chat Flutuante (Componente Principal)

**Botão de Abertura:**
- Posição: canto inferior direito (fixed)
- Ícone: 💬 (chat bubble)
- Implementado via CSS injetado + `st.markdown` com HTML customizado

**Modal do Chat:**
- Abre sobre o conteúdo atual sem navegar
- Estado do chat **salvo em `st.session_state`** — fechar e reabrir não perde o histórico
- Campos:
  - Histórico de mensagens (scrollável)
  - Input de texto
  - Botão "Enviar"
  - Botão "Reiniciar Conversa" (no topo do modal) — gera novo `thread_id` e limpa histórico do state
  - **Ações Interativas (Botões na UI):**
    - Quando o Agente de Crédito recusa um aumento de limite e oferece a entrevista de reavaliação de score, o chat exibe dois botões de ação rápida: **"Gostaria de fazer a entrevista"** e **"Mais tarde"**.
    - O clique nesses botões injeta a resposta correspondente no chat, disparando o gatilho de handoff no router.

**Integração com LangGraph:**
```python
# Chamada ao router via thread_id da sessão atual
config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
response = router_graph.invoke(
    {"messages": [HumanMessage(content=user_input)]},
    config=config
)
```

**Persistência do Chat na Sessão:**
```python
# st.session_state garante persistência enquanto o browser mantém a sessão
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "chat_open" not in st.session_state:
    st.session_state["chat_open"] = False
```

### Customização Visual via CSS Injetado

```python
# styles/theme.py
CUSTOM_CSS = """
<style>
:root {
    --color-primary: #6290C3;
    --color-secondary: #C2E7DA;
    --color-background: #F1FFE7;
    --color-dark: #1A1B41;
    --color-accent: #BAFF29;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: var(--color-dark) !important;
    color: white !important;
}

/* Botão flutuante do chat */
.chat-fab {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background-color: var(--color-primary);
    color: white;
    font-size: 1.5rem;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    z-index: 999;
}
</style>
"""

def inject_styles():
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
```

---

## Alternativas Consideradas

| Opção | Motivo de Rejeição |
|-------|-------------------|
| Next.js / React | Over-engineering para o escopo do desafio; Streamlit é o requisito explícito |
| Chat em página separada | Perde a experiência de chat flutuante sobre o dashboard |
| `st.chat_message` nativo sem modal | Não permite o comportamento de janela flutuante; perde o estado ao navegar |

---

## Consequências

**Positivas:**
- Streamlit `session_state` garante persistência do chat sem backend adicional
- CSS injetado via `st.markdown(unsafe_allow_html=True)` permite customização completa da paleta
- 4 cards de login tornam o sistema imediatamente demonstrável sem necessidade de memorizar dados

**Negativas:**
- Botão flutuante fixed requer CSS injetado; Streamlit não suporta `position: fixed` nativamente sem workarounds
- Streamlit re-executa o script inteiro a cada interação (cuidado com chamadas ao LangGraph repetidas — usar `st.session_state` para cachear respostas)
- A tela de registro não está integrada ao fluxo do agente de triagem (é apenas para fins de demo da UI)

---

## Referências

- [ADR-001: Arquitetura Geral](./ADR-001-arquitetura-geral-de-agentes.md)
- [ADR-002: Orquestração e Handoff](./ADR-002-orquestracao-e-handoff.md)
- [Streamlit Session State](https://docs.streamlit.io/library/api-reference/session-state)
