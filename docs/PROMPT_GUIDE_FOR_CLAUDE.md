# Инструкция по написанию промптов для анимационного фильма «Сигнал»

> Этот документ — полная инструкция для Claude. Загрузи его в чат, и после этого просто отправляй кусок сценария — Claude будет выдавать готовые промпты для Nano Banana Pro (изображения) и VEO 3.1 (видео).

---

## Контекст проекта

**Фильм:** «Сигнал» — короткометражный 3D анимационный фильм в стиле Pixar.
**Стиль:** 3D Pixar-style, family-friendly, cinematic.
**Инструменты:**
- **Nano Banana Pro (NB Pro)** — генерация ключевых кадров (PNG изображения)
- **VEO 3.1 Fast** — генерация видео из первого и последнего кадра (8 сек MP4)

**Пайплайн для каждого клипа:**
1. Генерируем **first frame** (первый кадр) через NB Pro
2. Генерируем **last frame** (последний кадр) через NB Pro (first используется как ингредиент для консистентности)
3. Генерируем **видео** через VEO 3.1 из first → last

---

## Персонажи и их одежда

Каждый персонаж загружается как фото-ингредиент (Image 1, Image 2, и т.д.). Одежда — ключевой идентификатор, чтобы модель не путала персонажей.

| Персонаж | Одежда для промпта |
|----------|-------------------|
| **Амин** | in a grey hoodie |
| **Карим** | in a black hoodie |
| **Тако** | in a red-and-white striped shirt and red cap |
| **Рами** | in a green hoodie and brown cargo pants |
| **Хасан** | in a light blue polo shirt |
| **Мама** | in a black hijab and black abaya |
| **Папа** | in a black turtleneck sweater and glasses |
| **Ая** | in a pink dress and dark navy striped hijab |

---

## ЧАСТЬ 1: Промпты для Nano Banana Pro (изображения)

### Главный принцип

NB Pro получает **три источника информации:**
1. **Фото персонажей** (ингредиенты) — лицо, тело, одежда
2. **Фото локации** (ингредиент) — интерьер, мебель, освещение
3. **Текст промпта** — действие, эмоция, ракурс камеры, стиль

**Золотое правило: текст НЕ описывает то, что уже есть на фото.**
Не описывай внешность персонажей, не описывай интерьер — модель берёт это из фото.

### Что описывать в тексте промпта:
- Действие персонажа (что делает)
- Эмоцию (выражение лица)
- Ракурс камеры
- Освещение
- Стиль

### Чего НИКОГДА не описывать:
- Внешность: цвет волос, глаз, рост, тип тела
- Возраст/пол: boy, girl, child, young, old, he, she
- Интерьер: расположение мебели, детали стен, объекты-декорации
- Пространственное позиционирование: "on the left", "on the right", "in the center"

### Identity Locking (закрепление персонажа)

Самая важная техника. Персонаж должен быть упомянут **в первых 10 словах промпта**.

Формулировка:
- Первое упоминание: `The exact character in [одежда] from Image N, preserving identical facial features and proportions,`
- Повторное: `the exact character in [одежда] from Image N`

**Одежда обязательна!** "The exact character from Image 1" — слабый идентификатор. "The exact character in a grey hoodie from Image 1" — сильный.

### Структура промпта NB Pro

```
[IDENTITY + ACTION] → [LOCATION] → [CAMERA + LIGHTING] → [STYLE]
```

### Для 2-3 персонажей: Chain-of-Thought

Используй `First... Then... Finally...` для последовательного описания:

```
First, the exact character in a grey hoodie from Image 1, preserving identical facial features, [ДЕЙСТВИЕ + ЭМОЦИЯ].
Then, the exact character in a black hoodie from Image 2, [ДЕЙСТВИЕ + ЭМОЦИЯ].
Use Image 3 as the exact background location.
[КАМЕРА], [СВЕТ]. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.
```

### Ракурсы камеры

| Ракурс | Когда |
|--------|-------|
| `Extreme close-up` | Деталь: рука, глаза |
| `Close-up` | Лицо, эмоция |
| `Medium close-up` | Грудь + лицо |
| `Medium shot` | Поясной — основной рабочий ракурс |
| `Medium-wide shot` | Персонаж + окружение |
| `Wide shot` | Полная локация |

Дополнительно: `eye-level`, `low angle`, `high angle`, `slight high angle`.

### Освещение

Один описатор, согласованный по сцене:
- `bright daylight` — дневные сцены
- `warm evening light` — вечер
- `dramatic side lighting` — напряжённые моменты
- `soft diffused light` — спокойные сцены

### First / Last стратегия

- **first**: начальная композиция клипа
- **last**: конечная композиция — что изменилось

**Delta Rule:** разница между first и last — ОДНО чёткое изменение:
- Позиция: стоял → сел
- Направление: смотрел на приёмник → повернулся к другому
- Эмоция: скучающий → заинтригованный

**80% промпта одинаковы, 20% — дельта.**

Для last кадра добавляй: `Maintain exact visual continuity with Image N.` (ссылка на принятый first кадр как ингредиент).

### Ингредиенты

