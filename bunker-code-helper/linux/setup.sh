#!/usr/bin/env bash
# Linux setup: make a local venv, install deps, open the config window.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"

if [ ! -d "$VENV" ]; then
  echo "Creating venv (first run only)..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet pynput requests pillow mss customtkinter
fi

exec "$VENV/bin/python" "$ROOT/app/setup.py"
