# Relatório — Sprint 🎨 Craft 2 (lote completo)

Execução autônoma, sem checkpoints. 1 commit por bloco, gate `tsc + build` verde antes de cada commit.
Merge `--no-ff` em `main`, deploy em produção (systemd `praxis-frontend`, porta 3040) e smoke test 200.

Ponto de restauração: tag **`pre-craft-2`** (empurrada para `origin`). Merge: **`53a23ce`**.

---

## Blocos (hash · resumo)

### Bloco 1 — fluxo diário · `a3b5f46`
- **I5 (resto)** — `SessaoRow` (agenda): sessão `agendada` mostra só **Realizada** (destaque, primary) + **Sala** (online); **Falta/Reagendar** no `MenuAcoes` e **Cancelar** na seção destrutiva. Demais status: **Reabrir** visível + Reagendar no menu.
- **I12** — `dataCurtaComHora(iso)` → `qua 08/07 · 14:00` (mono) + `sufixoRelativoProximo` em `lib/date.ts`; virou o formato primário da lista de sessões do prontuário, com o relativo como sufixo muted quando ≤6 dias.
- **I9** — carga do prontuário já era paralela (`Promise.allSettled`, tolerante a falha isolada); **skeleton anatômico** novo (retrato 56px + 2 linhas, faixa de subnav, grid de 4 KPIs) — sem layout shift.
- **I13** — toasts na paleta: removido `richColors`; `toastOptions.style` em tokens; acento só no ícone/borda esquerda via `[data-sonner-toast][data-type=...]`.
- **Sobras 17** — `ConfirmDialog` ganhou `confirmVariant` (default `danger`); os dois confirms de **assinatura** (evolução/documento) passaram a `confirmVariant="primary"`.
- **I8** — `ConfirmDialog` ao excluir conversa da Sofia.

### Bloco 2 — sofia · `f45a447`
- **I10** — empty state com `PresenceMark size={40}`, uma linha e **3 sugestões clicáveis** (determinísticas quando há `paciente_id`, gerais caso contrário) + badge de privacidade.
- **Histórico por teclado** — cards de conversa viraram `<button>` de largura total (mesmo visual `card`); lixeira segue botão separado com `stopPropagation`.
- **I11** — `aria-live`: loading com `role="status"`; anúncio único ao concluir o streaming (`Resposta da Sofia concluída, N fontes citadas.`) em live region `.sr-only` (nova classe em `globals.css`); botões `[Tn]` com `aria-label="Ver fonte Tn: {título}"`.

### Bloco 3 — instrumentos e scribe · `5e57969`
- **I4** — Likert em classes `.likert-opt`/`.likert-opcoes`: input escondido acessível dentro do label, pill ≥40px, seleção **teal-700** via `:has(input:checked)`, foco com ring padrão, grid de 2 colunas ≤640px. Mesmo padrão aplicado ao multiselect.
- **Y8** — Scribe: duração `mm:ss`/`h:mm:ss` em mono (botão Parar + badge do gravado); `<audio controls>` do blob para conferência antes de enviar.

### Bloco 4 — formulários · `bc80baf`
- **I14** — campo "Sexo" (texto livre) → `Gênero` com `select` (Mulher · Homem · Não binário · Prefiro não informar · Autodescrever…); a última revela input livre. Payload segue a mesma string.
- **I16** — 2FA (login e conta): `Field label="Código de verificação"`, `autoComplete="one-time-code"`, `inputMode="numeric"`, mono + `letter-spacing`+centro.
- **Y13** — login com `autoFocus` no e-mail e link discreto **Como o Práxis usa IA**.
- **Y17** — erro geral do form de paciente saiu do `Field` do Nome para bloco próprio (`--danger`, 13px).

### Bloco 5 — biblioteca · `d4ecdd9`
- **I17** — leitura de obra em **coluna contínua de 68ch**, sem Card por seção; título em Fraunces 20 com a página em mono 11px `--muted` à direita; corpo `line-height 1.7`; badges "Seção N" removidos (numeração vira fallback do título).

