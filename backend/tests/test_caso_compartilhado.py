"""PTS colaborativo (Onda 2.1): compartilhamento de caso com a equipe.

Modelo = flag por caso. Compartilhado ⇒ toda a equipe clínica do tenant vê e
co-edita PTS/matriciamento/rede DAQUELE caso — e nada mais do prontuário. Toggle
restrito ao dono do caso/owner. Autoria (autor_nome) atribuída em cada versão.
"""
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


async def _prof(client, owner_headers, nome, email, crp) -> dict:
    r = await client.post("/equipe/profissionais", headers=owner_headers, json={
        "nome": nome, "email": email, "senha": "senha12345", "crp": crp,
    })
    assert r.status_code == 201, r.text
    return await _login_e_2fa(client, email, "senha12345")


async def test_caso_compartilhado_visivel_e_coeditavel_pela_equipe(client, conta):
    owner = conta
    prof = await _prof(client, owner["headers"], "Prof Equipe", "coedita@example.com", "06/501001")

    pid = await _novo_paciente(client, owner["headers"], "Paciente Compartilhado")
    caso = (await client.post(f"/pacientes/{pid}/casos", headers=owner["headers"],
                              json={"titulo": "Caso RAPS"})).json()
    cid = caso["id"]

    # Sem compartilhar: prof não vê (404).
    assert (await client.get(f"/casos/{cid}", headers=prof)).status_code == 404

    # Owner compartilha.
    r = await client.patch(f"/casos/{cid}", headers=owner["headers"], json={"compartilhado": True})
    assert r.status_code == 200 and r.json()["compartilhado"] is True

    # Agora o prof vê o caso; não pode alterar o compartilhamento (não é dono/owner).
    r = await client.get(f"/casos/{cid}", headers=prof)
    assert r.status_code == 200
    assert r.json()["compartilhado"] is True
    assert r.json()["pode_compartilhar"] is False

    # E co-edita o PTS (várias mãos) — a versão fica atribuída a ele.
    r = await client.post(f"/casos/{cid}/pts", headers=prof,
                          json={"conteudo": {"metas": "contribuição da equipe"}})
    assert r.status_code == 201, r.text
    assert r.json()["autor_nome"] == "Prof Equipe"

    # O caso aparece no quadro de compartilhados do prof, com nome do paciente e dono.
    r = await client.get("/casos/compartilhados", headers=prof)
    assert r.status_code == 200
    board = {c["id"]: c for c in r.json()}
    assert cid in board
    assert board[cid]["paciente_nome"].lower().startswith("paciente compartilhado")
    assert board[cid]["dono_nome"] is not None


async def test_toggle_compartilhamento_restrito_ao_dono_ou_owner(client, conta):
    owner = conta
    prof_a = await _prof(client, owner["headers"], "Prof A", "toggle_a@example.com", "06/501002")
    prof_b = await _prof(client, owner["headers"], "Prof B", "toggle_b@example.com", "06/501003")

    # Caso pertence ao prof A (ele é o dono do paciente e do caso).
    pid = await _novo_paciente(client, prof_a, "Paciente do A")
    cid = (await client.post(f"/pacientes/{pid}/casos", headers=prof_a, json={})).json()["id"]

    # A (dono do caso) compartilha — pode.
    assert (await client.patch(f"/casos/{cid}", headers=prof_a, json={"compartilhado": True})).status_code == 200

    # B vê o caso (compartilhado), mas NÃO pode desligar o compartilhamento (403).
    assert (await client.get(f"/casos/{cid}", headers=prof_b)).status_code == 200
    assert (await client.patch(f"/casos/{cid}", headers=prof_b, json={"compartilhado": False})).status_code == 403

    # A pode desligar; e o owner do tenant também poderia.
    assert (await client.patch(f"/casos/{cid}", headers=prof_a, json={"compartilhado": False})).status_code == 200
    # Desligado, B volta a não ver.
    assert (await client.get(f"/casos/{cid}", headers=prof_b)).status_code == 404


async def test_compartilhar_caso_nao_expoe_resto_do_prontuario(client, conta):
    """Compartilhar o caso abre o caso — não o prontuário do paciente."""
    owner = conta
    prof = await _prof(client, owner["headers"], "Prof Limite", "limite@example.com", "06/501004")

    pid = await _novo_paciente(client, owner["headers"], "Paciente Limite")
    cid = (await client.post(f"/pacientes/{pid}/casos", headers=owner["headers"], json={})).json()["id"]
    # Dados clínicos fora do caso, do dono.
    await client.post(f"/pacientes/{pid}/avaliacoes-risco", headers=owner["headers"],
                      json={"cssrs": {"q1": True}})
    await client.patch(f"/casos/{cid}", headers=owner["headers"], json={"compartilhado": True})

    # O prof acessa o caso...
    assert (await client.get(f"/casos/{cid}", headers=prof)).status_code == 200
    # ...mas NÃO o paciente nem seus outros dados clínicos.
    assert (await client.get(f"/pacientes/{pid}", headers=prof)).status_code == 404
    assert (await client.get(f"/pacientes/{pid}/avaliacoes-risco", headers=prof)).status_code == 404
    assert (await client.get(f"/pacientes/{pid}/risco-atual", headers=prof)).status_code == 404


async def test_matriciamento_colaborativo_atribui_autor(client, conta):
    owner = conta
    prof = await _prof(client, owner["headers"], "Prof Matric", "matric@example.com", "06/501005")

    pid = await _novo_paciente(client, owner["headers"], "Paciente Matric")
    cid = (await client.post(f"/pacientes/{pid}/casos", headers=owner["headers"], json={})).json()["id"]
    await client.patch(f"/casos/{cid}", headers=owner["headers"], json={"compartilhado": True})

    r = await client.post(f"/casos/{cid}/matriciamentos", headers=prof,
                          json={"equipe_referencia": "ESF Vila", "demanda": "discutir caso"})
    assert r.status_code == 201, r.text
    assert r.json()["autor_nome"] == "Prof Matric"

    # Aparece na lista para o owner, com a autoria do prof.
    r = await client.get(f"/casos/{cid}/matriciamentos", headers=owner["headers"])
    assert r.json()[0]["autor_nome"] == "Prof Matric"


async def test_compartilhados_lista_so_os_compartilhados(client, conta):
    owner = conta
    prof = await _prof(client, owner["headers"], "Prof Board", "board@example.com", "06/501006")

    pid = await _novo_paciente(client, owner["headers"], "Paciente Board")
    # Um caso privado, um compartilhado.
    privado = (await client.post(f"/pacientes/{pid}/casos", headers=owner["headers"], json={})).json()["id"]
    compart = (await client.post(f"/pacientes/{pid}/casos", headers=owner["headers"], json={})).json()["id"]
    await client.patch(f"/casos/{compart}", headers=owner["headers"], json={"compartilhado": True})

    ids = {c["id"] for c in (await client.get("/casos/compartilhados", headers=prof)).json()}
    assert compart in ids
    assert privado not in ids
