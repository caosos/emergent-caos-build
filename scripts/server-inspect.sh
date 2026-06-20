#!/usr/bin/env bash
set -euo pipefail

echo "== CAOS prototype server inspection (read-only) =="
echo

echo "== pwd =="
pwd

echo

echo "== whoami =="
whoami

echo

echo "== hostname =="
hostname

echo

echo "== OS info =="
if [ -r /etc/os-release ]; then
  cat /etc/os-release
else
  uname -a
fi

echo

echo "== git version =="
if command -v git >/dev/null 2>&1; then
  git --version
else
  echo "git not found"
fi

echo

echo "== docker version =="
if command -v docker >/dev/null 2>&1; then
  docker --version
else
  echo "docker not found"
fi

echo

echo "== docker compose version =="
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker compose version
elif command -v docker-compose >/dev/null 2>&1; then
  docker-compose --version
else
  echo "docker compose not found"
fi

echo

echo "== memory =="
free -h || true

echo

echo "== disk =="
df -h || true

echo

echo "== open ports =="
if command -v ss >/dev/null 2>&1; then
  ss -tulpen || ss -tulpn || true
elif command -v netstat >/dev/null 2>&1; then
  netstat -tulpen || netstat -tulpn || true
else
  echo "ss/netstat not found"
fi
