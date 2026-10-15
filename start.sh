#!/usr/bin/env bash
# Run the scheduler on your computer: builds the web app, starts the server, opens
# http://localhost:8000. Needs uv (Python) and Node.js 20+. Stop with Ctrl+C.
set -euo pipefail
cd "$(dirname "$0")"

need() { command -v "$1" >/dev/null || { echo "Please install $1 first: $2"; exit 1; }; }
need uv   "https://docs.astral.sh/uv/getting-started/installation/"
need node "https://nodejs.org (version 20 or newer)"
need npm  "https://nodejs.org (it comes with Node.js)"

echo "Building the web app (first run takes a minute)…"
(cd web && npm ci --silent && npm run build --silent)

echo "Starting the scheduler at http://localhost:8000"
( sleep 4; (open http://localhost:8000 || xdg-open http://localhost:8000) >/dev/null 2>&1 || true ) &
cd api && uv sync --quiet && exec uv run uvicorn scheduling_api.server:app --port 8000
