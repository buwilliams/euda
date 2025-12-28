#!/bin/bash
#
# deploy.sh - Deploy Euno to a remote server
#
# Usage: ./deploy.sh user@server-ip
#
# This script:
# 1. Syncs the current directory to the server (excluding data/)
# 2. Installs Python dependencies
# 3. Restarts the service
#

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 user@server-ip"
    echo "Example: $0 root@192.168.1.100"
    exit 1
fi

SERVER="$1"
REMOTE_DIR="/opt/euno"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "==================================="
echo "Euno Deployment"
echo "==================================="
echo "Server: $SERVER"
echo "Local: $PROJECT_DIR"
echo "Remote: $REMOTE_DIR"
echo ""

# Check SSH connectivity
echo "[1/4] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'Connected'" || {
    echo "Error: Cannot connect to $SERVER"
    echo "Run ./setup-server.sh first if this is a new server"
    exit 1
}

# Sync files (exclude data, venv, __pycache__, .git)
echo "[2/4] Syncing files..."
rsync -avz --delete \
    --exclude 'data/' \
    --exclude 'venv/' \
    --exclude '.venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.git/' \
    --exclude '.env' \
    --exclude '*.log' \
    --exclude '.DS_Store' \
    "$PROJECT_DIR/" "$SERVER:$REMOTE_DIR/"

# Install dependencies
echo "[3/4] Installing dependencies..."
ssh "$SERVER" bash << REMOTE_SCRIPT
set -e
cd $REMOTE_DIR

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -q -r requirements.txt
REMOTE_SCRIPT

# Restart service
echo "[4/4] Restarting service..."
ssh "$SERVER" "sudo systemctl restart euno"

# Check status
sleep 2
echo ""
echo "Checking service status..."
ssh "$SERVER" "sudo systemctl status euno --no-pager -l" | head -15

echo ""
echo "==================================="
echo "Deployment complete!"
echo "==================================="
echo ""
echo "Application: http://$(echo $SERVER | cut -d@ -f2):8000"
echo ""
echo "Useful commands:"
echo "  View logs:    ssh $SERVER 'journalctl -u euno -f'"
echo "  Restart:      ssh $SERVER 'sudo systemctl restart euno'"
echo "  Set password: ssh $SERVER 'cd $REMOTE_DIR && ./venv/bin/python main.py set-password'"
echo ""
