# Flow App — Архитектура

> Локальное приложение для производства мультфильмов через Google Flow

## Стек технологий

| Слой | Технология |
|------|-----------|
| Backend | Node.js 22 + Express + TypeScript |
| Frontend | React 19 + Vite + Tailwind CSS |
| State | Zustand + TanStack Query |
| Bot | Python + Playwright (существующий, вызывается через subprocess) |
| AI | Claude API (Opus 4.6) через @anthropic-ai/sdk |
| Realtime | WebSocket (ws) |
| Monorepo | npm workspaces |

## Структура проекта

```
flow-app/
├── packages/
│   ├── shared/                     # Типы, константы, валидация
│   │   └── src/
│   │       ├── types/              # Clip, Manifest, Project, Bot
│   │       ├── validation.ts       # 12 правил валидации промптов
│   │       └── constants.ts
│   │
│   ├── server/                     # Node.js бэкенд
│   │   └── src/
│   │       ├── index.ts            # Express сервер
│   │       ├── config.ts           # .env + settings.json
│   │       ├── api/                # REST маршруты
│   │       │   ├── projects.ts     # CRUD проектов
│   │       │   ├── clips.ts        # Клипы и промпты
│   │       │   ├── review.ts       # Accept/reject/фидбек
│   │       │   ├── bot.ts          # Управление ботами
│   │       │   ├── ai.ts           # Claude API endpoints
│   │       │   ├── media.ts        # Раздача картинок/видео
│   │       │   ├── settings.ts     # Настройки
│   │       │   └── update.ts       # Авто-обновление
│   │       ├── bot/                # Управление Python-ботом через subprocess
│   │       │   ├── runner.ts       # Запуск/остановка Python-бота
│   │       │   ├── manager.ts      # Управление N ботами, распределение
│   │       │   └── parser.ts       # Парсинг stdout бота для статуса
│   │       ├── ai/                 # Claude API
│   │       │   ├── client.ts       # Anthropic SDK обёртка
│   │       │   ├── screenplay.ts   # Сценарий → клипы
│   │       │   ├── prompts.ts      # Генерация промптов
│   │       │   ├── feedback.ts     # Фидбек → новый промпт
│   │       │   ├── rules.ts        # Правила качества
│   │       │   └── templates.ts    # Системные промпты
│   │       ├── data/               # Файловая система
│   │       │   ├── project-store.ts
│   │       │   ├── manifest.ts
│   │       │   ├── file-manager.ts
│   │       │   └── docx-parser.ts
│   │       ├── update/             # Авто-обновление
│   │       │   ├── checker.ts
│   │       │   ├── applier.ts
│   │       │   └── migrations.ts
│   │       └── ws/                 # WebSocket
│   │           └── events.ts
│   │
│   └── client/                     # React фронтенд
│       └── src/
│           ├── App.tsx
│           ├── api/                # HTTP клиент
│           │   ├── client.ts
│           │   └── hooks.ts        # React Query хуки
│           ├── store/              # Zustand
│           │   ├── project.ts
│           │   ├── review.ts
│           │   └── bot.ts
│           ├── pages/
│           │   ├── ProjectList.tsx  # Список проектов
│           │   ├── ProjectSetup.tsx # Визард создания проекта
│           │   ├── Clips.tsx       # Таблица клипов
│           │   ├── Review.tsx      # Ревью кадров/видео
│           │   ├── BotControl.tsx  # Управление ботами
│           │   └── Settings.tsx    # Настройки
│           └── components/
│               ├── layout/         # Sidebar, Header
│               ├── review/         # ClipCard, VariantGrid, Lightbox
│               ├── clips/          # ClipTable, PromptEditor
│               ├── bot/            # BotCard, BotLog
│               ├── project/        # ScreenplayUpload, CharacterSetup
│               └── common/         # ProgressBar, Pagination
│
├── data/                           # Данные (gitignored)
│   ├── projects/                   # Проекты сотрудника
│   │   └── <project-id>/
│   │       ├── project.json
│   │       ├── screenplay.docx
│   │       ├── prompts/all_prompts.json
│   │       ├── references/         # Референсы проекта
│   │       │   ├── characters/
│   │       │   │   └── <char-id>/
│   │       │   │       ├── base.png           # Принятый базовый образ
│   │       │   │       ├── angles/            # Принятые ракурсы
│   │       │   │       │   ├── front_full.png
│   │       │   │       │   ├── profile.png
│   │       │   │       │   └── face_closeup.png
│   │       │   │       └── review/            # На ревью (4 варианта × N)
│   │       │   │           ├── base/attempt_1/variant_1-4.png
│   │       │   │           └── angles/<angle>/attempt_1/variant_1-4.png
│   │       │   └── locations/
│   │       │       └── <loc-id>/
│   │       │           ├── base.png           # Принятая базовая локация
│   │       │           ├── angles/            # Принятые ракурсы (15+)
│   │       │           │   ├── wide_front.png
│   │       │           │   ├── wide_left.png
│   │       │           │   ├── closeup_steps.png
│   │       │           │   └── ... (15+ файлов)
│   │       │           └── review/            # На ревью
│   │       │               ├── base/attempt_1/variant_1-4.png
│   │       │               └── angles/<angle>/attempt_1/variant_1-4.png
│   │       ├── review/             # Ревью клипов (основной pipeline)
│   │       │   └── <clip_id>/manifest.json + варианты
│   │       ├── frames/             # Принятые кадры
│   │       └── clips/              # Принятые видео
│   ├── sessions/                   # Playwright сессии
│   └── settings.json               # Глобальные настройки
│
├── rules/                          # Правила (обновляются с GitHub)
│   ├── prompt-spec.md
│   ├── veo-prompt-spec.md
│   ├── quality-rules.json
│   └── characters.json
│
└── scripts/
    ├── dev.sh                      # Запуск dev-сервера
    └── build.sh                    # Сборка production
```

