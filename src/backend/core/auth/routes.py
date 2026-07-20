import csv
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional

from core.config import settings
from utils.pii import hash_cpf
from core.auth.auth_service import (
    create_access_token,
    create_refresh_token,
    verify_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

# Schemas Pydantic
class LoginRequest(BaseModel):
    email: str = Field(..., description="E-mail do cliente")
    senha: str = Field(..., description="Senha do cliente")

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class RegisterRequest(BaseModel):
    nome: str = Field(..., description="Nome Completo")
    cpf: str = Field(..., description="CPF do cliente")
    data_nascimento: str = Field(..., description="Data de Nascimento")
    email: str = Field(..., description="E-mail")
    senha: str = Field(..., description="Senha")

class UserMeResponse(BaseModel):
    cpf_hash: str
    cpf_mask: str
    nome: str
    limite_atual: float
    score: int

# Helpers
def get_user_by_credentials(email: str, senha: str) -> Optional[dict]:
    if not settings.CLIENTES_CSV.exists():
        return None
    
    with open(settings.CLIENTES_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["email"].strip().lower() == email.strip().lower() and row["senha"].strip() == senha.strip():
                return {
                    "cpf_hash": row["cpf_hash"],
                    "cpf_mask": row.get("cpf_mask", "***.***.***-**"),
                    "nome": row["nome"],
                    "limite_atual": float(row["limite_atual"]),
                    "score": int(row["score"])
                }
    return None

def get_user_by_hash(cpf_hash: str) -> Optional[dict]:
    if not settings.CLIENTES_CSV.exists():
        return None
    with open(settings.CLIENTES_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["cpf_hash"] == cpf_hash:
                return {
                    "cpf_hash": row["cpf_hash"],
                    "cpf_mask": row.get("cpf_mask", "***.***.***-**"),
                    "nome": row["nome"],
                    "limite_atual": float(row["limite_atual"]),
                    "score": int(row["score"])
                }
    return None

# Dependency to get current authenticated user
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = verify_token(credentials.credentials, expected_type="access")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    cpf_hash = payload.get("sub")
    user = get_user_by_hash(cpf_hash)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado na base de dados",
        )
    return user

# Rotas
@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = get_user_by_credentials(req.email, req.senha)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos"
        )
    
    access_token = create_access_token(data={"sub": user["cpf_hash"]})
    refresh_token = create_refresh_token(data={"sub": user["cpf_hash"]})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshRequest):
    payload = verify_token(req.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado"
        )
    
    cpf_hash = payload.get("sub")
    # Gera novo par de tokens
    new_access = create_access_token(data={"sub": cpf_hash})
    new_refresh = create_refresh_token(data={"sub": cpf_hash})
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserMeResponse)
def me(current_user: dict = Depends(get_current_user)):
    return current_user

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    cpf_hash = hash_cpf(req.cpf)
    
    # Import the masking function
    from utils.pii import mask_cpf
    masked = mask_cpf(req.cpf)
    
    # Valida se já existe
    if get_user_by_hash(cpf_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CPF já cadastrado."
        )
        
    try:
        with open(settings.CLIENTES_CSV, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # cpf_hash,cpf_mask,nome,data_nascimento,limite_atual,score,email,senha
            writer.writerow([cpf_hash, masked, req.nome, req.data_nascimento, "0.0", "300", req.email, req.senha])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao cadastrar cliente."
        )
    return {"message": "Usuário cadastrado com sucesso!"}
