# Diretrizes de Desenvolvimento para Agentes de IA

Este documento define as diretrizes, boas condutas e fluxos de trabalho que todos os Agentes de IA (e desenvolvedores) devem seguir ao trabalhar no repositório do **Banco Ágil**.

---

## 🛠️ Fluxo de Trabalho para Alteração de Código

Sempre que for necessário implementar uma nova funcionalidade ou realizar alterações significativas na arquitetura, o agente deve seguir este ciclo de desenvolvimento:

```
[Decisão de Arquitetura] ──> [Criar/Atualizar ADR] ──> [Criar Testes de Limite/Fronteira]
                                                                  │
[Implementar Funcionalidade] <── [Validar Testes] <───────────────┘
```

1. **Documentar Decisões de Arquitetura:**
   - Toda decisão que mude a estrutura, fluxo de dados ou adicione dependências deve gerar uma nova **ADR (Architecture Decision Record)** em `/docs` no formato MADR.
2. **Desenvolvimento Orientado a Testes (TDD para Regras de Negócio):**
   - Antes de escrever o código de produção, crie um teste funcional que valide os limites (*boundaries*) estabelecidos pelo usuário (ex: limite de 3 tentativas de login, máscara de CPF, etc.).
   - Implemente a funcionalidade até que todos os testes passem.
3. **Tratamento de Integrações Externas:**
   - Integrações com APIs externas (como BrasilAPI ou AwesomeAPI) **não necessitam obrigatoriamente de testes automatizados**, visando evitar dependência de rede ou rate limits durante execuções locais de CI/CD.
4. **Sincronização de Ambiente:**
   - Qualquer variável de ambiente adicionada no código deve ser imediatamente adicionada com um valor fictício ou placeholder explicativo no arquivo `.env.example`.

---

## 🐍 Boas Práticas em Python & FastAPI

Para manter a consistência e manutenibilidade da base de código:

### 1. Tipagem e Modelagem de Dados
- Use **Pydantic (BaseModel)** para validação de dados de entrada (`Requests`) e saída (`Responses`) em todas as rotas da API.
- Aproveite o suporte de type hinting do Python 3.13 (`dict`, `list`, `Optional`, `Union`) de forma explícita. Evite imports legados do `typing` quando possível (ex: use `dict` ao invés de `Dict`).

### 2. Estrutura de Rotas e Segurança
- Use `APIRouter` com prefixos bem definidos para organizar os endpoints por domínio.
- Roteamento de autenticação deve injetar dependências utilizando o FastAPI `Depends` para validação de tokens JWT (Access Token).

### 3. Tratamento de Erros
- Nunca permita que o cliente final veja um traceback do Python ou erros não tratados.
- Lance exceções HTTP específicas utilizando `HTTPException` com o status code correto (ex: `401 Unauthorized`, `404 Not Found`, `422 Unprocessable Entity`).

### 4. Gerenciamento de Dependências
- Utilize o gerenciador de pacotes `uv` para instalar e gerenciar dependências.
- Certifique-se de documentar novas dependências adicionando-as na seção `dependencies` do [pyproject.toml](../finance/pyproject.toml).
