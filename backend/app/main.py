"""Práxis — FastAPI async app."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import SessionLocal
from app.instrumentos.seed import upsert_catalogo
from app.routers import assinatura, auth, biblioteca, casos, consentimentos, documentos, equipe, evolucoes, exportacao, financeiro, grupos, inicio, instrumentos as instrumentos_router, longitudinal, pacientes, preparacao, risco, scribe, sessoes, sofia, supervisao


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload settings & fernet key para falhar cedo se envs faltarem.
    get_settings()
    # Upsert do catálogo de instrumentos (idempotente).
    async with SessionLocal() as s:
        await upsert_catalogo(s)
    yield


settings = get_settings()

app = FastAPI(
    title="Práxis API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.env != "prod" else None,
    redoc_url=None,
    # Nginx expõe o backend em /api externamente; o proxy_pass strippa "/api",
    # então o app internamente vê "/auth/…". root_path faz Swagger e URLs
    # geradas conhecerem o prefixo público.
    root_path="/api",
    # Sem redirect automático de trailing slash: por trás do proxy o Location
    # sairia sem "/api" e o browser cai no Next. Todos os routers usam paths
    # determinísticos, então nada quebra.
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "env": settings.env}


app.include_router(auth.router)
app.include_router(equipe.router)
app.include_router(pacientes.router)
app.include_router(sessoes.router)
app.include_router(evolucoes.router)
app.include_router(consentimentos.router)
app.include_router(sofia.router)
app.include_router(biblioteca.router)
app.include_router(financeiro.router)
app.include_router(scribe.router)
app.include_router(instrumentos_router.router)
app.include_router(preparacao.router)
app.include_router(documentos.router)
app.include_router(supervisao.router)
app.include_router(inicio.router)
app.include_router(longitudinal.router)
app.include_router(exportacao.router)
app.include_router(assinatura.router)
app.include_router(risco.router)
app.include_router(casos.router)
app.include_router(grupos.router)
