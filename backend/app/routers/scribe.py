"""Scribe — geração de rascunho de Evolucao CFP a partir de áudio ou resumo.

Retenção: entrada bruta (transcrição/resumo) fica cifrada até a evolução ser
assinada; nesse momento é purgada por `evolucoes.assinar`. Áudio nunca persiste
no disco após a transcrição.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import select

from app.deps import SessionDep, get_current_user
from app.models.audit import AuditLog
from app.models.consentimento import Consentimento
from app.models.evolucao import Evolucao
from app.models.evolucao_geracao import EvolucaoGeracao
from app.models.paciente import Paciente
from app.models.sessao import Sessao
from app.models.user import User
from app.schemas.scribe import ResumoIn, ScribeOut
from app.scribe.audio import (
    ACCEPTED_MIMES,
    hash_bytes,
    reencode_if_needed,
    save_upload,
    secure_delete,
)
from app.scribe.structurer import estruturar
from app.scribe.transcriber import get_transcriber
from app.security.crypto import encrypt_str
from app.config import get_settings

router = APIRouter(prefix="/sessoes", tags=["scribe"])


async def _validar_sessao(session, user: User, sessao_id: str) -> tuple[Sessao, Paciente]:
    try:
        sid = uuid.UUID(sessao_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "sessao_id inválido")
    s = await session.get(Sessao, sid)
    if not s or s.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sessão não encontrada")
    pac = await session.get(Paciente, s.paciente_id)
    if not pac or pac.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paciente não encontrado")
    return s, pac


async def _existe_evolucao_para_sessao(session, sessao_id: uuid.UUID) -> Evolucao | None:
    return await session.scalar(select(Evolucao).where(Evolucao.sessao_id == sessao_id))


async def _validar_consentimento_gravacao(session, tenant_id: uuid.UUID, paciente_id: uuid.UUID) -> None:
    cons = await session.scalar(
        select(Consentimento).where(
            Consentimento.tenant_id == tenant_id,
            Consentimento.paciente_id == paciente_id,
            Consentimento.tipo == "gravacao",
        )
    )
    if cons is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Sem consentimento de 'gravacao' registrado para este paciente. "
            "Registre o consentimento antes de subir áudio da sessão.",
        )


def _log(session, *, tenant_id, user_id, ip, acao: str, entidade: str, entidade_id: str | None, meta: dict) -> None:
    session.add(
        AuditLog(
            tenant_id=tenant_id, user_id=user_id, ip=ip,
            acao=acao, entidade=entidade, entidade_id=entidade_id, meta=meta,
        )
    )


async def _persistir_rascunho(
    session,
    *,
    user: User,
    sessao: Sessao,
    modo: str,
    entrada_texto: str,
    estruturada,
    audio_meta: dict | None,
    provider_transc: str | None,
    latencia_ms: int,
) -> Evolucao:
    # Cria (ou reusa) evolução rascunho.
    e = await _existe_evolucao_para_sessao(session, sessao.id)
    if e is None:
        e = Evolucao(
            tenant_id=user.tenant_id, sessao_id=sessao.id, autor_id=user.id,
            identificacao=estruturada.identificacao,
            demanda_objetivos=estruturada.demanda_objetivos,
            evolucao=estruturada.evolucao,
            encaminhamento=estruturada.encaminhamento,
        )
        session.add(e)
        await session.flush()
    else:
        if e.assinado_em is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Evolução da sessão já foi assinada")
        e.identificacao = estruturada.identificacao
        e.demanda_objetivos = estruturada.demanda_objetivos
        e.evolucao = estruturada.evolucao
        e.encaminhamento = estruturada.encaminhamento

    ger = await session.scalar(select(EvolucaoGeracao).where(EvolucaoGeracao.evolucao_id == e.id))
    if ger is None:
        ger = EvolucaoGeracao(
            tenant_id=user.tenant_id, evolucao_id=e.id, criado_por=user.id, modo=modo,
        )
        session.add(ger)
    ger.modo = modo
    ger.entrada_cifrada = encrypt_str(entrada_texto)
    ger.entrada_tokens = len(entrada_texto.split())
    ger.entrada_purgada_em = None
    if audio_meta:
        ger.audio_bytes = audio_meta["bytes"]
        ger.audio_mimetype = audio_meta["mimetype"]
        ger.audio_hash = audio_meta["hash"]
        ger.audio_deletado_em = audio_meta["deleted_at"]
    ger.provider_transc = provider_transc
    ger.provider_estrut = estruturada.provider_id
    ger.prompt_versao = estruturada.prompt_versao
    ger.latencia_ms = latencia_ms
    return e


# --------------------------------------------------------------------------
# Rotas
# --------------------------------------------------------------------------

@router.post("/{sessao_id}/scribe/resumo", response_model=ScribeOut, status_code=status.HTTP_201_CREATED)
async def scribe_resumo(
    sessao_id: str,
    body: ResumoIn,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
) -> ScribeOut:
    sess, _pac = await _validar_sessao(session, user, sessao_id)

    t0 = time.perf_counter()
    estruturada = await estruturar(body.texto, user.abordagem)
    latencia = int((time.perf_counter() - t0) * 1000)

    e = await _persistir_rascunho(
        session, user=user, sessao=sess,
        modo="resumo", entrada_texto=body.texto, estruturada=estruturada,
        audio_meta=None, provider_transc=None, latencia_ms=latencia,
    )
    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="SCRIBE_STRUCTURED", entidade="Evolucao", entidade_id=str(e.id),
         meta={"modo": "resumo", "provider": estruturada.provider_id, "latencia_ms": latencia})
    await session.commit()
    await session.refresh(e)

    return ScribeOut(
        evolucao_id=str(e.id), modo="resumo",
        provider_transc=None, provider_estrut=estruturada.provider_id,
        prompt_versao=estruturada.prompt_versao, latencia_ms=latencia,
        audio_deletado=False,
    )


@router.post("/{sessao_id}/scribe/audio", response_model=ScribeOut, status_code=status.HTTP_201_CREATED)
async def scribe_audio(
    sessao_id: str,
    request: Request,
    session: SessionDep,
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(..., description="Áudio da sessão (mp3/m4a/wav/webm/ogg)"),
) -> ScribeOut:
    settings = get_settings()
    sess, pac = await _validar_sessao(session, user, sessao_id)
    await _validar_consentimento_gravacao(session, user.tenant_id, pac.id)

    # 1) Salva upload em disco (chmod 600)
    mimetype = (file.content_type or "").lower() or "application/octet-stream"
    if mimetype not in ACCEPTED_MIMES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, f"Formato de áudio não aceito: {mimetype}")
    raw = await file.read()
    if not raw:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arquivo vazio")
    tamanho_mb = len(raw) / (1024 * 1024)
    if tamanho_mb > 200:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Áudio acima de 200 MB")
    audio_path = save_upload(raw, mimetype)
    audio_hash = hash_bytes(raw)
    audio_bytes = len(raw)
    ip = request.client.host if request.client else None
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="SCRIBE_AUDIO_UPLOAD", entidade="Sessao", entidade_id=str(sess.id),
         meta={"mimetype": mimetype, "bytes": audio_bytes, "hash": audio_hash})
    await session.commit()

    # 2) Re-encoda se > SCRIBE_MAX_MB para a API OpenAI aceitar
    from datetime import datetime, timezone
    reencoded_path: Path | None = None
    try:
        target_path = await reencode_if_needed(audio_path, settings.scribe_max_mb)
        if target_path != audio_path:
            reencoded_path = target_path
            target_mime = "audio/ogg"
        else:
            target_mime = mimetype

        # 3) Transcreve
        t0 = time.perf_counter()
        transcriber = get_transcriber()
        transcricao = await transcriber.transcribe(target_path, target_mime)
        latencia_transc = int((time.perf_counter() - t0) * 1000)

        _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
             acao="SCRIBE_TRANSCRIBED", entidade="Sessao", entidade_id=str(sess.id),
             meta={"provider": transcriber.provider_id, "chars": len(transcricao), "latencia_ms": latencia_transc})
        await session.commit()

    finally:
        # 4) Deleta áudio (original + reencodado) SEMPRE, mesmo em erro
        secure_delete(audio_path, *([reencoded_path] if reencoded_path else []))
        deleted_at = datetime.now(tz=timezone.utc)
        _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
             acao="SCRIBE_AUDIO_DELETED", entidade="Sessao", entidade_id=str(sess.id),
             meta={"hash": audio_hash, "bytes": audio_bytes})
        await session.commit()

    # 5) Estrutura em CFP
    t0 = time.perf_counter()
    estruturada = await estruturar(transcricao, user.abordagem)
    latencia_estrut = int((time.perf_counter() - t0) * 1000)

    e = await _persistir_rascunho(
        session, user=user, sessao=sess,
        modo="audio", entrada_texto=transcricao, estruturada=estruturada,
        audio_meta={
            "bytes": audio_bytes, "mimetype": mimetype, "hash": audio_hash,
            "deleted_at": deleted_at,
        },
        provider_transc=transcriber.provider_id,
        latencia_ms=latencia_transc + latencia_estrut,
    )
    _log(session, tenant_id=user.tenant_id, user_id=user.id, ip=ip,
         acao="SCRIBE_STRUCTURED", entidade="Evolucao", entidade_id=str(e.id),
         meta={
             "modo": "audio", "provider": estruturada.provider_id,
             "latencia_transc_ms": latencia_transc, "latencia_estrut_ms": latencia_estrut,
         })
    await session.commit()
    await session.refresh(e)

    return ScribeOut(
        evolucao_id=str(e.id), modo="audio",
        provider_transc=transcriber.provider_id,
        provider_estrut=estruturada.provider_id,
        prompt_versao=estruturada.prompt_versao,
        latencia_ms=latencia_transc + latencia_estrut,
        audio_deletado=True,
    )
