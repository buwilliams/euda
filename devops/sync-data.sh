#!/bin/bash
#
# sync-data.sh - Sync data to a remote server
#
# Usage: ./sync-data.sh [user@server-ip]
#
# This script syncs the local data/ directory to the remote server.
# Use with caution - this overwrites remote data.
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
