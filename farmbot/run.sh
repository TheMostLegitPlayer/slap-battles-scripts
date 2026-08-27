#!/usr/bin/env bash
# Linux launcher (X11 / Roblox via Sober).
#  - mouse + hotkeys via pynput (XTEST), no root
#  - movement keys via ydotool (uinput), because Sober/Wine ignores XTEST keys
#  - window detection via xdotool
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating venv (first run)..."
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q -r "$DIR/requirements.txt"
fi
command -v xdotool >/dev/null || echo "[!] need xdotool:  sudo apt install xdotool"
command -v ydotool >/dev/null || echo "[!] need ydotool:  sudo apt install ydotool"
exec "$VENV/bin/python" "$DIR/farmbot.py"
