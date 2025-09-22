#!/usr/bin/env bash
set -euo pipefail

# One-click: create venv, install deps, run GUI

here="$(cd "${BASH_SOURCE[0]%/*}" && pwd)"
repo_root="${here%/scripts}"
cd "$repo_root"

# Choose a Python interpreter
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Error: python3/python not found in PATH" >&2
  exit 1
fi

# Create venv if missing
if [ ! -d .venv ]; then
  echo "[setup] Creating virtual environment in .venv"
  "$PY" -m venv .venv
fi

VENV_PY=".venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  echo "Error: venv Python not found at $VENV_PY" >&2
  exit 1
fi

echo "[setup] Upgrading pip"
"$VENV_PY" -m pip install --upgrade pip

if [ -f requirements.txt ]; then
  echo "[setup] Installing dependencies from requirements.txt"
  "$VENV_PY" -m pip install -r requirements.txt
fi

echo "[run] Launching GUI"
exec "$VENV_PY" download_icon_gui.py