## API маршруты

| Route | Метод | Описание |
|-------|-------|----------|
| `/api/projects` | GET/POST | Список / создание проектов |
| `/api/projects/:id` | GET | Данные проекта |
| `/api/projects/:id/clips` | GET | Все клипы |
| `/api/projects/:id/clips/:clipId` | GET/PATCH | Клип + промпты |
| `/api/projects/:id/review` | GET | Клипы на ревью |
| `/api/projects/:id/review/submit` | POST | Batch accept/reject |
| `/api/projects/:id/bot/start` | POST | Запустить ботов |
| `/api/projects/:id/bot/stop` | POST | Остановить ботов |
| `/api/projects/:id/bot/status` | GET | Статус ботов |
| `/api/projects/:id/ai/analyze-screenplay` | POST | Сценарий → сцены + персонажи + локации |
| `/api/projects/:id/ai/generate-clips` | POST | Сцены + референсы → клипы с промптами |
| `/api/projects/:id/ai/rewrite-prompts` | POST | Фидбек → новые промпты |
| `/api/projects/:id/references` | GET | Все референсы проекта (персонажи + локации) |
| `/api/projects/:id/references/characters` | GET/POST | Персонажи: список / создать |
| `/api/projects/:id/references/characters/:charId/angles` | GET/POST | Ракурсы персонажа |
| `/api/projects/:id/references/locations` | GET/POST | Локации: список / создать |
| `/api/projects/:id/references/locations/:locId/angles` | GET/POST | Ракурсы локации |
| `/api/projects/:id/references/review` | GET | Референсы на ревью |
| `/api/projects/:id/references/review/submit` | POST | Принять/отклонить референсы |
| `/api/projects/:id/references/generate` | POST | Запустить генерацию недостающих |
| `/api/media/:projectId/*` | GET | Картинки и видео |
| `/api/settings` | GET/PATCH | Настройки |
| `/api/update/check` | GET | Проверка обновлений |
| `/api/update/apply` | POST | Применить обновление |

## Data Flow — полный workflow

```
ЭТАП 1: ПОДГОТОВКА
══════════════════

1. Загрузка .docx сценария → парсинг текста

2. Claude разбивает на сцены, определяет:
   - Список персонажей (имена, описания)
   - Список локаций (названия, описания)

3. Проверка библиотеки референсов (GitHub):
   ├── ✅ Персонаж/локация есть → скачивает
   └── ❌ Нет → добавляет в очередь на генерацию

4. ГЕНЕРАЦИЯ ПЕРСОНАЖЕЙ (кого нет в библиотеке)
   a. Claude пишет промпт для базового образа
   b. Бот генерит 4 варианта
   c. Сотрудник ревьюит → принимает один
   d. Claude пишет промпты для ракурсов/поз
   e. Бот генерит → ревью → принятые = референсы персонажа

5. ГЕНЕРАЦИЯ ЛОКАЦИЙ (каких нет в библиотеке)
   a. Claude пишет промпт для базовой локации
   b. Бот генерит 4 варианта
   c. Сотрудник ревьюит → принимает один
   d. Claude пишет промпты для 15+ ракурсов
      (принятый вариант = ингредиент для каждого ракурса):
      - широкий план (фронт, слева, справа)
      - средний план (от двери, от окна, из угла)
      - крупный план (детали: ступени, перила, стол, полки)
      - вид изнутри наружу / снаружи внутрь
      - верхний ракурс / нижний ракурс
   e. Бот генерит 4 варианта на КАЖДЫЙ ракурс
   f. Сотрудник ревьюит каждый → принятые = библиотека ракурсов

   ИТОГ: 15+ принятых ракурсов на каждую локацию
   Это КРИТИЧНО для консистентности — каждый клип использует
   конкретный принятый ракурс, а не генерит локацию с нуля.

ЭТАП 2: ПРОИЗВОДСТВО
════════════════════

6. Claude пишет промпты для клипов
   (зная ВСЕ принятые ракурсы и персонажей,
    указывая конкретный файл ракурса в каждом клипе)

7. Сотрудник проверяет промпты

8. Запуск ботов → генерация кадров/видео

9. Ревью:
   ├── Accept → next component (first → last → VEO)
   └── Reject + фидбек → Claude переписывает промпт
       → manifest сбрасывается → бот перегенерирует

10. CHAIN: first → (accept) → last → (accept) → VEO → (accept)

11. Все клипы готовы → мультфильм собран
```

