#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== CAOS prototype cautious deploy helper =="
echo "Working directory: $ROOT_DIR"

if [ ! -f docker-compose.yml ]; then
  echo "ERROR: docker-compose.yml not found in $ROOT_DIR" >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo "ERROR: .env is required. Copy .env.example to .env and fill placeholders first." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not on PATH" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose plugin is not available" >&2
  exit 1
fi

echo "== Validating compose config =="
docker compose config

echo "== Building and starting services =="
docker compose up -d --build

echo "== Service status =="
docker compose ps
