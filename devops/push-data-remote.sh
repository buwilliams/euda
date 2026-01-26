#!/bin/bash
#
# push-data-remote.sh - Push local data to remote server
#
# Usage: ./push-data-remote.sh [--no-restart] [user@server-ip]
#
# This script pushes the local data/ directory to the remote server.
# Remote data is backed up before overwriting.
# By default, restarts the Euno service after syncing.
#
# Options:
#   --no-restart    Skip restarting the service after push
#
# If no server is specified, uses EUNO_SERVER from .env
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REMOTE_DIR="/opt/euno"
RESTART=true

# Load .env if it exists
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | grep -v '^$' | xargs)
fi

# Parse arguments
SERVER=""
for arg in "$@"; do
    case $arg in
        --no-restart)
            RESTART=false
            ;;
        *)
            SERVER="$arg"
            ;;
    esac
done

# Fall back to EUNO_SERVER from .env
SERVER="${SERVER:-$EUNO_SERVER}"

if [ -z "$SERVER" ]; then
    echo "Usage: $0 [--no-restart] [user@server-ip]"
    echo "Example: $0 root@192.168.1.100"
    echo ""
    echo "Options:"
    echo "  --no-restart    Skip restarting the service after push"
    echo ""
    echo "Or set EUNO_SERVER in .env to use without arguments"
    exit 1
fi

echo "==================================="
echo "Euno Data Push"
echo "==================================="
echo "Server: $SERVER"
echo "Local: $PROJECT_DIR/data/"
echo "Remote: $REMOTE_DIR/data/"
echo ""

# Determine step count
if [ "$RESTART" = true ]; then
    STEPS=4
else
    STEPS=3
fi

# Check SSH connectivity
echo "[1/$STEPS] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'Connected'" || {
    echo "Error: Cannot connect to $SERVER"
    exit 1
}

# Backup remote data first
BACKUP_NAME="data_backup-$(date +%Y%m%d-%H%M%S)"
echo "[2/$STEPS] Backing up remote data to $BACKUP_NAME..."
ssh "$SERVER" "cd $REMOTE_DIR && if [ -d data ]; then cp -r data $BACKUP_NAME; fi"

# Sync data directory (exclude auth.json to preserve remote password)
echo "[3/$STEPS] Pushing data..."
rsync -avz --delete \
    --exclude '__pycache__/' \
    --exclude '.DS_Store' \
    --exclude 'system/auth.json' \
    "$PROJECT_DIR/data/" "$SERVER:$REMOTE_DIR/data/"

# Restart service if requested
if [ "$RESTART" = true ]; then
    echo "[4/$STEPS] Restarting service..."
    timeout 30 ssh "$SERVER" "sudo systemctl restart euno" || echo "Warning: Restart timed out or failed, checking status..."
    sleep 2
    echo ""
    echo "Service status:"
    ssh "$SERVER" "sudo systemctl status euno --no-pager -l" | head -10
fi

echo ""
echo "==================================="
echo "Data push complete!"
echo "Remote backup saved to: $REMOTE_DIR/$BACKUP_NAME"
if [ "$RESTART" = true ]; then
    echo "Service restarted"
else
    echo "Service NOT restarted (use without --no-restart to restart)"
fi
echo "==================================="
