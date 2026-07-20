import hashlib
from functools import lru_cache
from core.config import settings

@lru_cache(maxsize=1)
def _get_salt() -> str:
    return settings.CPF_SALT

def hash_cpf(cpf: str) -> str:
    """
    Retorna o hash SHA-256 do CPF normalizado + salt.
    Remove formatação antes de aplicar o hash.
    """
    cpf_normalized = cpf.replace(".", "").replace("-", "").strip()
    salted = f"{_get_salt()}{cpf_normalized}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()

def mask_cpf(cpf: str) -> str:
    """
    Retorna o CPF mascarado (exibindo apenas os 3 primeiros e 2 últimos dígitos).
    """
    cpf_normalized = cpf.replace(".", "").replace("-", "").strip()
    if len(cpf_normalized) != 11:
        return "XXX.XXX.XXX-XX"
    return f"{cpf_normalized[:3]}.XXX.XXX-{cpf_normalized[-2:]}"
