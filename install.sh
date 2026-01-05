#!/bin/bash
# Omen Linux Installer

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./install.sh)"
  exit
fi

# Get the absolute path of the directory where install.sh is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
INSTALL_DIR="/opt/omen-linux"

echo "Installing Omen Linux to $INSTALL_DIR..."

# 1. Create Directory
mkdir -p $INSTALL_DIR

# 2. Copy Files
cp -r "$SCRIPT_DIR/backend" $INSTALL_DIR/
cp -r "$SCRIPT_DIR/frontend" $INSTALL_DIR/
cp -r "$SCRIPT_DIR/resources" $INSTALL_DIR/
cp -r "$SCRIPT_DIR/scripts" $INSTALL_DIR/

# 3. Setup Permissions
chmod +x $INSTALL_DIR/scripts/*.sh
mkdir -p $INSTALL_DIR/backend/venv

# 4. Setup Python Environment (in /opt)
echo "Setting up Python environment..."
cd $INSTALL_DIR/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Install Desktop File
echo "Registering Desktop App..."
# Fix: Ensure we copy from the installed location to /usr/share
cp "$INSTALL_DIR/resources/omen-linux.desktop" /usr/share/applications/omen-linux.desktop
update-desktop-database /usr/share/applications/

echo ""
echo "==========================================="
echo " INSTALLATION COMPLETE"
echo "==========================================="
echo "Search for 'Omen Linux' in your application menu."
echo ""
