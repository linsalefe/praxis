"""Práxis — FastAPI async app."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, consentimentos, evolucoes, pacientes, sessoes, sofia


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload settings & fernet key para falhar cedo se envs faltarem.
    get_settings()
    yield


settings = get_settings()

app = FastAPI(
    title="Práxis API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.env != "prod" else None,
    redoc_url=None,
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
app.include_router(pacientes.router)
app.include_router(sessoes.router)
app.include_router(evolucoes.router)
app.include_router(consentimentos.router)
app.include_router(sofia.router)
