# Práxis (by CENAT)

**Copiloto clínico para psicólogos que trabalham com novas abordagens em saúde mental**
(Diálogo Aberto, Ouvir Vozes, GAM, PTMF, WRAP, Redução de Danos).

Assistente interno: **Sofia** — responde com base no acervo curado do CENAT, sempre com citação de fontes e disclaimer de responsabilidade técnica do profissional.

> Para quem: psicólogas(os) e serviços que praticam abordagens contemporâneas em saúde mental e precisam de prontuário conforme CFP, apoio ao raciocínio clínico e geração de documentos, sem abrir mão de LGPD e da assinatura profissional.

---

## 1. Funcionalidades

Cada capacidade abaixo é entregue por um router do backend e telas correspondentes no frontend.

- **Prontuário CFP** — cadastro de pacientes (PII cifrada em repouso), sessões, evoluções com assinatura do profissional, termos de consentimento. Soft-delete respeitando prazos de retenção.
- **Sofia (RAG no acervo)** — pergunta livre respondida a partir dos trechos mais relevantes do acervo CENAT (busca vetorial pgvector), **com citação de fontes** no formato `[Tn] Título — Autor · cap. X · pp. Y-Z` e disclaimer clínico. Quando o acervo não sustenta a resposta, a Sofia avisa explicitamente.
- **Scribe (áudio/resumo → evolução CFP)** — envia um resumo em texto **ou um áudio da sessão**; o áudio é transcrito (OpenAI) e estruturado numa evolução no formato CFP, pronta para revisão e assinatura.
- **Instrumentos** — catálogo clínico com **Entrevista de Maastricht** e **WRAP**: preenchimento assistido, geração de saída interpretada e finalização em **anexo PDF** vinculado ao paciente.
- **Preparação de sessão** — gera um roteiro de sessão a partir do contexto clínico do paciente.
- **Documentos CFP (Res. 06/2019)** — templates de documentos psicológicos (declaração, atestado, relatório, laudo, parecer), geração, edição e assinatura.
- **Supervisão / estudo de caso** — análise assistida de casos para apoio a supervisão e estudo.
- **Biblioteca viva** — o acervo CENAT navegável e buscável direto: grade das obras, índice por obra e **busca semântica** (reusa a busca vetorial da Sofia). Guardrail de copyright: obras de terceiros expõem só estrutura + trecho curto.
- **Financeiro & Recibos** — valor por sessão (em **centavos**, nunca float), controle de pagamento (`pix`/`dinheiro`/`cartao`/`transferencia`) e emissão de **recibo em PDF** com numeração sequencial por tenant, anexado ao prontuário. **Recibo ≠ Nota Fiscal:** o recibo é o comprovante que o paciente usa para reembolso de plano; **NF-e/ISS municipal é integração fiscal separada, fora de escopo** (o PDF é marcado "Documento não fiscal"). Pendências e valores são sempre o registrado — sem projeção de receita.

Transversais: autenticação **JWT + 2FA TOTP obrigatório**, isolamento multi-tenant por `tenant_id`, `audit_log` de acessos/edições/exportações.

---

## 2. Arquitetura

Monorepo com dois serviços + banco:

