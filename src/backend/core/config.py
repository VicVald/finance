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
    
    # LangSmith Rastreabilidade
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "banco-agil")


settings = Settings()
