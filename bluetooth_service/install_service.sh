#!/bin/bash
#
# Installation script for iOvenado Bluetooth Service
# Run this on the Raspberry Pi to install the systemd service
#

echo "========================================"
echo "iOvenado Bluetooth Service Installer"
echo "========================================"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Check if running on Linux
if [ "$(uname)" != "Linux" ]; then
    echo "ERROR: This script is for Linux (Raspberry Pi) only"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/iovenado-bt.service"

echo "Script directory: $SCRIPT_DIR"
echo "Service file: $SERVICE_FILE"
echo

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "ERROR: Service file not found: $SERVICE_FILE"
    exit 1
fi

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y bluetooth libbluetooth-dev python3-pip python3-venv python3-bluez

# Check if venv exists in parent directory
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PARENT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo
    echo "ERROR: Virtual environment not found at $VENV_DIR"
    echo "Please run these commands first:"
    echo "  cd $PARENT_DIR"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo
echo "Using virtual environment: $VENV_DIR"

# Copy service file to systemd
echo
echo "Installing systemd service..."
cp "$SERVICE_FILE" /etc/systemd/system/
chmod 644 /etc/systemd/system/iovenado-bt.service

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service (start on boot)
echo "Enabling service..."
systemctl enable iovenado-bt.service

# Start service
echo "Starting service..."
systemctl start iovenado-bt.service

# Check status
echo
echo "========================================"
echo "Installation complete!"
echo "========================================"
echo
echo "Service status:"
systemctl status iovenado-bt.service --no-pager
echo
echo "Useful commands:"
echo "  sudo systemctl status iovenado-bt   - Check service status"
echo "  sudo systemctl start iovenado-bt    - Start service"
echo "  sudo systemctl stop iovenado-bt     - Stop service"
echo "  sudo systemctl restart iovenado-bt  - Restart service"
echo "  sudo journalctl -u iovenado-bt -f   - View logs (live)"
echo
