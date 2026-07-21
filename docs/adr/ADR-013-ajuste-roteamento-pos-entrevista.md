# ADR-013: Ajuste de Roteamento Pós-Entrevista de Crédito e Retorno Nulo à Triagem

**Status:** Aceito  
**Data:** 2026-07-21  
**Decididores:** Victor / Antigravity  

---

## Contexto

Ao concluir a entrevista de crédito (`calcular_e_salvar_score`), o estado `entrevista_concluida` era marcado como `True` e `active_agent` era atualizado para `"triage"`. No entanto, devido ao redirecionamento automático das bordas do LangGraph (`interview_subgraph -> triage_node`), o `triage_node` era imediatamente reexecutado na mesma iteração de execução.

No `triage_node`, o agente de triagem lia a solicitação do usuário já concluída e tentava redirecionar para autenticação ou reabrir triagem.

---

## Decisão

1. **Retorno Nulo (`__end__`) ao Concluir a Entrevista:**
   - O `interview_node` finaliza sua execução retornando `Command(goto="__end__")`.
   - O `active_agent` permanece atualizado para `"triage"` no estado global, permitindo que a próxima mensagem do usuário seja processada normalmente pelo `triage_node`.
   - Evita-se redirecionamentos espúrios e desnecessários ao nó de triagem/autenticação no exato momento da conclusão da entrevista.

2. **Remoção de Redirecionamento em `transfer_to_triage`:**
   - Em caso de solitação explicita de transferência via `transfer_to_triage`, o nó direciona para `goto="__end__"`, definindo `active_agent="triage"`, encerrando a run da entrevista de forma limpa.

---

## Consequências

**Positivas:**
- O cliente visualiza a mensagem final da entrevista com seu score recalculado sem ser sobressaltado por mensagens do triador/autenticação.
- O grafo aguarda pacificamente a próxima entrada do cliente para que a triagem processe a nova solicitação.

**Negativas:**
- Nenhuma identificada.
