# ADR-011: Suíte de Avaliações (/evals) com LLM Judge, Simple e AI-Battle

**Status:** Aceito  
**Data:** 2026-07-20  
**Decididores:** Victor  

---

## Contexto

Para garantir que a arquitetura multi-agente do Banco Ágil mantenha a qualidade de atendimento, cumpra limites operacionais e não sofra vazamentos de PII ou vulnerabilidades de engenharia social (prompt injection), é necessária uma suíte automatizada de testes comportamentais e avaliações de segurança (`/evals`).

A suíte deve contemplar:
1. **Modo `/simple`**: Testes determinísticos em passos sequenciais para fluxos básicos e comportamentos direcionados.
2. **Modo `/ai-battle`**: Simulação multi-turnos com uma IA adversária utilizando personas manipuladoras até um limite de turnos (`max_turns`).
3. **LLM Judge**: Avaliador baseado em LLM para julgar o cumprimento de objetivos, conformidade de segurança e tratamento de erros.
4. **Histórico Auditável (`/history`)**: Armazenamento em arquivos JSON e relatórios legíveis em Markdown em `src/evals/history/`.

---

## Decisão

1. **Estrutura de Arquivos e Datasets**:
   - Os cenários de avaliação são definidos em YAML sob `src/evals/datasets/simple/` e `src/evals/datasets/ai_battle/`.
   - A CLI em `src/evals/runner.py` permite disparar `uv run python -m src.evals.runner --type simple|ai_battle|all`.

2. **Provedor e Modelo do LLM Judge / Persona**:
   - Serão utilizadas variáveis de ambiente dedicadas no `.env`:
     - `EVAL_LLM_MODEL` (default: modelo compativel com OpenRouter/OpenAI)
     - `EVAL_LLM_API_KEY`
     - `EVAL_LLM_BASE_URL`

3. **Formato do Histórico**:
   - A cada execução, um log estruturado `.json` e um sumário `.md` são gravados em `src/evals/history/YYYYMMDD_HHMMSS_<tipo>.json` e `src/evals/history/YYYYMMDD_HHMMSS_<type>.md`.

---

## Alternativas Consideradas

| Opção | Motivo de Rejeição |
|-------|-------------------|
| Apenas testes unitários com mocks | Não avaliam o comportamento real do LLM contra engenharia social nem vereditos semânticos |
| Apenas `pytest` sem CLI dedicada | Dificulta customização de parâmetros de execução de batalhas adversárias longas e geração de relatórios ricos |
| Armazenamento de resultados em banco SQLite | Desnecessário para a proposta de logs auditáveis e portáveis em repositório |

---

## Consequências

**Positivas:**
- Rastreamento sistemático da resiliência do bot a ataques de engenharia social e solicitações indevidas.
- Datasets declarativos em YAML facilmente editáveis e expansíveis.
- Histórico completo com transcrição de mensagens e justificativas detalhadas do LLM Judge.

**Negativas:**
- Consumo de tokens adicionais de API durante a execução do LLM Judge e da IA adversária.

---

## Referências

- [AGENTS.md](../../AGENTS.md)
- [ADR-004: Rastreabilidade](./ADR-004-rastreabilidade.md)
- [ADR-005: Segurança e PII](./ADR-005-seguranca-e-pii.md)
