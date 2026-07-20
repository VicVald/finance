import uvicorn
import logging
from fastapi import FastAPI

# Configura o sistema de logging para gravar no console
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        # logging.FileHandler("app.log", encoding="utf-8")
    ]
)

from core.auth.routes import router as auth_router
from api.v1.agent_routes import router as agent_router

app = FastAPI(
    title="Banco Ágil API",
    description="API de serviços e agentes de IA do Banco Ágil",
    version="1.0"
)

# Registra os roteadores
app.include_router(auth_router)
app.include_router(agent_router)

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API do Banco Ágil!", "status": "active"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
