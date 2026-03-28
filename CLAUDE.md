# Flow App — правила для Claude Code

## Язык общения
- Русский язык

## КРИТИЧНО
- **НЕ трогать** папку `~/Documents/Projects/flow-automation/` — это отдельный проект
- **Анализировать** варианты перед принятием решений, обсуждать с пользователем
- **Таймауты** для всех Bash-команд: короткие 10с, средние 30с, длинные 120с

## Архитектура
- Monorepo: `packages/shared`, `packages/server`, `packages/client`
- Backend: Node.js + Express + TypeScript
- Frontend: React + Vite + Tailwind CSS
- Bot: Python (существующий `bot/flow_bot.py`, вызывается через subprocess)
- AI: Claude API через `@anthropic-ai/sdk` с prompt caching
- Video: FFmpeg (склейка/обрезка)
- Windows + macOS

## Ключевые решения
- Бот на Python, НЕ переписывать на TypeScript
- Промпты загружаются файлом, НЕ генерируются через API
- Референсы парсятся автоматически из ингредиентов промптов (без Claude API)
- nb_last (последние кадры) УДАЛЕНЫ — цепочка: first → VEO
- Claude API только для: исправление промптов по фидбеку + перевод
- Страница "Настройки" убрана — ключи доставляются через систему активации

## Навигация приложения
- **Настройка** — 3 шага: Сценарий → Промпты → Референсы
- **Промпты** — просмотр/редактирование с переводом и исправлением через API
- **Производство** — ревью кадров/видео, генерация, фидбеки
- **Сборка** — видеоредактор (склейка + обрезка через FFmpeg)

## Структура
```
flow-app/
├── packages/shared/     # Типы, валидация, константы
├── packages/server/     # Express API, бот-менеджер, AI модули, FFmpeg
├── packages/client/     # React SPA
├── bot/                 # Python бот (flow_bot.py, run_safe.sh/bat)
├── rules/               # Правила для Claude API
│   ├── prompt-spec.md
│   ├── veo-prompt-spec.md
│   ├── quality-rules.md
│   └── angle-generation.md
├── data/                # Данные проектов (gitignored)
└── scripts/             # install.sh, install.bat
```

## Защита
- Короткие коды активации (TEST001, MASHA2026)
- API ключ зашифрован в `access.json` на GitHub (genvid25/flow-app-refs)
- Удалённый контроль: active: false → блокировка

## Команды
```bash
npm run dev              # Запуск (сервер + клиент)
npm run build            # Сборка production
npx tsc --noEmit -p packages/server/tsconfig.json  # Type-check сервер
npx tsc --noEmit -p packages/client/tsconfig.json  # Type-check клиент
```

## GitHub
- `genvid25/flow-app-refs` — библиотека референсов + access.json (публичный)
- Пушить только по просьбе пользователя
