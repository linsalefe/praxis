"""Gate de consentimento uso_ia (C3) e revogação (C4)."""
import uuid

from app.conformidade.ia_cfp import consentimento_ativo
from app.db import SessionLocal


async def _criar_paciente(client, headers) -> str:
    r = await client.post("/pacientes", headers=headers, json={"nome": "Paciente Teste"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _criar_sessao(client, headers, paciente_id: str) -> str:
    r = await client.post("/sessoes", headers=headers, json={
        "paciente_id": paciente_id,
        "data": "2026-07-06T10:00:00+00:00",
        "modalidade": "presencial",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _registrar_consentimento(client, headers, paciente_id: str, tipo: str) -> str:
    r = await client.post("/consentimentos", headers=headers, json={
        "paciente_id": paciente_id, "tipo": tipo,
        "texto_aceito": "Aceito o termo.", "aceito_por": "Paciente Teste",
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_scribe_resumo_sem_uso_ia_403(client, conta):
    pid = await _criar_paciente(client, conta["headers"])
    sid = await _criar_sessao(client, conta["headers"], pid)
    r = await client.post(f"/sessoes/{sid}/scribe/resumo", headers=conta["headers"],
                          json={"texto": "Resumo da sessão para estruturar em evolução."})
    assert r.status_code == 403
    assert "uso_ia" in r.json()["detail"]


async def test_uso_ia_ativo_e_revogacao(client, conta):
    pid = await _criar_paciente(client, conta["headers"])
    tenant_id = None
    # Sem consentimento: gate ativo é None.
    async with SessionLocal() as s:
        pac_uuid = uuid.UUID(pid)
        # descobre tenant do paciente
        from app.models.paciente import Paciente
        pac = await s.get(Paciente, pac_uuid)
        tenant_id = pac.tenant_id
        assert await consentimento_ativo(s, tenant_id, pac_uuid, "uso_ia") is None

    cid = await _registrar_consentimento(client, conta["headers"], pid, "uso_ia")

    async with SessionLocal() as s:
        assert await consentimento_ativo(s, tenant_id, uuid.UUID(pid), "uso_ia") is not None

    # Revoga → deixa de ser ativo.
    r = await client.post(f"/consentimentos/{cid}/revogar", headers=conta["headers"])
    assert r.status_code == 200
    assert r.json()["revogado_em"] is not None

    async with SessionLocal() as s:
        assert await consentimento_ativo(s, tenant_id, uuid.UUID(pid), "uso_ia") is None

    # Revogar de novo → 409.
    r = await client.post(f"/consentimentos/{cid}/revogar", headers=conta["headers"])
    assert r.status_code == 409


async def test_scribe_bloqueia_apos_revogar_uso_ia(client, conta):
    pid = await _criar_paciente(client, conta["headers"])
    sid = await _criar_sessao(client, conta["headers"], pid)
    cid = await _registrar_consentimento(client, conta["headers"], pid, "uso_ia")
    await client.post(f"/consentimentos/{cid}/revogar", headers=conta["headers"])
    # Consentimento revogado → gate volta a bloquear (403 antes de qualquer IA).
    r = await client.post(f"/sessoes/{sid}/scribe/resumo", headers=conta["headers"],
                          json={"texto": "Resumo da sessão para estruturar em evolução."})
    assert r.status_code == 403
