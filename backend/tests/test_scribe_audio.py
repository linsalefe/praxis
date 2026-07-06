"""Scribe por áudio — processamento em memória, sem áudio em claro no disco (D2)."""
import os

from app.config import get_settings
from app.scribe.structurer import Estruturada


class _StubTranscriber:
    provider_id = "stub:transcriber"

    async def transcribe(self, data: bytes, filename: str, mimetype: str) -> str:
        assert isinstance(data, (bytes, bytearray))  # recebe bytes, não path
        return "transcrição fake da sessão clínica"


async def _fake_estruturar(entrada: str, abordagem):
    return Estruturada(
        identificacao="ident", demanda_objetivos="demanda", evolucao="evolução",
        encaminhamento="encaminhamento", provider_id="stub:llm", prompt_versao="v1",
    )


async def _paciente_sessao(client, headers) -> str:
    pid = (await client.post("/pacientes", headers=headers, json={"nome": "Pac"})).json()["id"]
    for tipo in ("gravacao", "uso_ia"):
        r = await client.post("/consentimentos", headers=headers, json={
            "paciente_id": pid, "tipo": tipo, "texto_aceito": "ok", "aceito_por": "Pac",
        })
        assert r.status_code == 201
    sid = (await client.post("/sessoes", headers=headers, json={
        "paciente_id": pid, "data": "2026-07-06T10:00:00+00:00", "modalidade": "presencial",
    })).json()["id"]
    return sid


async def test_scribe_audio_gera_evolucao_sem_persistir_audio(client, conta, monkeypatch):
    sid = await _paciente_sessao(client, conta["headers"])

    import app.routers.scribe as scribe_mod
    monkeypatch.setattr(scribe_mod, "get_transcriber", lambda: _StubTranscriber())
    monkeypatch.setattr(scribe_mod, "estruturar", _fake_estruturar)

    r = await client.post(
        f"/sessoes/{sid}/scribe/audio", headers=conta["headers"],
        files={"file": ("a.mp3", b"conteudo de audio falso" * 10, "audio/mpeg")},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["modo"] == "audio"
    assert body["audio_deletado"] is True
    assert body["evolucao_id"]

    # Nenhum arquivo de áudio em claro deixado no diretório de uploads.
    d = get_settings().scribe_audio_dir
    if os.path.isdir(d):
        soltos = [f for f in os.listdir(d) if f.endswith((".mp3", ".ogg", ".wav", ".m4a", ".webm"))]
        assert soltos == []


async def test_scribe_audio_sem_uso_ia_403(client, conta, monkeypatch):
    # Só gravacao, sem uso_ia → gate de IA bloqueia (não chega a transcrever).
    pid = (await client.post("/pacientes", headers=conta["headers"], json={"nome": "Pac"})).json()["id"]
    await client.post("/consentimentos", headers=conta["headers"], json={
        "paciente_id": pid, "tipo": "gravacao", "texto_aceito": "ok", "aceito_por": "Pac"})
    sid = (await client.post("/sessoes", headers=conta["headers"], json={
        "paciente_id": pid, "data": "2026-07-06T10:00:00+00:00", "modalidade": "presencial"})).json()["id"]

    import app.routers.scribe as scribe_mod
    monkeypatch.setattr(scribe_mod, "get_transcriber", lambda: _StubTranscriber())

    r = await client.post(
        f"/sessoes/{sid}/scribe/audio", headers=conta["headers"],
        files={"file": ("a.mp3", b"x" * 100, "audio/mpeg")},
    )
    assert r.status_code == 403
