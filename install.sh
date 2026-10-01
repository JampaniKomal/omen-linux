#!/bin/bash
# Omen Linux installer: copies the app to /opt/omen-linux and adds a menu entry.
set -e

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/omen-linux"

echo "Installing Omen Linux to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
for part in backend frontend resources scripts; do
    rm -rf "${INSTALL_DIR:?}/$part"
    cp -r "$SCRIPT_DIR/$part" "$INSTALL_DIR/"
done
rm -rf "$INSTALL_DIR/backend/venv"
chmod +x "$INSTALL_DIR"/scripts/*.sh

echo "Setting up the Python environment..."
python3 -m venv "$INSTALL_DIR/backend/venv"
"$INSTALL_DIR/backend/venv/bin/pip" install --quiet -r "$INSTALL_DIR/backend/requirements.txt"

echo "Registering the desktop app..."
cp "$INSTALL_DIR/resources/omen-linux.desktop" /usr/share/applications/omen-linux.desktop
update-desktop-database /usr/share/applications/ || true

echo ""
echo "==========================================="
echo " INSTALLATION COMPLETE"
echo "==========================================="
echo "Search for 'Omen Linux' in your application menu."
