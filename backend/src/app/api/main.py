import logging

from app.api.routers import estatisticas, operadoras
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("healthtech")

app = FastAPI(
    title="HealthTech API",
    version="1.0.0",
    description="Teste Técnico — Intuitive Care",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(operadoras.router, prefix="/api/operadoras", tags=["Operadoras"])
app.include_router(estatisticas.router, prefix="/api", tags=["Estatísticas"])


# Erro inesperado: não vazar detalhes ao cliente
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno inesperado. Tente novamente."},
    )
