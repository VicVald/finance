# ADR-005: Segurança e PII (Hash SHA-256 com Salt + PII Customizado para CPF)

**Status:** Aceito  
**Data:** 2026-07-19  
**Decididores:** Victor  

---

## Contexto

O sistema processa dados sensíveis de clientes, especialmente o CPF (Cadastro de Pessoa Física), que é considerado dado pessoal sensível pela LGPD. Dois requisitos precisam ser atendidos:

1. **Armazenamento seguro do CPF** no `clientes.csv` e nos CSVs de rastreabilidade
2. **Masking de PII nos outputs do LLM e logs** — exibir apenas os 3 primeiros e 2 últimos dígitos do CPF

---

## Decisão

### 1. Hash SHA-256 com Salt para Armazenamento de CPF

**Algoritmo:** SHA-256 com salt fixo por ambiente

**Implementação:**

```python
# utils/pii.py
import hashlib
import os
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_salt() -> str:
    salt = os.getenv("CPF_SALT")
    if not salt:
        raise ValueError("CPF_SALT não configurado no .env")
    return salt

def hash_cpf(cpf: str) -> str:
    """
    Retorna SHA-256 hex do CPF normalizado + salt.
    Remove formatação (pontos e traços) antes de hashear.
    """
    cpf_normalized = cpf.replace(".", "").replace("-", "").strip()
    salted = f"{_get_salt()}{cpf_normalized}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()

def mask_cpf(cpf: str) -> str:
    """
    Retorna CPF mascarado: primeiros 3 e últimos 2 dígitos visíveis.
    Ex: '123.456.789-09' → '123.XXX.XXX-09'
    """
    cpf_normalized = cpf.replace(".", "").replace("-", "").strip()
    if len(cpf_normalized) != 11:
        return "XXX.XXX.XXX-XX"
    return f"{cpf_normalized[:3]}.XXX.XXX-{cpf_normalized[-2:]}"
```

**Configuração no `.env`:**
```
CPF_SALT=<string-secreta-longa-e-aleatoria>
```

**No `clientes.csv`:** O campo `cpf` armazena apenas o hash (nunca o CPF em texto puro).

**No CSV de rastreabilidade (`trace_eventos.csv`):** O `payload_resumido` usa `mask_cpf()` ao incluir CPF.

### 2. PII Customizado para CPF

**Estratégia:** Foi implementada uma solução de PII própria e customizada para mascarar CPFs, não utilizando os callbacks do LangChain. O mascaramento (`mask_cpf`) é aplicado de maneira explícita e controlada nas camadas necessárias do sistema.

Essa abordagem customizada garante que o CPF é mascarado antes de:
- Enviar o prompt com histórico ou contexto ao LLM (o modelo nunca vê o CPF completo)
- Registrar eventos e logs de rastreabilidade
- Exibir os dados na UI do Streamlit

A validação e mascaramento do CPF ocorrem utilizando diretamente a função `mask_cpf` contida em `utils/pii.py`.

### Política de Exibição de CPF

| Contexto | Formato exibido |
|----------|----------------|
| Dashboard (UI Streamlit) | `123.XXX.XXX-09` |
| Mensagens do agente | `123.XXX.XXX-09` |
| LangSmith traces | `123.XXX.XXX-09` |
| CSV `trace_eventos.csv` | `123.XXX.XXX-09` |
| CSV `clientes.csv` (campo cpf) | Hash SHA-256 (nunca texto puro) |
| CSV `solicitacoes_aumento_limite.csv` | Hash SHA-256 |
| Logs de aplicação (stdout) | `123.XXX.XXX-09` |

### Autenticação: Comparação por Hash

O agente de triagem não reconstrói o CPF — apenas hasheia o CPF fornecido pelo usuário com o mesmo salt e compara com o hash armazenado:

```python
def authenticate(cpf_input: str, data_nasc_input: str) -> bool:
    cpf_hash = hash_cpf(cpf_input)
    # Busca no clientes.csv pelo cpf_hash + data_nascimento
    ...
```

---

## Alternativas Consideradas

| Opção | Motivo de Rejeição |
|-------|-------------------|
| CPF em texto puro no CSV | Violação da LGPD; risco direto em caso de vazamento |
| bcrypt para hash de CPF | Mais lento (proposital para senhas); CPFs têm apenas 11 dígitos (suscetível a rainbow table mesmo com bcrypt, pois o espaço é pequeno — o salt mitiga isso em SHA-256 também) |
| HMAC-SHA256 | Equivalente ao SHA-256 com salt para este caso de uso; sem benefício adicional |
| Masking apenas na UI | O LLM veria o CPF completo nos prompts — risco de exposição via LangSmith |

---

## Consequências

**Positivas:**
- CPF nunca trafega em texto puro dentro do sistema após a entrada do usuário
- O LangSmith não armazena CPFs completos (proteção de dados nos traces)
- O mascaramento customizado explícito nos pontos de entrada e saída evita bugs de manipulação de string e falsos positivos que poderiam ocorrer com um middleware de Regex interceptando todo o LLM
- Hash determinístico com salt: lookup O(1) no CSV

**Negativas:**
- O salt no `.env` é um segredo crítico; seu comprometimento invalida a proteção dos hashes
- Regex de CPF pode ter falsos positivos em textos com sequências numéricas similares
- CPFs com formatação não padrão precisam ser normalizados antes do masking

---

## Referências

- [ADR-004: Rastreabilidade](./ADR-004-rastreabilidade.md)
- [LGPD - Lei nº 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
