# Práxis (by CENAT)

Copiloto clínico para psicólogos que trabalham com novas abordagens em saúde mental.
Assistente interno: **Sofia**.

## Stack

- Backend: FastAPI 0.128 async · SQLAlchemy 2 async · PostgreSQL 16 (aqui reutilizando PG14+pgvector do host) · `uv`
- Frontend: Next 16 · React 19 · Tailwind 4 (raw) · lucide-react · sonner · `npm`
- Migrações: scripts SQL versionados em `backend/migrations/` (**sem Alembic**)
- Deploy: `systemd` na VPS (portas `8040` backend, `3040` frontend). Sem nginx/domínio nesta sprint.

## Layout

```
backend/    FastAPI + migrações + runner
frontend/   Next.js App Router
deploy/     unit-files systemd
```

## Setup local

```bash
# 1) Backend
cd backend
cp ../.env.example .env      # e ajuste segredos
uv sync
uv run python migrations/run_migrations.py
uv run uvicorn app.main:app --host 127.0.0.1 --port 8040 --reload

# 2) Frontend
cd ../frontend
npm install
npm run dev -- -p 3040
```

## Segurança

- PII de paciente cifrada em repouso (Fernet AEAD, chave em `PRAXIS_FIELD_KEY`).
- Autenticação com JWT + 2FA TOTP obrigatório.
- Isolamento por `tenant_id` em todo dado clínico.
- `audit_log` grava cada acesso/edição/exportação.
- Soft-delete respeitando prazos LGPD/CFP (5 anos registros administrativos, 20 anos prontuário).

## Regras de marca

- **Proibido** usar os ícones `Brain`, `BrainCircuit`, `BrainCog` do `lucide-react`.
