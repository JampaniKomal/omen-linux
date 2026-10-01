#!/bin/bash
# Desktop launcher for Omen Linux: start the root backend (unless it is already
# running), then open the dashboard as an app window.

APP_DIR="/opt/omen-linux"
URL="http://localhost:8000"

if ! curl -fs "$URL/" > /dev/null 2>&1; then
    echo "Starting the Omen Linux backend..."
    # OMEN_IDLE_EXIT: two minutes after the dashboard is closed, the backend
    # gives fan control back to the BIOS and exits.
    pkexec env OMEN_IDLE_EXIT=120 "$APP_DIR/scripts/start_server_root.sh" &
    for _ in $(seq 1 60); do
        curl -fs "$URL/" > /dev/null 2>&1 && break
        sleep 0.5
    done
fi

for browser in google-chrome chromium chromium-browser; do
    if command -v "$browser" > /dev/null 2>&1; then
        exec "$browser" --app="$URL/ui/" --class="OmenLinux" --user-data-dir="${XDG_RUNTIME_DIR:-/tmp}/omen-linux-browser"
    fi
done
xdg-open "$URL/ui/"
