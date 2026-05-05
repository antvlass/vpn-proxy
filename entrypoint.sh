#!/bin/sh
set -e

GLUETUN_URL="http://127.0.0.1:8000"
POLL_INTERVAL=3
POLL_MAX=40

cleanup() {
    echo "Shutting down..."
    kill "$GLUETUN_PID" 2>/dev/null || true
    wait "$GLUETUN_PID" 2>/dev/null || true
}
trap cleanup TERM INT

/gluetun-entrypoint &
GLUETUN_PID=$!

echo "Waiting for gluetun VPN tunnel..."
for i in $(seq 1 $POLL_MAX); do
    STATUS=$(wget -qO- --timeout=2 "$GLUETUN_URL/v1/vpn/status" 2>/dev/null || true)
    if echo "$STATUS" | grep -q 'running'; then
        echo "VPN tunnel is up."
        break
    fi
    if [ "$i" -eq "$POLL_MAX" ]; then
        echo "VPN tunnel did not come up in time, starting app anyway..."
    fi
    sleep "$POLL_INTERVAL"
done

echo "Starting Python app..."
exec /app/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080 --app-dir /app
