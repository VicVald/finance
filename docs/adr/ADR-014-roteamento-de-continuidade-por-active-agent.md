# ADR-014: Classificação Dinâmica de Intenção e Roteamento Contínuo por Triagem

**Status:** Aceito  
**Data:** 2026-07-21  
**Decididores:** Victor / Antigravity  

---

## Contexto

Anteriormente, quando um cliente transicionava para um agente especializado (`active_agent == "credit"` ou `"exchange"`), ou o sistema tentava re-autenticar o usuário solicitando CPF (quando caía na triagem padrão) ou pulava a triagem completamente, impedindo que o cliente mudasse de assunto (ex: estar no atendimento de crédito e solicitar uma cotação de câmbio).

O requisito de negócio estabelece que:
1. Uma vez autenticado (`is_authenticated == True`), o cliente **nunca mais deve ser solicitado a informar CPF/dados de autenticação**.
2. **Todas as mensagens** enviadas pelo cliente devem passar pela Triagem (`triage_node`) para classificação dinâmica de intenção.
3. Se a intenção mudar (ex: do Crédito para Câmbio), o `triage_node` deve realizar o handoff para o novo agente especializado (`transfer_to_exchange`).
4. Se a intenção for do mesmo domínio do agente atual ou uma continuidade conversacional, o `triage_node` encaminha para o subgrafo do `active_agent` correspondente.

---

## Decisão

1. **Roteamento de Intenção Pós-Autenticação no `triage_node`**:
   - Quando `is_authenticated == True`, o `triage_node` injeta no prompt do LLM o contexto de que o cliente já se encontra autenticado.
   - O prompt da triagem instrui o LLM a classificar a intenção e invocar a ferramenta adequada (`transfer_to_credit`, `transfer_to_exchange`, `transfer_to_interview`, `end_conversation`).
   - Removem-se quaisquer solicitações de re-autenticação para clientes autenticados.

2. **Gerenciamento de Transição de Assuntos**:
   - Permite troca fluida de escopo entre Crédito, Câmbio e Entrevista de Score sem perder os dados da sessão do usuário.

---

## Consequências

**Positivas:**
- Experiência do usuário fluida e inteligente com troca livre de assunto.
- Eliminação definitiva de solicitações redundantes de CPF pós-autenticação.
- Manutenção da triagem como ponto central de roteamento de intenção do sistema.

**Negativas:**
- Nenhuma.
