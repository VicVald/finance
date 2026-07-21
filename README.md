# 🏦 Banco Ágil - Sistema Multi-Agentes de IA para Serviços Bancários

Um sistema inteligente de atendimento bancário baseado em múltiplos agentes de IA especializados, orquestrados através de um roteador central. O sistema utiliza **LangGraph + LangChain** para construir uma experiência fluida onde cada agente é especialista em seu domínio.

## 📋 Visão Geral do Projeto

O Banco Ágil é uma solução de demonstração (PoC) que implementa:

- ✅ **Autenticação segura** via login JWT + CPF + data de nascimento com JWT
- ✅ **Múltiplos agentes especializados** (Crédito, Entrevista Financeira, Câmbio)
- ✅ **Orquestração dinâmica** com handoff transparente entre agentes
- ✅ **Rastreabilidade completa** via LangSmith + CSV de auditoria
- ✅ **Proteção de dados** com masking de PII e hash SHA-256 para CPF
- ✅ **Streaming de respostas** em tempo real via SSE
- ✅ **Interface simplificada** em Streamlit

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    UI STREAMLIT (Port 8501)                 │
│              Interface de Chat com o Cliente                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                       HTTP (SSE)
                           │
┌──────────────────────────▼──────────────────────────────────┐
│               FASTAPI BACKEND (Port 8000)                   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Router/Triagem (Orquestrador)              │   │
│  │  - Autenticação (CPF + Data de Nascimento)           │   │
│  │  - Detecção de intenção                              │   │
│  │  - Roteamento inteligente entre agentes              │   │
│  │  - Encerrar atendimento                              │   │
│  └─────────┬──────────────────┬──────────────────┬──────┘   │
│            │                  │                  │          │
│     ┌──────▼───────┐  ┌───────▼───────┐  ┌───────▼───────┐  │
│     │ Agente       │  │ Agente de     │  │ Agente de     │  │
│     │ de Crédito   │  │ Entrevista    │  │ Câmbio        │  │
│     │              │  │ Financeira    │  │ (Câmbio)      │  │
│     │ - Consulta   │  │ - Análise     │  │ - Cotação USD │  │
│     │   limite     │  │   financeira  │  │ - Cotação EUR │  │
│     │ - Aumento    │  │ - Recálculo   │  │ - APIs:       │  │
│     │   limite     │  │   de score    │  │   BrasilAPI   │  │
│     │ - Score      │  │               │  │   AwesomeAPI  │  │
│     └──────────────┘  └───────────────┘  └───────────────┘  │
│                                                             │
│  CSV Data Layer:                                            │
│  - clientes.csv (CPF hash, limites, scores)                 │
│  - score_limite.csv (regras de limite por score)            │
│  - solicitacoes_aumento_limite.csv (histórico)              │
│  - trace_eventos.csv (auditoria de eventos)                 │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Fluxo de Interação dos Agentes

```
1. AUTENTICAÇÃO (Router)
   Cliente → "Olá, sou João Silva"
   Router → Pede CPF + Data de Nascimento
   Router → Valida contra clientes.csv (hash SHA-256)
   ✓ Autenticado

2. HANDOFF AUTOMÁTICO (Router detecta intenção)
   Cliente → "Qual é meu limite de crédito?"
   Router → Detecta: intenção de CRÉDITO
   Router → Handoff para: Agente de Crédito

3. AGENTE DE CRÉDITO
   Agente → Consulta clientes.csv
   Agente → "Seu limite atual é R$ 5.000"
   Cliente → "Gostaria de aumentar meu limite para 5500"
   Agente → Analisa regras de crédito (ex: score >= 800 e aumento <= 50%)
   Agente → Se aprovado: Atualiza limite no clientes.csv e aprova direto sem entrevista

4. REJEITADO? → HANDOFF PARA ENTREVISTA
   Agente de Crédito → Solicitação rejeitada (score insuficiente)
   Router → Detecta: cliente deseja recalcular score/entrevista
   Router → Handoff para: Agente de Entrevista

5. ENTREVISTA FINANCEIRA
   Agente → Faz perguntas sobre renda, despesas, etc.
   Agente → Recalcula score baseado em respostas
   Agente → Se score ↑ → Autoriza aumento
   Router → Handoff volta para: Agente de Crédito

6. AGENTE SECUNDÁRIO (Câmbio)
   Cliente → "Qual a cotação do dólar?"
   Router → Detecta: intenção de CÂMBIO
   Router → Handoff para: Agente de Câmbio
   Agente → Chama BrasilAPI/AwesomeAPI
   Agente → Retorna cotação atualizada

7. ENCERRAMENTO
   Cliente → "Encerrar conversa"
   Router → Seta is_conversation_ended = True
   Router → Registra evento em trace_eventos.csv
   Conversa encerrada
```

