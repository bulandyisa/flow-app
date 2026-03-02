# Flow Automation — правила для Claude Code

## Язык общения
- Общаемся на русском языке

## КРИТИЧНО: Таймауты для всех Bash-команд
- **ВСЕГДА** указывай `timeout` параметр при вызове Bash tool
- Короткие команды (ls, git, pip): timeout 30000 (30 сек)
- Средние команды (python скрипты, тесты): timeout 120000 (2 мин)
- Длинные команды (flow_bot.py, генерация): timeout 300000 (5 мин)
- **НИКОГДА** не запускай Bash без timeout — это вешает чат!

## Запуск flow_bot.py
- Всегда через обёртку: `./scripts/run_safe.sh` (а не напрямую python)
- Python: использовать `venv/bin/python3`, НЕ системный python
- Для длинных генераций: `FLOW_TIMEOUT=900 ./scripts/run_safe.sh`
- Максимум **2 бота одновременно** — 4 Chromium крашат GPU

## Архитектура: 2 бота
2 Google аккаунта = 2 бота. Каждый бот на своём аккаунте навсегда.

| Бот | Аккаунт | Сессия | CLI |
|-----|---------|--------|-----|
| Bot 1 | Акк 1 | `.session` | `--account 1` |
| Bot 2 | Акк 2 | `.session_2` | `--account 2` |

### Важные правила для ботов
1. **НЕ переключать аккаунт** — каждый бот работает только на своём аккаунте
2. **Failover**: если один аккаунт не работает — передать задания рабочему боту
3. **Ничего руками не одобряется** — бот полностью автономен
4. **Retry на server_error** — до 2 попыток, потом failover на другой аккаунт
5. **Content filter** — НЕ повторять (prompt blocked)

## Двойные промпты (A + B)
Каждая генерация (nb_first, nb_last) имеет **два промпта**: Prompt A и Prompt B.
- Оба описывают ту же сцену, но разными словами
- Бот сначала генерирует Prompt A (4 варианта), потом Prompt B (4 варианта)
- Итого 8 вариантов на выбор
- В `all_prompts.json`: поля `nano_banana_prompt` (A) и `nano_banana_prompt_b` (B)
- Аналогично для VEO: `veo_prompt` (A) и `veo_prompt_b` (B)

## Pipeline генерации (порядок компонентов)
1. **nb_first** — NB Pro: первый кадр (4 варианта x2 промпта = 8 вариантов)
2. **nb_mid** (опционально) — NB Pro: средний кадр (принятый first как ингредиент)
3. **nb_last** — NB Pro: последний кадр (принятый mid/first как ингредиент)
4. **veo** — VEO 3.1 Fast: видео из кадров

## Воркфлоу анализа изображений (КРИТИЧНО)
Claude Code **сам** анализирует сгенерированные варианты. Без API ключей, без сторонних сервисов.

### Полный цикл для одного клипа:
1. Запустить `--review --clip {X} --component nb_first` → бот генерирует 8 PNG (4×A + 4×B)
2. **Прочитать PNG** из `output/review/{clip}/nb_first/attempt_N/prompt_a/` и `prompt_b/` через Read tool
3. **Оценить** каждый вариант по 17 критериям (шкала 1-10)
4. Выбрать лучший A → `--select --batch a`, лучший B → `--select --batch b`
5. Если avg >= 9.0 и все критические >= 6 → ACCEPTED, кадр в `output/frames/`
6. Повторить для nb_last (принятый first добавляется как ингредиент)
7. VEO: 8 видео → **все в дашборд, анализировать НЕ нужно**

### 17 критериев оценки
`char_face`, `char_outfit`, `char_count`, `anatomy_hands`, `anatomy_body`,
`anatomy_face`, `scale`, `physics`, `spatial`, `scenario_action`,
`scenario_emotion`, `scenario_objects`, `loc_match`, `lighting`,
`artifacts`, `style_3d`, `composition`, `continuity`

### Пороги
- QUALITY_THRESHOLD = 9.0 (среднее без нулевых)
- CRITICAL_MIN_SCORE = 6 для: `anatomy_hands`, `anatomy_body`, `scale`, `physics`, `spatial`, `char_count`

