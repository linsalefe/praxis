"""Posvenção (fecha Onda 1.1): protocolo, cifragem do plano em repouso, sigilo
por profissional e evolução do status do processo."""
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


async def test_definicao_disponivel(client, conta):
    r = await client.get("/posvencao/definicao", headers=conta["headers"])
    assert r.status_code == 200
    body = r.json()
    assert any(p["id"] == "acolhimento" for p in body["passos"])
    assert any(v["valor"] == "proprio_paciente" for v in body["vinculos_perda"])
    assert {s["valor"] for s in body["status"]} == {"aberto", "em_acompanhamento", "concluido"}


async def test_criar_conta_passos_preenchidos(client, conta):
    pid = await _novo_paciente(client, conta["headers"], "Enlutado")
    r = await client.post(
        f"/pacientes/{pid}/posvencao",
        headers=conta["headers"],
        json={
            "ocorrido_em": "2026-07-01",
            "vinculo_perda": "familiar",
            "plano_posvencao": {
                "acolhimento": "escuta na primeira semana",
                "rede_apoio": "acionado CAPS de referência",
                "inexistente": "deve ser ignorado",  # chave desconhecida
                "luto": "   ",  # vazio → descartado
            },
            "observacoes": "combinado retorno semanal",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "aberto"
    assert body["vinculo_perda"] == "familiar"
    assert body["passos_preenchidos"] == 2  # só os dois passos válidos e não vazios
    assert "inexistente" not in body["plano_posvencao"]
    assert body["plano_posvencao"]["acolhimento"] == "escuta na primeira semana"
    assert body["observacoes"] == "combinado retorno semanal"


async def test_plano_posvencao_cifrado_em_repouso(client, conta):
    """O plano de posvenção contém PII de enlutados → cifrado no banco."""
    from sqlalchemy import text
    from app.db import engine

    pid = await _novo_paciente(client, conta["headers"], "Paciente Cripto Posv")
    await client.post(
        f"/pacientes/{pid}/posvencao",
        headers=conta["headers"],
        json={
            "ocorrido_em": "2026-06-15",
            "vinculo_perda": "amigo",
            "plano_posvencao": {"contatos_ajuda": "irmã", "acolhimento": "Joana Prado, mãe, 11 98888-0000"},
        },
    )
    async with engine.begin() as conn:
        row = (await conn.execute(text(
            "SELECT plano_posvencao_cifrado FROM registros_posvencao LIMIT 1"))).first()
    blob = bytes(row[0])
    assert b"Joana Prado" not in blob and b"98888" not in blob  # não vaza em claro


async def test_evolucao_do_status(client, conta):
    pid = await _novo_paciente(client, conta["headers"], "Processo Posv")
    r = await client.post(
        f"/pacientes/{pid}/posvencao",
        headers=conta["headers"],
        json={"ocorrido_em": "2026-05-10", "vinculo_perda": "proprio_paciente"},
    )
    rid = r.json()["id"]
    assert r.json()["status"] == "aberto"

    # Avança o status e acrescenta um passo.
    r = await client.patch(
        f"/posvencao/{rid}",
        headers=conta["headers"],
        json={"status": "em_acompanhamento", "plano_posvencao": {"cuidado_equipe": "debriefing com a equipe"}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "em_acompanhamento"
    assert r.json()["passos_preenchidos"] == 1

    # Lista traz o registro com o status atualizado.
    lst = await client.get(f"/pacientes/{pid}/posvencao", headers=conta["headers"])
    assert [x["status"] for x in lst.json()] == ["em_acompanhamento"]

    # Conclui.
    r = await client.patch(f"/posvencao/{rid}", headers=conta["headers"], json={"status": "concluido"})
    assert r.json()["status"] == "concluido"


async def test_sigilo_por_profissional_na_posvencao(client, conta):
    owner = conta
    r = await client.post("/equipe/profissionais", headers=owner["headers"], json={
        "nome": "Prof Posv", "email": "posvb@example.com", "senha": "senha12345", "crp": "06/444444",
    })
    assert r.status_code == 201, r.text
    prof = await _login_e_2fa(client, "posvb@example.com", "senha12345")

    pid_owner = await _novo_paciente(client, owner["headers"], "Paciente do Owner Posv")
    # Profissional não cria posvenção no paciente de outro (404, não vaza).
    r = await client.post(f"/pacientes/{pid_owner}/posvencao", headers=prof,
                          json={"ocorrido_em": "2026-07-01", "vinculo_perda": "familiar"})
    assert r.status_code == 404
    # Nem lista.
    assert (await client.get(f"/pacientes/{pid_owner}/posvencao", headers=prof)).status_code == 404


async def test_registro_inexistente_404(client, conta):
    import uuid
    r = await client.get(f"/posvencao/{uuid.uuid4()}", headers=conta["headers"])
    assert r.status_code == 404
