#!/usr/bin/env bash
# Deploy ResearchPipe to muye@192.168.1.23 (Ubuntu laptop).
#
# Run from your dev machine (WSL):
#   ./deploy/deploy.sh
#
# Idempotent — pulls latest from GitHub, installs deps, builds frontend,
# restarts systemd services. First-time setup steps are at the bottom; do
# those manually once.

set -euo pipefail

REMOTE="muye@192.168.1.23"
REPO_DIR="/home/muye/researchpipe"
GIT_URL="https://github.com/miaomiaoxu999-cell/researchpipe.git"

echo "[deploy] sync code to $REMOTE:$REPO_DIR"
ssh "$REMOTE" "
  set -e
  cd ~ &&
  if [ ! -d researchpipe ]; then
    git clone $GIT_URL researchpipe
  fi
  cd researchpipe && git fetch origin && git reset --hard origin/main
"

echo "[deploy] backend: install deps + run migrations"
ssh "$REMOTE" "
  set -e
  cd $REPO_DIR/backend
  if [ ! -d .venv ]; then
    uv venv
  fi
  uv sync --no-dev
  # Apply migrations (idempotent)
  PGPASSWORD=postgres psql -h 192.168.1.23 -p 5433 -U postgres -d researchpipe \
    -f migrations/001_corpus_init.sql
  PGPASSWORD=postgres psql -h 192.168.1.23 -p 5433 -U postgres -d researchpipe \
    -f migrations/002_corpus_chunks.sql
"

echo "[deploy] frontend: install + production build"
ssh "$REMOTE" "
  set -e
  cd $REPO_DIR/frontend
  npm ci --silent
  # Use prod env for build
  cp .env.production .env.local 2>/dev/null || true
  npm run build
"

echo "[deploy] restart systemd services"
ssh "$REMOTE" "sudo systemctl restart researchpipe-backend researchpipe-frontend"

sleep 4
echo "[deploy] healthcheck"
ssh "$REMOTE" "
  curl -s -o /dev/null -w 'backend(:3725): %{http_code}\n' http://127.0.0.1:3725/healthz &&
  curl -s -o /dev/null -w 'frontend(:3726): %{http_code}\n' http://127.0.0.1:3726/
"

echo "[deploy] DONE — verify externally:"
echo "  https://rp.zgen.xin            (Landing + agent + downloads)"
echo "  https://rp.zgen.xin/agent      (Try Agent in browser)"
echo "  https://rpadmin.zgen.xin       (Admin console — needs RP_ADMIN_KEY)"
echo
echo "Logs:"
echo "  ssh $REMOTE 'journalctl -fu researchpipe-backend'"
echo "  ssh $REMOTE 'journalctl -fu researchpipe-frontend'"
