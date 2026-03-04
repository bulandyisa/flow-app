#!/bin/bash
# Запуск Chrome с debug-портом для подключения бота.
# Chrome запускается ПОЛЬЗОВАТЕЛЕМ — Google не видит автоматизацию.
#
# Использование (запускать в отдельных вкладках терминала):
#   ./scripts/launch_chrome.sh 1     # Бот 1: порт 9222, сессия .session
#   ./scripts/launch_chrome.sh 2     # Бот 2: порт 9223, сессия .session_1b
#   ./scripts/launch_chrome.sh 3     # Бот 3: порт 9224, сессия .session_2
#   ./scripts/launch_chrome.sh 4     # Бот 4: порт 9225, сессия .session_2b
#
# После запуска Chrome, в другом терминале запустить бота:
#   ./scripts/run_parallel.sh --account 1 --cdp-port 9222 --new-project --review

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

BOT_NUM="${1:-1}"

case "$BOT_NUM" in
    1) SESSION_DIR="$PROJECT_DIR/.session";    PORT=9222 ;;
    2) SESSION_DIR="$PROJECT_DIR/.session_1b"; PORT=9223 ;;
    3) SESSION_DIR="$PROJECT_DIR/.session_2";  PORT=9224 ;;
    4) SESSION_DIR="$PROJECT_DIR/.session_2b"; PORT=9225 ;;
    *) echo "Usage: $0 [1|2|3|4]"; exit 1 ;;
esac

# Очистка lock-файлов
rm -f "$SESSION_DIR/SingletonLock" "$SESSION_DIR/SingletonCookie" "$SESSION_DIR/SingletonSocket" 2>/dev/null

echo "=== Launching Chrome for Bot $BOT_NUM ==="
echo "  Session: $SESSION_DIR"
echo "  CDP port: $PORT"
echo "  URL: https://labs.google/fx/ru/tools/flow"
echo ""
echo "Chrome will open. Log into Google if needed."
echo "Then in another terminal run:"
echo "  ./scripts/run_parallel.sh --account $BOT_NUM --cdp-port $PORT --new-project --review"
echo ""

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --remote-debugging-port="$PORT" \
    --user-data-dir="$SESSION_DIR" \
    --no-first-run \
    --no-default-browser-check \
    --disable-infobars \
    --window-size=1440,900 \
    "https://labs.google/fx/ru/tools/flow" \
    2>/dev/null
