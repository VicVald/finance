# ADR-005: Segurança e PII (Hash SHA-256 com Salt + PII Middleware LangChain)

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

### 2. PII Middleware via LangChain Callbacks

**Estratégia:** Implementar um `BaseCallbackHandler` do LangChain que intercepta os inputs e outputs do LLM, aplicando masking de CPF antes de:
- Enviar o prompt ao LLM (o modelo nunca vê o CPF completo)
- Registrar no LangSmith
- Exibir na UI do Streamlit

```python
# utils/pii_middleware.py
import re
from langchain_core.callbacks import BaseCallbackHandler

CPF_PATTERN = re.compile(r'\b(\d{3})[.\-]?(\d{3})[.\-]?(\d{3})[.\-]?(\d{2})\b')

class PIIRedactionCallback(BaseCallbackHandler):
    """
    Callback que aplica masking de CPF em todos os inputs/outputs do LLM.
    """
    
    def _redact(self, text: str) -> str:
        def replace(m):
            digits = m.group(1) + m.group(2) + m.group(3) + m.group(4)
            return f"{digits[:3]}.XXX.XXX-{digits[-2:]}"
        return CPF_PATTERN.sub(replace, text)
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        # Redact aplicado nos prompts antes de enviar ao LLM
        redacted = [self._redact(p) for p in prompts]
        # Substituição in-place (LangChain não bloqueia mutação aqui)
        prompts[:] = redacted
    
    def on_llm_end(self, response, **kwargs):
        # Redact aplicado nas respostas do LLM
        for generation_list in response.generations:
            for gen in generation_list:
                gen.text = self._redact(gen.text)
```

**Registro do callback:**
```python
# Adicionado ao ChatOpenAI/ChatAnthropic instanciado para cada agente
llm = ChatOpenAI(
    model="...",
    callbacks=[PIIRedactionCallback()]
)
```

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
- O callback é reutilizável em todos os agentes via injeção no LLM instanciado
- Hash determinístico com salt: lookup O(1) no CSV

**Negativas:**
- O salt no `.env` é um segredo crítico; seu comprometimento invalida a proteção dos hashes
- Regex de CPF pode ter falsos positivos em textos com sequências numéricas similares
- CPFs com formatação não padrão precisam ser normalizados antes do masking

---

## Referências

- [ADR-004: Rastreabilidade](./ADR-004-rastreabilidade.md)
- [LGPD - Lei nº 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [LangChain Callbacks](https://python.langchain.com/docs/concepts/callbacks/)
