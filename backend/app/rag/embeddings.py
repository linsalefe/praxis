"""Cliente OpenAI para embeddings (text-embedding-3-small)."""
from __future__ import annotations

from openai import AsyncOpenAI, OpenAI

from app.config import get_settings


def _client_sync() -> OpenAI:
    s = get_settings()
    return OpenAI(api_key=s.openai_api_key)


def _client_async() -> AsyncOpenAI:
    s = get_settings()
    return AsyncOpenAI(api_key=s.openai_api_key)


def embed_batch(textos: list[str]) -> list[list[float]]:
    """Síncrono, usado pelo script de ingestão."""
    s = get_settings()
    if not textos:
        return []
    resp = _client_sync().embeddings.create(model=s.embed_model, input=textos)
    return [d.embedding for d in resp.data]


async def embed_query(texto: str) -> list[float]:
    """Assíncrono, usado no request da Sofia."""
    s = get_settings()
    resp = await _client_async().embeddings.create(model=s.embed_model, input=[texto])
    return resp.data[0].embedding