## 📊 Dados de Exemplo (CSV)

### Usuários no `clientes.csv`

O arquivo contém usuários de teste com dados hashados. Para usar os usuários de exemplo:

| Cliente | CPF | Data Nascimento |
|---------|-----------------|-----------------|
| João Silva | 11111111111 | 15/05/1990 
| Maria Oliveira | 22222222222 | 20/10/1985 
| Pedro Santos | 33333333333 | 03/03/1995 
| Ana Costa | 44444444444 | 12/12/1988 

**Como fazer login com esses usuários:**

Os usuários existem no sistema como CPF + data de nascimento. A senha é armazenada por hash. Para testar, use dados reais que correspondam aos CPFs:

```
Exemplo:
  CPF: Use um dos CPFs reais do clientes.csv
  Data de Nascimento: Use a data correspondente (ex: 15/05/1990)
  Senha: Qualquer uma (a validação atual usa CPF + data de nascimento)
```

> **Nota:** Os CPFs reais são armazenados como hash SHA-256 com salt no arquivo para proteção de dados (LGPD).

### Regras de Limite por Score (`score_limite.csv`)

```
Score 0-300       → Limite máximo: R$ 500
Score 301-500     → Limite máximo: R$ 2.000
Score 501-700     → Limite máximo: R$ 5.000
Score 701-850     → Limite máximo: R$ 10.000
Score 851-1000    → Limite máximo: R$ 25.000
```

O score é recalculado pelo **Agente de Entrevista Financeira** baseado em:
- Renda declarada
- Despesas mensais
- Histórico de pagamentos
- Tempo como cliente

## 🚀 Como Usar

### ⚙️ Variáveis de Ambiente

Antes de iniciar o projeto, crie o arquivo `.env` a partir do template:

```bash
cp .env.example .env
```

Variáveis cruciais para o funcionamento:
- `OPENROUTER_API_KEY` (ou `OPENAI_API_KEY`): Obrigatório para o funcionamento do LLM.
- `BACKEND_URL`: A URL do backend que a UI vai consumir.
  - Se rodar **Localmente**: `http://localhost:8000`
  - Se rodar via **Docker**: `http://backend:8000` (utilizando a rede interna do Docker).
- **Integração com LangSmith** (Opcional, mas recomendado para evals/tracing):
  - `LANGSMITH_TRACING=true`
  - `LANGSMITH_API_KEY=sua_chave`
  - `LANGSMITH_PROJECT="Finance"`

### Opção 1: Com Docker Compose (Recomendado)

```bash
# 1. Configure as variáveis de ambiente (conforme acima)

# 2. Build e inicie os containers
docker-compose up --build

# Backend: http://localhost:8000
# UI: http://localhost:8501
```

### Opção 2: Local (Desenvolvimento)

```bash
# 1. Instale uv (gerenciador de pacotes Python)
# macOS: brew install uv
# Linux: curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Sincronize as dependências
uv sync

# 3. Configure o .env
cp .env.example .env
# Edite e preencha suas chaves

# 4a. Execute o Backend (em um terminal)
.venv/bin/python -m uvicorn src.backend.main:app --reload

# 4b. Execute a UI (em outro terminal)
.venv/bin/streamlit run src/ui/streamlit_app.py

# Backend: http://localhost:8000
# UI: http://localhost:8501
```

