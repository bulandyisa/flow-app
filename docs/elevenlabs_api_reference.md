# ElevenLabs API — Полный справочник

**Базовый URL:** `https://api.elevenlabs.io`
**Аутентификация:** Заголовок `xi-api-key: <YOUR_API_KEY>`

---

## 1. TEXT-TO-SPEECH API

### 1.1 Генерация речи
**Endpoint:** `POST /v1/text-to-speech/{voice_id}`

**Body:**
| Параметр | Тип | Required | Описание |
|----------|-----|----------|----------|
| `text` | string | **Да** | Текст для озвучивания |
| `model_id` | string | Нет | ID модели |
| `language_code` | string | Нет | ISO 639-1 (напр. `ru`) |
| `voice_settings` | object | Нет | Настройки голоса |
| `seed` | int | Нет | Воспроизводимость |
| `previous_text` / `next_text` | string | Нет | Контекст |
| `previous_request_ids` / `next_request_ids` | array | Нет | До 3 ID для непрерывности |

**voice_settings:**
| Параметр | Тип | Описание |
|----------|-----|----------|
| `stability` | 0-1 | Стабильность (низкие = больше эмоций) |
| `similarity_boost` | 0-1 | Близость к оригиналу |
| `style` | 0-1 | Экспрессивность |
| `use_speaker_boost` | bool | Усиление сходства |
| `speed` | number | Скорость речи (1.0 = норма) |

### 1.2 С таймстемпами
**Endpoint:** `POST /v1/text-to-speech/{voice_id}/with-timestamps`
Возвращает JSON с `audio_base64` и `alignment` (посимвольные таймстемпы).

### 1.3 Стриминг
**Endpoint:** `POST /v1/text-to-speech/{voice_id}/stream`

### 1.4 WebSocket стриминг
**Endpoint:** `wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input`

---

## 2. TEXT-TO-DIALOGUE API

**Endpoint:** `POST /v1/text-to-dialogue`

Генерирует диалог из нескольких голосов в одном аудиофайле.

| Параметр | Тип | Required | Описание |
|----------|-----|----------|----------|
| `inputs` | array | **Да** | `[{text, voice_id}]` (макс. 10 голосов) |
| `model_id` | string | Нет | По умолч. `eleven_v3` |
| `language_code` | string | Нет | ISO 639-1 |

Стриминг: `POST /v1/text-to-dialogue/stream`

---

## 3. VOICES API

| Endpoint | Описание |
|----------|----------|
| `GET /v2/voices` | Список голосов (search, filter, paginate) |
| `GET /v1/voices/{voice_id}` | Получить голос |
| `GET /v1/voices/{voice_id}/settings` | Настройки голоса |
| `POST /v1/voices/{voice_id}/settings/edit` | Изменить настройки |
| `DELETE /v1/voices/{voice_id}` | Удалить голос |

---

## 4. VOICE CLONING (IVC)

**Endpoint:** `POST /v1/voices/add` (multipart/form-data)

| Параметр | Тип | Required | Описание |
|----------|-----|----------|----------|
| `name` | string | **Да** | Имя голоса |
| `files` | binary[] | **Да** | Аудиозаписи (мин. 30 сек) |
| `remove_background_noise` | bool | Нет | Удалить шум |

---

## 5. VOICE DESIGN

**Endpoint:** `POST /v1/text-to-voice/design` — создание голоса по описанию
**Endpoint:** `POST /v1/text-to-voice/{voice_id}/remix` — ремикс существующего голоса
**Сохранение:** `POST /v1/text-to-voice/create-voice-from-preview`

---

## 6. SPEECH-TO-SPEECH

**Endpoint:** `POST /v1/speech-to-speech/{voice_id}` (multipart/form-data)

Конвертирует голос, сохраняя эмоции и интонации.
Модель для русского: `eleven_multilingual_sts_v2`

---

## 7. SOUND EFFECTS API

**Endpoint:** `POST /v1/sound-generation`

| Параметр | Тип | Required | Описание |
|----------|-----|----------|----------|
| `text` | string | **Да** | Описание эффекта (на английском!) |
| `duration_seconds` | 0.5-30 | Нет | Длительность |
| `prompt_influence` | 0-1 | Нет | Строгость следования (default 0.3) |

---

## 8. MUSIC GENERATION API

**Endpoint:** `POST /v1/music` — простая генерация
**Endpoint:** `POST /v1/music/detailed` — с composition plan (секции)
**Endpoint:** `POST /v1/music/composition-plan` — создать план из промпта

Длительность: 3 сек — 10 мин. Модель: `music_v1`.

---

## 9. DUBBING API

**Endpoint:** `POST /v1/dubbing` (multipart/form-data)

Автоматический дубляж видео/аудио на другой язык.