### Bloco 6 — sistema e identidade · `883078d`
- **I7** — docblock de política na `PresenceMark`; removida dos usos decorativos (H1 do Financeiro → só `Wallet`; H1 da Biblioteca → `BookOpen`; título do `TelessessaoModal` → `Video`). Mantida em Sofia, geração, preparação, nav, `/como-usamos-ia`.
- **I15** — tokens `--fs-2xs…--fs-2xl` em `:root`; **todos os H1 de página = `--fs-xl`** (exceção: Início = `--fs-2xl`); fracionários `11.5`/`12.5` eliminados (→ 12/13).
- **Y14 (restrito)** — marca **"Práxis"** em Fraunces 600 com ponto âmbar (`--amber-600`) na Topbar e no login; favicon `app/icon.svg` ("P." serif tinta `--ink-800` sobre porcelana, ponto âmbar).
- **Lote Y** — `.btn-icon` (Y1, adotado no × de Modal/Drawer, lixeiras); `:focus-visible` sem `border-radius` fixo (Y2); `ItemLink` do Início com hover `teal-50` + seta desloca 2px (Y3); `Segmented` (Y4) no dia|semana da agenda + presets do Financeiro com estado ativo/toggle (Y5); `GraficoTrajetoria` `--paper`→`--surface` (Y6); hashes SHA-256 truncados `a3f2…9c1d` em mono + `CopiarBtn` (Y7); `Carregando…` → skeleton nas páginas listadas (Y9); `EmptyState` (Y10) em pacientes, abas do prontuário e supervisão; separadores de mês na timeline (Y11); logo da Topbar → `/inicio` (Y12); KPI "A receber" neutro `--text` (Y16); máscara de fade na `.subnav` (Y18); microcopy `Comece por aqui.` / `usar o contexto deste paciente` / `Hoje`/`Nova` (Y19); tokens de camada `--scrim`/`--z-*` consumidos em Modal/Drawer/ConfirmDialog/Topbar.

---

## Itens pulados / conservadores (com motivo)

- **Y15** — Fora de escopo por decisão do prompt (identidade opinativa). **Não tocado.**
- **6c · arcos concêntricos atrás do card de login** — **pulado**. A própria seção "Fora de escopo" do prompt orienta, para arcos, "na dúvida, não incluir"; sem meio de validar aqui a sutileza a 4% de opacidade, a escolha conservadora foi não incluir. Marca "Práxis." e favicon (as partes objetivas do 6c) foram feitas.
- **Y11 · cor dos badges de escore por severidade** — **pulado a parte de cor**; separadores de mês **feitos**. Motivo: o `meta` dos eventos da timeline traz o rótulo `faixa` (texto), mas **não** um valor de `severidade`; colorir "pela faixa declarada" de forma factual exigiria mapear severidade no backend (fora de escopo). Registrado para revisão humana.
- **Y9 (parcial)** — convertidos os alvos listados no prompt (evolução, documento, conta, acervo, supervisão/[id], fallback do Suspense da Sofia) + Financeiro/Supervisão. **Não** convertidos (fora da lista): splash `app/page.tsx`, `conta/2fa`, `CertificadoManager`, drawer de histórico da Sofia, `InstrumentoWizard` — `Carregando…` transitório, baixo impacto.
- **I9 (paralelo)** — já entregue em sprint anterior (`Promise.allSettled`); aqui só o skeleton anatômico foi adicionado.

---

## Verificação final

- `npx tsc --noEmit` — limpo (por bloco e no merge).
- `npm run build` — limpo (por bloco e build de produção pós-merge).
- Auto-varredura:
  - `grep -rn "Brain" app components lib` → **vazio**
  - `grep -rn "richColors" app` → **vazio** (comentário reescrito p/ não conter o termo)
  - `grep -rn "11.5\|12.5" app components --include=*.tsx` → **vazio**
  - `grep -rn 'onClick' app/sofia/page.tsx | grep div` → **vazio** (nenhum card clicável em `div`)

## Deploy e smoke test

1. `git tag pre-craft-2` + push (ponto de restauração).
2. `git merge --no-ff feat/craft-2` → `git push origin main --tags` (`77c0edb..53a23ce`).
3. `npm run build` (produção, `.env.production` com `NEXT_PUBLIC_API_BASE=/api`) → `sudo systemctl restart praxis-frontend.service`.
4. Serviço **`active (running)`** (next-server v16.2.9, porta 3040).
5. Smoke test (`curl` em `127.0.0.1:3040`): `/login` **200** · `/como-usamos-ia` **200** · `/inicio` **200** · `/icon.svg` **200** (`image/svg+xml`) · wordmark "Práxis" presente no HTML do login.

**Sem rollback.** Deploy no ar.
