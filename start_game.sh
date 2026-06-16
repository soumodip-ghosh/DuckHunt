#!/usr/bin/env bash
# Launcher for Duck Hunt (Unix shell)
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installing dependencies (requirements.txt)..."
if command -v python3 >/dev/null 2>&1; then
  python3 -m pip install -r "$SCRIPT_DIR/requirements.txt"
else
  python -m pip install -r "$SCRIPT_DIR/requirements.txt"
fi

echo "Starting Duck Hunt..."
if command -v python3 >/dev/null 2>&1; then
  python3 "$SCRIPT_DIR/duck_hunt.py" "$@"
else
  python "$SCRIPT_DIR/duck_hunt.py" "$@"
fi