| Тип сцены | Формула |
|-----------|---------|
| 1 персонаж | 1 char + 1 location = 2 ингредиента |
| 2 персонажа | 2 char + 1 location = 3 |
| 3 персонажа | 3 char + 1 location = 4 |

**Максимум 4 ингредиента.** Больше — нестабильный результат.

### Реквизит

Упоминай ТОЛЬКО если персонаж взаимодействует:
- OK: `hand on the tuning dial of a radio`
- НЕ OK: `a radio receiver on the bench` (просто стоит)

### Длина промпта

60-80 слов (без стиль-тега). Не перегружай.

### Завершающий блок

Всегда заканчивай:
```
No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.
```

---

## ЧАСТЬ 2: Промпты для VEO 3.1 (видео)

### Главный принцип

VEO получает **first frame + last frame + текст**. Он **видит оба кадра**. Промпт описывает **КАК перейти** из A в B, а НЕ что изображено.

**Золотое правило: НЕ переописывай то, что видно на кадрах.**

### Что описывать:
- Движение камеры
- Действие/переход между кадрами
- Звук (Audio)
- Стиль

### Чего НИКОГДА не описывать:
- Внешность персонажа (VEO видит на кадре)
- Обстановку / интерьер (VEO видит на кадре)
- Начальную позу (VEO видит first frame)
- Конечную позу (VEO видит last frame)
- Одежду, цвет (VEO видит на кадре)

### Структура промпта VEO

```
[CAMERA MOVEMENT]. [ACTION/TRANSITION]. Audio: [звук]. Smooth cinematic motion, 3D Pixar-style animation, family-friendly.
```

### Движения камеры

| Движение | Когда |
|----------|-------|
| `Slow dolly in` | Нарастание напряжения |
| `Slow dolly out` | Раскрытие пространства |
| `Tracking shot` | Следование за персонажем |
| `Slow pan right/left` | Обзор |
| `Static shot` / `Locked-off` | Спокойные сцены, напряжение |
| `Push in` | Драматический акцент |
| `Handheld` | Напряжение, реализм |

**Правило: одно движение камеры на промпт.**

### Действие

Описывай **движение**, а не статику:
- Плохо: `The character sits at the workbench.` (это описание кадра)
- Хорошо: `The character reaches for the dial and turns it.` (это действие)

Используй конкретные глаголы: `reaches`, `turns`, `leans`, `stands up`, `walks toward`
НЕ используй: `is sitting`, `is looking`, `appears to be`

**Одно главное действие на клип.** Не 5 действий за 8 секунд.

### Силовые глаголы (Force-Based Verbs)

Заменяй мягкие глаголы на физические:
- `moves toward` → `pushes forward`
- `looks at` → `snaps head toward`
- `picks up` → `snatches up`
- `turns around` → `pivots sharply`

### Audio (звук)

**VEO 3.1 генерирует звук!** Обязательно указывай.

Формат: `Audio: [описание]`

4 слоя:
- **SFX**: `radio crackling`, `footsteps`, `paper rustling`
- **Ambient**: `quiet room`, `garage hum`, `evening crickets`
- **Dialogue**: `says: "Что это?"` (в кавычках, с двоеточием!)
- **Music**: `soft piano`, `tense strings`

1-2 слоя на промпт достаточно.

### Lip-Sync (синхронизация речи)

**Критически важно:**
- Персонаж ГОВОРИТ в сценарии → включи `says: "реплика"` в промпт
- Персонаж МОЛЧИТ → используй `watches silently`, `listens`, `mouth closed`
- НЕ используй `reacts`, `responds`, `exclaims` для молчащих

Формат диалога с двоеточием предотвращает субтитры:
- `Character says: "Hello"` → БЕЗ субтитров
- `Character says "Hello"` → модель может наложить текст

### Timestamp Prompting (для сложных сцен)

```
[00:00-00:03] Character slowly turns the dial — static fills the air.
[00:03-00:06] A clear signal emerges. Character freezes, eyes widening.
[00:06-00:08] Grabs a pen and starts writing. Audio: rhythmic beeping.
```

Использовать только когда несколько последовательных действий.

### Оптимальная длина

150-300 символов — оптимально.
> 400 символов — непредсказуемая приоритизация.

### Завершающий блок

```
Smooth cinematic motion, 3D Pixar-style animation, family-friendly.
```

---

## ЧАСТЬ 3: Верность сценарию

### 7 правил

1. **Масштаб точно по тексту** — не преувеличивай. Если нет слова "огромный" — не пиши `enormous`
2. **Эмоциональная точность** — нюанс из сценария, не ярлык
3. **Действия буквально из сценария** — `переворачивается на бок` → `rolls over on his side`
4. **Реквизит только из сценария** — не добавляй фантазийных предметов
5. **Не додумывай эмоции** — если нет в тексте "улыбается" — не пиши `smiles`
6. **Сохраняй драматургическую функцию** кадра в истории
7. **Тон из контекста сцены**

### Процесс: Сценарий → Промпт