```
praxis/
├── backend/                  FastAPI async (Python 3.12+)
│   ├── app/
│   │   ├── main.py           app FastAPI, CORS, /healthz, include dos routers
│   │   ├── config.py         Settings (pydantic-settings) — fonte única de env
│   │   ├── db.py             engine/SessionLocal async (asyncpg)
│   │   ├── deps.py           dependências (auth, sessão de DB, tenant)
│   │   ├── routers/          auth, pacientes, sessoes, evolucoes, consentimentos,
│   │   │                     sofia, scribe, instrumentos, preparacao, documentos, supervisao
│   │   ├── models/           modelos SQLAlchemy
│   │   ├── schemas/          modelos Pydantic (I/O)
│   │   ├── security/         crypto (Fernet), password (argon2), jwt, totp
│   │   ├── middleware/        audit
│   │   ├── rag/              chunker, embeddings, pdf, retriever, sofia (prompt+LLM)
│   │   ├── scribe/           audio, transcriber, structurer
│   │   ├── instrumentos/     catálogo, geradores, seed, definitions/ (maastricht_v1, wrap_v1)
│   │   ├── preparacao/       contexto, roteiro
│   │   ├── documentos/       templates, gerador, pdf, substituir
│   │   └── supervisao/       analisador
│   ├── migrations/           NNN_*.sql + run_migrations.py (runner ad-hoc)
│   ├── acervo/               manifest.toml + os 8 PDFs do acervo
│   ├── scripts/ingest_acervo.py
│   └── pyproject.toml        (uv)
├── frontend/                 Next.js 16 App Router (React 19)
│   ├── app/                  login, registro, conta/2fa, pacientes, sofia, instrumentos,
│   │                         documentos, evolucoes, supervisao
│   ├── components/           Topbar, ScribeModal, InstrumentoModal/Wizard, ...
│   ├── lib/api.ts            cliente HTTP fino (JWT em localStorage)
│   └── package.json          (npm)
└── deploy/                   praxis-backend.service, praxis-frontend.service (systemd)
```

**Como as peças conversam (produção):**

```
navegador ──▶ nginx (443, praxis.cenatdata.online)
                 ├── /api/*  ─proxy_pass (strippa /api)─▶ 127.0.0.1:8040  (FastAPI/uvicorn)
                 └── /*      ─proxy_pass──────────────────▶ 127.0.0.1:3040  (Next.js)
```

O backend usa `root_path="/api"` (para Swagger e URLs geradas conhecerem o prefixo público, já que o nginx remove o `/api` antes do proxy) e `redirect_slashes=False` (evita redirects que perderiam o `/api` atrás do proxy). Ambos os serviços escutam apenas em `127.0.0.1`; a exposição pública é feita pelo nginx.

---

## 3. Stack & versões

**Backend** (`backend/pyproject.toml`):
FastAPI `0.128.*` · SQLAlchemy 2 async (`>=2.0.36`) + asyncpg · Pydantic 2 / pydantic-settings · Uvicorn · argon2-cffi (hash de senha) · PyJWT · pyotp + qrcode (2FA) · cryptography (Fernet) · OpenAI (`>=1.55`) · PyMuPDF (extração de PDF) · pgvector · tiktoken · httpx · psycopg2-binary (runner de migração/ingestão). Python `>=3.12,<3.14`.

**Frontend** (`frontend/package.json`):
Next `^16` · React `^19` · Tailwind CSS `^4` (raw, via `@tailwindcss/postcss`) · lucide-react · sonner · TypeScript 5.

---

## 4. Pré-requisitos

