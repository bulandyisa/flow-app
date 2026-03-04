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
# Use /tmp venv if available (avoids iCloud-evicted main venv)
if [ -x "/tmp/pw_venv/bin/python3" ]; then
    PYTHON="/tmp/pw_venv/bin/python3"
else
    PYTHON="$PROJECT_DIR/venv/bin/python3"
fi
BOT="$SCRIPT_DIR/flow_bot_v2.py"
TIMEOUT="${FLOW_TIMEOUT:-1200}"

# Определить сессию по --account (для очистки только своих lock-файлов)
ACCOUNT=""
for arg in "$@"; do
    if [ "$prev" = "--account" ]; then ACCOUNT="$arg"; fi
    prev="$arg"
done

# Очистить lock-файлы только для своего аккаунта
case "$ACCOUNT" in
    1) SESSION_DIR="$PROJECT_DIR/.session" ;;
    2) SESSION_DIR="$PROJECT_DIR/.session_1b" ;;
    3) SESSION_DIR="$PROJECT_DIR/.session_2" ;;
    4) SESSION_DIR="$PROJECT_DIR/.session_2b" ;;
    *) SESSION_DIR="$PROJECT_DIR/.session" ;;
esac
rm -f "$SESSION_DIR/SingletonLock" "$SESSION_DIR/SingletonCookie" "$SESSION_DIR/SingletonSocket" 2>/dev/null

echo "Starting flow_bot_v2.py with ${TIMEOUT}s timeout..."
echo "Account: ${ACCOUNT:-1}, Session: $(basename $SESSION_DIR)"
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
    PYTHONUNBUFFERED=1 FLOW_TIMEOUT="$TIMEOUT" "$PYTHON" -u "$BOT" "$@"
    EXIT_CODE=$?
    exit $EXIT_CODE
fi

PYTHONUNBUFFERED=1 FLOW_TIMEOUT="$TIMEOUT" "$TIMEOUT_CMD" --signal=KILL "$((TIMEOUT + 30))" \
    "$PYTHON" -u "$BOT" "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 137 ]; then
    echo ""
    echo "================================================"
    echo "  KILLED by system timeout after ${TIMEOUT}s"
    echo "  Cleaning up..."
    echo "================================================"
    rm -f "$SESSION_DIR/SingletonLock" "$SESSION_DIR/SingletonCookie" "$SESSION_DIR/SingletonSocket" 2>/dev/null
elif [ $EXIT_CODE -eq 42 ]; then
    echo ""
    echo "Exited by Python global timeout."
fi

exit $EXIT_CODE
