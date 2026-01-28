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
echo "[1/7] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'Connected'" || {
    echo "Error: Cannot connect to $SERVER"
    echo "Run ./setup-server.sh first if this is a new server"
    exit 1
}

# Clean up __pycache__ on remote so rsync --delete can remove old directories
echo "[2/7] Cleaning remote __pycache__..."
ssh -T "$SERVER" "find $REMOTE_DIR/src -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true"

# Sync files (exclude data, .venv, __pycache__, .git)
echo "[3/7] Syncing files..."
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
echo "[4/7] Copying .env file..."
scp "$PROJECT_DIR/.env" "$SERVER:$REMOTE_DIR/.env"

# Install dependencies
echo "[5/7] Installing dependencies..."
ssh -T "$SERVER" "cd $REMOTE_DIR && source ~/.local/bin/env && uv sync"

# Update service file if needed (euno start -> euno web)
echo "[6/7] Checking service file..."
ssh "$SERVER" "grep -q 'euno start' /etc/systemd/system/euno.service 2>/dev/null && sudo sed -i 's/euno start/euno web/g' /etc/systemd/system/euno.service && sudo systemctl daemon-reload && echo 'Updated service file (start -> web)' || echo 'Service file OK'"

# Restart service
echo "[7/7] Restarting service..."
ssh "$SERVER" "sudo systemctl restart euno" || echo "Warning: Restart failed, checking status..."

# Check status
sleep 2
echo ""
echo "Checking Euno service status..."
ssh "$SERVER" "sudo systemctl status euno --no-pager -l" | head -15

# Start/check SearXNG
echo ""
echo "Setting up SearXNG..."
ssh "$SERVER" bash << REMOTE_SCRIPT
set -e
cd $REMOTE_DIR

# Generate secret key if not already set
SEARXNG_CONFIG="$REMOTE_DIR/data/system/searxng.yml"
if grep -q "change-me-generate-with-openssl-rand-hex-32" "\$SEARXNG_CONFIG" 2>/dev/null; then
    echo "Generating SearXNG secret key..."
    SECRET_KEY=\$(openssl rand -hex 32)
    sed -i "s/change-me-generate-with-openssl-rand-hex-32/\$SECRET_KEY/" "\$SEARXNG_CONFIG"
fi

# Check if SearXNG is running
if docker ps | grep -q searxng; then
    echo "SearXNG: Running"
    # Test JSON API
    if curl -s "http://localhost:8080/search?q=test&format=json" 2>/dev/null | grep -q results; then
        echo "SearXNG API: OK"
    else
        echo "SearXNG API: Not responding, restarting..."
        docker compose restart
        sleep 5
    fi
else
    echo "SearXNG: Starting..."
    docker compose up -d
    # Wait for it to be ready
    for i in {1..15}; do
        if curl -s "http://localhost:8080/search?q=test&format=json" 2>/dev/null | grep -q results; then
            echo "SearXNG: Ready"
            break
        fi
        sleep 1
    done
fi
REMOTE_SCRIPT

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
