#!/bin/bash
#
# manage.sh - Manage Euno service on remote server
#
# Usage: ./manage.sh [start|stop|restart|status|logs] [user@server-ip]
#
# If no server is specified, uses EUNO_SERVER from .env
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env if it exists
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | grep -v '^$' | xargs)
fi

# Use second argument or fall back to EUNO_SERVER from .env
ACTION="$1"
SERVER="${2:-$EUNO_SERVER}"

if [ -z "$ACTION" ] || [ -z "$SERVER" ]; then
    echo "Usage: $0 [start|stop|restart|status|logs] [user@server-ip]"
    echo ""
    echo "Commands:"
    echo "  start    - Start the Euno service"
    echo "  stop     - Stop the Euno service"
    echo "  restart  - Restart the Euno service"
    echo "  status   - Show service status"
    echo "  logs     - Follow service logs (Ctrl+C to exit)"
    echo ""
    echo "Server can be omitted if EUNO_SERVER is set in .env"
    exit 1
fi

case "$ACTION" in
    start)
        echo "Starting Euno on $SERVER..."
        ssh "$SERVER" "sudo systemctl start euno"
        echo "Started."
        ;;
    stop)
        echo "Stopping Euno on $SERVER..."
        ssh "$SERVER" "sudo systemctl stop euno"
        echo "Stopped."
        ;;
    restart)
        echo "Restarting Euno on $SERVER..."
        ssh "$SERVER" "sudo systemctl restart euno" || echo "Warning: Restart failed, checking status..."
        ssh "$SERVER" "sudo systemctl status euno --no-pager -l" | head -10
        ;;
    status)
        ssh "$SERVER" "sudo systemctl status euno --no-pager -l"
        ;;
    logs)
        ssh "$SERVER" "journalctl -u euno -f"
        ;;
    *)
        echo "Unknown action: $ACTION"
        echo "Valid actions: start, stop, restart, status, logs"
        exit 1
        ;;
esac