## 🔐 Segurança e Proteção de Dados

### Proteção de CPF (PII - Personally Identifiable Information)

**Armazenamento:**
- CPF é armazenado como **hash SHA-256 com salt** no `clientes.csv`
- Nunca armazenamos CPF em texto puro
- Cada arquivo CSV de auditoria mascara CPF como: `123.XXX.XXX-09`

**Masking em Tempo Real:**
- Middleware LangChain `PIIRedactionCallback` reduz CPF antes de enviar ao LLM
- As respostas do agente exibem apenas os 3 primeiros e 2 últimos dígitos
- LangSmith traces também utilizam CPF mascarado

**Autenticação:**
- JWT com expiração de 15 minutos (access token)
- Refresh token com expiração de 7 dias
- 3 tentativas de autenticação antes de bloquear sessão

### Conformidade LGPD

- ✅ CPF armazenado apenas como hash
- ✅ Consentimento implícito no login
- ✅ Logs auditáveis de todas as operações
- ✅ Dados mascarados em outputs

## 📐 Decisões Arquiteturais (ADRs)

O projeto segue a metodologia **Architecture Decision Records (ADR)** em `/docs/adr/`:

| ADR | Título | Decisão |
|-----|--------|---------|
| ADR-001 | Arquitetura Geral | LangGraph + LangChain para orquestração multi-agentes |
| ADR-002 | Orquestração e Handoff | Router central com subgraphs compilados por domínio |
| ADR-003 | Gerenciamento de Estado | Pydantic BaseModel para validação de estados |
| ADR-004 | Rastreabilidade | LangSmith + CSV local para auditoria |
| ADR-005 | Segurança e PII | Hash SHA-256 + masking em middleware |
| ADR-006 | Interface Streamlit | Componentes customizados para chat e métricas |
| ADR-007 | Agente de Câmbio | BrasilAPI + AwesomeAPI com fallback |
| ADR-008 | Autenticação JWT | Token-based com refresh token |
| ADR-009 | Ajustes de Triage | Melhorias na detecção de intenção |
| ADR-010 | Melhorias no Fluxo de Crédito | Aprovação direta baseada em regras, evitando entrevistas desnecessárias, com persistência no CSV |
| ADR-011 | SSE Streaming Limpo | Filtragem de tags de controle (ex: `[HANDOFF:...]`) diretamente na camada de API para UI limpa |

Leia os detalhes completos em `/docs/adr/`.

## 📁 Estrutura de Diretórios

```
finance/
├── src/
│   ├── backend/
│   │   ├── main.py                    # Entry point FastAPI
│   │   ├── core/
│   │   │   ├── agents/
│   │   │   │   └── router_agent/      # Grafo raiz (orquestrador)
│   │   │   ├── auth/                  # Autenticação JWT
│   │   │   └── config.py              # Configurações globais
│   │   ├── modules/
│   │   │   ├── credit/                # Domínio: Crédito
│   │   │   │   ├── agents/
│   │   │   │   │   ├── credit_agent/  # Consulta de limite
│   │   │   │   │   └── interview_agent/ # Entrevista financeira
│   │   │   │   ├── models.py
│   │   │   │   └── services.py
│   │   │   └── exchange/              # Domínio: Câmbio
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── agent_routes.py    # Endpoints SSE
│   │   └── data/
│   │       ├── clientes.csv           # Base de clientes
│   │       ├── score_limite.csv       # Regras de limite
│   │       ├── solicitacoes_aumento_limite.csv
│   │       └── trace_eventos.csv      # Auditoria
│   └── ui/
│       ├── streamlit_app.py           # Entry point Streamlit
│       └── components/
├── docs/
│   └── adr/                           # Decisões arquiteturais
├── Dockerfile.backend                 # Build backend
├── Dockerfile.ui                      # Build UI
├── docker-compose.yml                 # Orquestração local
├── pyproject.toml                     # Dependências (uv)
├── uv.lock                            # Lock file (reproducível)
├── .env.example                       # Template de variáveis
└── README.md                          # Este arquivo
```

