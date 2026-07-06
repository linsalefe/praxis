"""Rate-limit / lockout de login (S2)."""


async def test_lockout_apos_5_falhas(client, criar_conta):
    conta = await criar_conta(com_2fa=False)
    payload = {"email": conta["email"], "senha": "errada____"}
    # 5 falhas de credencial → 401 cada.
    for _ in range(5):
        r = await client.post("/auth/login", json=payload)
        assert r.status_code == 401
    # 6ª tentativa: bloqueado → 429 com Retry-After.
    r = await client.post("/auth/login", json=payload)
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    # Mesmo com a senha CORRETA, segue bloqueado enquanto no lockout.
    r = await client.post("/auth/login", json={"email": conta["email"], "senha": conta["senha"]})
    assert r.status_code == 429


async def test_sucesso_reseta_contador(client, criar_conta):
    conta = await criar_conta(com_2fa=False)
    # Poucas falhas (abaixo do limiar), depois sucesso.
    for _ in range(3):
        r = await client.post("/auth/login", json={"email": conta["email"], "senha": "errada____"})
        assert r.status_code == 401
    r = await client.post("/auth/login", json={"email": conta["email"], "senha": conta["senha"]})
    assert r.status_code == 200
    # Contador zerado: novas falhas não bloqueiam de imediato.
    r = await client.post("/auth/login", json={"email": conta["email"], "senha": "errada____"})
    assert r.status_code == 401
