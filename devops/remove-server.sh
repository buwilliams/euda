#!/bin/bash
#
# remove-server.sh - Remove Euno from a Linux server
#
# Usage: ./remove-server.sh [user@server-ip]
#
# This script removes all Euno data and configuration:
# 1. Stops and disables the euno systemd service
# 2. Removes the systemd service file
# 3. Removes nginx configuration for euno
# 4. Deletes /opt/euno directory (all data and backups)
#
# If no server is specified, uses EUNO_SERVER from .env
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REMOTE_DIR="/opt/euno"

# Load .env if it exists
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | grep -v '^$' | xargs)
fi

# Use argument or fall back to EUNO_SERVER from .env
SERVER="${1:-$EUNO_SERVER}"

if [ -z "$SERVER" ]; then
    echo "Usage: $0 [user@server-ip]"
    echo "Example: $0 root@192.168.1.100"
    echo ""
    echo "Or set EUNO_SERVER in .env to use without arguments"
    exit 1
fi

echo "==================================="
echo "Euno Server Removal"
echo "==================================="
echo "Server: $SERVER"
echo "Remote directory: $REMOTE_DIR"
echo ""
echo "WARNING: This will permanently delete:"
echo "  - All Euno data and backups"
echo "  - The euno systemd service"
echo "  - The nginx configuration for euno"
echo ""
read -p "Type 'yes' to continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 1
fi
echo ""

# Check SSH connectivity
echo "[1/4] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'SSH connection successful'" || {
    echo "Error: Cannot connect to $SERVER"
    exit 1
}

# Stop and remove systemd service
echo "[2/4] Removing systemd service..."
ssh "$SERVER" bash << 'REMOTE_SCRIPT'
set -e

if systemctl is-active --quiet euno 2>/dev/null; then
    echo "  Stopping euno service..."
    sudo systemctl stop euno
fi

if systemctl is-enabled --quiet euno 2>/dev/null; then
    echo "  Disabling euno service..."
    sudo systemctl disable euno
fi

if [ -f /etc/systemd/system/euno.service ]; then
    echo "  Removing service file..."
    sudo rm -f /etc/systemd/system/euno.service
    sudo systemctl daemon-reload
fi

echo "  Systemd service removed"
REMOTE_SCRIPT

# Remove nginx configuration
echo "[3/4] Removing nginx configuration..."
ssh "$SERVER" bash << 'REMOTE_SCRIPT'
set -e

if [ -f /etc/nginx/sites-enabled/euno ]; then
    echo "  Removing enabled site..."
    sudo rm -f /etc/nginx/sites-enabled/euno
fi

if [ -f /etc/nginx/sites-available/euno ]; then
    echo "  Removing available site..."
    sudo rm -f /etc/nginx/sites-available/euno
fi

if command -v nginx &> /dev/null && systemctl is-active --quiet nginx; then
    echo "  Reloading nginx..."
    sudo nginx -t && sudo systemctl reload nginx
fi

echo "  Nginx configuration removed"
REMOTE_SCRIPT

# Remove euno directory
echo "[4/4] Removing Euno directory..."
ssh "$SERVER" bash << REMOTE_SCRIPT
set -e

if [ -d "$REMOTE_DIR" ]; then
    echo "  Deleting $REMOTE_DIR..."
    sudo rm -rf $REMOTE_DIR
    echo "  Directory removed"
else
    echo "  Directory $REMOTE_DIR does not exist"
fi
REMOTE_SCRIPT

echo ""
echo "==================================="
echo "Euno server removal complete!"
echo "==================================="
echo ""
echo "The following were removed:"
echo "  - Euno systemd service"
echo "  - Nginx configuration for euno"
echo "  - $REMOTE_DIR (all data and backups)"
echo ""
echo "Note: System packages (python3, nginx, etc.) were NOT removed"
echo "as they may be used by other applications."
echo ""
