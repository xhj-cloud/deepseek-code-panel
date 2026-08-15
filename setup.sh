#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Creating Python venv ..."
python3 -m venv venv

echo "==> Installing requirements ..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "==> Done."
echo "    Python: $(pwd)/venv/bin/python"
