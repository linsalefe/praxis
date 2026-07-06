"""2FA obrigatório (S1) e fluxo de autenticação."""


async def test_rota_clinica_sem_2fa_retorna_403_com_code(client, criar_conta):
    conta = await criar_conta(com_2fa=False)
    r = await client.get("/pacientes", headers=conta["headers"])
    assert r.status_code == 403
    detalhe = r.json()["detail"]
    assert isinstance(detalhe, dict) and detalhe["code"] == "2fa_setup_required"


async def test_onboarding_2fa_acessivel_sem_2fa(client, criar_conta):
    """/auth/me e /2fa/setup precisam funcionar durante o onboarding."""
    conta = await criar_conta(com_2fa=False)
    r = await client.get("/auth/me", headers=conta["headers"])
    assert r.status_code == 200
    assert r.json()["totp_ativado"] is False
    r = await client.post("/auth/2fa/setup", headers=conta["headers"])
    assert r.status_code == 200


async def test_2fa_ativo_libera_rota_clinica(client, conta):
    r = await client.get("/pacientes", headers=conta["headers"])
    assert r.status_code == 200


async def test_sem_token_401(client):
    r = await client.get("/pacientes")
    assert r.status_code == 401


async def test_login_credenciais_invalidas_401(client, criar_conta):
    conta = await criar_conta(com_2fa=False)
    r = await client.post("/auth/login", json={"email": conta["email"], "senha": "errada____"})
    assert r.status_code == 401


async def test_login_ok_emite_token_utilizavel(client, criar_conta):
    conta = await criar_conta(com_2fa=False)
    r = await client.post("/auth/login", json={"email": conta["email"], "senha": conta["senha"]})
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "session" and body["mfa_required"] is False
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert (await client.get("/auth/me", headers=headers)).status_code == 200
