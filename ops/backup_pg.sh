#!/usr/bin/env bash
#
# backup_pg.sh — dump lógico do Postgres do Práxis (formato custom -Fc).
#
# - Lê as coordenadas do banco (host/porta/db/usuário) do DATABASE_URL em backend/.env.
# - A SENHA nunca aparece aqui: vem do ~/.pgpass do usuário praxis (chmod 600).
# - Retenção: 14 diários + 8 semanais (cópia semanal aos domingos).
# - Todos os arquivos ficam 600 (umask 077), dono praxis.
#
# Uso: rodar como o usuário `praxis` (via systemd timer praxis-backup.timer).
#   ExecStart=/opt/praxis/ops/backup_pg.sh
#
set -euo pipefail
umask 077

ENV_FILE="/opt/praxis/backend/.env"
BACKUP_ROOT="/opt/praxis/backups"
DAILY_DIR="${BACKUP_ROOT}/daily"
WEEKLY_DIR="${BACKUP_ROOT}/weekly"
KEEP_DAILY=14
KEEP_WEEKLY=8

# --- extrai DATABASE_URL do .env ------------------------------------------
DB_URL="$(grep -E '^DATABASE_URL=' "${ENV_FILE}" | head -n1 | cut -d= -f2-)"
if [[ -z "${DB_URL}" ]]; then
  echo "ERRO: DATABASE_URL não encontrado em ${ENV_FILE}" >&2
  exit 1
fi

# Normaliza o driver SQLAlchemy (postgresql+asyncpg://) para libpq (postgresql://)
# e descarta a senha embutida — a autenticação usa ~/.pgpass.
# Formato esperado: postgresql+asyncpg://user:pass@host:port/dbname
NOSCHEME="${DB_URL#*://}"                       # user:pass@host:port/dbname
USERINFO="${NOSCHEME%@*}"                        # user:pass
HOSTPART="${NOSCHEME#*@}"                         # host:port/dbname
DB_USER="${USERINFO%%:*}"                         # user
HOSTPORT="${HOSTPART%%/*}"                        # host:port
DB_NAME="${HOSTPART#*/}"                          # dbname (pode ter ?params)
DB_NAME="${DB_NAME%%\?*}"                         # remove querystring, se houver
DB_HOST="${HOSTPORT%%:*}"                         # host
DB_PORT="${HOSTPORT#*:}"                          # port
[[ "${DB_PORT}" == "${DB_HOST}" ]] && DB_PORT=5432   # sem porta explícita

export PGPASSFILE="${PGPASSFILE:-/opt/praxis/.pgpass}"

# --- destino --------------------------------------------------------------
mkdir -p "${DAILY_DIR}" "${WEEKLY_DIR}"
STAMP="$(date +%Y%m%d_%H%M)"
OUT="${DAILY_DIR}/praxis_${STAMP}.dump"
TMP="${OUT}.partial"

echo "[$(date -Is)] pg_dump ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME} -> ${OUT}"
pg_dump --format=custom --compress=6 --no-owner --no-privileges \
        --host="${DB_HOST}" --port="${DB_PORT}" \
        --username="${DB_USER}" --dbname="${DB_NAME}" \
        --file="${TMP}"

# Só promove o arquivo se o dump completou (evita .dump truncado).
mv "${TMP}" "${OUT}"
chmod 600 "${OUT}"
echo "[$(date -Is)] OK: $(du -h "${OUT}" | cut -f1) ${OUT}"

# --- cópia semanal (domingo = 7) ------------------------------------------
if [[ "$(date +%u)" == "7" ]]; then
  WOUT="${WEEKLY_DIR}/praxis_weekly_${STAMP}.dump"
  cp -p "${OUT}" "${WOUT}"
  echo "[$(date -Is)] cópia semanal -> ${WOUT}"
fi

# --- retenção (mantém os N mais recentes por mtime) -----------------------
prune() {
  local dir="$1" keep="$2" f n=0
  # lista por mtime desc; remove além do keep. Nomes controlados (sem espaços).
  while IFS= read -r f; do
    n=$((n+1))
    if (( n > keep )); then
      rm -f -- "${f}"
      echo "[$(date -Is)] retenção: removido ${f}"
    fi
  done < <(ls -1t "${dir}"/*.dump 2>/dev/null)
}
prune "${DAILY_DIR}"  "${KEEP_DAILY}"
prune "${WEEKLY_DIR}" "${KEEP_WEEKLY}"

echo "[$(date -Is)] backup concluído."
