#!/bin/bash
#
# start.sh - Start SearXNG locally for development
#
# Usage: ./start.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Generate secret key if not already set
if grep -q "change-me-generate-with-openssl-rand-hex-32" settings.yml 2>/dev/null; then
    echo "Generating secret key..."
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s/change-me-generate-with-openssl-rand-hex-32/$SECRET_KEY/" settings.yml
fi

# Start SearXNG
echo "Starting SearXNG..."
docker compose up -d

# Wait for it to be ready
echo "Waiting for SearXNG to start..."
for i in {1..30}; do
    if curl -s "http://localhost:8080/search?q=test&format=json" 2>/dev/null | grep -q results; then
        echo ""
        echo "SearXNG is ready at http://localhost:8080"
        echo ""
        echo "Test: curl 'http://localhost:8080/search?q=hello&format=json'"
        echo "Stop: docker compose down (in this directory)"
        exit 0
    fi
    printf "."
    sleep 1
done

echo ""
echo "Warning: SearXNG may not be fully ready yet"
echo "Check logs: docker compose logs -f"
