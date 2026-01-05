#!/bin/bash
# Native Application Launcher for Omen Linux

APP_DIR="/opt/omen-linux"
PORT=8000

# 1. Start External Backend (Root required for Hardware Access)
echo "Starting Omen Backend Service..."
pkexec env DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY $APP_DIR/scripts/start_server_root.sh &

# 2. Wait for Server to be ready
echo "Waiting for server..."
sleep 3

# 3. Launch UI in App Mode (Borderless Window)
BROWSER_BIN=""
if command -v google-chrome &> /dev/null; then
    BROWSER_BIN="google-chrome"
elif command -v chromium &> /dev/null; then
    BROWSER_BIN="chromium"
fi

if [ -n "$BROWSER_BIN" ]; then
    $BROWSER_BIN --app="http://localhost:$PORT/ui/" --class="OmenLinux" --user-data-dir="/tmp/omen_linux_chrome_dummy"
else
    xdg-open "http://localhost:$PORT/ui/"
fi
