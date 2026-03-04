#!/bin/bash
# Запуск одного бота БЕЗ убийства уже работающих Chrome-процессов.
# В отличие от run_safe.sh, этот скрипт безопасен для параллельного запуска.
# Бот работает до завершения задачи — без жёсткого таймаута.
#
# Использование:
#   ./scripts/run_parallel.sh --account 1 --review --clip S01_A
#   ./scripts/run_parallel.sh --account 2 --disable-gpu --review --clip S02_D
#   ./scripts/run_parallel.sh --account 1 --new-project --review  # создать новый проект
#
# Для запуска 4 ботов одновременно (с новыми проектами):
#   ./scripts/run_parallel.sh --account 1 --new-project --review &
#   sleep 60
#   ./scripts/run_parallel.sh --account 2 --disable-gpu --new-project --review &
#   sleep 60
#   ./scripts/run_parallel.sh --account 3 --new-project --review &
#   sleep 60
#   ./scripts/run_parallel.sh --account 4 --disable-gpu --new-project --review &

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON="$PROJECT_DIR/venv/bin/python3"

# Определяем номер аккаунта из аргументов для очистки ТОЛЬКО его lock-файлов
ACCOUNT_NUM=""
for arg in "$@"; do
    if [ "$prev_arg" = "--account" ]; then
        ACCOUNT_NUM="$arg"
    fi
    prev_arg="$arg"
done

# Очищаем lock-файлы ТОЛЬКО для данного аккаунта (не трогаем другие!)
if [ "$ACCOUNT_NUM" = "1" ]; then
    rm -f "$PROJECT_DIR/.session/SingletonLock" "$PROJECT_DIR/.session/SingletonCookie" "$PROJECT_DIR/.session/SingletonSocket" 2>/dev/null
elif [ "$ACCOUNT_NUM" = "2" ]; then
    rm -f "$PROJECT_DIR/.session_1b/SingletonLock" "$PROJECT_DIR/.session_1b/SingletonCookie" "$PROJECT_DIR/.session_1b/SingletonSocket" 2>/dev/null
elif [ "$ACCOUNT_NUM" = "3" ]; then
    rm -f "$PROJECT_DIR/.session_2/SingletonLock" "$PROJECT_DIR/.session_2/SingletonCookie" "$PROJECT_DIR/.session_2/SingletonSocket" 2>/dev/null
elif [ "$ACCOUNT_NUM" = "4" ]; then
    rm -f "$PROJECT_DIR/.session_2b/SingletonLock" "$PROJECT_DIR/.session_2b/SingletonCookie" "$PROJECT_DIR/.session_2b/SingletonSocket" 2>/dev/null
fi

echo "Starting flow_bot.py (parallel-safe, no timeout)..."
echo "Args: $@"
echo ""

# Запуск без таймаута — бот работает до завершения задачи
PYTHONUNBUFFERED=1 FLOW_TIMEOUT=0 "$PYTHON" -u "$SCRIPT_DIR/flow_bot.py" "$@"
EXIT_CODE=$?

exit $EXIT_CODE
