# ADR-010: CI/CD com GitHub Actions e Deploy via SSH na OCI

- **Status:** Aceito
- **Data:** 2026-07-20
- **Deciders:** Time de Desenvolvimento

---

## Contexto

O projeto Banco Ágil precisa de um pipeline automatizado que garanta a qualidade do código a cada push e realize o deploy contínuo na infraestrutura de produção hospedada em uma máquina Oracle Cloud Infrastructure (OCI), sem depender de um registry de imagens Docker externo.

## Decisão

Adotar **GitHub Actions** como plataforma de CI/CD, dividindo o pipeline em dois workflows independentes:

1. **CI (`ci.yml`)** — roda em todo push de qualquer branch e em pull requests para `main`/`master`.
2. **CD (`cd.yml`)** — roda exclusivamente em pushes para `main`/`master`, fazendo deploy direto na OCI via SSH.

### Estratégia de Deploy

O deploy é feito via **rsync + SSH** diretamente na máquina OCI, sem uso de container registry:

```
GitHub Actions Runner
       │
       │  rsync (SSH)
       ▼
Máquina OCI (~banco-agil/)
       │
       │  docker compose up --build -d
       ▼
Containers rodando (backend:8000, ui:8501)
```

O arquivo `.env` é gerado dinamicamente na OCI a partir dos **GitHub Secrets**, nunca sendo armazenado no repositório.

### Secrets necessários no GitHub

| Secret | Descrição |
|---|---|
| `OCI_SSH_KEY` | Chave privada SSH (conteúdo do arquivo `~/.ssh/id_rsa`) |
| `OCI_HOST` | IP ou hostname da máquina OCI |
| `OCI_USERNAME` | Usuário SSH na OCI (ex: `ubuntu`, `opc`) |
| `JWT_SECRET_KEY` | Chave secreta para geração de tokens JWT |
| `FERNET_SECRET_KEY` | Chave Fernet para criptografia de dados sensíveis |
| `OPENROUTER_API_KEY` | Token da API OpenRouter |
| `OPENROUTER_BASE_URL` | URL base do OpenRouter |
| `OPENROUTER_MODEL` | Modelo LLM a ser utilizado |
| `LANGSMITH_TRACING` | Ativar ou não rastreabilidade (`true`/`false`) |
| `LANGSMITH_API_KEY` | Token da API LangSmith |
| `LANGSMITH_PROJECT` | Nome do projeto no LangSmith |

## Alternativas Consideradas

| Alternativa | Motivo de rejeição |
|---|---|
| Docker Hub / GHCR com pull na OCI | Adiciona complexidade de autenticação no registry e latência de push/pull para uma infra single-node |
| Self-hosted runner na OCI | Exige manutenção do runner; rsync+SSH é mais simples para o escopo atual |
| Webhook + script na OCI | Menos rastreável e sem integração nativa com o GitHub PR flow |

## Consequências

**Positivas:**
- Deploy totalmente automatizado ao fazer merge na branch principal.
- Testes rodam em todo push, impedindo que código quebrado chegue à `main`.
- Secrets nunca ficam no repositório; o `.env` é gerado em runtime na OCI.
- `concurrency: cancel-in-progress: false` garante que um deploy em andamento não seja interrompido por outro push.

**Negativas / Riscos:**
- O `docker compose up --build` constrói as imagens diretamente na OCI, consumindo CPU/memória da instância durante o deploy.
- Se a instância OCI estiver inacessível (firewall, manutenção), o CD falha sem rollback automático.
- Não há estratégia de rollback automatizada; reversão manual requer re-push de commit anterior.

## Pré-requisitos na Máquina OCI

```bash
# Docker e Docker Compose instalados
sudo apt-get install -y docker.io docker-compose-plugin

# Usuário no grupo docker (evita sudo)
sudo usermod -aG docker $USER

# Porta SSH (22) liberada no Security List da OCI
# Portas 8000 e 8501 liberadas para acesso externo
```