1. Определи: кто в кадре, что делает, какая эмоция, какой реквизит, время суток
2. Определи: какие фото-ингредиенты нужны (персонажи + локация)
3. Напиши промпт NB Pro для first frame
4. Напиши промпт NB Pro для last frame (80% общее, 20% дельта)
5. Напиши промпт VEO (переход из first в last)

---

## ЧАСТЬ 4: Примеры

### Пример 1: Кухня, ужин (5 персонажей)

**Сценарий:** Тако рассказывает историю про прыжок, размахивая руками. Мама: «И порвал штаны».

**Ингредиенты:**
- Image 1: Тако (char_tako_full.jpeg)
- Image 2: Мама (char_mama_full.jpeg)
- Image 3: Амин (char_amin_full.jpeg)
- Image 4: Папа (char_papa_full.jpeg)
- Image 5: Ая (char_aya_full.jpeg)
- Image 6: Локация кухни

**NB Pro — first frame:**
```
First, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features and proportions, sits at the dinner table, gesturing enthusiastically with both hands raised, mouth open mid-story, eyes bright with excitement. Then, the exact character in a black hijab and black abaya from Image 2, preserving identical facial features, sits across the table, watching with patient amusement. Then, the exact character in a grey hoodie from Image 3, preserving identical facial features, sits at the table looking bored, arms crossed. Then, the exact character in a black turtleneck sweater and glasses from Image 4, preserving identical facial features, sits at the head of the table, eating quietly. Then, the exact character in a pink dress and dark navy striped hijab from Image 5, preserving identical facial features, sits beside Image 2 character, listening with a curious smile. Use Image 6 as the exact background location. Medium-wide shot, eye-level. Warm evening indoor lighting. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.
```

**NB Pro — last frame:**
```
First, the exact character in a black hijab and black abaya from Image 2, preserving identical facial features and proportions, sits at the dinner table, eyebrows raised, expression of exasperated amusement. Then, the exact character in a red-and-white striped shirt and red cap from Image 1, preserving identical facial features, sits across, looking slightly sheepish, hands lowered. [остальные персонажи аналогично]. Use Image 6 as the exact background location. Maintain exact visual continuity with Image 7. Medium-wide shot, eye-level. Warm evening indoor lighting. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.
```

**VEO:**
```
Static medium shot. The character at the table gestures animatedly, waving both hands while telling a story, then pauses as the other character responds with a calm remark. Subtle shift from excitement to sheepish expression. Audio: dinner table ambiance, soft clink of dishes. Smooth cinematic motion, 3D Pixar-style animation, family-friendly.
```

### Пример 2: Гараж, 2 персонажа (крупный план)

**Сценарий:** Амин записывает цифры по памяти. Берёт атлас, палец на точке: «Рядом со школой».

**Ингредиенты:**
- Image 1: Амин
- Image 2: Карим
- Image 3: Локация гаража

**NB Pro — first frame:**
```
First, the exact character in a grey hoodie from Image 1, preserving identical facial features and proportions, writes rapidly on a piece of paper at the workbench, pen gripped tightly, brow furrowed in concentration. Then, the exact character in a black hoodie from Image 2, preserving identical facial features, watches from beside, leaning over to see what is being written. Use Image 3 as the exact background location. Close-up, slightly high angle. Warm garage light focused on the paper. No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.
```

**VEO:**
```
Slow dolly in. The character writes numbers quickly on paper, then grabs an old atlas. Flips pages. Finger traces the map and stops on a point. Eyes widen — realization. Audio: pen scratching paper, pages rustling, a soft gasp. Smooth cinematic motion, 3D Pixar-style animation, family-friendly.
```

---

## ЧАСТЬ 5: Формат вывода

Когда я отправляю кусок сценария, выдай для каждого клипа:

```
### Клип: [ID]
**Сцена:** [краткое описание]
**Ингредиенты:** [список Image N: кто/что]

**NB Pro — first frame:**
[промпт]

**NB Pro — last frame:**
[промпт]

**VEO:**
[промпт]
```

Если в сцене несколько клипов — разбей на логические блоки по 4-8 секунд действия каждый.

---

## Чек-лист перед отправкой промпта

### NB Pro:
- [ ] Identity lock в первых 10 словах
- [ ] Одежда указана при каждом упоминании персонажа
- [ ] Нет описания внешности / интерьера / пространственного расположения
- [ ] Один ракурс камеры + один описатор света
- [ ] `No text, no watermarks. 3D Pixar-style, family-friendly, cinematic.`
- [ ] 60-80 слов
- [ ] First/last: 80% общего, 20% дельта
- [ ] Реквизит только при взаимодействии
- [ ] Chain-of-thought (First... Then...) для 2+ персонажей

### VEO:
- [ ] Одно движение камеры, отдельным предложением
- [ ] Конкретные глаголы движения
- [ ] НЕ описан интерьер / внешность
- [ ] Audio: хотя бы один звуковой слой
- [ ] Lip-sync: реплики как `says: "..."`, молчание как `watches silently`
- [ ] `Smooth cinematic motion, 3D Pixar-style animation, family-friendly.`
- [ ] 150-300 символов
- [ ] Одно главное действие
