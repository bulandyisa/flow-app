# VEO 3.1 — Prompt Specification v2.0

> Режим: `frames_to_video_first_last` (интерполяция между first и last кадром)
> Модель: `Veo 3.1 - Fast`
> Проект: «Сигнал» (3D Pixar-style анимация)
>
> Источники: Google Cloud, Google DeepMind, LTX Studio, Visla, fal.ai, Replicate,
> Skywork, Habr/BotHub, GitHub snubroot, architjn.com, Vertex AI docs

---

## Core Principle

В режиме first+last frame VEO **видит оба кадра**. Он знает, как начинается и заканчивается сцена.
Промпт должен описывать **КАК перейти** из A в B, а НЕ что изображено на кадрах.

**Три источника информации для VEO:**

| Источник | Что контролирует |
|----------|-----------------|
| First frame | Начальная композиция, персонажи, обстановка |
| Last frame | Конечная композиция, изменения |
| Текст промпта | Движение, камера, аудио, стиль перехода |

**Золотое правило: НЕ переописывай то, что видно на кадрах.**
VEO уже видит кадры — дублирование текстом создаёт конфликт и нестабильность.

---

## Два режима VEO

### «Видео по кадрам» (frames) — default
- Загружает first + last frame в слоты кадров
- VEO интерполирует между ними
- **Когда:** простые переходы, 1 действие

### «Видео по образцам» (samples) — новый
- Загружает 2-3 референсных изображения как ингредиенты
- VEO использует их как стилевые/композиционные ориентиры
- **Когда:** сложные переходы, нужен mid frame для подсказки
- **Кадры:** first + mid + last (3 ингредиента)
- **Без mid:** first + last (2 ингредиента)

| Параметр | По кадрам | По образцам |
|----------|-----------|-------------|
| Слоты | frame slot 0, 1 | ingredient panel |
| Кадры | first + last | first + (mid) + last |
| Max кадров | 2 | 3 |
| Промпт | переход A→B | стиль + действие |
| JSON поле | `"veo_mode": "frames"` | `"veo_mode": "samples"` |

**Выбор режима:** задаётся полем `veo_mode` в JSON-конфиге клипа. Default = `"frames"`.

---

## Prompt Formula

