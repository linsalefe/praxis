"""Módulo de risco (Onda 1.1): estratificação C-SSRS, derivação server-side,
sigilo por profissional, cifragem do Plano de Segurança e sinal do Scribe."""
import urllib.parse as up

import pyotp

from app.risco.scoring import detectar_sinal_risco, estratificar


# --- Estratificação determinística (pura) ----------------------------------

def test_estratificacao_minimo():
    assert estratificar({})["nivel"] == "minimo"
    assert estratificar({"q1": False, "q2": False})["nivel"] == "minimo"


def test_estratificacao_baixo_por_ideacao():
    assert estratificar({"q1": True})["nivel"] == "baixo"
    assert estratificar({"q2": True})["nivel"] == "baixo"


def test_estratificacao_baixo_por_comportamento_ao_longo_da_vida():
    assert estratificar({"comportamento_quando": "vida"})["nivel"] == "baixo"


def test_estratificacao_moderado_por_metodo():
    r = estratificar({"q2": True, "q3": True})
    assert r["nivel"] == "moderado"
    assert "q3" in r["gatilhos"]


def test_estratificacao_alto_por_intencao_plano_ou_comportamento_recente():
    assert estratificar({"q4": True})["nivel"] == "alto"
    assert estratificar({"q5": True})["nivel"] == "alto"
    assert estratificar({"comportamento_quando": "recente"})["nivel"] == "alto"
    assert estratificar({"q3": True, "q5": True})["nivel"] == "alto"  # o mais grave vence


def test_detectar_sinal_risco():
    assert detectar_sinal_risco("paciente relata ideação suicida recorrente") is True
    assert detectar_sinal_risco("Falou que seria melhor estar morto") is True
    assert detectar_sinal_risco("sessão tranquila, sem intercorrências") is False
    assert detectar_sinal_risco(None) is False


# --- Fluxo de API -----------------------------------------------------------

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


async def test_criar_avaliacao_deriva_nivel_no_servidor(client, conta):
    pid = await _novo_paciente(client, conta["headers"], "Paciente Risco")
    # Cliente não decide o nível: q5=True ⇒ alto, independentemente de qualquer campo.
    r = await client.post(
        f"/pacientes/{pid}/avaliacoes-risco",
        headers=conta["headers"],
        json={
            "cssrs": {"q1": True, "q2": True, "q5": True, "comportamento_quando": "nao"},
            "plano_seguranca": {"sinais_alerta": "insônia e isolamento",
                                "profissionais_agencias": "CVV 188; CAPS III"},
            "observacoes": "combinado retorno em 48h",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["nivel_risco"] == "alto"
    assert "q5" in body["gatilhos"]
    assert body["plano_seguranca"]["sinais_alerta"] == "insônia e isolamento"
    assert body["observacoes"] == "combinado retorno em 48h"


async def test_risco_atual_reflete_ultima_avaliacao(client, conta):
    pid = await _novo_paciente(client, conta["headers"], "Paciente Fluxo")
    # Sem avaliação ainda.
    r = await client.get(f"/pacientes/{pid}/risco-atual", headers=conta["headers"])
    assert r.status_code == 200 and r.json()["tem_avaliacao"] is False

    # Primeira: baixo.
    await client.post(f"/pacientes/{pid}/avaliacoes-risco", headers=conta["headers"],
                      json={"cssrs": {"q1": True}, "avaliado_em": "2026-07-01T10:00:00+00:00"})
    # Segunda (mais recente): moderado.
    await client.post(f"/pacientes/{pid}/avaliacoes-risco", headers=conta["headers"],
                      json={"cssrs": {"q3": True}, "avaliado_em": "2026-07-05T10:00:00+00:00"})

    r = await client.get(f"/pacientes/{pid}/risco-atual", headers=conta["headers"])
    assert r.json()["tem_avaliacao"] is True
    assert r.json()["nivel_risco"] == "moderado"

    lst = await client.get(f"/pacientes/{pid}/avaliacoes-risco", headers=conta["headers"])
    assert [a["nivel_risco"] for a in lst.json()] == ["moderado", "baixo"]  # mais recente primeiro


async def test_plano_seguranca_cifrado_em_repouso(client, conta):
    """O Plano de Segurança contém PII de rede de apoio → cifrado no banco."""
    from sqlalchemy import text
    from app.db import engine

    pid = await _novo_paciente(client, conta["headers"], "Paciente Cripto")
    await client.post(f"/pacientes/{pid}/avaliacoes-risco", headers=conta["headers"],
                      json={"cssrs": {"q1": True},
                            "plano_seguranca": {"contatos_ajuda": "Maria Silva (irmã) 11 99999-0000"}})
    async with engine.begin() as conn:
        row = (await conn.execute(text(
            "SELECT plano_seguranca_cifrado FROM avaliacoes_risco LIMIT 1"))).first()
    blob = bytes(row[0])
    assert b"Maria Silva" not in blob and b"99999" not in blob  # não vaza em claro


async def test_sigilo_por_profissional_no_risco(client, conta):
    owner = conta
    # cria profissional e loga
    r = await client.post("/equipe/profissionais", headers=owner["headers"], json={
        "nome": "Prof B", "email": "riscob@example.com", "senha": "senha12345", "crp": "06/333333",
    })
    assert r.status_code == 201, r.text
    prof = await _login_e_2fa(client, "riscob@example.com", "senha12345")

    pid_owner = await _novo_paciente(client, owner["headers"], "Paciente do Owner")
    # Profissional não cria avaliação no paciente de outro (404, não vaza).
    r = await client.post(f"/pacientes/{pid_owner}/avaliacoes-risco", headers=prof,
                          json={"cssrs": {"q1": True}})
    assert r.status_code == 404
    # Nem lê o risco-atual dele.
    assert (await client.get(f"/pacientes/{pid_owner}/risco-atual", headers=prof)).status_code == 404


async def test_definicao_disponivel(client, conta):
    r = await client.get("/risco/definicao", headers=conta["headers"])
    assert r.status_code == 200
    body = r.json()
    assert len(body["cssrs"]["itens"]) == 6
    assert any(p["id"] == "sinais_alerta" for p in body["plano_seguranca"]["passos"])
