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
echo "[1/6] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'Connected'" || {
    echo "Error: Cannot connect to $SERVER"
    echo "Run ./setup-server.sh first if this is a new server"
    exit 1
}

# Clean up __pycache__ on remote so rsync --delete can remove old directories
echo "[2/6] Cleaning remote __pycache__..."
ssh -T "$SERVER" "find $REMOTE_DIR/src -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true"

# Sync files (exclude data, .venv, __pycache__, .git)
echo "[3/6] Syncing files..."
rsync -avz --delete \
    --exclude '/data/' \
    --exclude '/android-app/' \
    --exclude '.venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.git/' \
    --exclude '.env' \
    --exclude '*.log' \
    --exclude '.DS_Store' \
    "$PROJECT_DIR/" "$SERVER:$REMOTE_DIR/"

# Copy .env file
echo "[4/6] Copying .env file..."
scp "$PROJECT_DIR/.env" "$SERVER:$REMOTE_DIR/.env"

# Install dependencies
echo "[5/6] Installing dependencies..."
ssh -T "$SERVER" "cd $REMOTE_DIR && source ~/.local/bin/env && uv sync"

# Restart service
echo "[6/6] Restarting service..."
timeout 30 ssh "$SERVER" "sudo systemctl restart euno" || echo "Warning: Restart timed out or failed, checking status..."

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
echo "  Set password: ssh $SERVER 'cd $REMOTE_DIR && source ~/.local/bin/env && uv run euno set-password'"
echo ""
