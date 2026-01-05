#!/bin/bash
# Omen Linux Installer

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./install.sh)"
  exit
fi

INSTALL_DIR="/opt/omen-linux"
echo "Installing Omen Linux to $INSTALL_DIR..."

# 1. Create Directory
mkdir -p $INSTALL_DIR

# 2. Copy Files
cp -r backend $INSTALL_DIR/
cp -r frontend $INSTALL_DIR/
cp icon.png $INSTALL_DIR/
cp launch.sh $INSTALL_DIR/
cp start_server_root.sh $INSTALL_DIR/

# 3. Setup Permissions
chmod +x $INSTALL_DIR/launch.sh
chmod +x $INSTALL_DIR/start_server_root.sh
mkdir -p $INSTALL_DIR/backend/venv

# 4. Setup Python Environment (in /opt)
echo "Setting up Python environment..."
cd $INSTALL_DIR/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Install Desktop File
echo "Registering Desktop App..."
cp "omen-linux.desktop" /usr/share/applications/omen-linux.desktop

echo ""
echo "==========================================="
echo " INSTALLATION COMPLETE"
echo "==========================================="
echo "Search for 'Omen Linux' in your application menu."
echo ""
