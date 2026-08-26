#!/usr/bin/env bash
# Linux launcher (X11). pynput drives input via XTEST — no root needed.
# Needs xdotool for window detection:  sudo apt install xdotool
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating venv (first run)..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -r "$DIR/requirements.txt"
fi
command -v xdotool >/dev/null || echo "[!] install xdotool: sudo apt install xdotool"
exec "$VENV/bin/python" "$DIR/farmbot.py"
