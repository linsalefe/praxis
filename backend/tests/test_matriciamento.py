"""Registro de matriciamento / apoio matricial (Onda 2.4)."""
import urllib.parse as up

import pyotp


async def _novo_paciente(client, headers, nome: str) -> str:
    r = await client.post("/pacientes", headers=headers, json={"nome": nome})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _novo_caso(client, headers, pid: str) -> str:
    r = await client.post(f"/pacientes/{pid}/casos", headers=headers, json={})
    return r.json()["id"]


async def _login_e_2fa(client, email: str, senha: str) -> dict:
    r = await client.post("/auth/login", json={"email": email, "senha": senha})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    rs = await client.post("/auth/2fa/setup", headers=headers)
    secret = up.parse_qs(up.urlparse(rs.json()["otpauth_url"]).query)["secret"][0]
    await client.post("/auth/2fa/verify", headers=headers, json={"codigo": pyotp.TOTP(secret).now()})
    return headers


async def test_criar_listar_remover_matriciamento(client, conta):
    pid = await _novo_paciente(client, conta["headers"], "Pessoa Cuidada")
    caso = await _novo_caso(client, conta["headers"], pid)

    r = await client.post(f"/casos/{caso}/matriciamentos", headers=conta["headers"], json={
        "equipe_referencia": "ESF Vila Nova", "demanda": "manejo de crise",
        "discussao": "construção conjunta do PTS", "combinados": "visita domiciliar conjunta",
    })
    assert r.status_code == 201, r.text
    matric = r.json()
    assert matric["equipe_referencia"] == "ESF Vila Nova"

    r = await client.get(f"/casos/{caso}/matriciamentos", headers=conta["headers"])
    assert len(r.json()) == 1

    r = await client.delete(f"/casos/{caso}/matriciamentos/{matric['id']}", headers=conta["headers"])
    assert r.status_code == 204
    r = await client.get(f"/casos/{caso}/matriciamentos", headers=conta["headers"])
    assert r.json() == []


async def test_sigilo_matriciamento(client, conta):
    owner = conta
    r = await client.post("/equipe/profissionais", headers=owner["headers"], json={
        "nome": "Prof M", "email": "matricb@example.com", "senha": "senha12345", "crp": "06/888888",
    })
    assert r.status_code == 201, r.text
    prof = await _login_e_2fa(client, "matricb@example.com", "senha12345")

    pid = await _novo_paciente(client, owner["headers"], "Paciente do Owner")
    caso = await _novo_caso(client, owner["headers"], pid)
    # Profissional não acessa/registra matriciamento no caso de outro (404).
    assert (await client.get(f"/casos/{caso}/matriciamentos", headers=prof)).status_code == 404
    assert (await client.post(f"/casos/{caso}/matriciamentos", headers=prof,
                              json={"demanda": "x"})).status_code == 404