| Параметр | Тип | Required | Описание |
|----------|-----|----------|----------|
| `file` / `source_url` | binary/string | **Да** (одно из) | Источник |
| `target_lang` | string | **Да** | Целевой язык |
| `source_lang` | string | Нет | Исходный язык (auto) |
| `num_speakers` | int | Нет | Число спикеров (0=auto) |

Дополнительные endpoint-ы для управления сегментами, транскрипцией, рендером.

---

## 10. SPEECH-TO-TEXT (Scribe)

**Endpoint:** `POST /v1/speech-to-text` (multipart/form-data)

| Параметр | Тип | Описание |
|----------|-----|----------|
| `model_id` | string | `scribe_v2` |
| `file` | binary | Аудио/видео (до 3 GB) |
| `language_code` | string | ISO-639 |
| `diarize` | bool | Диаризация спикеров |
| `num_speakers` | int (1-32) | Макс спикеров |
| `tag_audio_events` | bool | Теги: (laughter), (music) |
| `timestamps_granularity` | string | `word` / `character` |
| `additional_formats` | array | `srt`, `txt`, `pdf` и др. |

Realtime: `wss://api.elevenlabs.io/v1/speech-to-text/realtime`

---

## 11. AUDIO ISOLATION

**Endpoint:** `POST /v1/audio-isolation`
Удаляет фон, оставляя только голос. Макс 500 MB / 1 час.

---

## 12. FORCED ALIGNMENT

**Endpoint:** `POST /v1/forced-alignment`
Выравнивает текст по аудио — точные таймстемпы для каждого слова/символа.

---

## 13. PRONUNCIATION DICTIONARIES

Управление словарями произношения (PLS формат):
- `GET /v1/pronunciation-dictionaries` — список
- `POST /v1/pronunciation-dictionaries/add-from-file` — создать
- `POST /v1/pronunciation-dictionaries/{id}/rules` — добавить правила

---

## МОДЕЛИ

### TTS модели:

| Model ID | Языки | Лимит символов | Особенности |
|----------|-------|---------------|-------------|
| `eleven_v3` | 70+ (русский) | 5,000 | Максимальная экспрессивность |
| `eleven_multilingual_v2` | 29 (русский) | 10,000 | Самое реалистичное звучание |
| `eleven_flash_v2_5` | 32 (русский) | 40,000 | ~75 мс задержка, -50% стоимость |
| `eleven_turbo_v2_5` | 32 (русский) | 40,000 | Баланс качества/скорости |

### Для русского языка:
- **Качество:** `eleven_multilingual_v2` — стабильный, реалистичный
- **Экспрессия:** `eleven_v3` — больше эмоций (лимит 5000 символов)
- **Скорость:** `eleven_flash_v2_5` — для реального времени

**ВАЖНО:** Всегда указывать `language_code: "ru"`

---

## ФОРМАТЫ АУДИО

| Формат | Варианты | Требования |
|--------|----------|-----------|
| MP3 | 22050-44100 Hz, 32-192 kbps | Free (192 kbps → Creator+) |
| PCM | 8000-48000 Hz | Free (44100+ → Pro+) |
| WAV | 8000-48000 Hz | Free (44100+ → Pro+) |
| Opus | 48000 Hz, 32-192 kbps | — |

---

## PYTHON SDK

```bash
pip install elevenlabs
```

```python
from elevenlabs.client import ElevenLabs, AsyncElevenLabs
from elevenlabs import play, stream, save

client = ElevenLabs(api_key="KEY")

# TTS
audio = client.text_to_speech.convert(
    text="Привет!", voice_id="...",
    model_id="eleven_multilingual_v2", language_code="ru"
)
save(audio, "output.mp3")

# Dialogue
audio = client.text_to_dialogue.convert(
    model_id="eleven_v3", language_code="ru",
    inputs=[{"text": "Привет!", "voice_id": "v1"}, {"text": "Ответ", "voice_id": "v2"}]
)

# Sound Effects
audio = client.text_to_sound_effects.convert(text="Thunder rumbling", duration_seconds=5.0)

# STT
result = client.speech_to_text.convert(
    model_id="scribe_v2", file=open("audio.mp3", "rb"),
    language_code="ru", diarize=True
)

# Audio Isolation
audio = client.audio_isolation.convert(audio=open("noisy.mp3", "rb"))
```

---

## ТАРИФЫ

| План | Цена/мес | Credits | Конкурентность (v2/v3) |
|------|----------|---------|----------------------|
| Free | $0 | 10K | 2 |
| Starter | $5 | 30K | 3 |
| Creator | $22 | 100K | 5 |
| Pro | $99 | 500K | 10 |
| Scale | $330 | Millions | 15 |

1 символ TTS (v2/v3) = 1 credit. Flash/Turbo = 0.5 credit/символ.
