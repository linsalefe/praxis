"""Isolamento multi-tenant: um tenant não enxerga paciente de outro."""


async def test_paciente_de_outro_tenant_nao_acessivel(client, criar_conta):
    a = await criar_conta(tenant_nome="Clinica A")
    b = await criar_conta(tenant_nome="Clinica B")

    r = await client.post("/pacientes", headers=a["headers"], json={"nome": "Paciente de A"})
    assert r.status_code == 201
    pid_a = r.json()["id"]

    # B não obtém o paciente de A (404, não 403 — não vaza existência).
    r = await client.get(f"/pacientes/{pid_a}", headers=b["headers"])
    assert r.status_code == 404

    # A lista de B não inclui o paciente de A.
    r = await client.get("/pacientes", headers=b["headers"])
    assert r.status_code == 200
    assert r.json() == []

    # A enxerga o próprio paciente.
    r = await client.get(f"/pacientes/{pid_a}", headers=a["headers"])
    assert r.status_code == 200
    assert r.json()["nome"] == "Paciente de A"
