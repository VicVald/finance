import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    # Segurança e PII
    CPF_SALT: str = os.getenv("CPF_SALT", "banco_agil_salt_2026")
    
    # Autenticação JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "banco_agil_super_secret_key_2026_change_me")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Caminhos de dados
    DATA_DIR: Path = BASE_DIR / "data"
    CLIENTES_CSV: Path = DATA_DIR / "clientes.csv"
    SCORE_LIMITE_CSV: Path = DATA_DIR / "score_limite.csv"
    SOLICITACOES_AUMENTO_CSV: Path = DATA_DIR / "solicitacoes_aumento_limite.csv"
    TRACE_EVENTOS_CSV: Path = DATA_DIR / "trace_eventos.csv"

    # API Keys & LLM Config
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

    # Exchange API
    EXCHANGE_TIMEOUT_SECONDS: float = 5.0

    # LangSmith Rastreabilidade
    LANGSMITH_TRACING: str = os.getenv("LANGSMITH_TRACING", "false")
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "Finance")


settings = Settings()

# Exporta variáveis LANGSMITH para as variáveis LANGCHAIN_ correspondentes esperadas pela biblioteca
if settings.LANGSMITH_TRACING.lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT

