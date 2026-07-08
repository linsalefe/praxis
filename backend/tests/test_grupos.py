"""Encontros de grupo/oficina/assembleia (Onda 2.2): criação com participantes,
cifragem de nome livre, presença, sigilo por profissional."""
import urllib.parse as up

import pyotp


async def _novo_paciente(client, headers, nome: str) -> str:
    r = await client.post("/pacientes", headers=headers, json={"nome": nome})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _login_e_2fa(client, email: str, senha: str) -> dict:
    r = await client.post("/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    rs = await client.post("/auth/2fa/setup", headers=headers)
    secret = up.parse_qs(up.urlparse(rs.json()["otpauth_url"]).query)["secret"][0]
    r = await client.post("/auth/2fa/verify", headers=headers, json={"codigo": pyotp.TOTP(secret).now()})
    assert r.status_code == 200, r.text
    return headers


async def test_criar_encontro_com_participantes(client, conta):
    pid = await _novo_paciente(client, conta["headers"], "Ana Paciente")
    r = await client.post("/grupos", headers=conta["headers"], json={
        "tipo": "oficina", "titulo": "Oficina de geração de renda",
        "data": "2026-07-08T14:00:00+00:00", "local": "CAPS III", "tema": "autonomia",
        "registro": "boa adesão do grupo",
        "participantes": [
            {"paciente_id": pid, "presente": True},
            {"nome_livre": "João da Comunidade", "presente": True},
            {"nome_livre": "Faltante", "presente": False},
        ],
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["tipo"] == "oficina" and len(body["participantes"]) == 3
    nomes = {p["nome"] for p in body["participantes"]}
    assert "Ana Paciente" in nomes and "João da Comunidade" in nomes

    # Lista traz contagem de presentes.
    r = await client.get("/grupos", headers=conta["headers"])
    item = next(e for e in r.json() if e["id"] == body["id"])
    assert item["total_participantes"] == 3 and item["presentes"] == 2


async def test_nome_livre_cifrado(client, conta):
    from sqlalchemy import text
    from app.db import engine

    await client.post("/grupos", headers=conta["headers"], json={
        "tipo": "assembleia", "titulo": "Assembleia", "data": "2026-07-08T09:00:00+00:00",
        "participantes": [{"nome_livre": "Maria Comunidade"}],
    })
    async with engine.begin() as conn:
        row = (await conn.execute(text(
            "SELECT nome_livre_cifrado FROM participantes_encontro "
            "WHERE nome_livre_cifrado IS NOT NULL LIMIT 1"))).first()
    assert b"Maria" not in bytes(row[0])  # não vaza em claro


async def test_adicionar_e_remover_participante(client, conta):
    enc = (await client.post("/grupos", headers=conta["headers"], json={
        "tipo": "grupo", "titulo": "Grupo terapêutico", "data": "2026-07-08T10:00:00+00:00",
    })).json()
    r = await client.post(f"/grupos/{enc['id']}/participantes", headers=conta["headers"],
                          json={"nome_livre": "Novo membro"})
    assert r.status_code == 201
    part = r.json()["participantes"][0]
    r = await client.delete(f"/grupos/{enc['id']}/participantes/{part['id']}", headers=conta["headers"])
    assert r.status_code == 204
    r = await client.get(f"/grupos/{enc['id']}", headers=conta["headers"])
    assert r.json()["participantes"] == []


async def test_sigilo_por_profissional_nos_grupos(client, conta):
    owner = conta
    r = await client.post("/equipe/profissionais", headers=owner["headers"], json={
        "nome": "Prof G", "email": "grupob@example.com", "senha": "senha12345", "crp": "06/555555",
    })
    assert r.status_code == 201, r.text
    prof = await _login_e_2fa(client, "grupob@example.com", "senha12345")

    enc = (await client.post("/grupos", headers=owner["headers"], json={
        "tipo": "grupo", "titulo": "Grupo do owner", "data": "2026-07-08T10:00:00+00:00",
    })).json()
    # Profissional não vê o encontro do owner na lista nem no detalhe.
    r = await client.get("/grupos", headers=prof)
    assert all(e["id"] != enc["id"] for e in r.json())
    assert (await client.get(f"/grupos/{enc['id']}", headers=prof)).status_code == 404


async def test_prof_nao_adiciona_paciente_de_outro(client, conta):
    owner = conta
    r = await client.post("/equipe/profissionais", headers=owner["headers"], json={
        "nome": "Prof H", "email": "grupoc@example.com", "senha": "senha12345", "crp": "06/666666",
    })
    assert r.status_code == 201, r.text
    prof = await _login_e_2fa(client, "grupoc@example.com", "senha12345")
    pid_owner = await _novo_paciente(client, owner["headers"], "Paciente do Owner")
    # Profissional tenta criar encontro com paciente do owner → 404 (sigilo).
    r = await client.post("/grupos", headers=prof, json={
        "tipo": "grupo", "titulo": "x", "data": "2026-07-08T10:00:00+00:00",
        "participantes": [{"paciente_id": pid_owner}],
    })
    assert r.status_code == 404
