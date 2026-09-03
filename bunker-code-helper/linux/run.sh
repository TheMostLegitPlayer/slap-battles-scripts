#!/usr/bin/env bash
# Linux launcher. Uses pynput for the hotkey, so NO root is needed on X11.
# Run linux/setup.sh once first.
#
# Note: global hotkeys are reliable on an X11 session. On a pure Wayland session
# pynput may not capture keys app-wide — log in to an "Xorg" session for this.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"

if [ ! -x "$VENV/bin/python" ]; then
  echo "No venv yet — run linux/setup.sh first."
  exit 1
fi

exec "$VENV/bin/python" "$ROOT/app/bunker_code_helper.py"
