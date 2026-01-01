#!/bin/bash
#
# push-data-remote.sh - Push local data to remote server
#
# Usage: ./push-data-remote.sh [user@server-ip]
#
# This script pushes the local data/ directory to the remote server.
# Remote data is backed up before overwriting.
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
echo "Euno Data Push"
echo "==================================="
echo "Server: $SERVER"
echo "Local: $PROJECT_DIR/data/"
echo "Remote: $REMOTE_DIR/data/"
echo ""

# Check SSH connectivity
echo "[1/3] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'Connected'" || {
    echo "Error: Cannot connect to $SERVER"
    exit 1
}

# Backup remote data first
BACKUP_NAME="data_backup-$(date +%Y%m%d-%H%M%S)"
echo "[2/3] Backing up remote data to $BACKUP_NAME..."
ssh "$SERVER" "cd $REMOTE_DIR && if [ -d data ]; then cp -r data $BACKUP_NAME; fi"

# Sync data directory
echo "[3/3] Pushing data..."
rsync -avz --delete \
    --exclude '__pycache__/' \
    --exclude '.DS_Store' \
    "$PROJECT_DIR/data/" "$SERVER:$REMOTE_DIR/data/"

echo ""
echo "==================================="
echo "Data push complete!"
echo "Remote backup saved to: $REMOTE_DIR/$BACKUP_NAME"
echo "==================================="