- **PostgreSQL 14+** com a extensão **pgvector** instalada (a migração `001` habilita as extensões).
- **Node.js 20** (frontend Next 16).
- **[`uv`](https://docs.astral.sh/uv/)** para gerenciar o ambiente Python do backend.
- **Chave da OpenAI** (`OPENAI_API_KEY`) — necessária para Sofia (RAG/embeddings) e Scribe (transcrição).

---

## 5. Variáveis de ambiente

Fonte única: `backend/app/config.py`. A tabela abaixo bate 1:1 com o `Settings`. Copie `.env.example` para `backend/.env` e ajuste.

### Banco
| Var | Obrigatória | Default | Para quê |
|---|:---:|---|---|
| `DATABASE_URL` | **sim** | — | DSN async, ex.: `postgresql+asyncpg://praxis_user:...@127.0.0.1:5432/praxis` |

### Segurança
| Var | Obrigatória | Default | Para quê |
|---|:---:|---|---|
| `PRAXIS_FIELD_KEY` | **sim** | — | Chave Fernet (32 bytes base64 url-safe) para cifrar PII em repouso |
| `PRAXIS_JWT_SECRET` | **sim** | — | Segredo de assinatura dos JWT |
| `PRAXIS_JWT_ALG` | não | `HS256` | Algoritmo do JWT |
| `PRAXIS_JWT_TTL_MINUTES` | não | `60` | Validade do token em minutos |
| `PRAXIS_TOTP_ISSUER` | não | `Praxis by CENAT` | Nome exibido no app autenticador (2FA TOTP) |

### Sofia / RAG
| Var | Obrigatória | Default | Para quê |
|---|:---:|---|---|
| `OPENAI_API_KEY` | **sim (p/ Sofia e Scribe)** | `""` | Chave da OpenAI (LLM, embeddings, transcrição) |
| `PRAXIS_LLM_MODEL` | não | `gpt-5.1-mini` | Modelo de geração das respostas da Sofia |
| `PRAXIS_EMBED_MODEL` | não | `text-embedding-3-small` | Modelo de embeddings da ingestão/busca |
| `PRAXIS_EMBED_DIM` | não | `1536` | Dimensão do vetor (deve casar com o modelo e a coluna pgvector) |
| `PRAXIS_RAG_TOPK` | não | `6` | Nº de trechos recuperados por pergunta |
| `PRAXIS_RAG_SIM_MIN` | não | `0.28` | Similaridade mínima; abaixo disso a Sofia sinaliza "sem respaldo" |
| `PRAXIS_SOFIA_SEND_PATIENT` | não | `false` | Se `false` (padrão LGPD), dados de paciente não são enviados ao LLM |

### Scribe
| Var | Obrigatória | Default | Para quê |
|---|:---:|---|---|
| `PRAXIS_TRANSCRIBER` | não | `openai` | Backend de transcrição de áudio |
| `PRAXIS_TRANSC_MODEL` | não | `gpt-4o-mini-transcribe` | Modelo de transcrição |
| `PRAXIS_SCRIBE_AUDIO_DIR` | não | `/opt/praxis/backend/uploads/audio` | Diretório onde o áudio enviado é salvo |
| `PRAXIS_SCRIBE_MAX_MB` | não | `25` | Tamanho máximo do áudio (MB) |

### App
| Var | Obrigatória | Default | Para quê |
|---|:---:|---|---|
| `PRAXIS_ENV` | não | `dev` | Ambiente; se `prod`, `/docs` é desativado |
| `PRAXIS_BIND_HOST` | não | `127.0.0.1` | Host de bind do backend |
| `PRAXIS_BIND_PORT` | não | `8040` | Porta do backend |
| `PRAXIS_CORS_ORIGINS` | não | `http://127.0.0.1:3040,http://localhost:3040` | Origens permitidas (lista separada por vírgula) |

### Frontend
| Var | Obrigatória | Default | Para quê |
|---|:---:|---|---|
| `NEXT_PUBLIC_API_BASE` | não (recomendada) | `http://127.0.0.1:8040` | Base da API usada pelo navegador. **Em produção deve ser `https://praxis.cenatdata.online/api`** (ver §11) |

---

## 6. Setup local

**Backend:**
```bash
cd backend
cp ../.env.example .env         # e ajuste segredos (DATABASE_URL, PRAXIS_FIELD_KEY, PRAXIS_JWT_SECRET, OPENAI_API_KEY...)
uv sync
uv run python migrations/run_migrations.py
uv run uvicorn app.main:app --host 127.0.0.1 --port 8040 --reload
```
No boot, o app pré-carrega as configurações (falha cedo se faltar env) e faz *upsert* idempotente do catálogo de instrumentos.

**Frontend:**
```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_BASE=http://127.0.0.1:8040 em dev
npm install
npm run dev -- -p 3040
```

Acesse `http://localhost:3040`. Swagger da API em `http://localhost:8040/docs` (apenas quando `PRAXIS_ENV != prod`).

Gerar segredos:
```bash
# Fernet (PRAXIS_FIELD_KEY)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# JWT (PRAXIS_JWT_SECRET)
openssl rand -hex 32
```

---

## 7. Migrações

Padrão **ad-hoc, sem Alembic**: scripts SQL versionados em `backend/migrations/`, aplicados em ordem pelo runner.

```bash
cd backend
uv run python migrations/run_migrations.py
```

- **Runner** (`run_migrations.py`): usa psycopg2 (com fallback para o `psql` do sistema), lê `DATABASE_URL` do `backend/.env`, converte o DSN async para síncrono e aplica cada arquivo `NNN_*.sql` numa transação.
- **Controle**: tabela `_schema_migrations` (PK `nome`, `aplicado_em`). Cada arquivo aplicado é registrado; reexecutar é seguro (idempotente) — arquivos já aplicados são pulados.
- **Ordem atual**: `001_extensions_and_tenants` → `002_clinical` → `003_audit` → `004_acervo_e_sofia` → `005_scribe` → `006_instrumentos` → `007_roteiros_sessao` → `008_documentos_cfp` → `010_supervisao`.

> **Nota — salto do 009:** não existe `009_*.sql`. O runner ordena pelo nome do arquivo e simplesmente não vê o 009, sem erro. O gap é intencional/histórico; **não** crie um `009` "para preencher" sem necessidade real, ou você mudaria a ordem de aplicação.

---

## 8. Acervo & ingestão

O acervo são **8 obras** descritas em `backend/acervo/manifest.toml`. Cada `[[livro]]` vira um `AcervoDocumento`; a chave de idempotência é o `slug`.

**Passos:**
1. Coloque os 8 PDFs em `backend/acervo/` usando exatamente os nomes do campo `arquivo` do manifesto:
   `maastricht-interview.pdf`, `trabalhar-com-criancas-que-ouvem-vozes.pdf`, `implantar-novas-abordagens.pdf`, `guia-reducao-de-danos.pdf`, `saude-mental-atencao-basica.pdf`, `reforma-psiquiatrica-brasil.pdf`, `paul-baker-a-voz-interior.pdf`, `novas-abordagens-saude-mental.pdf`.
2. Rode a ingestão:
   ```bash
   cd backend && uv run python scripts/ingest_acervo.py
   ```
   O script extrai o texto (PyMuPDF), chunka, gera embeddings em lotes e faz upsert.

**Idempotência (dupla):** `fonte_hash` (sha256 do PDF) pula documentos já ingeridos e inalterados; se o PDF muda, os chunks antigos são apagados e reingeridos. No nível do trecho, `chunk_hash` + `ON CONFLICT DO NOTHING` evita duplicatas.

**Guardrail de terceiros:** livros com `is_terceiro = true` (hoje: `maastricht-interview` e `paul-baker-a-voz-interior`) são marcados `[TERCEIRO]` no contexto enviado à Sofia. O prompt **proíbe transcrição literal** desses trechos — a Sofia deve **parafrasear** a ideia e citar normalmente. Obras da editora CENAT (`is_terceiro=false`) não têm essa restrição.

---

## 9. API

Backend FastAPI. Externamente as rotas ficam sob `/api` (nginx); internamente o app as vê sem o prefixo.

| Prefixo | Router | Observações |
|---|---|---|
| `/auth` | auth | `register`, `login`, `2fa/setup`, `2fa/verify`, `2fa/login`, `me` |
| `/pacientes` | pacientes | CRUD + soft-delete |
| `/sessoes` | sessoes | sessões clínicas |
| `/evolucoes` | evolucoes | inclui `/{id}/assinar` |
| `/consentimentos` | consentimentos | termos por paciente |
| `/sofia` | sofia | `/perguntar`, `/acervo` |
| `/sessoes/{id}/scribe/...` | scribe | `resumo`, `audio` |
| `/instrumentos`, `/pacientes/{id}/respostas-instrumento`, `/anexos/...` | instrumentos | catálogo, respostas, `gerar-saida`, `finalizar`, download do anexo |
| `/sessao/preparar`, `/roteiros/...` | preparacao | roteiro de sessão |
| `/documentos/...`, `/pacientes/{id}/documentos` | documentos | templates, `gerar`, `{id}/assinar` |
| `/supervisao` | supervisao | `/analisar`, `/estudos` |
| `/healthz` | — | healthcheck: `{"status":"ok","env":...}` |
| `/docs` | — | Swagger, **apenas quando `PRAXIS_ENV != prod`** (ReDoc desativado) |

---

## 10. Deploy

Serviços systemd em `deploy/` (ambos escutam apenas em `127.0.0.1`; a exposição pública é do nginx). **Todos rodam como o usuário de sistema `praxis`** (não `root`) — ver §11.

- **`praxis-backend.service`** — `User=praxis`; `/usr/local/bin/uv run uvicorn app.main:app --host 127.0.0.1 --port 8040 --workers 1 --proxy-headers`; `EnvironmentFile=/opt/praxis/backend/.env`; logs em `backend/praxis-backend.log`.
- **`praxis-frontend.service`** — `User=praxis`; `npm run start -- -p 3040 -H 127.0.0.1`; `NODE_ENV=production`; logs em `frontend/praxis-frontend.log`.
- **`praxis-backup.service` + `praxis-backup.timer`** — dump diário do Postgres como `praxis` (ver "Backups" abaixo).

**Usuário dedicado (pré-requisito).** O `uv` precisa estar num caminho alcançável pelo `praxis` (o `/root/.local/bin` fica sob `/root`, modo `0700` — inacessível). Instale-o em `/usr/local/bin/uv`:
```bash
sudo useradd --system --home-dir /opt/praxis --shell /usr/sbin/nologin praxis
sudo cp /root/.local/bin/uv /usr/local/bin/uv && sudo chmod 755 /usr/local/bin/uv
sudo chown -R praxis:praxis /opt/praxis && sudo chmod 600 /opt/praxis/backend/.env
```

Instalação típica:
```bash
sudo cp deploy/praxis-backend.service deploy/praxis-frontend.service \
        deploy/praxis-backup.service deploy/praxis-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now praxis-backend praxis-frontend praxis-backup.timer
```

**nginx + certbot** para `praxis.cenatdata.online`: o vhost não está versionado neste repo; siga o prompt/procedimento de configuração do domínio. O nginx deve rotear `/api/*` → `127.0.0.1:8040` (com strip do `/api`) e o restante → `127.0.0.1:3040`, e o certbot emite o certificado TLS.

### `NEXT_PUBLIC_API_BASE` (build-time)

Como é `NEXT_PUBLIC_*`, essa variável é **inlinada no bundle durante o `next build`**, não em runtime — definir no unit systemd **não tem efeito** sobre o código que roda no navegador. O valor de produção vive em **`frontend/.env.production`** (versionado):

```
NEXT_PUBLIC_API_BASE=/api
```

Usamos o caminho **relativo `/api`** (mesma origem): o nginx roteia `location /api/ → 127.0.0.1:8040` (com strip do `/api`), então o navegador nunca precisa de um host absoluto. Isso é imune a troca de domínio e não vaza `127.0.0.1`. Se um dia precisar do absoluto, use `https://praxis.cenatdata.online/api`. Após alterar, **rebuild** (`sudo -u praxis npm run build`) e `restart` do frontend — não basta reiniciar.

> Nota: `.env.local` (gitignored) **sobrepõe** `.env.production` em builds. Mantenha ambos consistentes ou remova o `.env.local` em produção.

### Backups do Postgres

`ops/backup_pg.sh` roda via `praxis-backup.timer` (diário, 03:30) como `praxis`:

- `pg_dump -Fc` (custom format, comprimido) → `/opt/praxis/backups/daily/praxis_YYYYMMDD_HHMM.dump`.
- **Retenção:** 14 diários + 8 semanais (cópia aos domingos em `backups/weekly/`).
- Coordenadas do banco lidas do `DATABASE_URL`; **senha via `~praxis/.pgpass`** (`chmod 600`) — nunca na linha de comando. Arquivos de dump ficam `600`, dono `praxis`.
- **Escopo:** apenas o banco. O áudio bruto do Scribe é efêmero (apagado pós-transcrição); anexos/PII já vivem **cifrados dentro do DB**, cobertos pelo dump.

```bash
sudo systemctl start praxis-backup.service      # rodar sob demanda
systemctl list-timers praxis-backup.timer       # conferir próximo disparo
```

**Restore** (num banco descartável, como superusuário para recriar as extensões):
```bash
sudo -u postgres createdb praxis_restore_test
sudo -u postgres pg_restore --no-owner --no-privileges -d praxis_restore_test <arquivo>.dump
```

---

## 11. Segurança & compliance

- **PII cifrada em repouso** — dados sensíveis de paciente são cifrados com **Fernet** (chave em `PRAXIS_FIELD_KEY`).
- **Autenticação** — JWT + **2FA TOTP obrigatório**; senhas com argon2.
- **Isolamento multi-tenant** — todo dado clínico é filtrado por `tenant_id`.
- **Auditoria** — `audit_log` registra acessos, edições e exportações.
- **Retenção LGPD/CFP** — soft-delete respeitando prazos (5 anos para registros administrativos, 20 anos para prontuário).
- **Assinatura digital ICP-Brasil (PAdES)** — documentos CFP têm dois tiers: **simples** (hash SHA-256 do conteúdo, padrão) e **qualificada ICP-Brasil** (PAdES/A1 via pyHanko) sobre o PDF. O certificado **A1** (`.pfx`) é guardado **cifrado** (Fernet) por profissional; a **senha do PKCS#12 nunca é armazenada** (informada a cada assinatura, usada só em memória). `POST /documentos/{id}/assinar-icp` assina; `GET /documentos/{id}/assinatura` verifica (integridade + validade; "confiável" exige a AC Raiz ICP-Brasil no validador). **A3** (token/cartão) é fora de escopo (assinatura no dispositivo); **TSA/carimbo de tempo** é TODO. Documento assinado é imutável.
- **Portabilidade / exportação (LGPD art. 18)** — `GET /pacientes/{id}/exportar` gera um pacote `.zip` read-only por paciente: `export.json` (todos os registros com PII decifrada), `anexos/` (PDFs originais decifrados) e `resumo.pdf` (sumário legível). `?formato=json` devolve só o JSON. Tenant-scoped, **auditado** (`acao=EXPORT`), sem migração. Exportar **≠** excluir (a retenção acima continua valendo). O pacote contém dados sensíveis — a guarda é responsabilidade do profissional.
- **IA como apoio** — respostas da Sofia e saídas geradas são **apoio ao raciocínio clínico**; a responsabilidade técnica e a **assinatura são do profissional** (disclaimer explícito nas respostas). Por padrão (`PRAXIS_SOFIA_SEND_PATIENT=false`), dados de paciente não são enviados ao LLM.
- **Obras de terceiros** — paráfrase obrigatória (ver §8).

- **Serviços sem privilégios** — os units systemd rodam como o usuário de sistema **`praxis`** (sem shell), dono de `/opt/praxis`; `.env` em `600`. Ver §10.
- **Backups automáticos** — dump diário do Postgres com retenção e `.pgpass` restrito (§10, "Backups").

### Rotação de segredos

- **`PRAXIS_JWT_SECRET` (barato).** Rotacionar apenas invalida sessões ativas — usuários refazem login. Gerar um segredo forte, atualizar o `.env` e `restart` do backend:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```

- **`PRAXIS_FIELD_KEY` (⚠️ PERIGOSO — não rotacionar sem plano).** Trocar a chave torna **toda a PII cifrada indecifrável**. As colunas Fernet são: `pacientes.{nome,contato,nascimento,documento}_cifrado`, `users.totp_secret_cifrado`, `anexos_prontuario.arquivo_cifrado`, `evolucao_geracao.entrada_cifrada` (4 tabelas, 7 colunas). **TODO** para rotacionar com segurança:
  1. Migrar `crypto.py` de `Fernet` para **`MultiFernet([nova, antiga])`** (decifra o legado, cifra o novo com a chave nova).
  2. Rodar um **passe de re-cifragem** de todas as colunas acima (migração ad-hoc `011+`, respeitando o salto do `009`).
  3. Só então **remover a chave antiga** do `MultiFernet`.

---

## 12. Regras de marca

- **Proibido** usar os ícones `Brain`, `BrainCircuit`, `BrainCog` do `lucide-react`.

---

## 13. Roadmap

**Entregue (v1):** prontuário CFP, Sofia (RAG com citação), Scribe (áudio→evolução), Instrumentos (Maastricht, WRAP), Preparação de sessão, Documentos CFP (Res. 06/2019), Supervisão, 2FA, deploy com domínio.

**Futuro:** agenda, financeiro, telessessão. Modelo de **pré-venda founding** para os primeiros assinantes.
