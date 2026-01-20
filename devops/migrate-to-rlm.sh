#!/bin/bash
#
# migrate-to-rlm.sh - Migrate existing Euno installation to RLM architecture
#
# Usage: ./migrate-to-rlm.sh [user@server-ip]
#
# This script prepares an existing Euno server for the RLM branch upgrade by:
# 1. Installing uv package manager
# 2. Updating systemd service configuration
# 3. Creating backup before changes
#
# Safe to run multiple times - checks before making changes
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REMOTE_DIR="/opt/euno"

# Load .env if it exists
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | grep -v '^$' | xargs 2>/dev/null || true)
fi

# Use argument or fall back to EUNO_SERVER from .env
SERVER="${1:-$EUNO_SERVER}"

if [ -z "$SERVER" ]; then
    echo "Usage: $0 [user@server-ip]"
    echo "Example: $0 root@192.168.1.100"
    echo ""
    echo "Or set EUNO_SERVER in .env"
    exit 1
fi

echo "==========================================="
echo "Euno RLM Migration"
echo "==========================================="
echo "Server: $SERVER"
echo "Remote: $REMOTE_DIR"
echo ""
echo "This migration prepares your server for the RLM branch upgrade."
echo "It will:"
echo "  - Install uv package manager"
echo "  - Update systemd service configuration"
echo "  - Create a backup before making changes"
echo ""
echo "After this migration, run: ./deploy-euno.sh $SERVER"
echo ""
read -p "Type 'yes' to continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 1
fi
echo ""

# Test SSH connectivity
echo "[1/5] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'SSH connection successful'" || {
    echo "Error: Cannot connect to $SERVER"
    exit 1
}

# Create backup
echo "[2/5] Creating backup of current data..."
ssh "$SERVER" bash << 'REMOTE_SCRIPT'
set -e
cd /opt
if [ -d "euno/data" ]; then
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    BACKUP_NAME="data_backup-rlm-migration-${TIMESTAMP}"
    echo "Creating backup: ${BACKUP_NAME}"
    cp -r euno/data "${BACKUP_NAME}"
    echo "✓ Backup created at: /opt/${BACKUP_NAME}"
else
    echo "ℹ No data directory found - fresh installation?"
fi
REMOTE_SCRIPT

# Install uv
echo "[3/5] Installing uv package manager..."
ssh "$SERVER" bash << 'REMOTE_SCRIPT'
set -e

if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version)
    echo "ℹ uv already installed: $UV_VERSION"
    exit 0
fi

echo "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH for this session
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
if command -v uv &> /dev/null; then
    UV_VERSION=$(uv --version)
    echo "✓ uv installed successfully: $UV_VERSION"
else
    echo "✗ ERROR: uv installation failed"
    exit 1
fi
REMOTE_SCRIPT

# Update systemd service
echo "[4/5] Updating systemd service configuration..."
ssh "$SERVER" bash << 'REMOTE_SCRIPT'
set -e

SERVICE_FILE="/etc/systemd/system/euno.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "✗ ERROR: Service file not found at $SERVICE_FILE"
    echo "  Please ensure Euno is installed first"
    exit 1
fi

# Check if service needs updating
if grep -q "/root/.local/bin/uv run euno start" "$SERVICE_FILE"; then
    echo "ℹ Service already configured for uv"
    exit 0
fi

# Backup existing service file
sudo cp "$SERVICE_FILE" "${SERVICE_FILE}.backup-$(date +%Y%m%d-%H%M%S)"
echo "✓ Backed up existing service file"

# Update service file
echo "Updating service configuration..."
sudo tee "$SERVICE_FILE" > /dev/null << 'EOF'
[Unit]
Description=Euno Personal Intelligence
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/euno
EnvironmentFile=/opt/euno/.env
Environment=PATH=/root/.local/bin:/usr/bin:/bin
ExecStart=/root/.local/bin/uv run euno start
Restart=always
RestartSec=5
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
echo "✓ Service configuration updated and daemon reloaded"
REMOTE_SCRIPT

# Validate migration
echo "[5/5] Validating migration..."
ssh "$SERVER" bash << 'REMOTE_SCRIPT'
set -e

# Source uv environment for validation
export PATH="$HOME/.local/bin:$PATH"

FAILED=0

# Check uv
echo -n "Checking uv installation... "
if command -v uv &> /dev/null; then
    echo "✓"
else
    echo "✗ FAILED: uv not found in PATH"
    FAILED=1
fi

# Check systemd service
echo -n "Checking systemd service... "
if grep -q "/root/.local/bin/uv run euno start" /etc/systemd/system/euno.service; then
    echo "✓"
else
    echo "✗ FAILED: Service not configured correctly"
    FAILED=1
fi

# Check if service can be loaded
echo -n "Checking service can be loaded... "
if sudo systemctl daemon-reload 2>/dev/null && sudo systemctl status euno --no-pager -n 0 &>/dev/null; then
    echo "✓"
else
    echo "⚠ Service check skipped (service may be stopped)"
fi

if [ $FAILED -eq 0 ]; then
    echo ""
    echo "✓ All validation checks passed!"
else
    echo ""
    echo "✗ Some checks failed - please review errors above"
    exit 1
fi
REMOTE_SCRIPT

echo ""
echo "==========================================="
echo "Migration Complete!"
echo "==========================================="
echo ""
echo "✓ uv package manager installed"
echo "✓ systemd service updated"
echo "✓ Backup created"
echo ""
echo "Next steps:"
echo "  1. Run: ./deploy-euno.sh $SERVER"
echo "  2. The deployment will:"
echo "     - Sync code to the server"
echo "     - Install dependencies with uv"
echo "     - Update system templates"
echo "     - Restart the service"
echo ""
echo "If you encounter issues after deployment, restore backup with:"
echo "  ssh $SERVER 'sudo systemctl stop euno && rm -rf /opt/euno/data && cp -r /opt/data_backup-rlm-migration-* /opt/euno/data && sudo systemctl start euno'"
echo ""