## 🧪 Testando o Sistema

### 1. Testes Automatizados (pytest)

Para executar a suíte de testes unitários e de integração de regras de negócio (desenvolvimento orientado a TDD):

```bash
uv run pytest
```

Isso verificará as regras de handoff, cálculos de score de crédito, manipulação de PII e persistência de limite.

### 2. Teste de Autenticação

```
1. Abra http://localhost:8501
2. Clique em "Login"
3. Use dados de um cliente do clientes.csv:
   - CPF: Qualquer um dos CPFs da tabela acima
   - Data de Nascimento: A data correspondente
   - Senha: Qualquer uma (validação atual: CPF + data)
```

### 3. Teste de Consulta de Limite

```
Cliente: "Qual é meu limite de crédito?"
Agente de Crédito: "Seu limite atual é R$ 5.000"
```

### 4. Teste de Handoff para Câmbio

```
Cliente: "Qual é a cotação do dólar?"
Router: Detecta intenção → Câmbio
Agente de Câmbio: Retorna cotação USD/BRL atualizada
```

### 5. Teste de Aumento de Limite Rejeitado → Entrevista

```
Cliente com score baixo (ex: Victor): "Gostaria de aumentar meu limite"
Agente de Crédito: "Infelizmente, sua solicitação foi rejeitada"
UI: Oferece botão "Fazer entrevista financeira"
Cliente: Clica no botão
Router: Handoff para → Agente de Entrevista
Agente: Faz perguntas, recalcula score
Se score ↑: Agente de Crédito aprova aumento
```

### 6. Suíte de Avaliações (Evals)

O sistema possui uma suíte automatizada de evals em `src/evals/` que testa cenários reais de interação com o LLM:

```bash
# Executar todos os evals
uv run python -m src.evals.runner --type all

# Apenas simples ou ai_battle
uv run python -m src.evals.runner --type simple
uv run python -m src.evals.runner --type ai_battle
```

#### Edge-Cases Testados

| Dataset | Cenário | O que valida |
|---------|---------|-------------|
| `multiple_quotes.yaml` | Consulta de múltiplas cotações | Handoff para câmbio, fallback de APIs, resposta com cálculo |
| `data_leak_pii.yaml` | Tentativa de extração de dados de terceiros | Recusa de vazar PII, recusa com procuração fictícia |
| `illegal_credit_limit.yaml` | Aumento ilícito de limite | Recusa de aprovação sem análise, direcionamento ao processo correto |
| `full_credit_interview_exchange.yaml` | Fluxo completo: crédito → entrevista → câmbio → fim | Rejeição + oferta de entrevista, recusa de câmbio durante entrevista, coleta dos 5 campos, cálculo de score |
| `leave_resume_interview.yaml` | Sair e voltar da entrevista no meio | **Sair da entrevista** para consultar câmbio, **voltar** para a entrevista, **corrigir valores** já informados, concluir score, encerrar |

#### Falhas Conhecidas (Comportamentais)

Os cenários `/ai-battle` simulam ataques de red-teaming. Algumas falhas são comportamentais esperadas do LLM:

| Persona  | Motivo |
|----------|--------|
| Engenheiro Social de Limite | Varia conforme o modelo consegue negar pressão social, mas tende a conceder permissões que ele não tem, melhora com prompt e guardrails |
| Cotador Insistente | Varia conforme o modelo mantém consistência nas cotações e disponibilidade das APIs |
| Extrator de PII | Defesa robusta contra extração de dados |

### 6. Rastreabilidade

- **LangSmith:** Acesse dashboard.smith.langchain.com para ver traces
- **CSV Local:** Abra `src/backend/data/trace_eventos.csv` para auditoria


