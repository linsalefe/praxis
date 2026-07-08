"""Espinha Caso/PTS (Onda 1.2): criação, PTS versionado, sessão pendurada em
caso, sigilo por profissional."""
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


async def test_criar_caso_e_versionar_pts(client, conta):
    pid = await _novo_paciente(client, conta["headers"], "Paciente Caso")
    r = await client.post(f"/pacientes/{pid}/casos", headers=conta["headers"],
                          json={"titulo": "Acompanhamento RAPS"})
    assert r.status_code == 201, r.text
    caso = r.json()
    assert caso["status"] == "ativo" and caso["pts_atual"] is None

    # Primeira versão do PTS.
    r = await client.post(f"/casos/{caso['id']}/pts", headers=conta["headers"],
                          json={"conteudo": {"compreensao": "jovem em CAPS", "metas": "reduzir crises",
                                             "chave_invalida": "ignorar"}})
    assert r.status_code == 201, r.text
    assert r.json()["versao"] == 1
    assert "chave_invalida" not in r.json()["conteudo"]  # só seções conhecidas

    # Segunda versão.
    r = await client.post(f"/casos/{caso['id']}/pts", headers=conta["headers"],
                          json={"conteudo": {"compreensao": "revisado", "reavaliacao": "em 30 dias"}})
    assert r.json()["versao"] == 2

    # PTS atual = versão 2.
    r = await client.get(f"/casos/{caso['id']}", headers=conta["headers"])
    assert r.json()["pts_atual"]["versao"] == 2
    assert r.json()["pts_atual"]["conteudo"]["compreensao"] == "revisado"

    # Histórico tem as duas, mais recente primeiro.
    r = await client.get(f"/casos/{caso['id']}/pts", headers=conta["headers"])
    assert [v["versao"] for v in r.json()] == [2, 1]


async def test_encerrar_caso(client, conta):
    pid = await _novo_paciente(client, conta["headers"], "Paciente Encerrar")
    caso = (await client.post(f"/pacientes/{pid}/casos", headers=conta["headers"], json={})).json()
    r = await client.patch(f"/casos/{caso['id']}", headers=conta["headers"], json={"status": "encerrado"})
    assert r.status_code == 200
    assert r.json()["status"] == "encerrado" and r.json()["encerrado_em"] is not None


async def test_sessao_pendurada_em_caso(client, conta):
    pid = await _novo_paciente(client, conta["headers"], "Paciente Sessao Caso")
    caso = (await client.post(f"/pacientes/{pid}/casos", headers=conta["headers"], json={})).json()
    r = await client.post("/sessoes", headers=conta["headers"], json={
        "paciente_id": pid, "data": "2026-07-08T10:00:00+00:00",
        "modalidade": "presencial", "caso_id": caso["id"],
    })
    assert r.status_code == 201, r.text
    assert r.json()["caso_id"] == caso["id"]


async def test_sessao_com_caso_de_outro_paciente_falha(client, conta):
    p1 = await _novo_paciente(client, conta["headers"], "P1")
    p2 = await _novo_paciente(client, conta["headers"], "P2")
    caso_p1 = (await client.post(f"/pacientes/{p1}/casos", headers=conta["headers"], json={})).json()
    # Tenta pendurar sessão de p2 num caso de p1 → 404 (não vaza).
    r = await client.post("/sessoes", headers=conta["headers"], json={
        "paciente_id": p2, "data": "2026-07-08T10:00:00+00:00",
        "modalidade": "presencial", "caso_id": caso_p1["id"],
    })
    assert r.status_code == 404


async def test_sigilo_por_profissional_no_caso(client, conta):
    owner = conta
    r = await client.post("/equipe/profissionais", headers=owner["headers"], json={
        "nome": "Prof C", "email": "casob@example.com", "senha": "senha12345", "crp": "06/444444",
    })
    assert r.status_code == 201, r.text
    prof = await _login_e_2fa(client, "casob@example.com", "senha12345")

    pid = await _novo_paciente(client, owner["headers"], "Paciente do Owner")
    caso = (await client.post(f"/pacientes/{pid}/casos", headers=owner["headers"], json={})).json()
    # Profissional não acessa o caso do paciente de outro (404).
    assert (await client.get(f"/casos/{caso['id']}", headers=prof)).status_code == 404
    assert (await client.post(f"/casos/{caso['id']}/pts", headers=prof,
                              json={"conteudo": {"metas": "x"}})).status_code == 404


async def test_definicao_pts(client, conta):
    r = await client.get("/casos/pts/definicao", headers=conta["headers"])
    assert r.status_code == 200
    assert any(s["id"] == "compreensao" for s in r.json()["secoes"])
