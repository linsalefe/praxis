"""Laudo de risco psicossocial NR-1 (Onda 3.1)."""
import urllib.parse as up

import pyotp


async def _login_e_2fa(client, email: str, senha: str) -> dict:
    r = await client.post("/auth/login", json={"email": email, "senha": senha})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    rs = await client.post("/auth/2fa/setup", headers=headers)
    secret = up.parse_qs(up.urlparse(rs.json()["otpauth_url"]).query)["secret"][0]
    await client.post("/auth/2fa/verify", headers=headers, json={"codigo": pyotp.TOTP(secret).now()})
    return headers


async def test_criar_editar_finalizar_laudo(client, conta):
    r = await client.post("/laudos-nr1", headers=conta["headers"], json={
        "organizacao": "Empresa X", "setor": "Atendimento", "responsavel": "Psi. Fulano CRP 06/123",
    })
    assert r.status_code == 201, r.text
    laudo = r.json()
    assert laudo["status"] == "rascunho"

    # Avalia fatores (fator inválido é descartado).
    r = await client.patch(f"/laudos-nr1/{laudo['id']}", headers=conta["headers"], json={
        "fatores": {
            "carga_ritmo": {"nivel": "alto", "observacao": "metas agressivas"},
            "assedio_violencia": {"nivel": "medio"},
            "fator_inexistente": {"nivel": "alto"},
        },
        "analise": "há sobrecarga relevante",
        "recomendacoes": "revisar metas e canal de denúncia",
    })
    assert r.status_code == 200, r.text
    fatores = r.json()["fatores"]
    assert fatores["carga_ritmo"]["nivel"] == "alto"
    assert "fator_inexistente" not in fatores

    # Lista traz contagem de fatores altos.
    r = await client.get("/laudos-nr1", headers=conta["headers"])
    item = next(x for x in r.json() if x["id"] == laudo["id"])
    assert item["fatores_alto"] == 1

    # Finaliza e trava edição.
    r = await client.post(f"/laudos-nr1/{laudo['id']}/finalizar", headers=conta["headers"])
    assert r.json()["status"] == "finalizado" and r.json()["finalizado_em"] is not None
    r = await client.patch(f"/laudos-nr1/{laudo['id']}", headers=conta["headers"], json={"analise": "x"})
    assert r.status_code == 409


async def test_nivel_invalido_rejeitado(client, conta):
    laudo = (await client.post("/laudos-nr1", headers=conta["headers"], json={"organizacao": "Y"})).json()
    r = await client.patch(f"/laudos-nr1/{laudo['id']}", headers=conta["headers"], json={
        "fatores": {"carga_ritmo": {"nivel": "gravissimo"}},
    })
    assert r.status_code == 422  # Literal do schema barra nível fora do enum


async def test_definicao_nr1(client, conta):
    r = await client.get("/laudos-nr1/definicao", headers=conta["headers"])
    assert r.status_code == 200
    ids = {f["id"] for f in r.json()["fatores"]}
    assert {"carga_ritmo", "assedio_violencia", "autonomia_controle"} <= ids


async def test_sigilo_laudo_por_profissional(client, conta):
    owner = conta
    r = await client.post("/equipe/profissionais", headers=owner["headers"], json={
        "nome": "Prof L", "email": "laudob@example.com", "senha": "senha12345", "crp": "06/999999",
    })
    assert r.status_code == 201, r.text
    prof = await _login_e_2fa(client, "laudob@example.com", "senha12345")

    laudo = (await client.post("/laudos-nr1", headers=owner["headers"], json={"organizacao": "Do Owner"})).json()
    # Profissional não vê o laudo do owner na lista nem no detalhe.
    r = await client.get("/laudos-nr1", headers=prof)
    assert all(x["id"] != laudo["id"] for x in r.json())
    assert (await client.get(f"/laudos-nr1/{laudo['id']}", headers=prof)).status_code == 404
