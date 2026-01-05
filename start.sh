#!/bin/bash
# Omen Linux Control Launcher

# Navigate to script directory
cd "$(dirname "$0")"

# Go to backend
cd backend

# Setup Python Environment
if [ ! -d "venv" ]; then
    echo "[*] First run setup: Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "[*] Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo ""
echo "========================================"
echo "   OMEN LINUX CONTROL // ONLINE"
echo "========================================"
echo "Dashboard: http://localhost:8000/ui/"
echo ""

# Run with root privileges (Required for /dev/mem access)
if [ "$EUID" -ne 0 ]; then
  echo "[!] Hardware Access requires ROOT privileges."
  echo "[!] Please enter sudo password:"
  sudo ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
else
  ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
fi
