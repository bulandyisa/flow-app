#!/bin/bash
# Обёртка для запуска flow_bot.py с гарантированным таймаутом.
# Если Python-процесс зависнет, этот скрипт его убьёт.
#
# Использование:
#   ./scripts/run_safe.sh --review --clip S01_A
#   FLOW_TIMEOUT=900 ./scripts/run_safe.sh --review  # 15 минут
#
# По умолчанию: 10 минут (600 секунд)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_DIR/venv/bin/python3"
TIMEOUT="${FLOW_TIMEOUT:-600}"

# Убить зомби-браузеры перед запуском
pkill -f "Google Chrome for Testing" 2>/dev/null
rm -f "$PROJECT_DIR/.session/SingletonLock" "$PROJECT_DIR/.session_2/SingletonLock" \
      "$PROJECT_DIR/.session/SingletonCookie" "$PROJECT_DIR/.session_2/SingletonCookie" \
      "$PROJECT_DIR/.session/SingletonSocket" "$PROJECT_DIR/.session_2/SingletonSocket" 2>/dev/null

echo "Starting flow_bot.py with ${TIMEOUT}s timeout..."
echo "Args: $@"
echo ""

# gtimeout (GNU coreutils) для macOS; timeout для Linux
if command -v gtimeout &>/dev/null; then
    TIMEOUT_CMD="gtimeout"
elif command -v timeout &>/dev/null; then
    TIMEOUT_CMD="timeout"
else
    echo "WARNING: no timeout command found. Install coreutils: brew install coreutils"
    echo "Running without system timeout (Python signal timeout still active)."
    FLOW_TIMEOUT="$TIMEOUT" "$PYTHON" "$SCRIPT_DIR/flow_bot.py" "$@"
    EXIT_CODE=$?
    exit $EXIT_CODE
fi

FLOW_TIMEOUT="$TIMEOUT" "$TIMEOUT_CMD" --signal=KILL "$((TIMEOUT + 30))" \
    "$PYTHON" "$SCRIPT_DIR/flow_bot.py" "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 137 ]; then
    echo ""
    echo "================================================"
    echo "  KILLED by system timeout after ${TIMEOUT}s"
    echo "  Cleaning up zombie processes..."
    echo "================================================"
    pkill -f "Google Chrome for Testing" 2>/dev/null
    rm -f "$PROJECT_DIR/.session/SingletonLock" "$PROJECT_DIR/.session_2/SingletonLock" 2>/dev/null
elif [ $EXIT_CODE -eq 42 ]; then
    echo ""
    echo "Exited by Python global timeout."
fi

exit $EXIT_CODE