## Pipeline генерации референсов (подробно)

### Локации
```
Сценарий: "действие происходит на крыльце старого дома"
  ↓
Claude: "Нужна локация: крыльцо старого дома"
  ↓
Проверка GitHub библиотеки → НЕТ
  ↓
Claude пишет промпт базовой локации:
  "Old wooden porch of a village house, weathered steps,
   carved railings, potted plants. 3D Pixar-style."
  ↓
Бот генерит 4 варианта → РЕВЬЮ → принят вариант 2
  ↓
Принятый вариант = loc_porch_base.png
  ↓
Claude пишет 15+ промптов для ракурсов,
каждый с ингредиентом loc_porch_base.png:
  1. "Wide establishing shot from the street..."
  2. "Wide shot from the left side..."
  3. "Wide shot from the right side..."
  4. "Close-up of the wooden steps..."
  5. "Close-up of the carved railings from the left..."
  6. "Close-up of the carved railings from the right..."
  7. "View from the porch looking outward..."
  8. "View through the doorway into the house..."
  9. "Low angle looking up at the porch roof..."
  10. "High angle looking down at the steps..."
  11. "Detail shot of potted plants on the railing..."
  12. "The porch at golden hour, warm light..."
  13. "Corner of the porch, showing depth..."
  14. "Side view showing the full length..."
  15. "Over-the-shoulder angle from inside..."
  ↓
Бот генерит 4 варианта × 15 ракурсов = 60 изображений
  ↓
Сотрудник ревьюит каждый ракурс → принимает лучшие
  ↓
ИТОГ: loc_porch_wide_front.png
       loc_porch_wide_left.png
       loc_porch_wide_right.png
       loc_porch_steps_closeup.png
       loc_porch_railing_left.png
       ... (15+ файлов)
```

### Персонажи
```
Сценарий: "Амин, мальчик в серой толстовке"
  ↓
Проверка GitHub библиотеки → НЕТ
  ↓
Claude пишет промпт базового образа:
  "A boy in a grey hoodie, friendly expression,
   full body shot. 3D Pixar-style."
  ↓
Бот генерит 4 варианта → РЕВЬЮ → принят
  ↓
Claude генерит ракурсы/позы:
  - Полный рост (фронт)
  - Полный рост (профиль, 3/4)
  - Крупный план лица
  - Сидящий
  - В движении (бежит)
  ↓
Бот генерит → РЕВЬЮ → принятые = референсы персонажа
```

## Конфигурация

### settings.json (глобальные)
```json
{
  "claudeApiKey": "sk-ant-...",
  "animationStyle": "3D Pixar-style",
  "defaultVariantCount": 4,
  "accounts": [
    { "email": "user@gmail.com", "sessionDir": "account_1", "maxBots": 3 }
  ],
  "generationTimeout": 300,
  "pollInterval": 5,
  "githubToken": "ghp_...",
  "updateRepo": "genvid25/flow-app",
  "dataDir": "./data"
}
```

### project.json (per-project)
```json
{
  "id": "uuid",
  "name": "Сосед",
  "style": "3D Pixar-style",
  "skipLast": true,
  "characters": [
    { "id": "amin", "name": "Амин", "clothing": "in the grey hoodie", "refImage": "characters/amin.jpeg" }
  ],
  "locations": [
    { "id": "kitchen", "name": "Кухня", "angles": [{"file": "locations/kitchen_wide.jpg", "type": "wide"}] }
  ],
  "seating": {
    "kitchen": { "Papa": "at the head of the table", "Mama": "next to Papa" }
  }
}
```

## Фазы реализации

| Фаза | Что | Описание |
|------|-----|----------|
| 1 | Фундамент | Monorepo, типы, Express, React + Layout, data layer |
| 2 | Бот | Порт Playwright логики из Python в TypeScript |
| 3 | Дашборд | Review page, варианты, lightbox, accept/reject |
| 4 | AI | Claude API: генерация промптов, обработка фидбеков |
| 5 | Полировка | Авто-обновление, настройки, тестирование |

## Ключевые решения

1. **Медиа через HTTP** — Express раздаёт файлы напрямую, не base64 (решает проблему 3-минутной загрузки)
2. **WebSocket** — realtime статус ботов без polling
3. **Боты как child_process** — каждый бот в своём процессе, manager перезапускает упавших
4. **Правила отделены от кода** — `rules/` обновляется с GitHub независимо
5. **Совместимый формат** — all_prompts.json и manifest.json такие же, как в текущем проекте
6. **data/ вне iCloud** — по умолчанию ~/FlowData/ чтобы macOS не выгружал файлы
