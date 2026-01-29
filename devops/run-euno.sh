#!/bin/bash
#
# Euno Server Wrapper Script
#
# Runs the Euno server with automatic restart support.
# When the server exits with code 42, it will be restarted automatically.
# Exit with Ctrl+C or any other exit code to stop completely.
#
# Usage:
#   ./devops/run-euno.sh
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Euno with auto-restart support${NC}"
echo "Exit code 42 will trigger automatic restart"
echo "Press Ctrl+C to stop completely"
echo ""

while true; do
    # Run the server
    uv run python main.py web

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 42 ]; then
        echo ""
        echo -e "${YELLOW}Restart requested (exit code 42)${NC}"
        echo "Restarting in 2 seconds..."
        sleep 2
        echo ""
    elif [ $EXIT_CODE -eq 0 ]; then
        echo ""
        echo "Server stopped cleanly (exit code 0)"
        break
    else
        echo ""
        echo "Server exited with code $EXIT_CODE"
        break
    fi
done

echo "Goodbye!"
