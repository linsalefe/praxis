"""Isolamento por profissional dentro da clínica (P1)."""
import urllib.parse as up

import pyotp


async def _login_e_2fa(client, email: str, senha: str) -> dict:
    r = await client.post("/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    rs = await client.post("/auth/2fa/setup", headers=headers)
    secret = up.parse_qs(up.urlparse(rs.json()["otpauth_url"]).query)["secret"][0]
    r = await client.post("/auth/2fa/verify", headers=headers, json={"codigo": pyotp.TOTP(secret).now()})
    assert r.status_code == 200, r.text
    return headers


async def _novo_paciente(client, headers, nome: str) -> str:
    r = await client.post("/pacientes", headers=headers, json={"nome": nome})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _add_profissional(client, owner_headers, email: str) -> dict:
    r = await client.post("/equipe/profissionais", headers=owner_headers, json={
        "nome": "Profissional", "email": email, "senha": "senha12345", "crp": "06/222222",
    })
    assert r.status_code == 201, r.text
    assert r.json()["papel"] == "profissional"
    return await _login_e_2fa(client, email, "senha12345")


async def test_profissional_ve_so_os_seus_owner_ve_todos(client, conta):
    owner = conta  # papel owner, 2FA ativo
    prof = await _add_profissional(client, owner["headers"], "beta@example.com")

    pid_owner = await _novo_paciente(client, owner["headers"], "Paciente do Owner")
    pid_prof = await _novo_paciente(client, prof, "Paciente da Beta")

    # Profissional enxerga apenas o próprio paciente.
    r = await client.get("/pacientes", headers=prof)
    assert {p["id"] for p in r.json()} == {pid_prof}

    # Profissional não acessa o paciente do owner (404, não vaza).
    assert (await client.get(f"/pacientes/{pid_owner}", headers=prof)).status_code == 404

    # Owner enxerga todos os pacientes da clínica.
    r = await client.get("/pacientes", headers=owner["headers"])
    assert {p["id"] for p in r.json()} == {pid_owner, pid_prof}
    # Owner acessa o paciente da profissional.
    assert (await client.get(f"/pacientes/{pid_prof}", headers=owner["headers"])).status_code == 200


async def test_profissional_nao_acessa_sessoes_de_outro(client, conta):
    owner = conta
    prof = await _add_profissional(client, owner["headers"], "gama@example.com")
    pid_owner = await _novo_paciente(client, owner["headers"], "Paciente do Owner")
    # Sessão do paciente do owner.
    r = await client.post("/sessoes", headers=owner["headers"], json={
        "paciente_id": pid_owner, "data": "2026-07-06T10:00:00+00:00", "modalidade": "presencial",
    })
    assert r.status_code == 201
    # Profissional não lista sessões do paciente de outro → 404.
    assert (await client.get(f"/sessoes/paciente/{pid_owner}", headers=prof)).status_code == 404


async def test_profissional_nao_gerencia_equipe(client, conta):
    prof = await _add_profissional(client, conta["headers"], "delta@example.com")
    r = await client.post("/equipe/profissionais", headers=prof, json={
        "nome": "X", "email": "epsilon@example.com", "senha": "senha12345",
    })
    assert r.status_code == 403
    assert (await client.get("/equipe", headers=prof)).status_code == 403


async def test_owner_lista_equipe(client, conta):
    await _add_profissional(client, conta["headers"], "zeta@example.com")
    r = await client.get("/equipe", headers=conta["headers"])
    assert r.status_code == 200
    assert sorted(m["papel"] for m in r.json()) == ["owner", "profissional"]
