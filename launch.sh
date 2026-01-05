#!/bin/bash
# Native Application Launcher for Omen Linux

APP_DIR="/opt/omen-linux"
PORT=8000

# 1. Start External Backend (Root required for Hardware Access)
# We use pkexec to get a GUI password prompt if needed.
# We run the server in background.
echo "Starting Omen Backend Service..."
pkexec env DISPLAY=$DISPLAY XAUTHORITY=$XAUTHORITY $APP_DIR/start_server_root.sh &

# 2. Wait for Server to be ready
echo "Waiting for server..."
sleep 3
# In a robust app, we would loop check localhost:8000

# 3. Launch UI in App Mode (Borderless Window)
# Using google-chrome if available, or finding others.
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

# 4. Cleanup (Optional: Kill backend when window closes?)
# For now, we leave backend running so closing window doesn't crash system fan control.
