#!/bin/bash
# Omen Linux: run the backend from a source checkout (dev mode).
# Set OMEN_SIMULATE=1 to try the dashboard without touching any hardware.
set -e

# The backend lives next to this scripts/ directory.
cd "$(dirname "$0")/../backend"

if [ ! -d "venv" ]; then
    echo "[*] First run setup: creating a virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
fi

echo ""
echo "========================================"
echo "   OMEN LINUX CONTROL // ONLINE"
echo "========================================"
echo "Dashboard: http://localhost:8000/ui/"
echo ""

if [ "${OMEN_SIMULATE:-0}" = "1" ] || [ "$EUID" -eq 0 ]; then
    exec ./venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
fi
# Hardware access (/dev/mem) needs root.
echo "[!] Hardware access requires root; enter your sudo password."
exec sudo --preserve-env=OMEN_FORCE,OMEN_SAFE_TEMP ./venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
