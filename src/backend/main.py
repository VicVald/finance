import uvicorn
from fastapi import FastAPI
from core.auth.routes import router as auth_router

app = FastAPI(
    title="Banco Ágil API",
    description="API de serviços e agentes de IA do Banco Ágil",
    version="0.1.0"
)

# Registra os roteadores
app.include_router(auth_router)

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API do Banco Ágil!", "status": "active"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
