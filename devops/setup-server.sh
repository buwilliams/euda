#!/bin/bash
#
# setup-server.sh - Initial setup of a fresh Linux server for Euno
#
# Usage: ./setup-server.sh [user@server-ip]
#
# This script:
# 1. Installs Python 3, pip, and dependencies
# 2. Creates the euno directory structure
# 3. Sets up a systemd service
# 4. Configures firewall (optional)
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
echo "Euno Server Setup"
echo "==================================="
echo "Server: $SERVER"
echo "Remote directory: $REMOTE_DIR"
echo ""

# Check SSH connectivity
echo "[1/5] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'SSH connection successful'" || {
    echo "Error: Cannot connect to $SERVER"
    exit 1
}

# Install dependencies
echo "[2/5] Installing system dependencies..."
ssh "$SERVER" bash << 'REMOTE_SCRIPT'
set -e

# Detect package manager
if command -v apt-get &> /dev/null; then
    export DEBIAN_FRONTEND=noninteractive
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 python3-pip python3-venv git
elif command -v dnf &> /dev/null; then
    sudo dnf install -y python3 python3-pip git
elif command -v yum &> /dev/null; then
    sudo yum install -y python3 python3-pip git
elif command -v pacman &> /dev/null; then
    sudo pacman -Sy --noconfirm python python-pip git
else
    echo "Error: Could not detect package manager"
    exit 1
fi

echo "Python version: $(python3 --version)"
REMOTE_SCRIPT

# Create directory structure
echo "[3/5] Creating directory structure..."
ssh "$SERVER" bash << REMOTE_SCRIPT
set -e
sudo mkdir -p $REMOTE_DIR
sudo chown \$USER:\$USER $REMOTE_DIR
mkdir -p $REMOTE_DIR/data
REMOTE_SCRIPT

# Create systemd service
echo "[4/5] Setting up systemd service..."
ssh "$SERVER" bash << REMOTE_SCRIPT
set -e

# Create virtual environment if it doesn't exist
if [ ! -d "$REMOTE_DIR/venv" ]; then
    python3 -m venv $REMOTE_DIR/venv
fi

# Create systemd service file
sudo tee /etc/systemd/system/euno.service > /dev/null << 'EOF'
[Unit]
Description=Euno Personal Intelligence
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$REMOTE_DIR
Environment=PATH=$REMOTE_DIR/venv/bin:/usr/bin:/bin
ExecStart=$REMOTE_DIR/venv/bin/python main.py start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable euno
REMOTE_SCRIPT

# Install and configure nginx
echo "[5/6] Setting up nginx reverse proxy..."
ssh "$SERVER" bash << 'REMOTE_SCRIPT'
set -e

# Install nginx
if command -v apt-get &> /dev/null; then
    sudo apt-get install -y -qq nginx
elif command -v dnf &> /dev/null; then
    sudo dnf install -y nginx
elif command -v yum &> /dev/null; then
    sudo yum install -y nginx
elif command -v pacman &> /dev/null; then
    sudo pacman -Sy --noconfirm nginx
fi

# Create nginx config for Euno
sudo tee /etc/nginx/sites-available/euno > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    # Static files - no caching during development
    location /static/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;

        # Prevent caching of static files
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    # HTML pages - no caching
    location = / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    location = /app {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }

    # Server-Sent Events - requires special handling
    location /api/events {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Critical for SSE: disable all buffering
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400;

        # Ensure nginx doesn't buffer the response
        chunked_transfer_encoding off;
    }

    # All other requests (API, etc)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/euno /etc/nginx/sites-enabled/euno
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl reload nginx
echo "nginx configured to proxy port 80 -> 8000"
REMOTE_SCRIPT

# Configure firewall (if ufw is available)
echo "[6/6] Configuring firewall..."
ssh "$SERVER" bash << 'REMOTE_SCRIPT'
if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp 2>/dev/null || true
    sudo ufw allow 443/tcp 2>/dev/null || true
    echo "Firewall: Ports 80 and 443 opened"
else
    echo "Firewall: ufw not found, skipping"
fi
REMOTE_SCRIPT

echo ""
echo "==================================="
echo "Server setup complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "  1. Run ./deploy-euno.sh $SERVER to deploy the application"
echo "  2. SSH in and run: cd $REMOTE_DIR && python main.py set-password"
echo "  3. Access at http://<server-ip>"
echo ""
