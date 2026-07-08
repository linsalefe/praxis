"""Rede de apoio do caso — genograma/ecomapa (Onda 2.3)."""
import urllib.parse as up

import pyotp


async def _novo_paciente(client, headers, nome: str) -> str:
    r = await client.post("/pacientes", headers=headers, json={"nome": nome})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _novo_caso(client, headers, pid: str) -> str:
    r = await client.post(f"/pacientes/{pid}/casos", headers=headers, json={})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _login_e_2fa(client, email: str, senha: str) -> dict:
    r = await client.post("/auth/login", json={"email": email, "senha": senha})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    rs = await client.post("/auth/2fa/setup", headers=headers)
    secret = up.parse_qs(up.urlparse(rs.json()["otpauth_url"]).query)["secret"][0]
    await client.post("/auth/2fa/verify", headers=headers, json={"codigo": pyotp.TOTP(secret).now()})
    return headers


async def test_adicionar_listar_atualizar_remover_membro(client, conta):
    pid = await _novo_paciente(client, conta["headers"], "Pessoa Cuidada")
    caso = await _novo_caso(client, conta["headers"], pid)

    r = await client.post(f"/casos/{caso}/rede", headers=conta["headers"], json={
        "nome": "Dona Maria", "papel": "mãe", "tipo_vinculo": "familiar", "forca_vinculo": "forte",
    })
    assert r.status_code == 201, r.text
    membro = r.json()
    assert membro["nome"] == "Dona Maria" and membro["tipo_vinculo"] == "familiar"

    await client.post(f"/casos/{caso}/rede", headers=conta["headers"], json={
        "nome": "CAPS III", "papel": "serviço de referência", "tipo_vinculo": "servico", "forca_vinculo": "fragil",
    })
    r = await client.get(f"/casos/{caso}/rede", headers=conta["headers"])
    assert len(r.json()) == 2

    # Atualiza força do vínculo.
    r = await client.patch(f"/casos/{caso}/rede/{membro['id']}", headers=conta["headers"],
                           json={"forca_vinculo": "conflito"})
    assert r.json()["forca_vinculo"] == "conflito"

    # Remove.
    r = await client.delete(f"/casos/{caso}/rede/{membro['id']}", headers=conta["headers"])
    assert r.status_code == 204
    r = await client.get(f"/casos/{caso}/rede", headers=conta["headers"])
    assert len(r.json()) == 1


async def test_nome_membro_cifrado(client, conta):
    from sqlalchemy import text
    from app.db import engine

    pid = await _novo_paciente(client, conta["headers"], "Pessoa")
    caso = await _novo_caso(client, conta["headers"], pid)
    await client.post(f"/casos/{caso}/rede", headers=conta["headers"], json={"nome": "Vizinho Pedro"})
    async with engine.begin() as conn:
        row = (await conn.execute(text("SELECT nome_cifrado FROM membros_rede LIMIT 1"))).first()
    assert b"Pedro" not in bytes(row[0])


async def test_sigilo_rede_por_profissional(client, conta):
    owner = conta
    r = await client.post("/equipe/profissionais", headers=owner["headers"], json={
        "nome": "Prof R", "email": "redeb@example.com", "senha": "senha12345", "crp": "06/777777",
    })
    assert r.status_code == 201, r.text
    prof = await _login_e_2fa(client, "redeb@example.com", "senha12345")

    pid = await _novo_paciente(client, owner["headers"], "Paciente do Owner")
    caso = await _novo_caso(client, owner["headers"], pid)
    # Profissional não acessa a rede do caso de outro (404).
    assert (await client.get(f"/casos/{caso}/rede", headers=prof)).status_code == 404
    assert (await client.post(f"/casos/{caso}/rede", headers=prof, json={"nome": "X"})).status_code == 404