### Команды
```bash
# Генерация
./scripts/run_safe.sh --review --clip S01_A --component nb_first --account 1
# Выбор (batch a или b)
./scripts/run_safe.sh --select --clip S01_A --component nb_first --attempt 1 --variant 0 --batch a --scores '{"char_face":9,...}'
# Извлечение кадров видео для анализа
./scripts/run_safe.sh --extract-frames --clip S01_A --component veo --attempt 1
# Отклонить все варианты попытки
./scripts/run_safe.sh --fail --clip S01_A --component nb_first --attempt 1
# Таблица статусов
./scripts/run_safe.sh --status
```

## Nano Banana промпты
- НИКОГДА не описывай внешность персонажей — модель берёт из фото-ингредиентов
- НИКОГДА не описывай интерьер локаций — модель берёт из фото-ингредиентов
- Описывай ТОЛЬКО действия, композицию, стиль
- Ссылайся на персонажей по номеру ингредиента: "the character from Image 1"
- Identity Locking: первые 10 слов — идентификация персонажа
- Спецификация: `PROMPT_SPEC.md` (NB Pro v3.0), `VEO_PROMPT_SPEC.md` (VEO v2.0)

## VEO правила
- ВСЕГДА `Veo 3.1 - Fast` (не Quality)
- НИКОГДА не включать возраст в промпт
- Всегда: `3D Pixar-style animation, family-friendly`
- Enhance Prompt toggle = OFF
- `sanitize_prompt()` делает это автоматически

## Структура проекта
- `scripts/flow_bot.py` — Главный Playwright бот (~3500+ строк)
- `scripts/run_safe.sh` — Обёртка с таймаутом и cleanup
- `output/prompts/all_prompts.json` — Все промпты и конфиги (14 клипов)
- `output/review/` — Сгенерированные варианты для ревью
- `output/frames/` — Принятые кифреймы
- `output/clips/` — Принятые видеоклипы
- `персонажи_hq/` — Референсы персонажей (апскейл 4x)
- `локации_hq/` — Референсы локаций (апскейл 4x)
- `PROMPT_SPEC.md` — Спецификация NB Pro промптов v3.0
- `VEO_PROMPT_SPEC.md` — Спецификация VEO промптов v2.0
- `venv/` — Python venv (**ВСЕГДА** `venv/bin/python3`)

## Google Flow UI (февраль 2026)
Flow полностью обновил UI на чат-интерфейс:
- Промпт: `[role="textbox"]` (contenteditable div), НЕ textarea
- Настройки: чип "Nano Banana Pro x4" → popup с табами Image/Video и кнопками x1-x4
- Генерация: кнопка `arrow_forward` (круглая "→")
- Ингредиенты: кнопка "+" → "Загрузить изображение"
- Результаты: `img[alt="Сгенерированное изображение"]` в чат-сообщениях
- **Виртуальный скроллинг**: НЕ скроллить во время polling — элементы удаляются из DOM
- Детекция генерации: по плейсхолдерам с процентами (13%, 27%), НЕ по тексту страницы

## Озвучка (voice_bot.py)
- `--init` → генерация audio_config.json из сценария
- `--tts [--clip X]` → генерация голоса через ElevenLabs API
- `--sfx [--clip X]` → генерация звуковых эффектов
- `--mix-full [--clip X]` → ffmpeg: видео + голос + SFX → финальные клипы
- `--assemble` → склейка всех клипов в один ролик
- `--status` → таблица прогресса
- Конфиг: `output/audio/audio_config.json`
- Выход: `output/audio/clips_voiced/`, `output/audio/final/`

## GitHub
- Репозиторий: `genvid25/flow` (private)
- Пушить только по просьбе пользователя, НЕ автоматически

## Персонажи — одежда для промптов
- **Амин**: grey hoodie
- **Карим**: black hoodie
- **Тако**: red-and-white striped shirt, red cap
- **Рами**: green hoodie, brown cargo pants
- **Хасан**: light blue polo shirt
- **Мама**: black hijab, black abaya
- **Папа**: black turtleneck sweater, glasses
- **Ая**: pink dress, dark navy striped hijab
