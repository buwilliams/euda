#!/bin/bash
#
# setup-server.sh - Initial setup of a fresh Linux server for Euno
#
# Usage: ./setup-server.sh [user@server-ip]
#
# This script:
# 1. Installs Python 3 and uv package manager
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
echo "This will install dependencies and configure the server."
echo ""
read -p "Type 'yes' to continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 1
fi
echo ""

# Check SSH connectivity
echo "[1/6] Testing SSH connection..."
ssh -o ConnectTimeout=10 "$SERVER" "echo 'SSH connection successful'" || {
    echo "Error: Cannot connect to $SERVER"
    exit 1
}

# Install dependencies
echo "[2/6] Installing system dependencies..."
ssh "$SERVER" bash << 'REMOTE_SCRIPT'
set -e

# Detect package manager and install Python
if command -v apt-get &> /dev/null; then
    export DEBIAN_FRONTEND=noninteractive
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 git curl
elif command -v dnf &> /dev/null; then
    sudo dnf install -y python3 git curl
elif command -v yum &> /dev/null; then
    sudo yum install -y python3 git curl
elif command -v pacman &> /dev/null; then
    sudo pacman -Sy --noconfirm python git curl
else
    echo "Error: Could not detect package manager"
    exit 1
fi

# Install uv
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "Python version: $(python3 --version)"
echo "uv version: $(uv --version)"
REMOTE_SCRIPT

# Create directory structure
echo "[3/6] Creating directory structure..."
ssh "$SERVER" bash << REMOTE_SCRIPT
set -e
sudo mkdir -p $REMOTE_DIR
sudo chown \$USER:\$USER $REMOTE_DIR
mkdir -p $REMOTE_DIR/data

# Create euno wrapper script
sudo tee /usr/local/bin/euno > /dev/null << 'EOF'
#!/bin/bash
cd /opt/euno && uv run euno "\$@"
EOF
sudo chmod +x /usr/local/bin/euno
echo "Created /usr/local/bin/euno wrapper"
REMOTE_SCRIPT

# Create systemd service
echo "[4/6] Setting up systemd service..."
ssh "$SERVER" bash << REMOTE_SCRIPT
set -e

# Create systemd service file
sudo tee /etc/systemd/system/euno.service > /dev/null << 'EOF'
[Unit]
Description=Euno Personal Intelligence
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$REMOTE_DIR
EnvironmentFile=$REMOTE_DIR/.env
Environment=PATH=/root/.local/bin:/usr/bin:/bin
ExecStart=/root/.local/bin/uv run euno web
Restart=always
RestartSec=5
TimeoutStopSec=10

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

    # Web files - no caching during development
    location /web/ {
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
echo "  1. Run 'euno sync' to deploy code and data"
echo "  2. SSH in and create .env: cd $REMOTE_DIR && cp .env.example .env && nano .env"
echo "  3. SSH in and set password: cd $REMOTE_DIR && uv run euno set-password"
echo "  4. Start the service: sudo systemctl start euno"
echo "  5. Access at http://<server-ip>"
echo ""
