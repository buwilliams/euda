#!/bin/bash
#
# manage.sh - Manage Euno service on remote server
#
# Usage: ./manage.sh user@server-ip [start|stop|restart|status|logs]
#

set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 user@server-ip [start|stop|restart|status|logs]"
    echo ""
    echo "Commands:"
    echo "  start    - Start the Euno service"
    echo "  stop     - Stop the Euno service"
    echo "  restart  - Restart the Euno service"
    echo "  status   - Show service status"
    echo "  logs     - Follow service logs (Ctrl+C to exit)"
    exit 1
fi

SERVER="$1"
ACTION="$2"

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
        ssh "$SERVER" "sudo systemctl restart euno"
        echo "Restarted."
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
