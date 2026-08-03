#!/bin/bash
# Jalankan backend C3MR dari mana pun skrip ini berada.
set -e
cd "$(dirname "$0")"

# Pakai interpreter dari virtualenv bila ada, supaya dependensi pasti terpasang.
PY="python3"
[ -x ".venv/bin/python" ] && PY=".venv/bin/python"

echo "Starting C3MR backend from $(pwd) using $PY"
exec "$PY" -m uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
