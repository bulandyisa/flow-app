#!/bin/bash
# ============================================
# Flow App - macOS Launcher
# Аналог launcher.bat для macOS
# ============================================

set -euo pipefail

# ============================================
# 1. Set environment variables
# ============================================
APP_ROOT="$(cd "$(dirname "$0")" && pwd)"

NODE_EXE="$APP_ROOT/node/bin/node"
APP_DIR="$APP_ROOT/app"
DATA_DIR="$APP_ROOT/data"

export NODE_ENV=production
export PYTHON_PATH="$APP_ROOT/python/bin/python3"
export FFMPEG_DIR="$APP_ROOT/ffmpeg"
export PLAYWRIGHT_BROWSERS_PATH="$APP_ROOT/chromium"
export APP_ROOT_DIR="$APP_ROOT"

echo ""
echo "  ========================================"
echo "   Flow App - Launcher"
echo "  ========================================"
echo ""

# Cleanup on exit
cleanup() {
    if [ -n "${SERVER_PID:-}" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
    fi
    rm -f "$DATA_DIR/server.pid"
    echo ""
    echo "  Server stopped."
}
trap cleanup EXIT INT TERM

# ============================================
# 2. Check Node.js exists
# ============================================
echo "  [1/7] Checking Node.js..."
if [ ! -x "$NODE_EXE" ]; then
    echo "  [ERROR] Node.js not found: $NODE_EXE"
    echo "  Please reinstall the application."
    exit 1
fi
echo "  OK: Node.js found"

# ============================================
# 3. Check app code exists
# ============================================
echo "  [2/7] Checking application code..."
if [ ! -f "$APP_DIR/packages/server/dist/index.js" ]; then
    echo "  [ERROR] Application code not found."
    echo "  Please reinstall the application."
    exit 1
fi
echo "  OK: Application code found"

# ============================================
# 4. Create data directories
# ============================================
echo "  [3/7] Checking data directories..."
mkdir -p "$DATA_DIR/projects" "$DATA_DIR/sessions"
echo "  OK: Data directories ready"

# ============================================
# 5. Kill previous instances
# ============================================
echo "  [4/7] Checking for previous instances..."
PID_FILE="$DATA_DIR/server.pid"
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "  Stopping previous instance (PID $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 2
        # Force kill if still running
        if kill -0 "$OLD_PID" 2>/dev/null; then
            kill -9 "$OLD_PID" 2>/dev/null || true
        fi
        echo "  OK: Previous instance stopped"
    else
        echo "  OK: No previous instances found"
    fi
    rm -f "$PID_FILE"
else
    echo "  OK: No previous instances found"
fi

# ============================================
# 6. Run update checker (if exists)
# ============================================
echo "  [5/7] Checking for updates..."
if [ -f "$APP_ROOT/update-checker.js" ]; then
    set +e
    "$NODE_EXE" "$APP_ROOT/update-checker.js" "$APP_ROOT"
    UPDATE_EXIT=$?
    set -e
    if [ "$UPDATE_EXIT" -eq 2 ]; then
        echo "  Update applied, restarting..."
        exec "$0"
    fi
    echo "  OK: Update check complete"
else
    echo "  Skipped: No update checker found"
fi

# ============================================
# 7. Find a free port
# ============================================
echo "  [6/7] Finding free port..."
PORT=3000

while [ "$PORT" -le 3020 ]; do
    if "$NODE_EXE" -e "
        var s = require('net').createServer();
        s.listen($PORT, function() { s.close(); process.exit(0); });
        s.on('error', function() { process.exit(1); });
    " 2>/dev/null; then
        break
    fi
    PORT=$((PORT + 1))
done

if [ "$PORT" -gt 3020 ]; then
    echo "  [ERROR] No free port found in range 3000-3020."
    exit 1
fi
echo "  OK: Port $PORT is free"
export PORT

# ============================================
# 8. Start server
# ============================================
echo "  [7/7] Starting server on port $PORT..."
echo ""

"$NODE_EXE" "$APP_DIR/packages/server/dist/index.js" &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

# ============================================
# 9. Wait for server to be ready (up to 30 seconds)
# ============================================
RETRIES=0

while [ "$RETRIES" -lt 30 ]; do
    sleep 1
    RETRIES=$((RETRIES + 1))
    echo "  Waiting for server... ($RETRIES/30)"

    if curl -s -o /dev/null -w '' --max-time 3 "http://localhost:$PORT/api/auth/status" 2>/dev/null; then
        break
    fi
done

if [ "$RETRIES" -ge 30 ]; then
    echo ""
    echo "  [ERROR] Server did not start within 30 seconds."
    exit 1
fi

echo ""
echo "  ========================================"
echo "   Flow App is running!"
echo "   http://localhost:$PORT"
echo "  ========================================"
echo ""
echo "  Opening browser..."

open "http://localhost:$PORT"

echo ""
echo "  Server is running. Press Ctrl+C to stop."
echo ""

# ============================================
# 10. Keep alive until server stops
# ============================================
while true; do
    sleep 5
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        break
    fi
    if ! curl -s -o /dev/null --max-time 3 "http://localhost:$PORT/api/auth/status" 2>/dev/null; then
        break
    fi
done
