#!/bin/bash
#
# sync.sh - Sync data to a remote server
#
# Usage: ./sync.sh user@server-ip
#
# This script syncs the local data/ directory to the remote server.
# Use with caution - this overwrites remote data.
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
echo "Euno Data Sync"
echo "==================================="
echo "Server: $SERVER"
echo "Local: $PROJECT_DIR/data/"
echo "Remote: $REMOTE_DIR/data/"
echo ""

# Check SSH connectivity
echo "[1/2] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'Connected'" || {
    echo "Error: Cannot connect to $SERVER"
    exit 1
}

# Sync data directory
echo "[2/2] Syncing data..."
rsync -avz --delete \
    --exclude '*.log' \
    --exclude '__pycache__/' \
    --exclude '.DS_Store' \
    "$PROJECT_DIR/data/" "$SERVER:$REMOTE_DIR/data/"

echo ""
echo "==================================="
echo "Data sync complete!"
echo "==================================="
