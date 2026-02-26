#!/bin/bash
# Бот 1 — Аккаунт 1, основная сессия (.session/)
# Использование:
#   ./scripts/run_bot1.sh --review --clip S01_A
#   ./scripts/run_bot1.sh --generate-refs
#   FLOW_TIMEOUT=900 ./scripts/run_bot1.sh --review

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_DIR/venv/bin/python3"
TIMEOUT="${FLOW_TIMEOUT:-600}"
BOT_NUM=1
SESSION_DIR="$PROJECT_DIR/.session"

# Очистка локов только своей сессии
rm -f "$SESSION_DIR/SingletonLock" "$SESSION_DIR/SingletonCookie" "$SESSION_DIR/SingletonSocket" 2>/dev/null

echo "[BOT $BOT_NUM] Starting with ${TIMEOUT}s timeout..."
echo "Session: $SESSION_DIR"
echo "Args: $@"
echo ""

if command -v gtimeout &>/dev/null; then
    TIMEOUT_CMD="gtimeout"
elif command -v timeout &>/dev/null; then
    TIMEOUT_CMD="timeout"
else
    FLOW_TIMEOUT="$TIMEOUT" "$PYTHON" "$SCRIPT_DIR/flow_bot.py" --account $BOT_NUM "$@"
    exit $?
fi

FLOW_TIMEOUT="$TIMEOUT" "$TIMEOUT_CMD" --signal=KILL "$((TIMEOUT + 30))" \
    "$PYTHON" "$SCRIPT_DIR/flow_bot.py" --account $BOT_NUM "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 137 ]; then
    echo "[BOT $BOT_NUM] KILLED by system timeout after ${TIMEOUT}s"
    rm -f "$SESSION_DIR/SingletonLock" 2>/dev/null
elif [ $EXIT_CODE -eq 42 ]; then
    echo "[BOT $BOT_NUM] Exited by Python global timeout."
fi

exit $EXIT_CODE
