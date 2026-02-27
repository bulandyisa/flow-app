# Nano Banana Pro — Prompt Specification v3.0

> Обновлено на основе официальных рекомендаций Google, гайдов по identity locking,
> продвинутых community-техник и лучших практик (2025-2026).
> 30+ источников исследовано.

---

## Core Principle

NB Pro — это «думающая» модель (Thinking Process). Она понимает намерение и композицию,
а не просто ключевые слова. Пиши промпт как инструкцию для режиссёра-аниматора,
а не как теги для Midjourney.

**Три источника информации:**

| Источник | Что контролирует |
|----------|-----------------|
| Референс-фото персонажа | Лицо, тело, одежда, пропорции |
| Референс-фото локации | Интерьер, мебель, освещение, декор |
| Текст промпта | Действие, эмоция, ракурс камеры, стиль |

**Золотое правило: текст НЕ ДОЛЖЕН описывать то, что уже есть на референсе.**
Когда текст и фото конфликтуют — модель «теряется» и результат нестабилен.

---

## Identity Locking (Закрепление персонажа)

Самая важная техника для консистентности. Источники:
- [Google Official](https://blog.google/products/gemini/prompting-tips-nano-banana-pro/)
- [Dev.to Guide](https://dev.to/googleai/nano-banana-pro-prompting-guide-strategies-1h9n)
- [Apiyi Face Consistency Guide](https://help.apiyi.com/en/nano-banana-pro-face-consistency-guide-en.html)

### Правила:

1. **Identity tag в первых 10 словах промпта.**
   Модель «лочит» идентичность рано — чем раньше упомянуть персонажа, тем точнее результат.

   **Плохо:** `In a warm garage, on a workbench, the exact character from Image 1...`
   **Хорошо:** `The exact character from Image 1 sits at a workbench...`

2. **Формулировка identity lock:**
   `The exact character from Image N, preserving identical facial features and proportions`
   — для первого упоминания персонажа в промпте.

   Сокращённо для второго/третьего: `The exact character from Image N`

3. **Один персонаж = один основной референс.** Модель лучше работает с одним чётким full-body снимком.
   Для максимальной консистентности можно добавить 2-3 ракурса (фронт + 3/4 + профиль),
   но это занимает слоты ингредиентов. NB Pro поддерживает до 14 референсов, но оптимально 6 или меньше.

4. **Меняй только одну переменную за раз:**
   Если нужен другой ракурс — не меняй одновременно позу и эмоцию.
   Если нужна другая эмоция — не меняй одновременно ракурс и освещение.

---

## Референсные изображения

Источник: [Apiyi Guide](https://help.apiyi.com/en/nano-banana-pro-face-consistency-guide-en.html)

### Требования к качеству:
- **Разрешение:** минимум 1024×1024, идеально 2048+ (мы уже апскейлили)
- **Освещение:** ровное, фронтальное, без жёстких теней
- **Фон:** чистый, без отвлекающих элементов (наши на белом фоне — идеально)
- **Лицо:** полностью видно, без перекрытий

### Сколько ингредиентов:
| Тип сцены | Ингредиенты | Формула |
|-----------|-------------|---------|
| Крупный план, 1 персонаж | 2 | 1 char + 1 location |
| Средний план, 1 персонаж | 2 | 1 char + 1 location |
| Средний план, 2 персонажа | 3 | 2 char + 1 location |
| Групповая сцена, 3 персонажа | 3-4 | 3 char + (0-1 location) |

**Max 4 ингредиента.** Больше — нестабильный результат.
При 3 персонажах можно убрать локацию и описать setting в тексте минимально.

---

## Структура промпта (5 компонентов)

Источники: [Higgsfield](https://higgsfield.ai/nano-banana-pro-prompt-guide), [Radical Curiosity](https://www.radicalcuriosity.xyz/p/how-to-create-an-effective-prompt)

### Формула:
```
[IDENTITY + ACTION] → [LOCATION] → [CAMERA + LIGHTING] → [STYLE]
```

### 1. Identity + Action (КТО + ЧТО ДЕЛАЕТ)
- Начинай с персонажа: `The exact character from Image 1, preserving identical facial features and proportions,`
- Одно главное действие: `sits at a workbench, hand on the tuning dial of a radio receiver`
- Одна эмоция: `with a surprised expression`

### 2. Location (ГДЕ)
- `Use Image N as the exact background location.`
- Если нет ингредиента-локации: можно кратко обозначить setting: `Inside a garage.`

### 3. Camera (КАК СНЯТО)

Используй терминологию кинематографа — NB Pro её отлично понимает:

| Ракурс | Когда |
|--------|-------|
| `Extreme close-up` | Деталь: рука на ручке, глаза |
| `Close-up` | Лицо, эмоция |
| `Medium close-up` | Грудь + лицо |
| `Medium shot` | Поясной план — основной рабочий ракурс |
| `Medium wide shot` | Персонаж + окружение |
| `Wide shot` / `Establishing shot` | Полная локация + персонажи |
| `Over-the-shoulder shot` | Через плечо одного на другого |

**Опционально (сильно повышает контроль):**
- Фокусное расстояние: `85mm lens` (портрет), `35mm lens` (средний), `24mm lens` (широкий)
- Глубина резкости: `shallow depth of field` (размытый фон)
- Перспектива: `eye-level`, `low angle`, `high angle`, `bird's eye view`

### 4. Lighting (СВЕТ)
Один описатор, согласованный по всей сцене:
- `bright daylight` — дневные сцены
- `warm evening light` — вечер, гараж
- `dramatic side lighting` — напряжённые моменты
- `soft diffused light` — спокойные сцены
- `night atmosphere, single lamp` — ночь

### 5. Style (СТИЛЬ)
Для NB Pro (изображений) завершать:
```
3D Pixar-style, family-friendly, cinematic.
```
Для VEO (видео) завершать:
```
3D Pixar-style animation, family-friendly.
```
**Важно:** слово `animation` только для VEO промптов, НЕ для NB изображений.

---

## Chain-of-Thought для сложных сцен

Источник: [Dev.to Guide](https://dev.to/googleai/nano-banana-pro-prompting-guide-strategies-1h9n)

Для сцен с 2-3 персонажами используй пошаговую логику композиции:

```
First, the exact character from Image 1 stands in the doorway, just arriving.
Then, the exact character from Image 2 lies on a sofa, staring at the ceiling.
The scene is framed as a wide shot showing both characters.
Use Image 3 as the exact background location.
Bright daylight, 35mm lens. 3D Pixar-style animation, family-friendly, cinematic.
```

Слова `First`, `Then`, `Finally` помогают модели выстроить элементы последовательно,
а не пытаться обработать всё одновременно.

---

## NEVER Include (Hard Rules)

### 1. Внешность персонажа
- Одежда: hoodie, shirt, jeans, shoes, jacket, striped...
- Физика: hair color, eye color, height, body type
- Возраст/пол: boy, girl, child, young, old, he, she

### 2. Описание интерьера
- Расположение мебели: "sofa on the right", "workbench on the left"
- Детали стен/пола: "plain walls", "wooden floor"
- Объекты-декорации: "pegboard with tools", "bicycle near the wall"

### 3. Пространственное позиционирование
- "on the left side", "on the right side", "in the center"
- Модель сама расположит персонажей на основе action anchors

---

## Action Anchors (разрешённые пространственные ссылки)

Якоря действия — ГДЕ персонаж выполняет действие (не описание мебели):

| OK (действие) | НЕ OK (описание) |
|----------------|-------------------|
| `sits at the workbench` | `The workbench is on the left` |
| `stands in the doorway` | `The door is open` |
| `lies on the sofa` | `sofa visible on the right` |
| `leans over a desk` | `a desk with papers and books` |

---

## Props Rule (Реквизит)

**Упоминай реквизит ТОЛЬКО если персонаж с ним взаимодействует:**
- `hand on the tuning dial of a radio` — OK
- `writing numbers in a notepad` — OK
- `a radio receiver on the bench` — НЕ OK (просто стоит)

**Исключение:** Один ключевой сюжетный предмет можно упомянуть без взаимодействия,
если он центральный для сцены (напр. `A radio receiver nearby.`)

---

## First / Mid / Last Frame Strategy

- **first**: начальная композиция клипа
- **mid** (опциональный): промежуточная точка — для сложных переходов
- **last**: конечная композиция — что изменилось

### Mid Frame — средний кадр

Mid frame **опционален**. Используй его когда:
- Переход из first в last слишком сложный для одного VEO-клипа (> 2 действий)
- Нужна промежуточная точка для VEO режима «по образцам» (3 референса)
- Есть явная «середина» сценарного действия

**Цепочка консистентности:**
```
first → mid (ингредиент: first) → last (ингредиент: mid)
```

- При генерации mid: принятый first добавляется как ингредиент + `Maintain exact visual continuity with Image N.`
- При генерации last (если mid есть): принятый mid добавляется как ингредиент + `Maintain exact visual continuity with Image N.`
- При генерации last (если mid нет): принятый first добавляется как ингредиент (как раньше)

**Промпт mid:** в JSON-конфиге поле `nano_banana_prompt_mid`. Если null или отсутствует — mid пропускается.

### Delta Rule
Разница между соседними кадрами — ОДНО чёткое изменение:
- Позиция: стоял → сел
- Направление: смотрел на приёмник → повернулся к камере
- Эмоция: скучающий → заинтригованный
- Состояние объекта: радио тихо → индикатор горит

**80% промпта одинаковы, 20% — дельта.**

При трёх кадрах:
- first↔mid: 80% общего, 20% дельта
- mid↔last: 80% общего, 20% дельта
- first↔last может отличаться сильнее (суммарная дельта двух шагов)

### nb_last / nb_mid с scene reference
Когда принятый кадр-предшественник добавлен как ингредиент, в промпте указать:
`Maintain exact visual continuity with Image N.`

---

## Multi-Round Refinement (Итеративное улучшение)

Источник: [Apiyi Guide](https://help.apiyi.com/en/nano-banana-pro-face-consistency-guide-en.html)

Подход «от общего к частному»:
1. **Round 1:** Референс + промпт → 4 варианта. Выбрать лучший
2. **Round 2:** Лучший вариант как дополнительный ингредиент + уточнённый промпт → 4 варианта
3. **Round 3:** Финальная корректировка деталей

**NB Pro не может достичь 100% консистентности лиц между генерациями.**
Референсные фото — решающий фактор, важнее промпта.

---

## Negative Instructions (Что исключить)

Источники: [Sider](https://sider.ai/blog/ai-image/how-to-write-negative-prompts-in-nano-banana-a-practical-guide),
[GLB GPT Ultimate Guide](https://www.glbgpt.com/hub/the-ultimate-guide-of-nano-banana-pro-prompt/)

NB Pro не имеет отдельного поля negative prompt, но понимает запреты прямо в тексте.

### Формат:
Добавлять в конец промпта, **перед** стиль-тегом:
```
Avoid: [конкретная проблема]. No [артефакт].
```

### Стандартный блок для нашего проекта:
```
No text, no subtitles, no watermarks.
```

### Когда добавлять расширенные запреты:
- Если в предыдущем варианте были артефакты → `No distorted hands, no extra fingers.`
- Если модель добавляет лишних людей → `Only the characters described, no additional people.`
- Если текст/надписи появляются → `No text, no labels, no signs.`

**Правило: не спамь запретами заранее.** Добавляй только после того, как увидел проблему.
10-20 слов запретов максимум.

---

## Storyboard Consistency (Между кадрами)

Источники: [Apiyi Storyboard Guide](https://help.apiyi.com/nano-banana-pro-storyboard-generation-guide-en.html),
[Max Woolf](https://minimaxir.com/2025/11/nano-banana-prompts/)

### Принципы анимационной серии:

1. **Генерируй по порядку сценария.** Первый кадр устанавливает baseline — все следующие должны на него ссылаться.

2. **Между кадрами меняй ТОЛЬКО одну переменную:**
   - Действие / поза
   - Ракурс камеры
   - Эмоция
   Не меняй одновременно позу + ракурс + эмоцию — результат будет нестабильным.

3. **Consistency keywords** — при описании персонажа в серии кадров добавляй:
   `same face, same appearance as in all previous shots`
   (Это кроме identity lock через Image N — дополнительный якорь.)

4. **Реинтродукция референса каждые 5-8 кадров.**
   Если генерируешь длинную серию — после 5+ кадров модель может «дрейфовать».
   Повторно добавь оригинальный референс как ингредиент для сброса.

5. **Фильтрация > перегенерация.** Генерируй 4 варианта, выбирай лучший.
   Не пытайся добиться идеала с первого раза — это работа с вероятностями.

---

## Advanced Techniques

Источники: [Max Woolf](https://minimaxir.com/2025/11/nano-banana-prompts/),
[Flux AI](https://flux-ai.io/blog/detail/Nano-Banana-Pro-Guide-10-Best-Image-Prompts-for-Expert-Use-Cases-551f2895890a/),
[Replicate](https://replicate.com/blog/how-to-prompt-nano-banana-pro)

### 1. Compositional Buzzwords (контекстные якоря)
Вместо детального описания композиции — одно «волшебное слово»:
- `Pulitzer-prize-winning photo` → rule of thirds, негативное пространство
- `Cinematic still from Pixar film` → профессиональная компоновка
- `Film storyboard panel` → чёткая драматургическая композиция

Модель знает, как выглядят эти жанры, и применяет их принципы автоматически.

### 2. Imperfection Specification (для реализма)
Если нужен реализм — добавляй конкретные несовершенства:
- `dust particles floating in sunlight` — пылинки
- `slight lens flare from the window` — блик
- `a scratch on the workbench surface` — царапина

Не пиши `make it imperfect` — будь конкретен.

### 3. Edit, Don't Re-roll
Если вариант на 80% хороший — не перегенерируй с нуля.
Добавь его как ингредиент и попроси конкретную правку:
`Keep everything exactly the same, but change the character's expression to surprised.`

### 4. One-Variable Iteration Rule
При доработке промпта — **меняй только одну вещь за раз:**
- Итерация 1: поменял action → сгенерировал
- Итерация 2: поменял camera → сгенерировал
- НЕ: поменял action + camera + lighting одновременно

Это позволяет понять, какое изменение дало результат.

### 5. Micro-Detail для ключевых кадров
Для крупных планов — добавляй микро-детали:
- `catchlights visible in eyes`
- `individual strands of hair`
- `fabric texture visible on sleeves`

Модель хорошо это обрабатывает на close-up.

### 6. Context Injection (Контекст «Зачем»)

Вместо перечисления деталей — дай контекст назначения:
- Плохо: `A garage with warm lighting, shallow depth of field, perfect composition`
- Хорошо: `A cinematic still from a Pixar animated short film about a boy and his radio`

Модель сама выведет профессиональное освещение, композицию, глубину резкости.
Контекст «зачем» сильнее, чем перечисление «что».

### 7. Prompt Weighting (Веса элементов)

NB Pro поддерживает числовые модификаторы для приоритизации:
- `(sharp focus:1.3)` — усилить резкость
- `(background blur:0.8)` — ослабить фон
- `(warm lighting:1.2)` — усилить тёплый свет

Использовать осторожно — не все провайдеры API поддерживают синтаксис.

### 8. Viewpoint Lock (Стабилизация ракурса)

Для серии кадров одного персонажа — фиксируй ракурс:
`3/4 view, mid-shot, eye-level camera angle`

**Менять ракурс = менять переменную.** Изменение угла камеры —
одна из главных причин «дрейфа» лица между генерациями.

### 9. Multi-Character Identity Separation

Для сцен с 2+ персонажами — используй цвет одежды как идентификатор:
```
First, the character in the grey hoodie from Image 1 [ACTION].
Then, the character in the black hoodie from Image 2 [ACTION].
```

Это помогает модели не путать, какой референс к какому персонажу относится.
Дополнительно: `only have one of each character in each image` предотвращает дубликаты.

### 10. Материальность (Texture Descriptors)

Описание текстур усиливает 3D-эффект Pixar-стиля:
- `subsurface scattering on skin` — подповерхностное рассеивание
- `soft ambient occlusion` — мягкие тени в углублениях
- `warm saturated color palette` — насыщенная палитра
- `smooth motion-ready design` — готовность к анимации

Для нашего проекта полезно добавлять в стиль-тег:
`3D Pixar-style animation, subsurface scattering, soft ambient occlusion, family-friendly, cinematic.`

### 11. Negative Prompt Best Practices (Расширенные)

**Baseline (всегда):** `No text, no subtitles, no watermarks.`

**По проблемам (добавлять только после обнаружения):**
- Руки/пальцы: `Avoid: distorted hands, extra fingers, deformed hands`
- Лицо: `Avoid: fat face, round puffy cheeks, waxy appearance, plastic skin`
- Фон: `Avoid: cluttered background, distracting elements`
- Артефакты: `Avoid: ghosting, tiling, low quality, grain`

**Правило:** 10-20 токенов негативов максимум. Длинные списки ослабляют эффект.

### 12. NB Pro не поддерживает Seed

**Критически важно:** NB Pro не имеет параметра seed для воспроизводимости.

4 альтернативы для консистентности (по убыванию эффективности):
1. **Reference images** — 80-90% консистентности (наш основной метод)
2. **Multi-turn dialogue editing** — 70-85% (уточнение через диалог)
3. **Detailed character description** — 60-70% (только текст, без референсов)
4. **External tool pipeline** — 95%+ (генерация через SD → использование как NB Pro референс)

---

## Полный шаблон промпта

### Одиночный персонаж:
```
The exact character from Image 1, preserving identical facial features and proportions, [ACTION + EMOTION]. [OPTIONAL: key prop interaction]. Use Image 2 as the exact background location. [CAMERA ANGLE], [FOCAL LENGTH optional], [LIGHTING]. 3D Pixar-style animation, family-friendly, cinematic.
```

### Два персонажа:
```
First, the exact character from Image 1, preserving identical facial features, [ACTION].
Then, the exact character from Image 2 [ACTION + EMOTION].
Use Image 3 as the exact background location.
[CAMERA ANGLE], [LIGHTING]. 3D Pixar-style animation, family-friendly, cinematic.
```

### Три персонажа:
```
First, the exact character from Image 1 [ACTION].
Then, the exact character from Image 2 [ACTION].
Finally, the exact character from Image 3 [ACTION].
Use Image 4 as the exact background location.
[CAMERA ANGLE], [LIGHTING]. 3D Pixar-style animation, family-friendly, cinematic.
```

---

## Validation Checklist (автоматизирован в flow_bot.py)

- [ ] Нет слов-описаний внешности (hoodie, shirt, striped...)
- [ ] Нет возраста/пола (boy, girl, young, old, he, she)
- [ ] Нет пространственных указаний (left side, right side, center)
- [ ] Нет описания интерьера (plain walls, sofa visible...)
- [ ] Identity lock: `exact character from Image N` (в первых 10 словах)
- [ ] Локация: `Use Image N as the exact background location`
- [ ] Камера: один ракурс из списка
- [ ] Свет: один описатор
- [ ] Стиль: `3D Pixar-style animation, family-friendly, cinematic.`
- [ ] Длина: до 60-80 слов (без стиль-тега)
- [ ] First/last: 80% общего, 20% дельта
- [ ] Chain-of-thought (`First... Then... Finally...`) для 2+ персонажей

---

## Screenplay Fidelity (Верность сценарию) — v3.0

Промпт — это **перевод** сценария в визуальную инструкцию, а НЕ пересказ и НЕ интерпретация.

### Принцип: «Переводи, не приукрашивай»

Каждый промпт должен быть обратно прослеживаем до конкретных строк сценария.
Если деталь есть в промпте, но её нет в сценарии — это ошибка.

### 7 правил верности

**1. Масштаб и пропорции — точно по тексту**
Сценарий: *«конструкция из палок, проволоки и скотча. Еле протискивается в дверь»*
- Плохо: `enormous homemade antenna` — модель рисует гротеск
- Хорошо: `a makeshift antenna of sticks, wire, and duct tape, barely fitting through the doorway`
Правило: используй те же определения масштаба, что в сценарии. Если сценарий не говорит «огромный» — не пиши «enormous».

**2. Эмоциональная точность — передавай нюанс, а не ярлык**
Сценарий: *«Даже Тако чувствует — что-то не так»*
- Плохо: `looking quiet` — слишком нейтрально
- Хорошо: `subdued, sensing something is wrong`
Правило: эмоция в промпте должна совпадать по интенсивности и оттенку со сценарием.

**3. Действия — из сценария, не выдуманные**
Сценарий: *«Проводит пальцем по плате — на пальце пыль»*
- Это конкретное действие → переноси как есть: `runs a finger across a circuit board, looks at dust on fingertip`
Сценарий: *«Переворачивается на бок, лицом к стене»*
- Плохо: `turns away, back to the others` — потеряна конкретика
- Хорошо: `rolls over on his side, facing the wall`
Правило: если сценарий описывает конкретное физическое действие, переноси его буквально.

**4. Реквизит — только упомянутый в сценарии**
Сценарий Сцены 5: *«старый бумажный атлас с полки»*
- OK: `an old paper atlas` — упомянут в сценарии
- НЕ OK: `a glowing map` — фантазия
Правило: не добавляй реквизит, которого нет в сценарии. Не убирай реквизит, который в сценарии есть.

**5. Атмосфера и тон — из контекста сцены**
Сцена 2: Амин апатичен, гараж в запустении, пыль. Тон: **вялость, стагнация**.
Сцена 5: Амин «включается». Тон: **пробуждение, переломный момент**.
Правило: промпт должен отражать тональную арку сцены, а не быть нейтральным.

**6. Не додумывай то, чего нет**
Сценарий: *«Папа не заходит. Не спрашивает. Стоит секунду.»*
- Плохо: `smiles gently` — сценарий НЕ говорит, что он улыбается. Он просто стоит.
- Хорошо: `pauses at the doorway, watching silently`
Правило: если сценарий не описывает эмоцию — используй нейтральную. Не проецируй.

**7. Сохраняй драматургическую функцию кадра**
Каждый клип несёт функцию в истории:
- S02_A: **экспозиция** — Амин апатичен, Карим пытается расшевелить
- S02_B: **комическая вставка** — Тако приносит антенну (но это НЕ гэг — он действительно старался)
- S02_C: **эмоциональный удар** — даже Тако понимает, что с Амином что-то не так
- S05_B: **поворотный пункт** — Амин впервые за дни проявляет интерес
- S05_D: **кульминация сцены** — Амин уходит другим человеком

Правило: промпт должен визуально служить этой функции. Не сглаживай конфликт, не добавляй комедию где её нет.

### Процесс: Сценарий → Промпт

1. **Найди строки сценария** для данного клипа (по `scene_description_ru`)
2. **Выпиши ключевые элементы:**
   - Кто в кадре
   - Что конкретно делает (физические действия из текста)
   - Какая эмоция (из контекста, НЕ выдуманная)
   - Какой реквизит задействован
   - Время суток / освещение
3. **Сформулируй промпт** по шаблону из PROMPT_SPEC
4. **Проверь обратную прослеживаемость:** каждое слово в промпте должно быть обосновано сценарием

### Чего НИКОГДА не делать:

| Ошибка | Пример | Почему опасно |
|--------|--------|---------------|
| Преувеличение масштаба | `enormous`, `huge`, `massive` (если нет в сценарии) | Модель интерпретирует буквально |
| Додумывание эмоций | `smiles gently` (когда нет в тексте) | Меняет характер персонажа |
| Добавление реквизита | `glowing map`, `colorful wires` | Противоречит референсам |
| Пересказ вместо перевода | длинные описания атмосферы | Шум для модели |
| Игнорирование конкретики | `turns away` вместо `rolls on his side facing the wall` | Потеря уникальности кадра |

---

## Источники

### Официальные Google
- [Google Official: 7 Tips for Nano Banana Pro](https://blog.google/products/gemini/prompting-tips-nano-banana-pro/)
- [Google DeepMind: Nano Banana Pro](https://deepmind.google/models/gemini-image/pro/)
- [Vertex AI: Imagen Prompt & Attribute Guide](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/image/img-gen-prompt-guide)
- [Vertex AI: Imagen 3 API Reference](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/model-reference/imagen-api)
- [Gemini API: Nano Banana Image Generation](https://ai.google.dev/gemini-api/docs/image-generation)

### Гайды и руководства
- [Dev.to: Nano-Banana Pro Prompting Guide & Strategies](https://dev.to/googleai/nano-banana-pro-prompting-guide-strategies-1h9n)
- [Higgsfield: High-Control Prompting & Templates](https://higgsfield.ai/nano-banana-pro-prompt-guide)
- [GLB GPT: Ultimate Guide of NB Pro Prompt](https://www.glbgpt.com/hub/the-ultimate-guide-of-nano-banana-pro-prompt/)
- [Imagine.art: NB Pro Prompting Guide + 75 Prompts](https://www.imagine.art/blogs/nano-banana-pro-prompt-guide)
- [Atlabs AI: Ultimate NB Pro Prompting Guide 2026](https://www.atlabs.ai/blog/the-ultimate-nano-banana-pro-prompting-guide-mastering-gemini-3-pro-image)
- [Radical Curiosity: Effective Prompt Creation](https://www.radicalcuriosity.xyz/p/how-to-create-an-effective-prompt)

### Консистентность персонажей
- [Apiyi: Face Consistency Complete Guide](https://help.apiyi.com/en/nano-banana-pro-face-consistency-guide-en.html)
- [Apiyi: Seed Not Supported — 4 Alternatives](https://help.apiyi.com/en/nano-banana-pro-seed-parameter-not-supported-alternatives-en.html)
- [Sider: NB Pro Cheat Sheet for Character Consistency](https://sider.ai/blog/ai-image/nano-banana-pro-cheat-sheet-for-character-consistency)
- [Sider: 3D Pixar-style Avatars with NB Pro](https://sider.ai/blog/ai-image/create-3d-pixar-style-avatars-with-nano-banana-pro)
- [GLB GPT: Consistent Characters Guide](https://www.glbgpt.com/hub/how-to-generate-consistent-characters-in-different-scenes-with-nano-banana/)

### Storyboard и анимация
- [Apiyi: Storyboard Generation Guide](https://help.apiyi.com/nano-banana-pro-storyboard-generation-guide-en.html)
- [Sider: NB Pro Storyboard Creation Guide](https://sider.ai/blog/ai-image/nano-banana-pro-storyboard-creation-guide-for-video)
- [Atlabs AI: Full CGI Ads with NB Pro + VEO 3.1](https://www.atlabs.ai/blog/create-full-cgi-ads-ai-complete-guide)

### Негативные промпты
- [Sider: How to Write Negative Prompts in NB](https://sider.ai/blog/ai-image/how-to-write-negative-prompts-in-nano-banana-a-practical-guide)

### Community
- [GitHub: awesome-nanobanana-pro (ZeroLu)](https://github.com/ZeroLu/awesome-nanobanana-pro)
- [GitHub: Imagen 3 Prompt Bible (yanis112)](https://github.com/yanis112/Prompting-Guide-For-Google-Imagen3)
- [Max Woolf: Advanced NB Prompt Engineering](https://minimaxir.com/2025/11/nano-banana-prompts/)
- [Flux AI: Expert Image Prompts](https://flux-ai.io/blog/detail/Nano-Banana-Pro-Guide-10-Best-Image-Prompts-for-Expert-Use-Cases-551f2895890a/)
- [Replicate: How to Prompt NB Pro](https://replicate.com/blog/how-to-prompt-nano-banana-pro)
- [DataCamp: NB Pro Complete Guide](https://www.datacamp.com/tutorial/nano-banana-pro)
