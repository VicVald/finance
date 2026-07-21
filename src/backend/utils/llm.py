from langchain_openai import ChatOpenAI

from core.config import settings


def build_llm(*, temperature: float = 0.1) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=settings.OPENROUTER_BASE_URL,
        temperature=temperature,
        streaming=True,
        max_retries=3,
    )
