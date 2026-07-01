"""Transcrição plugável. Selecionado via PRAXIS_TRANSCRIBER."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from openai import AsyncOpenAI

from app.config import get_settings

PROMPT_CLINICO_PT = (
    "Transcrição de sessão clínica em português do Brasil. "
    "Terminologia: psicoterapia, saúde mental, novas abordagens (Diálogo Aberto, "
    "Ouvir Vozes, GAM, PTMF, WRAP, Redução de Danos), CFP, LGPD, CAPS, RAPS, RD. "
    "Nomes próprios devem ser preservados. Preserve pontuação."
)


class Transcriber(Protocol):
    provider_id: str

    async def transcribe(self, path: Path, mimetype: str) -> str: ...


class OpenAITranscriber:
    """gpt-4o-mini-transcribe / gpt-4o-transcribe / whisper-1."""

    def __init__(self, model: str | None = None) -> None:
        s = get_settings()
        self.model = model or s.transc_model
        self.provider_id = f"openai:{self.model}"
        self._client = AsyncOpenAI(api_key=s.openai_api_key)

    async def transcribe(self, path: Path, mimetype: str) -> str:
        with path.open("rb") as f:
            resp = await self._client.audio.transcriptions.create(
                model=self.model,
                file=(path.name, f, mimetype),
                language="pt",
                prompt=PROMPT_CLINICO_PT,
                response_format="text",
            )
        # Para response_format=text, resp já é string.
        return str(resp).strip()


class WhisperLocalTranscriber:
    """Stub — quando ativado, exige `openai-whisper` + torch + swap. Não instalado nesta sprint."""

    provider_id = "local:whisper-large-v3"

    async def transcribe(self, path: Path, mimetype: str) -> str:
        raise NotImplementedError(
            "Whisper local não está habilitado. Instale `openai-whisper` e torch, "
            "crie swap de 8 GB e defina PRAXIS_TRANSCRIBER=whisper_local."
        )


def get_transcriber() -> Transcriber:
    s = get_settings()
    if s.transcriber == "openai":
        return OpenAITranscriber()
    if s.transcriber == "whisper_local":
        return WhisperLocalTranscriber()
    raise ValueError(f"PRAXIS_TRANSCRIBER inválido: {s.transcriber}")
