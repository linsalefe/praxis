"""Validação de CRP no cadastro (S4)."""
import pytest


@pytest.mark.parametrize("crp_invalido", ["abc", "123", "6/1", "06/12"])
async def test_register_crp_invalido_422(client, crp_invalido):
    r = await client.post("/auth/register", json={
        "nome": "X Y", "email": "crpbad@example.com", "senha": "senha12345",
        "crp": crp_invalido, "tenant_nome": "Consultorio",
    })
    assert r.status_code == 422


async def test_register_crp_normalizado(client):
    r = await client.post("/auth/register", json={
        "nome": "X Y", "email": "crpok@example.com", "senha": "senha12345",
        "crp": "CRP 06/12345", "tenant_nome": "Consultorio",
    })
    assert r.status_code == 201
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    me = (await client.get("/auth/me", headers=headers)).json()
    assert me["crp"] == "06/12345"
    assert me["crp_verificado"] is False


async def test_register_sem_crp_ok(client):
    r = await client.post("/auth/register", json={
        "nome": "X Y", "email": "semcrp@example.com", "senha": "senha12345",
        "tenant_nome": "Consultorio",
    })
    assert r.status_code == 201