Источники: [LTX Studio](https://ltx.studio/blog/veo-prompt-guide),
[Visla](https://www.visla.us/blog/guides/how-to-prompt-veo-3-and-veo-3-1/)

### Формула для first+last frame:
```
[CAMERA MOVEMENT] → [ACTION/TRANSITION] → [AUDIO] → [STYLE]
```

### 4 компонента:

### 1. Camera Movement (ДВИЖЕНИЕ КАМЕРЫ)
**Самый важный компонент для first+last.** Камера = что зритель видит между кадрами.

Писать как отдельное предложение, НЕ встраивать в описание действия.

| Движение | Когда | Пример |
|----------|-------|--------|
| `Slow dolly in` | Нарастание напряжения, фокус | Камера плавно приближается |
| `Slow dolly out` / `Pull back` | Раскрытие пространства | Камера отъезжает, показывая контекст |
| `Tracking shot` | Следование за персонажем | Камера идёт за героем |
| `Slow pan right/left` | Обзор пространства | Горизонтальный поворот |
| `Static shot` / `Locked-off` | Спокойные сцены, напряжение | Камера неподвижна |
| `Crane up` / `Crane down` | Масштаб, драматизм | Подъём/спуск |
| `Handheld` | Напряжение, реализм | Лёгкая тряска |
| `Push in` | Драматический акцент | Медленное приближение |
| `Over-the-shoulder` | Диалог, взаимодействие | Через плечо |

**Правило: одно движение камеры на промпт.** Не комбинируй `dolly in` + `pan left` + `crane up`.

### 2. Action/Transition (ДЕЙСТВИЕ)
Описывай **движение** между кадрами, а НЕ статические позы.

- Плохо: `The character sits at the workbench with a radio.` ← это описание кадра
- Хорошо: `The character reaches for the tuning dial and slowly turns it.` ← это действие

**Для first+last:** фокусируйся на ОДНОМ главном действии, которое трансформирует first в last.

Используй конкретные глаголы движения:
- `reaches`, `turns`, `leans forward`, `stands up`, `walks toward`
- НЕ: `is sitting`, `is looking`, `appears to be` (статика)

### 3. Audio (ЗВУК)
**VEO 3.1 генерирует звук!** Это мощный инструмент, который мы НЕ использовали.

Формат — отдельная строка с маркером:
```
Audio: [описание звука]
```

Или интегрировано:
```
SFX: crackling static from the radio. Ambient: quiet garage hum.
```

**4 слоя звука:**

| Слой | Пример | Когда |
|------|--------|-------|
| **Dialogue** | `"Что... это?"` (в кавычках) | Если персонаж говорит |
| **SFX** | `radio crackling`, `footsteps`, `paper rustling` | Звуки действий |
| **Ambient** | `quiet room`, `garage hum`, `evening crickets` | Фоновая атмосфера |
| **Music/Score** | `soft piano`, `tense strings` | Эмоциональный акцент |

**Правила аудио:**
- Привязывай звуки к действиям: `He turns the dial — static crackles, then a clear signal emerges.`
- Не перегружай: 1-2 слоя на промпт
- Для нашего проекта: `Audio:` маркер перед стиль-тегом

### ⚠️ КРИТИЧНО: Lip-Sync — Синхронизация речи со сценарием

**Золотое правило лип-синка:** рот персонажа открывается ТОЛЬКО когда он говорит по сценарию. Молчит по сценарию = рот закрыт.

**Если персонаж ГОВОРИТ в сценарии:**
- ОБЯЗАТЕЛЬНО включи диалог в VEO промпт в формате `says: "текст реплики"`
- Это заставит VEO анимировать рот в нужный момент
- Пример: `The character says: "What is this?" while leaning forward.`
- Финальный звук потом заменяется на ElevenLabs — не важно, как VEO озвучит

**Если персонаж МОЛЧИТ в сценарии:**
- ОБЯЗАТЕЛЬНО используй глаголы БЕЗ речи: `watches silently`, `stares`, `listens`
- НЕ используй глаголы, провоцирующие движение рта: `reacts`, `responds`, `exclaims`
- При необходимости добавь: `mouth closed, no dialogue`

**Разбивка клипа по речи:**
- Если в одном клипе персонаж сначала молчит, потом говорит — разбей на два клипа или используй timestamp:
  ```
  [00:00-00:03] Character watches silently, mouth closed.
  [00:03-00:06] Character says: "What is this?" with surprise.
  ```

**Проверочный чек-лист (для каждого клипа):**
- [ ] Все реплики из сценария включены как `says: "..."` в промпт
- [ ] Молчащие персонажи не имеют речевых глаголов
- [ ] Если два персонажа в кадре — чётко указано, КТО говорит, а кто молчит

### 4. Style (СТИЛЬ)
Всегда завершать:
```
Smooth cinematic motion, 3D Pixar-style animation.
```

---

## НЕ описывай в промпте (для first+last)

Источник: [LTX Studio](https://ltx.studio/blog/veo-prompt-guide) —
*«Skip redescribing what's visible in your reference image.»*

| Не нужно | Почему | Что вместо |
|----------|--------|------------|
| Внешность персонажа | VEO видит на кадре | Только действие |
| Обстановку / интерьер | VEO видит на кадре | Ничего |
| Начальную позу | VEO видит first frame | Описывай переход |
| Конечную позу | VEO видит last frame | Описывай переход |
| Одежду, цвет | VEO видит на кадре | Ничего |

**Исключение:** если действие неочевидно из кадров, можно кратко уточнить контекст.

---

## Screenplay Fidelity (Верность сценарию)

Те же 7 правил, что в PROMPT_SPEC.md для NB Pro:

1. **Масштаб точно по тексту** — не преувеличивай
2. **Эмоциональная точность** — нюанс из сценария, не ярлык
3. **Действия буквально из сценария**
4. **Реквизит только из сценария**
5. **Не додумывай эмоции** — `smiles gently` запрещено если нет в тексте
6. **Сохраняй драматургическую функцию кадра**
7. **Тон и атмосфера из контекста сцены**

---

## Timestamp Prompting (продвинутая техника)

Источник: [LTX Studio](https://ltx.studio/blog/veo-prompt-guide)

Для сложных переходов можно разбить 8 секунд на сегменты:

```
[00:00-00:03] The character slowly turns the dial — static fills the air.
[00:03-00:06] A clear signal emerges. The character freezes, eyes widening.
[00:06-00:08] He grabs a pen and starts writing numbers. Audio: rhythmic beeping signal.
```

**Когда использовать:** когда в клипе несколько последовательных действий.
**Когда НЕ использовать:** простой одно-действийный переход (большинство наших клипов).

---

## Длительность клипа

| Действие | Рекомендация |
|----------|-------------|
| Простое (поворот, взгляд) | 4-5 сек |
| Среднее (встать + подойти) | 6 сек |
| Сложное (несколько действий) | 8 сек |

**Правило:** лучше короче и точнее, чем длиннее и размазаннее.

---

## Полный шаблон промпта

### Простой переход (1 действие):
```
[CAMERA MOVEMENT]. [ONE MAIN ACTION between frames]. Audio: [SFX/ambient]. Smooth cinematic motion, 3D Pixar-style animation.
```

Пример:
```
Slow push in. The character reaches for the tuning dial and turns it — static crackles, then a clear signal emerges. Audio: radio static transitioning to a rhythmic beeping signal. Smooth cinematic motion, 3D Pixar-style animation.
```

### Переход с двумя персонажами:
```
[CAMERA MOVEMENT]. [CHARACTER A ACTION]. [CHARACTER B REACTION]. Audio: [SFX/ambient]. Smooth cinematic motion, 3D Pixar-style animation.
```

Пример:
```
Static wide shot. The arriving character sets his backpack down and walks to the workbench. The character on the sofa doesn't move. Audio: footsteps on concrete, quiet garage ambience. Smooth cinematic motion, 3D Pixar-style animation.
```

### Переход с таймстемпами (сложный):
```
[00:00-00:03] [CAMERA + ACTION 1].
[00:03-00:06] [ACTION 2 + REACTION].
[00:06-00:08] [RESOLUTION].
Audio: [layered sound]. Smooth cinematic motion, 3D Pixar-style animation.
```

---

## Два варианта промпта (A/B)

Мы генерируем два варианта для каждого клипа. Правила:

- **Prompt A:** прямолинейный, короткий (40-60 слов)
- **Prompt B:** более детальный, с нюансами (60-80 слов)
- Оба должны описывать ОДНО И ТО ЖЕ действие, но разными словами
- НЕ менять суть действия между A и B — только формулировку

---

## Чего НИКОГДА не делать

| Ошибка | Пример | Почему |
|--------|--------|--------|
| Переописание кадров | `The character sits at the workbench` | VEO уже видит кадры |
| Описание внешности | `character in grey hoodie` | VEO видит на кадре |
| Описание интерьера | `wooden workbench, tools on wall` | VEO видит на кадре |
| Множественные действия | 5 действий за 6 секунд | Результат хаотичный |
| Нет камеры | пропуск camera movement | Камера непредсказуема |
| Нет аудио | пропуск Audio: | Упущенный контроль |
| Слова-преувеличения | `enormous`, `huge`, `massive` | Искажение масштаба |
| Додуманные эмоции | `smiles gently` (нет в сценарии) | Нарушение верности |
| Конфликтующие инструкции | `slow` + `quickly` в одном промпте | Модель путается |
| Абстрактные описания | `dramatic atmosphere` | Нет конкретики |
| Нет диалога, когда в сценарии есть | персонаж молча стоит, хотя говорит | Рот не двигается — рассинхрон с озвучкой |
| Диалог, которого нет в сценарии | `reacts`, `responds` у молчащего | Рот двигается без причины |

---

## Validation Checklist

- [ ] Камера: одно движение, отдельным предложением
- [ ] Действие: конкретные глаголы движения (reaches, turns, walks)
- [ ] НЕ описан интерьер/обстановка (VEO видит кадры)
- [ ] НЕ описана внешность персонажей
- [ ] Audio: хотя бы один звуковой слой
- [ ] Стиль: `Smooth cinematic motion, 3D Pixar-style animation.`
- [ ] Длина: 40-80 слов (без стиль-тега)
- [ ] Одно главное действие (не 5 за 6 секунд)
- [ ] Screenplay Fidelity: действие из сценария, не выдуманное
- [ ] Нет слов-преувеличений (enormous, huge...)
- [ ] Нет конфликтующих инструкций
- [ ] Prompt A и B описывают одно действие разными словами
- [ ] **Lip-Sync: реплики из сценария включены как `says: "..."`**
- [ ] **Lip-Sync: молчащие персонажи без речевых глаголов (`listens`, `watches silently`)**

---

## Advanced Techniques (v2.0)

Источники: [JSON Prompting Hacks](https://www.architjn.com/blog/json-prompting-veo3-hacks-tricks),
[GitHub Veo-3-Prompting-Guide](https://github.com/snubroot/Veo-3-Prompting-Guide),
[Invideo Guide](https://invideo.io/blog/google-veo-prompt-guide/),
[Skywork Cinematic Presets](https://skywork.ai/blog/veo-3-1-cinematic-presets-best-practices-storytelling/),
[Habr BotHub](https://habr.com/ru/companies/bothub/articles/943114/),
[Vertex AI Docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide),
[Medium mastering-veo-3](https://medium.com/@miguelivanov/mastering-veo-3-an-expert-guide-to-optimal-prompt-structure-and-cinematic-camera-control-693d01ae9f8b)

### 1. Force-Based Verbs (Физика движения)
Заменяй мягкие описания на глаголы с ощущением силы/веса:

| Плохо (ватно) | Хорошо (физика) |
|--------|---------|
| `moves toward` | `pushes forward` |
| `looks at` | `snaps head toward` |
| `picks up` | `snatches up` |
| `walks in` | `steps inside` |
| `turns around` | `pivots sharply` |

Мягкие глаголы → «ватное», невесомое движение.
Силовые глаголы → модель добавляет вес, инерцию, физику.

### 2. Micro-Expression Control
Для эмоциональных крупных планов — управляй микровыражениями:
- `eyes narrow slightly, furrow between brows`
- `brief pause before speaking, head tilts`
- `slight smile forms at corner of mouth`

Убирает «модельное лицо» и создаёт живую мимику.

### 3. Clip Chaining (Сцепка клипов)
Для длинных сцен из нескольких клипов:
1. Генерируй Clip 1 (Frame A → Frame B)
2. Последний кадр Clip 1 = первый кадр Clip 2
3. Генерируй Clip 2 (Frame B → Frame C)
4. Склеивай в таймлайне

Сохраняет позицию камеры, освещение, идентичность персонажа.

### 4. Lens Selection (Фокусное расстояние)
VEO понимает фокусное расстояние:
- `16mm lens` — расширяет пространство, делает сцену масштабнее
- `35mm lens` — естественный, разговорный фрейминг
- `85mm lens` — сжимает фон, интимный крупный план

Для нашего проекта:
- Гараж: `35mm` (естественный средний план)
- Лицо крупно: `85mm` (портрет)
- Общий план: `16mm` или `24mm`

### 5. Physical Light Source Naming
Вместо `warm lighting` — называй источник:
- `daylight from the garage door` — а не `bright light`
- `single desk lamp casting shadows` — а не `dim lighting`
- `sunset glow through the window` — а не `warm evening`

Физический источник стабилизирует тени и убирает визуальные артефакты.

### 6. Anti-Plastic Rendering (против «пластикового» вида)
Для Pixar-стиля не так критично, но полезно:
- `subtle fabric texture visible`
- `dust particles floating in light`
- `natural color variation, no gloss`

### 7. Single Dominant Action Rule
**Одно главное действие на клип.** Если нужно «идёт + говорит + жестикулирует» — разбивай на отдельные клипы.

Совмещение нескольких действий → нестабильное движение, размытый результат.

### 8. Emotional Progression (This-Then-That)
Для эмоциональных переходов:
```
Character starts bored and disengaged, then freezes with surprise, finally leans forward with intense curiosity.
```
Три фазы: начало → перелом → финал. Модель выстраивает арку.

### 9. Count Abstraction
Вместо точных чисел — диапазоны:
- `a few tools` вместо `five tools`
- `some dust particles` вместо `twelve particles`

Точные числа (>5) → дубликаты или слияние объектов.

### 10. Negative Prompting
В конец промпта (перед стилем):
```
No text, no subtitles, no warping, no morphing.
```

Добавляй только при наличии конкретных проблем. НЕ спамь заранее.

**Формат negative prompt для API**: описывать существительными, НЕ инструкциями.
- Хорошо: `cartoon, drawing, blur, text, ghosting, distorted faces`
- Плохо: ~~`no walls`~~, ~~`don't show faces`~~

### 11. Transformer Attention Decay (Приоритет первых токенов)

**Критическое открытие:** Первые ~10% слов промпта получают ~45% внимания модели.

Иерархия приоритетов (что ставить раньше):
1. **Tier 1** (ПЕРВЫМ): Camera system, lens, aspect ratio — фундамент кадра
2. **Tier 2**: Subject identity — ключевые черты персонажа
3. **Tier 3**: Action, setting, mood
4. **Tier 4** (последним): Audio, constraints, negatives

**Для нас**: стиль `3D Pixar-style animation` и камеру ставить в НАЧАЛО промпта, а не в конец.

### 12. Focus Techniques (Динамический фокус)

VEO понимает кинематографические техники фокуса:
- **Rack Focus**: `rack focus from foreground tools to character's face` — смена фокуса между объектами
- **Shallow DOF**: `shallow depth of field, f/2.8, background bokeh` — размытый фон
- **Deep Focus**: `deep focus, everything sharp` — всё в фокусе
- **Anamorphic Bokeh**: `anamorphic bokeh with oval highlights` — стилизация

Для нашего проекта: `shallow DOF` для крупных планов, `deep focus` для общих.

### 13. Camera Position Marker

Уникальный синтаксис для фиксации точки камеры:
```
The garage door opens revealing the workbench (that's where the camera is).
Character walks toward camera from the sofa.
```

Маркер `(that's where the camera is)` фиксирует POV без стандартных camera terms.
Работает лучше, чем абстрактные `POV shot` или `first-person view`.

### 14. Match Cut & Cinematic Transitions

VEO понимает кинематографические термины монтажа внутри клипа:
- **Match Cut**: `match cut from spinning wheel to clock face` — переход по форме/цвету
- **Whip Pan**: `whip pan right` — хлёсткий поворот (резать на пике размытия)
- **Jump Cut**: `sharp jump cuts between poses` — резкие смены

### 15. Dialogue Syntax (Предотвращение субтитров + Lip-Sync)

**Критический трюк:** формат диалога влияет на субтитры.
- С двоеточием: `Character says: "Hello"` → **БЕЗ субтитров**
- Без двоеточия: `Character says "Hello"` → модель может наложить текст

Для упорных случаев: `(no subtitles!)` после реплики.
Оптимальная длина диалога: **5-8 секунд** (меньше = тишина, больше = торопливая речь).

**Lip-Sync обязательные правила:**
- Реплика из сценария → `says: "реплика"` в промпте. Рот ДОЛЖЕН двигаться.
- Молчание в сценарии → `watches silently` / `listens` / `mouth closed`. Рот НЕ двигается.
- Два персонажа в кадре: один говорит, другой молчит → указать явно: `Character A says: "..." while Character B listens silently.`
- VEO-аудио потом заменяется на ElevenLabs — но анимация рта из VEO сохраняется.

### 16. Color Science & Film Stock

VEO понимает профессиональную цветокоррекцию:
- **Film stock**: `Kodachrome-esque`, `bleach-bypass`
- **Color grading**: `teal/orange blockbuster palette`, `pastel film palette`
- **Color temperature**: `3200K tungsten`, `5600K daylight`
- **Grain**: `film grain 400 ISO`, `halation`

Для нашего Pixar-стиля: `warm saturated palette, soft bloom, no film grain`

### 17. Lighting Ratios (Количественный контроль)

Вместо абстрактного `cinematic lighting`:
```
Key: soft window light from left at 3/4 angle;
Fill: minimal ambient bounce;
3:1 key-to-fill ratio
```

| Ratio | Эффект |
|-------|--------|
| 2:1 | Мягкий, friendly (подходит для Pixar) |
| 3:1 | Стандартный кинематограф |
| 4:1+ | Драматичный, noir |

### 18. Visual Storytelling (Без абстракций)

Описывай осязаемые визуальные детали вместо абстрактных эмоций:
- Плохо: `The scene conveys loneliness`
- Хорошо: `Empty chair across the table; character avoids eye contact; long pause before sipping`

Модель — статистическая система. Она не понимает «одиночество», но точно визуализирует пустой стул.

### 19. Causal Chains (Причина → Реакция)

Описывай причинно-следственные цепочки:
```
Character hears noise → turns head sharply → eyes widen with recognition
```

VEO хорошо обрабатывает `trigger → physical reaction → emotional response`.

### 20. Optimal Prompt Length

По данным fal.ai и community:
- **< 100 символов** — слишком дженерик, модель додумывает
- **150-300 символов** — оптимальный диапазон
- **> 400 символов** — непредсказуемая приоритизация, часть элементов игнорируется

---

## Technical Parameters (API / Vertex AI)

> Для справки — эти параметры доступны через API, НЕ через Flow UI

| Параметр | Значение | Описание |
|----------|---------|----------|
| `aspectRatio` | `"16:9"`, `"9:16"` | Соотношение сторон |
| `resolution` | `"720p"`, `"1080p"`, `"4k"` | 1080p/4K только при 8 сек |
| `durationSeconds` | `4`, `6`, `8` | Длительность клипа |
| `sampleCount` | 1-4 | Количество вариантов |
| `seed` | 0-4,294,967,295 | Для воспроизводимости (не гарантирует) |
| `enhancePrompt` | `true`/`false` | Автоперезапись промпта через Gemini |
| `generateAudio` | `true`/`false` | Генерация звука |
| `negativePrompt` | текст | Что НЕ генерировать (существительные!) |
| `referenceImages` | до 3 | Только `"asset"` type для VEO 3.1 |
| `compressionQuality` | `"optimized"`/`"lossless"` | Качество сжатия |

### Модели VEO 3.1

| Модель | Назначение |
|--------|-----------|
| `veo-3.1-generate-001` | Production (качество) |
| `veo-3.1-fast-generate-001` | Production (скорость) ← мы используем |
| `veo-3.1-generate-preview` | Preview (больше фич: 4K, reference images) |
| `veo-3.1-fast-generate-preview` | Preview (скорость + больше фич) |

### Video Extension
- Каждый hop добавляет **7 секунд**
- До **20 hops** = до **148 секунд** макс
- Только 720p при extension
- Принимает только VEO-generated MP4, 24fps

---

## Проблемы текущих промптов (для будущего исправления)

### Системные проблемы (все 14 клипов):
1. **Нет Camera Movement** — 12 из 14 промптов не указывают движение камеры
2. **Нет Audio** — ни один промпт не управляет звуком
3. **Переописание кадров** — большинство описывают то, что VEO уже видит

### Конкретные нарушения:
- **S02_B**: `large antenna` → должно быть `makeshift antenna`
- **S03_A**: `smiles gently` → нет в сценарии (папа просто стоит)
- **S02_C**: слишком много действий для 5 секунд (4 разных персонажа делают 4 разных действия)
- **S01_B, S04_B**: хорошие промпты — конкретные действия, разумная длина

---

## Источники

### Официальные Google
- [Google Cloud: Ultimate Prompting Guide for VEO 3.1](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1)
- [Google DeepMind: VEO Prompt Guide](https://deepmind.google/models/veo/prompt-guide/)
- [Vertex AI: Video Generation API Reference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/veo-video-generation)
- [Vertex AI: VEO Prompt Guide](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/video-gen-prompt-guide)
- [Vertex AI: Reference Images Guide](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/use-reference-images-to-guide-video-generation)
- [Vertex AI: Video Extension](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/extend-a-veo-video)
- [Google Developers: Introducing VEO 3.1](https://developers.googleblog.com/introducing-veo-3-1-and-new-creative-capabilities-in-the-gemini-api/)
- [Google: 5 Tips for Flow](https://blog.google/innovation-and-ai/products/flow-video-tips/)

### Руководства и гайды
- [LTX Studio: VEO 3.1 Prompt Guide](https://ltx.studio/blog/veo-prompt-guide)
- [Visla: How to Prompt VEO 3 and 3.1](https://www.visla.us/blog/guides/how-to-prompt-veo-3-and-veo-3-1/)
- [fal.ai: VEO 3.1 Prompt Guide](https://fal.ai/learn/devs/veo3-prompt-guide-master-google-video-generation)
- [Replicate: How to Prompt VEO 3.1](https://replicate.com/blog/veo-3-1)
- [Imagine.art: VEO 3.1 Prompt Guide](https://www.imagine.art/blogs/veo-3-1-prompt-guide)
- [Invideo: VEO 3.1 Prompting Guide](https://invideo.io/blog/google-veo-prompt-guide/)
- [DreamHost: VEO 3.1 Prompt Guide](https://www.dreamhost.com/blog/veo-3-1-prompt-guide/)

### Продвинутые техники
- [JSON Prompting: Hacks & Tricks (architjn)](https://www.architjn.com/blog/json-prompting-veo3-hacks-tricks)
- [JSON Prompting: Format That Beats Generic (architjn)](https://www.architjn.com/blog/veo-3-json-prompt-format-beats-generic-prompts)
- [atlabs.ai: JSON vs Spatial vs YAML Comparison](https://www.atlabs.ai/blog/json-prompting-veo3)
- [GitHub: Veo-3-Prompting-Guide (snubroot)](https://github.com/snubroot/Veo-3-Prompting-Guide)
- [Skywork: Multi-Shot Consistency](https://skywork.ai/blog/multi-prompt-multi-shot-consistency-veo-3-1-best-practices/)
- [Skywork: 26 Essential Prompt Patterns](https://skywork.ai/blog/veo-3-1-prompt-patterns-shot-lists-camera-moves-lighting-cues/)
- [Skywork: Cinematic Presets](https://skywork.ai/blog/veo-3-1-cinematic-presets-best-practices-storytelling/)
- [Skywork: Lighting and Camera Tricks](https://skywork.ai/blog/ai-video/veo-3-1-lighting-and-camera-prompt-tricks/)
- [Skywork: Scene Extension Guide](https://skywork.ai/blog/how-to-extend-veo-3-1-scene-guide/)
- [Medium: Mastering VEO 3 Prompt Structure](https://medium.com/@miguelivanov/mastering-veo-3-an-expert-guide-to-optimal-prompt-structure-and-cinematic-camera-control-693d01ae9f8b)
- [Medium: Controlling Video AI — Runway/Kling/VEO/Sora](https://medium.com/@creativeaininja/how-to-actually-control-next-gen-video-ai-runway-kling-veo-and-sora-prompting-strategies-92ef0055658b)
- [Scenario: Spatial Prompting for Videos](https://help.scenario.com/en/articles/spatial-prompting-for-videos-generation/)
- [DEV.to: JSON Prompting Best Practices](https://dev.to/yigit-konur/best-practices-of-json-prompting-for-video-generation-models-examples-for-veo-31-1mc0)
- [Prompt Helper: Consistent Characters](https://prompt-helper.com/consistent-characters-in-veo-3-your-ultimate-guide-to-flawless-ai-video-scenes/)

### Русскоязычные
- [Хабр: Как пользоваться Veo 3 (BotHub)](https://habr.com/ru/companies/bothub/articles/943114/)
- [Хабр: Промпты для Veo 3 (BotHub)](https://habr.com/ru/companies/bothub/articles/942346/)
