#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== Compile =="
python3 -m compileall -q backend/app scripts

echo "== Build API =="
docker build \
  -t covid19-kg-integration-api:latest \
  ./backend

echo "== Recreate API =="
docker compose up -d \
  --no-build \
  --force-recreate \
  api

echo "== Wait for health =="
until curl -sf http://localhost:8000/health >/dev/null
do
  sleep 1
done

echo "API ready"

echo
echo "== Targeted semantic regressions =="
python3 scripts/verify_cases.py

if [[ "${1:-}" == "--full" ]]; then
  echo
  echo "== Full regressions =="
  ./scripts/run_regressions.sh
fi
