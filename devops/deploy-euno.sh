#!/bin/bash
#
# deploy-euno.sh - Deploy Euno to a remote server
#
# Usage: ./deploy-euno.sh [user@server-ip]
#
# This script:
# 1. Syncs the current directory to the server (excluding data/)
# 2. Copies .env file
# 3. Installs Python dependencies
# 4. Restarts the service
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
echo "Euno Deployment"
echo "==================================="
echo "Server: $SERVER"
echo "Local: $PROJECT_DIR"
echo "Remote: $REMOTE_DIR"
echo ""

# Check .env file exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "Error: .env file not found in $PROJECT_DIR"
    echo "Copy .env.example to .env and add your API keys"
    exit 1
fi

# Check SSH connectivity
echo "[1/5] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'Connected'" || {
    echo "Error: Cannot connect to $SERVER"
    echo "Run ./setup-server.sh first if this is a new server"
    exit 1
}

# Sync files (exclude data, venv, __pycache__, .git)
echo "[2/5] Syncing files..."
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

# Copy .env file
echo "[3/5] Copying .env file..."
scp "$PROJECT_DIR/.env" "$SERVER:$REMOTE_DIR/.env"

# Install dependencies
echo "[4/5] Installing dependencies..."
ssh -T "$SERVER" "cd $REMOTE_DIR && source venv/bin/activate && pip install --no-input --progress-bar off -r requirements.txt"

# Restart service
echo "[5/5] Restarting service..."
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
echo "Application: http://$(echo $SERVER | cut -d@ -f2)"
echo ""
echo "Useful commands:"
echo "  View logs:    ssh $SERVER 'journalctl -u euno -f'"
echo "  Restart:      ssh $SERVER 'sudo systemctl restart euno'"
echo "  Set password: ssh $SERVER 'cd $REMOTE_DIR && ./venv/bin/python main.py set-password'"
echo ""
