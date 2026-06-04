#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=========================================="
echo " Starting Debian VM Setup for Trading Bot "
echo "=========================================="

# 1. Update and Upgrade Packages
echo "[1/6] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# 2. Install Required Dependencies
echo "[2/6] Installing Python, pip, and system dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv git curl ufw

# 3. Setup Project Directory and Virtual Environment
PROJECT_DIR="/opt/trading_bot"
echo "[3/6] Setting up project directory at $PROJECT_DIR..."

if [ ! -d "$PROJECT_DIR" ]; then
    sudo git clone https://github.com/webdotpulse/MyBit $PROJECT_DIR
    sudo chown -R $USER:$USER $PROJECT_DIR
fi

echo "[4/6] Creating Python virtual environment..."
cd $PROJECT_DIR
python3 -m venv venv
source venv/bin/activate

# 4. Install Python Requirements
echo "[5/6] Installing Python packages..."
# Ensure requirements.txt exists in the dir before running this
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
else
    echo "Warning: requirements.txt not found. Skipping pip install."
fi

# 5. Configure Firewall (UFW)
echo "[6/6] Configuring Firewall..."
sudo sed -i 's/IPV6=yes/IPV6=no/' /etc/default/ufw || true
sudo ufw allow ssh || true
sudo ufw allow 80/tcp || true
sudo ufw allow 8000/tcp || true # Web Dashboard Port
sudo ufw --force enable || true

echo "=========================================="
echo " Setup Complete! "
echo " Please edit the .env file with your API keys."
echo " To start the service, run the systemd setup steps."
echo "=========================================="
