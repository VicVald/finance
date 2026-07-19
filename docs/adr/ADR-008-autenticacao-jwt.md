# ADR-008: Autenticação JWT com Access e Refresh Token

**Status:** Aceito  
**Data:** 2026-07-19  
**Decididores:** Victor  

---

## Contexto

Para proteger a comunicação entre a UI (Streamlit) e a API de agentes (FastAPI), precisamos de um mecanismo de autenticação robusto. O usuário solicitou um padrão de autenticação utilizando tokens JWT contendo um **Access Token** e um **Refresh Token** para reautenticação automática caso a requisição retorne `401 Unauthorized` (Token Expirado).

---

## Decisão

### Mecanismo de Autenticação

1. **Access Token (Curta Duração):**
   - Duração: 15 minutos.
   - Utilizado em todas as requisições autenticadas no header `Authorization: Bearer <token>`.
   - Armazena a identidade do usuário (CPF hasheado).

2. **Refresh Token (Longa Duração):**
   - Duração: 7 dias.
   - Armazenado de forma segura no cliente (st.session_state).
   - Enviado para o endpoint `/auth/refresh` apenas quando o Access Token expirar.

### Endpoints do Backend (FastAPI)

- `POST /auth/login`: Recebe as credenciais (CPF e data de nascimento) -> Retorna `access_token` e `refresh_token`.
- `POST /auth/refresh`: Recebe o `refresh_token` no body ou header -> Retorna um novo `access_token`.
- `GET /auth/me`: Retorna os dados do usuário autenticado no momento.

### Comportamento no Frontend (Streamlit)

Criaremos um cliente HTTP wrapper (ex: `HttpClient`) para requisições que intercepta respostas com status `401 Unauthorized`. 

**Fluxo de Interceptação Transparente:**
1. A requisição original falha com `401 Unauthorized` devido a um Access Token expirado.
2. O wrapper intercepta a falha e dispara silenciosamente uma chamada para `/auth/refresh` enviando o `refresh_token` armazenado em `st.session_state`.
3. Se o refresh retornar sucesso (novos tokens):
   - Os novos tokens são salvos em `st.session_state`.
   - A requisição original é **automaticamente refeita** usando o novo Access Token.
   - O resultado da requisição resolvida é retornado ao fluxo da aplicação, garantindo que o usuário final **não sinta qualquer interrupção ou falha**.
4. Se o refresh falhar (refresh token expirado/inválido):
   - Os tokens são limpos do estado e o usuário é redirecionado para a tela de login.

```
[Streamlit API Call] ──(Access Token expirado)──> [FastAPI (401)]
       │                                            │
       ▼                                            │
[HttpClient Wrapper] <─── Retorna 401 ──────────────┘
       │
       ├─── Envia POST /auth/refresh com o Refresh Token
       ├─── Se SUCESSO: Salva novos tokens -> Refaz chamada original (Transparente para o Usuário)
       └─── Se FALHA: Limpa sessão -> Redireciona para tela de Login
```

---

## Alternativas Consideradas

| Opção | Motivo de Rejeição |
|-------|-------------------|
| Apenas Access Token simples | Exige que o usuário faça login novamente toda vez que o token expirar (ruim para UX). |
| Cookies de sessão (Stateful) | Menos aderente ao padrão stateless de APIs FastAPI + Streamlit. |

---

## Consequências

**Positivas:**
- UX fluida: o usuário não precisa logar frequentemente.
- Segurança aprimorada: Access Token de curta duração mitiga impacto de vazamento.
- Arquitetura padrão de mercado para APIs SPA/Client-Server.

**Negativas:**
- Complexidade extra no controle de estados e chamadas assíncronas do Streamlit.
- Necessidade de adicionar a biblioteca `pyjwt` ou `jose` nas dependências.

---

## Referências

- [ADR-001: Arquitetura Geral](./ADR-001-arquitetura-geral-de-agentes.md)
- [ADR-006: Interface Streamlit](./ADR-006-interface-streamlit.md)
