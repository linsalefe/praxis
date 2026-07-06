"""Revogação de sessão server-side (S3)."""
import pyotp


async def _login_2fa(client, email, senha, secret) -> dict:
    r = await client.post("/auth/login", json={"email": email, "senha": senha})
    assert r.status_code == 200 and r.json()["mfa_required"] is True
    pre = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = await client.post("/auth/2fa/login", headers=pre, json={"codigo": pyotp.TOTP(secret).now()})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_logout_revoga_sessao_atual(client, conta):
    # Sessão válida acessa rota clínica.
    assert (await client.get("/pacientes", headers=conta["headers"])).status_code == 200
    # Logout revoga o token atual (blocklist por jti).
    assert (await client.post("/auth/logout", headers=conta["headers"])).status_code == 204
    # O mesmo token deixa de funcionar.
    assert (await client.get("/pacientes", headers=conta["headers"])).status_code == 401


async def test_logout_idempotente(client, conta):
    assert (await client.post("/auth/logout", headers=conta["headers"])).status_code == 204
    # Segundo logout com token já revogado ainda responde 204 (get_principal só
    # exige assinatura/exp válidos, não checa blocklist).
    assert (await client.post("/auth/logout", headers=conta["headers"])).status_code == 204


async def test_revogar_todas_invalida_e_relogin_funciona(client, conta):
    # Encerra todas as sessões → token atual morre.
    assert (await client.post("/auth/sessoes/revogar-todas", headers=conta["headers"])).status_code == 204
    assert (await client.get("/pacientes", headers=conta["headers"])).status_code == 401
    # Novo login (auth_at > epoch) volta a funcionar.
    novo = await _login_2fa(client, conta["email"], conta["senha"], conta["secret"])
    assert (await client.get("/pacientes", headers=novo)).status_code == 200


async def test_token_tem_jti(conta):
    import base64, json
    payload_b64 = conta["token"].split(".")[1]
    payload_b64 += "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    assert "jti" in payload and payload["jti"]
