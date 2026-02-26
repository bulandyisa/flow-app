"""
Модуль озвучки: автоматизация дубляжа мультфильма через ElevenLabs Dubbing Studio

Пайплайн:
  1. --init               — Парсинг сценария + промптов → audio_config.json
  2. --upload --clip S05_C — Загрузить клип в ElevenLabs Dubbing Studio (API)
  3. --upload-all          — Загрузить все клипы с диалогами (API)
  4. --sfx --clip S01_A    — Сгенерировать фоновые звуки для клипа
  5. --sfx-all             — Сгенерировать фоновые звуки для всех клипов
  6. --strip-audio          — Удалить аудио VEO из видеоклипов (авто при upload)
  7. --dub-login           — Открыть браузер для логина в ElevenLabs
  7. --dub --clip S05_C    — Автоматизация Dubbing Studio (голоса + фон + генерация)
  8. --dub-all             — Автоматизация Studio для всех клипов
  9. --download --clip S05_C — Скачать озвученное видео из ElevenLabs
  10. --download-all        — Скачать все озвученные видео
  11. --mix --clip S05_C    — Наложить SFX на скачанный аудио + видео
  12. --mix-all             — Наложить SFX на все клипы
  13. --assemble            — Склеить все клипы в финальный ролик
  14. --status              — Показать прогресс

Использование:
  python scripts/voice_bot.py --init
  python scripts/voice_bot.py --sfx-all
  python scripts/voice_bot.py --upload-all
  python scripts/voice_bot.py --dub-login
  python scripts/voice_bot.py --dub-all
  python scripts/voice_bot.py --download-all
  python scripts/voice_bot.py --mix-all
  python scripts/voice_bot.py --assemble
  python scripts/voice_bot.py --status
"""
import argparse
import csv
import hashlib
import io
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SCENARIO_FILE = PROJECT_ROOT / "scenario_signal.txt"
PROMPTS_FILE = PROJECT_ROOT / "output" / "prompts" / "all_prompts.json"
AUDIO_DIR = PROJECT_ROOT / "output" / "audio"
CONFIG_FILE = AUDIO_DIR / "audio_config.json"
CLIPS_DIR = PROJECT_ROOT / "output" / "clips"
SFX_DIR = AUDIO_DIR / "sfx"
TTS_DIR = AUDIO_DIR / "tts"
MIXED_DIR = AUDIO_DIR / "mixed"
VOICED_DIR = AUDIO_DIR / "clips_voiced"
FINAL_DIR = AUDIO_DIR / "final"
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "screenshots"

# ── ElevenLabs Browser Session ────────────────────────────────────────────
EL_SESSION_DIR = PROJECT_ROOT / ".session_elevenlabs"
EL_BASE_URL = "https://elevenlabs.io"
EL_DUBBING_URL = f"{EL_BASE_URL}/app/dubbing"

# ── ElevenLabs config ──────────────────────────────────────────────────────
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
API_BASE = "https://api.elevenlabs.io/v1"

# Voice cast from .env
VOICE_CAST = {
    "Karim": os.environ.get("VOICE_KARIM", ""),
    "Amin": os.environ.get("VOICE_AMIN", ""),
    "Tako": os.environ.get("VOICE_TAKO", ""),
    "Papa": os.environ.get("VOICE_PAPA", ""),
    "Mama": os.environ.get("VOICE_MAMA", ""),
    "Aya": os.environ.get("VOICE_AYA", ""),
    "Rami": os.environ.get("VOICE_RAMI", ""),
    "Hasan": os.environ.get("VOICE_HASAN", ""),
    "Samir": os.environ.get("VOICE_SAMIR", ""),
    "Shaki": os.environ.get("VOICE_SHAKI", ""),
}

# Speaker name normalization (Russian → English)
SPEAKER_MAP = {
    "КАРИМ": "Karim",
    "АМИН": "Amin",
    "ТАКО": "Tako",
    "ПАПА": "Papa",
    "МАМА": "Mama",
    "АЯ": "Aya",
    "АЙЯ": "Aya",
    "РАМИ": "Rami",
    "ХАСАН": "Hasan",
    "САМИР": "Samir",
    "ШАКИ": "Shaki",
    "НАЗИР": "Samir",
}

# Modifier → voice_settings overrides
MODIFIER_EFFECTS = {
    "шёпотом": {"stability": 0.3, "similarity": 0.8, "style": 0.2},
    "шепотом": {"stability": 0.3, "similarity": 0.8, "style": 0.2},
    "бормочет": {"stability": 0.4, "similarity": 0.7, "style": 0.3},
    "кричит": {"stability": 0.7, "similarity": 0.8, "style": 0.6},
    "одними губами": {"stability": 0.2, "similarity": 0.7, "style": 0.1},
    "еле слышно": {"stability": 0.3, "similarity": 0.8, "style": 0.2},
}

# ══════════════════════════════════════════════════════════════════════════════
#  SOUND DESIGN: Многослойный звуковой дизайн для каждого клипа
# ══════════════════════════════════════════════════════════════════════════════
# Каждый клип имеет несколько слоёв звука:
#   - ambient: база, на всю длину клипа (тихий)
#   - sfx: конкретные звуки событий (с таймингами и громкостью)
# Громкость (volume): 0.0–1.0 → ffmpeg dB
#   0.15 = очень тихий (-16dB), 0.3 = тихий (-10dB),
#   0.5 = средний (-6dB), 0.7 = громкий (-3dB), 1.0 = полный (0dB)
# ElevenLabs Sound Effects API: английские промпты, макс 30 сек

SCENE_SOUND_DESIGN = {
    # ── СЦЕНА 1: ГАРАЖ, НОЧЬ ──────────────────────────────────────────────
    "S01_A": [
        {"id": "amb", "type": "ambient",
         "prompt": "Dark quiet garage at night, subtle electrical hum from fluorescent light, very faint wind outside",
         "volume": 0.25},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Shortwave radio tuning dial being turned, static noise, crackling interference, scanning through frequencies",
         "volume": 0.8},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Mysterious monotone voice reading numbers through radio static, number station broadcast, eerie and distant",
         "volume": 0.5, "start_sec": 4.0},
    ],
    "S01_B": [
        {"id": "amb", "type": "ambient",
         "prompt": "Dark quiet garage at night, very faint electrical hum, tense silence, subtle distant wind",
         "volume": 0.2},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Faint radio static in background, low volume, barely audible shortwave receiver hiss",
         "volume": 0.15},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Wooden stool creaking slightly as someone turns around, subtle fabric rustle of clothing",
         "volume": 0.25, "start_sec": 2.0},
    ],

    # ── СЦЕНА 2: ГАРАЖ, ДЕНЬ ──────────────────────────────────────────────
    "S02_A": [
        {"id": "amb", "type": "ambient",
         "prompt": "Daytime garage workshop interior, muffled street sounds outside, distant birds chirping, slight breeze through gap under garage door",
         "volume": 0.35},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Backpack being set down on concrete floor, zipper and fabric thud, casual drop",
         "volume": 0.3, "start_sec": 3.0},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Finger sliding slowly across dusty surface, light wiping scraping sound",
         "volume": 0.2, "start_sec": 5.0},
    ],
    "S02_B": [
        {"id": "amb", "type": "ambient",
         "prompt": "Daytime garage interior, muffled outdoor sounds, birds outside",
         "volume": 0.2},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Door bursting open energetically, wooden stick hitting door frame hard, wire scraping against wall, clumsy stumbling footsteps",
         "volume": 0.75},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Comedic spring wire bouncing and hitting someone on forehead, light bonk impact, cartoon-like",
         "volume": 0.5, "start_sec": 2.5},
    ],
    "S02_C": [
        {"id": "amb", "type": "ambient",
         "prompt": "Quiet garage interior, awkward tense silence, faint outdoor birds very subtle, uncomfortable atmosphere",
         "volume": 0.2},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Old sofa fabric rustling as someone turns away, cushion and leather shifting sound",
         "volume": 0.2, "start_sec": 0.5},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Very soft quiet footsteps walking away slowly on concrete floor, subdued shuffling, dejected pace",
         "volume": 0.25, "start_sec": 2.5},
    ],

    # ── СЦЕНА 3: ДОМ АМИНА, ВЕЧЕР ─────────────────────────────────────────
    "S03_A": [
        {"id": "amb", "type": "ambient",
         "prompt": "Quiet warm home interior evening, distant muffled kitchen sounds, faint clock ticking from another room, residential calm",
         "volume": 0.3},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Slow deliberate footsteps on wooden floor hallway, leather shoes, indoor residential, man walking",
         "volume": 0.5},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Wooden door creaking open slowly, gentle old hinges, door handle turning quietly",
         "volume": 0.3, "start_sec": 3.5},
    ],
    "S03_B": [
        {"id": "amb", "type": "ambient",
         "prompt": "Quiet study room at evening, wall clock ticking steadily, warm interior, very faint distant street sounds through closed window",
         "volume": 0.4},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Fountain pen writing on paper, slow deliberate scratching strokes, ink pen on quality paper",
         "volume": 0.4},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Pen being placed down gently on wooden desk, soft thud, then deep thoughtful sigh, silence",
         "volume": 0.3, "start_sec": 3.5},
    ],

    # ── СЦЕНА 4: ГАРАЖ, ВЕЧЕР ─────────────────────────────────────────────
    "S04_A": [
        {"id": "amb", "type": "ambient",
         "prompt": "Evening garage workshop, fluorescent light buzzing faintly overhead, quiet residential neighborhood outside",
         "volume": 0.2},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Soldering iron on circuit board, tin sizzling and melting, small electronic clicking, focused repair work",
         "volume": 0.5},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Electronic device powering on, capacitor charging whine, LED click, then shortwave radio static slowly starting",
         "volume": 0.5, "start_sec": 5.0},
    ],
    "S04_B": [
        {"id": "amb", "type": "ambient",
         "prompt": "Tense quiet garage at night, barely audible electrical hum, suspenseful atmosphere",
         "volume": 0.15},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Mysterious shortwave number station signal, rhythmic electronic beeps then monotone coded voice reading numbers, eerie unsettling, radio static between transmissions",
         "volume": 0.7},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Pencil writing quickly and urgently on paper, frantic scribbling, note-taking under pressure",
         "volume": 0.3, "start_sec": 2.0},
    ],
    "S04_C": [
        {"id": "amb", "type": "ambient",
         "prompt": "Evening outdoor residential street, distant dog barking once, crickets chirping softly, calm quiet neighborhood, slight breeze",
         "volume": 0.4},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Paper being grabbed quickly with rustling, then running footsteps on pavement, sneakers, fast urgent pace getting louder",
         "volume": 0.65},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Metal garage door slamming shut, heavy rattling clang",
         "volume": 0.4, "start_sec": 0.5},
    ],

    # ── СЦЕНА 5: ГАРАЖ, ВЕЧЕР (ЧУТЬ ПОЗЖЕ) ────────────────────────────────
    "S05_A": [
        {"id": "amb", "type": "ambient",
         "prompt": "Evening garage workshop interior, fluorescent light subtle buzz, quiet still atmosphere",
         "volume": 0.2},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Door opening with slight creak, then lazy shuffling footsteps entering room, bored casual walk on concrete floor",
         "volume": 0.35},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Radio tuning dial turning slowly, white noise static, scanning frequencies, nothing found, empty hiss and crackle",
         "volume": 0.45, "start_sec": 2.0},
    ],
    "S05_B": [
        {"id": "amb", "type": "ambient",
         "prompt": "Dead quiet garage, extremely tense atmosphere, barely audible fluorescent light hum, breath-holding silence",
         "volume": 0.1},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Radio signal slowly emerging from white noise static, mysterious number station growing clearer, rhythmic beeps becoming distinct, eerie coded broadcast materializing",
         "volume": 0.6},
    ],
    "S05_C": [
        {"id": "amb", "type": "ambient",
         "prompt": "Quiet garage interior, faint electrical hum, focused concentrated atmosphere",
         "volume": 0.15},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Pen writing quickly on paper, scribbling numbers urgently, determined strokes",
         "volume": 0.35},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Heavy old book opening, thick atlas pages turning and rustling, finger tracing across paper map surface",
         "volume": 0.35, "start_sec": 2.5},
    ],
    "S05_D": [
        {"id": "amb", "type": "ambient",
         "prompt": "Quiet garage transitioning to outdoor evening sounds, door opening with fresh air and distant neighborhood sounds",
         "volume": 0.3},
        {"id": "sfx1", "type": "sfx",
         "prompt": "Person standing up quickly from metal stool, stool scraping on concrete floor with sharp sound",
         "volume": 0.3, "start_sec": 3.0},
        {"id": "sfx2", "type": "sfx",
         "prompt": "Confident footsteps walking then gradually speeding up to determined fast pace, sneakers on concrete then outdoor pavement",
         "volume": 0.4, "start_sec": 3.5},
    ],
}

# ── Emotion analysis: scene context → voice_settings ────────────────────────
# Each dialogue gets voice_settings based on modifier + scene context

def analyze_emotion(dialogue: dict, scene_desc: str, clip_id: str) -> dict:
    """Determine voice_settings based on dialogue modifier and scene context.

    Returns dict with stability, similarity, style for ElevenLabs voice.
    Lower stability = more emotional/expressive.
    Higher style = more dramatic delivery.
    """
    modifier = dialogue.get("modifier", "").lower()
    text = dialogue.get("text_ru", "")

    # 1. Explicit modifier takes priority
    if modifier in MODIFIER_EFFECTS:
        return MODIFIER_EFFECTS[modifier]

    # 2. Text-based analysis
    if "..." in text or "…" in text:
        # Hesitation, uncertainty, wonder
        return {"stability": 0.35, "similarity": 0.8, "style": 0.3}

    if text.endswith("?"):
        # Question
        return {"stability": 0.45, "similarity": 0.8, "style": 0.4}

    if text.endswith("!"):
        # Exclamation, excitement
        return {"stability": 0.5, "similarity": 0.8, "style": 0.5}

    # 3. Scene context analysis
    scene_lower = scene_desc.lower()

    if any(w in scene_lower for w in ["замирает", "медленно", "тихо"]):
        # Tense, quiet scene
        return {"stability": 0.35, "similarity": 0.8, "style": 0.25}

    if any(w in scene_lower for w in ["бежит", "хватает", "влетает"]):
        # Fast-paced, excited scene
        return {"stability": 0.5, "similarity": 0.8, "style": 0.5}

    if any(w in scene_lower for w in ["скучающий", "лежит", "отворачивается"]):
        # Bored, apathetic scene
        return {"stability": 0.6, "similarity": 0.8, "style": 0.15}

    # 4. Default: natural conversational
    return {"stability": 0.5, "similarity": 0.8, "style": 0.35}


# ══════════════════════════════════════════════════════════════════════════════
#  ElevenLabs API helpers
# ══════════════════════════════════════════════════════════════════════════════

def api_headers():
    return {"xi-api-key": ELEVENLABS_API_KEY}


def api_get(endpoint: str, **kwargs) -> requests.Response:
    return requests.get(f"{API_BASE}{endpoint}", headers=api_headers(), **kwargs)


def api_post(endpoint: str, **kwargs) -> requests.Response:
    return requests.post(f"{API_BASE}{endpoint}", headers=api_headers(), **kwargs)


def api_patch(endpoint: str, **kwargs) -> requests.Response:
    return requests.patch(f"{API_BASE}{endpoint}", headers=api_headers(), **kwargs)


def wait_for_dubbing(dubbing_id: str, timeout: int = 300) -> bool:
    """Wait for dubbing project to finish processing."""
    start = time.time()
    while time.time() - start < timeout:
        resp = api_get(f"/dubbing/{dubbing_id}")
        if resp.status_code != 200:
            print(f"    ✗ Ошибка статуса: {resp.status_code} {resp.text[:200]}")
            return False
        data = resp.json()
        status = data.get("status", "")
        if status == "dubbed" or status == "ready":
            return True
        if status == "failed":
            print(f"    ✗ Дубляж провалился: {data.get('error', 'unknown')}")
            return False
        print(f"    ... статус: {status}, жду...")
        time.sleep(5)
    print(f"    ✗ Таймаут {timeout}s")
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  SFX: Генерация и микширование многослойных фоновых звуков
# ══════════════════════════════════════════════════════════════════════════════

def volume_to_db(volume: float) -> float:
    """Convert 0-1 volume to dB. 1.0=0dB, 0.5=-6dB, 0.25=-12dB, etc."""
    if volume <= 0:
        return -60
    import math
    return 20 * math.log10(max(volume, 0.01))


def get_sound_layers(clip_id: str) -> list[dict]:
    """Get sound design layers for a clip from SCENE_SOUND_DESIGN."""
    return SCENE_SOUND_DESIGN.get(clip_id, [])


def generate_sfx_file(prompt: str, duration_sec: float, output_path: Path,
                       prompt_influence: float = 0.4) -> bool:
    """Generate a single SFX file via ElevenLabs Sound Effects API."""
    if output_path.exists():
        print(f"      Кэш: {output_path.name}")
        return True

    duration = min(max(duration_sec, 0.5), 30.0)
    resp = api_post("/sound-generation", json={
        "text": prompt,
        "duration_seconds": duration,
        "prompt_influence": prompt_influence,
    })

    if resp.status_code != 200:
        print(f"      ✗ Ошибка SFX: {resp.status_code} {resp.text[:200]}")
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(resp.content)
    print(f"      ✓ {output_path.name} ({duration:.1f}s)")
    return True


def mix_sound_layers(layers_info: list[dict], clip_duration: float,
                     output_path: Path) -> bool:
    """Mix multiple sound layers with individual timing and volume into one file.

    layers_info: list of {"path": Path, "volume": float, "start_sec": float, "duration": float}
    """
    if not layers_info:
        return False

    if len(layers_info) == 1:
        li = layers_info[0]
        db = volume_to_db(li["volume"])
        start_ms = int(li.get("start_sec", 0) * 1000)
        filters = []
        if start_ms > 0:
            filters.append(f"adelay={start_ms}|{start_ms}")
        filters.append(f"volume={db:.1f}dB")
        filters.append(f"apad=whole_dur={clip_duration}")
        cmd = [
            "ffmpeg", "-y", "-i", str(li["path"]),
            "-af", ",".join(filters),
            "-t", str(clip_duration),
            "-ar", "44100", "-ac", "2",
            str(output_path),
        ]
    else:
        inputs = []
        filter_parts = []

        for i, li in enumerate(layers_info):
            inputs.extend(["-i", str(li["path"])])
            db = volume_to_db(li["volume"])
            start_ms = int(li.get("start_sec", 0) * 1000)

            chain = []
            if start_ms > 0:
                chain.append(f"adelay={start_ms}|{start_ms}")
            chain.append(f"volume={db:.1f}dB")
            chain.append(f"apad=whole_dur={clip_duration}")

            filter_parts.append(f"[{i}]{','.join(chain)}[l{i}]")

        mix_inputs = "".join(f"[l{i}]" for i in range(len(layers_info)))
        filter_parts.append(
            f"{mix_inputs}amix=inputs={len(layers_info)}:duration=longest"
            f":dropout_transition=0:normalize=0"
        )

        cmd = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", ";".join(filter_parts),
            "-t", str(clip_duration),
            "-ar", "44100", "-ac", "2",
            str(output_path),
        ]

    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        print(f"      ✗ ffmpeg ошибка: {result.stderr.decode()[:300]}")
        return False

    return True


def generate_clip_sfx(clip: dict) -> Path | None:
    """Generate all sound layers for a clip and mix into one background file."""
    clip_id = clip["clip_id"]
    duration = clip["duration_sec"]
    layers = get_sound_layers(clip_id)

    if not layers:
        return None

    print(f"\n  [{clip_id}] Звуковой дизайн ({len(layers)} слоёв)...")
    SFX_DIR.mkdir(parents=True, exist_ok=True)

    # Check if final mix already exists
    mixed_path = SFX_DIR / f"{clip_id}_mix.mp3"
    if mixed_path.exists():
        print(f"    Кэш: {mixed_path.name}")
        return mixed_path

    generated = []

    for layer in layers:
        layer_id = f"{clip_id}_{layer['id']}"
        fpath = SFX_DIR / f"{layer_id}.mp3"
        start = layer.get("start_sec", 0)
        # Duration of this layer = clip_duration - start_sec
        layer_dur = duration - start

        ltype = "AMB" if layer["type"] == "ambient" else "SFX"
        print(f"    {ltype}: {layer['prompt'][:65]}...")
        print(f"         vol={layer['volume']}, start={start}s, dur={layer_dur:.1f}s")

        if generate_sfx_file(layer["prompt"], layer_dur, fpath):
            generated.append({
                "path": fpath,
                "volume": layer["volume"],
                "start_sec": start,
                "duration": layer_dur,
            })

    if not generated:
        return None

    # Mix all layers
    print(f"    Микширую {len(generated)} слоёв...")
    if mix_sound_layers(generated, duration, mixed_path):
        size_kb = mixed_path.stat().st_size / 1024
        print(f"    ✓ Готово: {mixed_path.name} ({size_kb:.0f} KB)")
        return mixed_path

    # Fallback: return first file
    return generated[0]["path"]


def cmd_sfx(clip_id: str | None):
    """Generate SFX for one clip or all clips."""
    config = load_config()

    if clip_id:
        clip = next((c for c in config["clips"] if c["clip_id"] == clip_id), None)
        if not clip:
            print(f"ОШИБКА: Клип {clip_id} не найден")
            return
        result = generate_clip_sfx(clip)
        if result:
            print(f"\n  Готово: {result}")
        else:
            print(f"\n  [{clip_id}] Нет звукового дизайна (добавьте в SCENE_SOUND_DESIGN)")
    else:
        print("═" * 60)
        print("  SFX: Генерация звукового дизайна для всех клипов")
        print("═" * 60)
        total_layers = 0
        count = 0
        for clip in config["clips"]:
            layers = get_sound_layers(clip["clip_id"])
            if layers:
                total_layers += len(layers)
            result = generate_clip_sfx(clip)
            if result:
                count += 1
        print(f"\n{'═' * 60}")
        print(f"  Готово! {count} клипов, {total_layers} звуковых слоёв")
        print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════════════════════
#  INIT: Parse scenario + prompts → audio_config.json
# ══════════════════════════════════════════════════════════════════════════════

def parse_dialogues(scenario_text: str) -> dict[int, list[dict]]:
    """Parse scenario text and extract dialogues grouped by scene number."""
    scenes: dict[int, list[dict]] = {}
    current_scene = None
    dialogue_re = re.compile(r'^([А-ЯЁ]+)\s*(?:\(([^)]+)\))?\s*:\s*(.+)$')
    scene_re = re.compile(r'^СЦЕНА\s+(\d+)')

    for line in scenario_text.splitlines():
        line = line.strip()
        scene_match = scene_re.match(line)
        if scene_match:
            current_scene = int(scene_match.group(1))
            if current_scene not in scenes:
                scenes[current_scene] = []
            continue

        if current_scene is None:
            continue

        if line.startswith("ТИТР"):
            continue

        dialogue_match = dialogue_re.match(line)
        if dialogue_match:
            speaker_ru = dialogue_match.group(1)
            modifier = (dialogue_match.group(2) or "").strip()
            text = dialogue_match.group(3).strip()

            speaker_en = SPEAKER_MAP.get(speaker_ru, speaker_ru.capitalize())

            speech_modifier = ""
            if modifier:
                speech_keywords = ["шёпотом", "шепотом", "бормочет", "кричит",
                                   "одними губами", "еле слышно", "бодрым голосом"]
                for kw in speech_keywords:
                    if kw in modifier.lower():
                        speech_modifier = modifier.lower()
                        break

            scenes[current_scene].append({
                "speaker": speaker_en,
                "modifier": speech_modifier,
                "text_ru": text,
            })

    return scenes


def map_dialogues_to_clips(dialogues_by_scene: dict, prompts: list[dict]) -> dict[str, list[dict]]:
    """Map parsed dialogues to specific clips based on scenario analysis."""
    clip_dialogues = {}

    # Manual mapping for S01-S05 (based on detailed scenario/clip analysis)
    mapping = {
        "S01_B": _slice(dialogues_by_scene, 1, 0, 1),
        "S05_A": _slice(dialogues_by_scene, 5, 0, 2),
        "S05_C": _slice(dialogues_by_scene, 5, 2, 5),
        "S05_D": _slice(dialogues_by_scene, 5, 5, 8),
    }

    for clip_id, dlgs in mapping.items():
        if dlgs:
            clip_dialogues[clip_id] = dlgs

    return clip_dialogues


def _slice(dialogues_by_scene: dict, scene_num: int, start: int, end: int) -> list[dict]:
    return dialogues_by_scene.get(scene_num, [])[start:end]


def auto_timing(dialogues: list[dict], clip_duration: float) -> list[dict]:
    """Distribute dialogues evenly across clip duration. Estimate end_sec based on text length."""
    n = len(dialogues)
    if n == 0:
        return dialogues

    margin = 0.5
    available = clip_duration - 2 * margin

    if n == 1:
        dialogues[0]["start_sec"] = round(clip_duration * 0.6, 1)
    else:
        gap = available / n
        for i, d in enumerate(dialogues):
            d["start_sec"] = round(margin + i * gap, 1)

    # Estimate end_sec based on ~5 chars/sec for Russian speech
    for d in dialogues:
        text_len = len(d["text_ru"])
        estimated_duration = max(1.0, text_len / 5.0)
        d["end_sec"] = round(d["start_sec"] + estimated_duration, 1)
        # Clamp to clip duration
        if d["end_sec"] > clip_duration:
            d["end_sec"] = round(clip_duration - 0.1, 1)

    return dialogues


def init_config():
    """Parse scenario + prompts → audio_config.json."""
    print("═" * 60)
    print("  INIT: Парсинг сценария → audio_config.json")
    print("═" * 60)

    scenario_text = SCENARIO_FILE.read_text(encoding="utf-8")
    prompts = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))

    dialogues_by_scene = parse_dialogues(scenario_text)
    total_dialogues = sum(len(v) for v in dialogues_by_scene.values())
    print(f"\n  Найдено реплик в сценарии: {total_dialogues}")
    for scene_num, dlgs in sorted(dialogues_by_scene.items()):
        print(f"    Сцена {scene_num}: {len(dlgs)} реплик")

    clip_dialogues = map_dialogues_to_clips(dialogues_by_scene, prompts)
    print(f"\n  Реплики привязаны к клипам:")
    for clip_id, dlgs in sorted(clip_dialogues.items()):
        speakers = ", ".join(d["speaker"] for d in dlgs)
        print(f"    {clip_id}: {len(dlgs)} реплик ({speakers})")

    # Build voice_cast
    voice_cast = {}
    for name, voice_id in VOICE_CAST.items():
        if voice_id:
            voice_cast[name] = {"voice_id": voice_id}

    # Build clips config
    clips = []
    for p in prompts:
        clip_id = p["clip_id"]
        duration = p.get("veo_duration", 8)

        raw_dialogues = clip_dialogues.get(clip_id, [])
        timed_dialogues = auto_timing(raw_dialogues, duration)

        enriched = []
        for i, d in enumerate(timed_dialogues):
            entry = {
                "id": f"{clip_id}_D{i+1}",
                "speaker": d["speaker"],
                "text_ru": d["text_ru"],
                "modifier": d.get("modifier", ""),
                "start_sec": d.get("start_sec"),
                "end_sec": d.get("end_sec"),
            }
            enriched.append(entry)

        clips.append({
            "clip_id": clip_id,
            "scene_id": p["scene_id"],
            "scene_description_ru": p.get("scene_description_ru", ""),
            "duration_sec": duration,
            "dialogues": enriched,
            "audio_note": p.get("audio_note", ""),
            "dubbing_id": None,  # filled after upload
            "studio_url": None,  # filled after upload
        })

    config = {
        "version": 2,
        "language_code": "ru",
        "voice_cast": voice_cast,
        "clips": clips,
    }

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    total_tts = sum(len(c["dialogues"]) for c in clips)
    print(f"\n{'═' * 60}")
    print(f"  Готово! Сохранено: {CONFIG_FILE}")
    print(f"  Клипов: {len(clips)}")
    print(f"  Реплик для озвучки: {total_tts}")
    print(f"  Голосов настроено: {len(voice_cast)}")
    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════════════════════
#  TTS: Generate voice lines via ElevenLabs Text-to-Speech API
# ══════════════════════════════════════════════════════════════════════════════

def tts_single(dialogue: dict, voice_cast: dict, lang: str = "ru") -> Path | None:
    """Generate TTS for a single dialogue line.

    Returns path to the generated .mp3 file, or None on error.
    Skips if file already exists (caching).
    """
    d_id = dialogue["id"]
    speaker = dialogue["speaker"]
    text = dialogue["text_ru"]

    TTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TTS_DIR / f"{d_id}.mp3"

    # Cache: skip if already generated
    if out_path.exists() and out_path.stat().st_size > 100:
        return out_path

    voice_info = voice_cast.get(speaker, {})
    voice_id = voice_info.get("voice_id")
    if not voice_id:
        print(f"    ⚠ Нет voice_id для {speaker}")
        return None

    # Voice settings from _emotion or defaults
    emotion = dialogue.get("_emotion", {})
    stability = emotion.get("stability", 0.5)
    similarity = emotion.get("similarity", 0.8)
    style = emotion.get("style", 0.3)

    # Modifier adjustments
    modifier = dialogue.get("modifier", "")
    if "шёпот" in modifier.lower():
        stability = min(stability, 0.3)
        style = max(style, 0.1)
    elif "крич" in modifier.lower():
        stability = max(stability, 0.7)

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "language_code": lang,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity,
            "style": style,
            "use_speaker_boost": True,
        },
    }

    try:
        resp = requests.post(
            f"{API_BASE}/text-to-speech/{voice_id}",
            headers={**api_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if resp.status_code == 200:
            with open(out_path, "wb") as f:
                f.write(resp.content)
            dur = _get_audio_duration(out_path)
            print(f"    ✓ {d_id}: {speaker} «{text[:30]}» ({dur:.1f}s)")
            return out_path
        else:
            print(f"    ✗ {d_id}: HTTP {resp.status_code} — {resp.text[:100]}")
            return None
    except Exception as e:
        print(f"    ✗ {d_id}: {str(e)[:100]}")
        return None


def _get_audio_duration(path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def cmd_tts(clip_id: str | None = None):
    """Generate TTS for all dialogues (or one clip) via ElevenLabs API."""
    config = load_config()

    clips = config["clips"]
    if clip_id:
        clips = [c for c in clips if c["clip_id"] == clip_id]
        if not clips:
            print(f"ОШИБКА: Клип {clip_id} не найден")
            return

    print(f"\n{'═' * 60}")
    print(f"  TTS: Генерация голосов через ElevenLabs API")
    print(f"{'═' * 60}")

    total = 0
    generated = 0
    for clip in clips:
        if not clip["dialogues"]:
            continue
        print(f"\n  [{clip['clip_id']}]")
        for d in clip["dialogues"]:
            total += 1
            result = tts_single(d, config["voice_cast"])
            if result:
                generated += 1
            time.sleep(0.5)  # Rate limit

    print(f"\n{'═' * 60}")
    print(f"  TTS: {generated}/{total} реплик сгенерировано")
    print(f"{'═' * 60}")


def cmd_mix_full(clip_id: str | None = None):
    """Mix video + SFX + TTS voices into final clips.

    For each clip:
    1. Start with silent video
    2. Overlay SFX background at proper timing
    3. Overlay TTS voice lines at their start_sec positions
    4. Output final mp4
    """
    config = load_config()
    clips = config["clips"]
    if clip_id:
        clips = [c for c in clips if c["clip_id"] == clip_id]

    print(f"\n{'═' * 60}")
    print(f"  MIX: Сборка видео + SFX + голоса")
    print(f"{'═' * 60}")

    VOICED_DIR.mkdir(parents=True, exist_ok=True)
    count = 0

    for clip in clips:
        cid = clip["clip_id"]
        duration = clip["duration_sec"]

        # Find video file
        candidates = [
            CLIPS_DIR / f"{cid}_clip_silent.mp4",
            CLIPS_DIR / f"{cid}_silent.mp4",
            CLIPS_DIR / f"{cid}_clip.mp4",
            CLIPS_DIR / f"{cid}.mp4",
        ]
        vpath = next((p for p in candidates if p.exists()), None)
        if not vpath:
            print(f"  [{cid}] ✗ Видео не найдено, пропускаю")
            continue

        print(f"\n  [{cid}] {vpath.name}")

        # Collect all audio inputs
        audio_inputs = []  # list of (path, start_sec, volume_db)

        # SFX layers
        sfx_dir = AUDIO_DIR / "sfx"
        if sfx_dir.exists():
            sfx_files = sorted(sfx_dir.glob(f"{cid}_*.mp3")) + sorted(sfx_dir.glob(f"{cid}_*.wav"))
            for sf in sfx_files:
                audio_inputs.append((sf, 0.0, -3))  # SFX at start, slightly quieter
                print(f"    SFX: {sf.name}")

        # TTS voice lines
        for d in clip.get("dialogues", []):
            tts_path = TTS_DIR / f"{d['id']}.mp3"
            if tts_path.exists():
                start = d.get("start_sec", 0.5)
                vol = 0  # Voice at full volume
                # Modifier volume adjustments
                mod = d.get("modifier", "")
                if "шёпот" in mod.lower():
                    vol = -6
                elif "крич" in mod.lower():
                    vol = 3
                audio_inputs.append((tts_path, start, vol))
                print(f"    TTS: {d['id']} @ {start}s ({d['speaker']}: «{d['text_ru'][:25]}»)")
            else:
                print(f"    ⚠ TTS не найден: {d['id']}")

        if not audio_inputs:
            # No audio to mix — just copy video
            target = VOICED_DIR / f"{cid}_final.mp4"
            subprocess.run(["cp", str(vpath), str(target)], timeout=10)
            print(f"    → {target.name} (без аудио)")
            count += 1
            continue

        # Build ffmpeg command with adelay + amix
        target = VOICED_DIR / f"{cid}_final.mp4"
        cmd_parts = ["ffmpeg", "-y", "-i", str(vpath)]

        # Add silence as base track
        cmd_parts += ["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo"]

        # Add all audio inputs
        for (apath, _, _) in audio_inputs:
            cmd_parts += ["-i", str(apath)]

        # Build filter_complex
        n_audio = len(audio_inputs)
        filters = []
        mix_inputs = ["[base]"]

        # Base silence track (input 1)
        filters.append(f"[1]atrim=0:{duration},asetpts=PTS-STARTPTS[base]")

        for i, (apath, start_sec, vol_db) in enumerate(audio_inputs):
            input_idx = i + 2  # 0=video, 1=silence, 2+=audio
            label = f"a{i}"
            delay_ms = int(start_sec * 1000)
            parts = []
            if delay_ms > 0:
                parts.append(f"adelay={delay_ms}|{delay_ms}")
            if vol_db != 0:
                parts.append(f"volume={vol_db}dB")
            parts.append(f"apad=whole_dur={duration}")
            filter_str = ",".join(parts)
            filters.append(f"[{input_idx}]{filter_str}[{label}]")
            mix_inputs.append(f"[{label}]")

        # Mix all together
        mix_count = len(mix_inputs)
        mix_labels = "".join(mix_inputs)
        filters.append(f"{mix_labels}amix=inputs={mix_count}:duration=first:normalize=0[mixed]")

        filter_complex = ";".join(filters)
        cmd_parts += ["-filter_complex", filter_complex]
        cmd_parts += ["-map", "0:v", "-map", "[mixed]"]
        cmd_parts += ["-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k"]
        cmd_parts += ["-shortest", str(target)]

        try:
            result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and target.exists():
                size_mb = target.stat().st_size / (1024 * 1024)
                print(f"    ✓ {target.name} ({size_mb:.1f} MB)")
                count += 1
            else:
                print(f"    ✗ ffmpeg error: {result.stderr[-200:]}")
        except Exception as e:
            print(f"    ✗ {str(e)[:100]}")

    print(f"\n{'═' * 60}")
    print(f"  MIX: {count} клипов собрано")
    print(f"{'═' * 60}")


def cmd_assemble():
    """Concatenate all final clips into one movie."""
    config = load_config()
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    # Collect clips in order
    clip_files = []
    for clip in config["clips"]:
        cid = clip["clip_id"]
        final = VOICED_DIR / f"{cid}_final.mp4"
        if final.exists():
            clip_files.append(final)
        else:
            print(f"  ⚠ Пропуск {cid} (нет _final.mp4)")

    if not clip_files:
        print("  ✗ Нет клипов для склейки")
        return

    print(f"\n{'═' * 60}")
    print(f"  ASSEMBLE: Склейка {len(clip_files)} клипов")
    print(f"{'═' * 60}")

    for f in clip_files:
        print(f"  → {f.name}")

    # Create concat list
    concat_file = FINAL_DIR / "concat.txt"
    with open(concat_file, "w") as f:
        for cf in clip_files:
            f.write(f"file '{cf.resolve()}'\n")

    target = FINAL_DIR / "signal_episode_01.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        str(target),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and target.exists():
            size_mb = target.stat().st_size / (1024 * 1024)
            dur = _get_audio_duration(target)
            print(f"\n  ✓ Финальный ролик: {target.name}")
            print(f"    {size_mb:.1f} MB, {dur:.0f} сек")
        else:
            print(f"  ✗ Ошибка: {result.stderr[-200:]}")
    except Exception as e:
        print(f"  ✗ {str(e)[:100]}")

    # Cleanup
    concat_file.unlink(missing_ok=True)

    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════════════════════
#  UPLOAD: Upload video + dialogues to ElevenLabs Dubbing Studio
# ══════════════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print("ОШИБКА: audio_config.json не найден. Запустите --init сначала.")
        sys.exit(1)
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def save_config(config: dict):
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def strip_audio(video_path: Path) -> Path:
    """Replace VEO audio with silence. Returns path to silent video.

    VEO часто генерирует аудио вместе с видео — это мешает озвучке в ElevenLabs.
    ElevenLabs ТРЕБУЕТ аудиодорожку, поэтому заменяем на тишину (не удаляем).
    Создаёт {name}_silent.mp4 рядом с оригиналом.
    """
    # Already silent — return as is
    if "_silent" in video_path.stem:
        print(f"      Уже silent: {video_path.name}")
        return video_path

    silent_path = video_path.parent / f"{video_path.stem}_silent.mp4"

    if silent_path.exists():
        print(f"      Кэш: {silent_path.name}")
        return silent_path

    # Replace audio with silent track (ElevenLabs requires audio stream)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "64k",
        "-map", "0:v", "-map", "1:a",
        "-shortest",
        str(silent_path),
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        print(f"      ✗ ffmpeg strip ошибка: {result.stderr.decode()[:200]}")
        return video_path  # fallback to original

    size_kb = silent_path.stat().st_size / 1024
    print(f"      ✓ Аудио удалено: {silent_path.name} ({size_kb:.0f} KB)")
    return silent_path


def cmd_strip_audio():
    """Strip VEO-generated audio from all video clips."""
    print("═" * 60)
    print("  STRIP AUDIO: Удаление аудио VEO из видеоклипов")
    print("═" * 60)

    clips = list(CLIPS_DIR.glob("*.mp4"))
    if not clips:
        print("  Нет видеоклипов в output/clips/")
        return

    count = 0
    for vpath in sorted(clips):
        # Skip already-stripped files
        if "_silent" in vpath.stem:
            continue
        print(f"\n  {vpath.name}:")
        result = strip_audio(vpath)
        if result != vpath:
            count += 1

    print(f"\n{'═' * 60}")
    print(f"  Обработано: {count} клипов (аудио удалено)")
    print(f"{'═' * 60}")


def build_csv(dialogues: list[dict]) -> str:
    """Build CSV string for Dubbing API manual mode."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["speaker", "start_time", "end_time", "transcription", "translation"])
    for d in dialogues:
        writer.writerow([
            d["speaker"],
            f"{d['start_sec']:.3f}",
            f"{d['end_sec']:.3f}",
            d["text_ru"],   # "transcription" = source text
            d["text_ru"],   # "translation" = same (ru → ru, not translating)
        ])
    return output.getvalue()


def upload_clip(clip_id: str, video_path: str | None = None):
    """Upload a single clip to ElevenLabs Dubbing Studio with SFX background."""
    config = load_config()
    clip = next((c for c in config["clips"] if c["clip_id"] == clip_id), None)

    if not clip:
        print(f"ОШИБКА: Клип {clip_id} не найден в audio_config.json")
        return

    # Find video file — try multiple naming patterns
    if video_path:
        vpath = Path(video_path)
    else:
        candidates = [
            CLIPS_DIR / f"{clip_id}_clip_silent.mp4",
            CLIPS_DIR / f"{clip_id}_silent.mp4",
            CLIPS_DIR / f"{clip_id}_clip.mp4",
            CLIPS_DIR / f"{clip_id}.mp4",
        ]
        vpath = next((p for p in candidates if p.exists()), None)

    if not vpath or not vpath.exists():
        print(f"ОШИБКА: Видео не найдено для {clip_id}")
        print(f"  Проверены: {clip_id}_clip_silent.mp4, {clip_id}_clip.mp4, {clip_id}.mp4")
        return

    # Check if already uploaded
    if clip.get("dubbing_id"):
        print(f"  [{clip_id}] Уже загружен: dubbing_id={clip['dubbing_id']}")
        print(f"  Studio: {clip.get('studio_url', 'N/A')}")
        print(f"  Для перезагрузки удалите dubbing_id из audio_config.json")
        return

    has_dialogues = bool(clip["dialogues"])

    # Check voice_id availability
    if has_dialogues:
        speakers = set(d["speaker"] for d in clip["dialogues"])
        missing = [s for s in speakers if s not in config["voice_cast"]]
        if missing:
            print(f"  ⚠ Нет voice_id для: {', '.join(missing)}")
            print(f"  Загружу проект, но голоса придётся назначить вручную в Studio")

    # Step 0: Strip VEO audio — озвучку делаем с нуля в ElevenLabs
    print(f"\n  [{clip_id}] Подготовка видео...")
    vpath = strip_audio(vpath)

    print(f"    Видео: {vpath}")
    if has_dialogues:
        print(f"    Диалогов: {len(clip['dialogues'])}")

    # Step 1: Generate SFX background if needed
    bg_path = None
    layers = get_sound_layers(clip_id)
    if layers:
        print(f"\n    Генерация фоновых звуков ({len(layers)} слоёв)...")
        bg_path = generate_clip_sfx(clip)

    # Step 2: Build CSV (only if dialogues exist)
    csv_content = None
    if has_dialogues:
        # Enrich dialogues with emotion analysis
        scene_desc = clip.get("scene_description_ru", "")
        for d in clip["dialogues"]:
            emotion = analyze_emotion(d, scene_desc, clip_id)
            d["_emotion"] = emotion

        csv_content = build_csv(clip["dialogues"])
        print(f"\n    CSV:")
        for line in csv_content.strip().split("\n")[1:]:
            print(f"      {line}")

        # Show emotion settings
        print(f"    Эмоции:")
        for d in clip["dialogues"]:
            em = d.get("_emotion", {})
            mod_label = f" ({d['modifier']})" if d.get("modifier") else ""
            print(f"      {d['speaker']}{mod_label}: stability={em.get('stability', '?')}, style={em.get('style', '?')}")

    # Step 3: Create dubbing project
    print(f"\n    Создаю проект...")
    with open(vpath, "rb") as video_file:
        files = {
            "file": (vpath.name, video_file, "video/mp4"),
        }
        if csv_content:
            files["csv_file"] = ("dialogues.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")
        # NOTE: background_audio_file + CSV combo causes 500 error in ElevenLabs API
        # So we only include bg audio when there's NO CSV. SFX will be mixed locally after download.
        if bg_path and bg_path.exists() and not csv_content:
            files["background_audio_file"] = (bg_path.name, open(bg_path, "rb"), "audio/mpeg")
            print(f"    Фоновый звук: {bg_path.name}")
        elif bg_path and csv_content:
            print(f"    ℹ SFX будет наложен локально (API баг: CSV + bg audio = 500)")

        data = {
            "name": f"Signal - {clip_id}",
            "source_lang": "ru",
            "target_lang": "ru",
            "mode": "manual",
            "dubbing_studio": "true",
            "highest_resolution": "true",
        }
        if not has_dialogues:
            data["num_speakers"] = "0"

        resp = api_post("/dubbing", files=files, data=data)

    if resp.status_code not in (200, 201):
        print(f"    ✗ Ошибка создания: {resp.status_code}")
        print(f"      {resp.text[:500]}")
        return

    result = resp.json()
    dubbing_id = result["dubbing_id"]
    print(f"    ✓ Проект создан: {dubbing_id}")

    # Step 4: Wait for processing
    print(f"    Жду обработки...")
    if not wait_for_dubbing(dubbing_id):
        print(f"    ✗ Обработка не завершилась")
        clip["dubbing_id"] = dubbing_id
        clip["studio_url"] = f"https://elevenlabs.io/app/dubbing (проект: {dubbing_id})"
        save_config(config)
        return

    # Step 5: Try to assign voices and trigger dubbing via Resource API
    # Note: Resource API is in closed beta — may return 401
    if has_dialogues:
        print(f"    Пробую назначить голоса через API...")
        resp = api_get(f"/dubbing/resource/{dubbing_id}")
        if resp.status_code == 200:
            resource = resp.json()
            speaker_tracks = resource.get("speaker_tracks", {})

            for track_id, track_info in speaker_tracks.items():
                speaker_name = track_info.get("speaker_name", "")
                voice_id = config["voice_cast"].get(speaker_name, {}).get("voice_id", "")

                if voice_id:
                    speaker_emotion = {"stability": 0.5, "similarity": 0.8, "style": 0.35}
                    for d in clip["dialogues"]:
                        if d["speaker"] == speaker_name and "_emotion" in d:
                            speaker_emotion = d["_emotion"]
                            break

                    print(f"    Назначаю голос: {speaker_name} → {voice_id[:12]}...")
                    patch_resp = api_patch(
                        f"/dubbing/resource/{dubbing_id}/speaker/{track_id}",
                        json={
                            "speaker_name": speaker_name,
                            "voice_id": voice_id,
                            "voice_stability": speaker_emotion["stability"],
                            "voice_similarity": speaker_emotion["similarity"],
                            "voice_style": speaker_emotion["style"],
                        }
                    )
                    if patch_resp.status_code == 200:
                        print(f"      ✓ {speaker_name}")
                    else:
                        print(f"      ✗ {patch_resp.status_code}: {patch_resp.text[:200]}")

            # Trigger dubbing
            all_segments = list(resource.get("speaker_segments", {}).keys())
            if all_segments:
                dub_resp = api_post(
                    f"/dubbing/resource/{dubbing_id}/dub",
                    json={"segments": all_segments, "languages": ["ru"]}
                )
                if dub_resp.status_code == 200:
                    print(f"    ✓ Озвучка запущена для {len(all_segments)} сегментов")
                else:
                    print(f"    ⚠ Генерацию озвучки запусти вручную в Studio")
        elif resp.status_code in (401, 403):
            print(f"    ℹ Resource API в closed beta — назначь голоса вручную в Studio")
            print(f"    Рекомендуемые настройки:")
            for d in clip["dialogues"]:
                em = d.get("_emotion", {})
                vid = config["voice_cast"].get(d["speaker"], {}).get("voice_id", "нет")
                mod = f" ({d['modifier']})" if d.get("modifier") else ""
                print(f"      {d['speaker']}{mod}: voice={vid[:12]}... stab={em.get('stability','?')} style={em.get('style','?')}")
        else:
            print(f"    ⚠ Ошибка Resource API: {resp.status_code}")

    # Save dubbing_id
    studio_url = f"https://elevenlabs.io/app/dubbing (проект: {dubbing_id})"
    clip["dubbing_id"] = dubbing_id
    clip["studio_url"] = studio_url
    save_config(config)

    print(f"\n{'═' * 60}")
    print(f"  ✓ {clip_id} загружен в ElevenLabs Dubbing Studio!")
    print(f"  Dubbing ID: {dubbing_id}")
    print(f"  Studio URL: {studio_url}")
    print(f"{'═' * 60}")


def upload_all():
    """Upload all clips (with dialogues and/or SFX)."""
    config = load_config()

    print("═" * 60)
    print("  UPLOAD ALL: Загрузка всех клипов")
    print("═" * 60)

    count = 0
    for clip in config["clips"]:
        if clip.get("dubbing_id"):
            continue
        # Upload if clip has dialogues OR has sound design
        has_dialogues = bool(clip["dialogues"])
        has_sfx = bool(get_sound_layers(clip["clip_id"]))
        if has_dialogues or has_sfx:
            upload_clip(clip["clip_id"])
            count += 1
            time.sleep(2)  # rate limit buffer

    print(f"\n{'═' * 60}")
    print(f"  Загружено клипов: {count}")
    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS: Show progress table
# ══════════════════════════════════════════════════════════════════════════════

def show_status():
    """Show progress table for all clips."""
    config = load_config()

    print("═" * 90)
    print("  STATUS: Прогресс озвучки")
    print("═" * 90)
    print(f"  {'Клип':<8} {'Реп.':<5} {'SFX':<8} {'Upload':<9} {'Dubbed':<9} {'Mixed':<8} {'Спикеры':<15}")
    print("  " + "─" * 78)

    for clip in config["clips"]:
        clip_id = clip["clip_id"]
        n_dlg = len(clip["dialogues"])
        speakers = ", ".join(set(d["speaker"] for d in clip["dialogues"])) if n_dlg else "—"

        # SFX status
        layers = get_sound_layers(clip_id)
        sfx_mix = SFX_DIR / f"{clip_id}_mix.mp3"
        sfx_s = "✓" if sfx_mix.exists() else (f"○ ({len(layers)})" if layers else "—")

        # Upload status
        upload_s = "✓" if clip.get("dubbing_id") else ("○" if (n_dlg or layers) else "—")

        # Dubbed/downloaded status
        dubbed_file = VOICED_DIR / f"{clip_id}_dubbed.mp4"
        dub_s = "✓" if dubbed_file.exists() else ("○" if clip.get("dubbing_id") else "—")

        # Final mix status
        final_file = VOICED_DIR / f"{clip_id}_final.mp4"
        mix_s = "✓" if final_file.exists() else "○"

        print(f"  {clip_id:<8} {n_dlg:<5} {sfx_s:<8} {upload_s:<9} {dub_s:<9} {mix_s:<8} {speakers:<15}")

    # Legend
    print(f"\n  ✓ = готово, ○ = ожидает, — = не нужно")

    # Studio URLs
    uploaded = [c for c in config["clips"] if c.get("dubbing_id")]
    if uploaded:
        print(f"\n  Проекты ElevenLabs:")
        for clip in uploaded:
            print(f"    {clip['clip_id']}: {clip['dubbing_id']}")

    # Voice cast status
    print(f"\n  Голоса персонажей:")
    for name, info in config["voice_cast"].items():
        vid = info.get("voice_id", "")
        status = f"✓ {vid[:12]}..." if vid else "✗ НЕТ"
        print(f"    {name:<10} {status}")

    missing = [name for name, vid in VOICE_CAST.items() if not vid]
    if missing:
        print(f"\n  ⚠ Нет voice_id: {', '.join(missing)}")

    # Final movie
    final_movie = FINAL_DIR / "signal_episode_01.mp4"
    if final_movie.exists():
        size_mb = final_movie.stat().st_size / (1024 * 1024)
        print(f"\n  Финальный ролик: {final_movie} ({size_mb:.1f} MB)")


# ══════════════════════════════════════════════════════════════════════════════
#  PLAYWRIGHT: Автоматизация ElevenLabs Dubbing Studio
# ══════════════════════════════════════════════════════════════════════════════

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
if (!window.chrome) { window.chrome = {}; }
if (!window.chrome.runtime) {
    window.chrome.runtime = { connect: function() {}, sendMessage: function() {} };
}
Object.defineProperty(navigator, 'languages', {
    get: () => ['ru-RU', 'ru', 'en-US', 'en']
});
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const p = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {name: 'Native Client', filename: 'internal-nacl-plugin'},
        ];
        p.length = 3;
        return p;
    }
});
"""


def _human_delay(min_s=0.3, max_s=0.8):
    """Short random delay."""
    time.sleep(random.uniform(min_s, max_s))


def _human_delay_medium(min_s=1.5, max_s=3.5):
    """Medium delay for UI transitions."""
    time.sleep(random.uniform(min_s, max_s))


def _human_click(page, selector_or_element, timeout=10000):
    """Click with human-like behavior."""
    _human_delay(0.1, 0.4)
    if isinstance(selector_or_element, str):
        el = page.wait_for_selector(selector_or_element, timeout=timeout)
    else:
        el = selector_or_element
    if el:
        box = el.bounding_box()
        if box:
            x = box["x"] + box["width"] * random.uniform(0.25, 0.75)
            y = box["y"] + box["height"] * random.uniform(0.25, 0.75)
            page.mouse.move(x, y, steps=random.randint(8, 20))
            _human_delay(0.03, 0.1)
            page.mouse.click(x, y)
        else:
            el.click()
    _human_delay(0.08, 0.3)


def _take_screenshot(page, name):
    """Save debug screenshot."""
    try:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOTS_DIR / f"{name}.png"
        page.screenshot(path=str(path))
        print(f"    Screenshot: {path.name}")
    except Exception:
        pass


def el_launch_browser(pw, headless=False):
    """Launch Chromium with persistent ElevenLabs session."""
    EL_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    # Remove stale lock files
    for lock_file in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        lock_path = EL_SESSION_DIR / lock_file
        if lock_path.exists():
            lock_path.unlink()

    vp_w = 1440 + random.randint(-20, 20)
    vp_h = 900 + random.randint(-15, 15)
    print(f"  Запуск браузера (session: {EL_SESSION_DIR.name})")
    print(f"  Viewport: {vp_w}x{vp_h}")

    ctx = pw.chromium.launch_persistent_context(
        str(EL_SESSION_DIR),
        headless=headless,
        viewport={"width": vp_w, "height": vp_h},
        locale="ru-RU",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-features=AutomationControlled",
            "--disable-infobars",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            f"--window-size={vp_w + random.randint(0, 10)},{vp_h + random.randint(50, 80)}",
        ],
    )
    ctx.add_init_script(STEALTH_JS)
    return ctx


def el_check_logged_in(page) -> bool:
    """Check if user is logged into ElevenLabs."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        time.sleep(3)

        url = page.url
        # Login/signup pages → not logged in
        if any(x in url for x in ["/sign-in", "/login", "/sign-up", "/welcome"]):
            return False

        # "Welcome back" form → login page
        welcome = page.query_selector('h1:has-text("Welcome back"), h2:has-text("Welcome back")')
        if welcome:
            return False

        # Check for authenticated elements in sidebar/nav
        auth_selectors = [
            'nav a[href="/app/speech-synthesis"]',
            'nav a[href="/app/dubbing"]',
            'a[href="/app/voice-library"]',
            '[data-testid="user-menu"]',
            'button[aria-label="User menu"]',
            'img[alt*="avatar" i]',
            'img[alt*="profile" i]',
        ]
        for sel in auth_selectors:
            el = page.query_selector(sel)
            if el:
                return True

        # If URL contains /app/ — likely logged in
        if "/app/" in url:
            return True

        return False
    except Exception:
        return False


def el_navigate_to_dubbing(page):
    """Navigate to the Dubbing page listing all projects."""
    print("  Переход на страницу Dubbing...")
    page.goto(EL_DUBBING_URL, wait_until="domcontentloaded", timeout=30000)
    _human_delay_medium(2, 4)
    _take_screenshot(page, "el_dubbing_page")


def el_open_project(page, dubbing_id: str, clip_id: str = "") -> bool:
    """Open a specific dubbing project in the Studio.

    Strategy: navigate to /app/dubbing, find the row with project name, click it.
    ElevenLabs dubbing list is a table with clickable rows.
    """
    project_name = f"Signal - {clip_id}" if clip_id else ""
    search_text = project_name or dubbing_id[:12]
    print(f"    Открываю проект {search_text}...")

    # Navigate to dubbing list
    page.goto(EL_DUBBING_URL, wait_until="domcontentloaded", timeout=60000)
    _human_delay_medium(4, 7)
    # Wait for project list to appear
    page.wait_for_selector('text="Recent Dubs"', timeout=15000).wait_for_element_state("visible")
    _human_delay(1, 2)
    _take_screenshot(page, f"el_list_before_{clip_id}")

    # Debug: dump all visible text elements that contain our project name
    debug_info = page.evaluate(f"""() => {{
        const searchText = "{search_text}";
        const results = [];
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
        while (walker.nextNode()) {{
            const el = walker.currentNode;
            const text = (el.innerText || '').trim();
            if (text.includes(searchText) && text.length < 200) {{
                results.push({{
                    tag: el.tagName,
                    text: text.substring(0, 100),
                    clickable: el.tagName === 'A' || el.tagName === 'BUTTON' || el.onclick != null || el.getAttribute('role') === 'button',
                    href: el.href || '',
                    classes: (el.className || '').substring(0, 80)
                }});
            }}
        }}
        return results;
    }}""")
    print(f"    Элементов с '{search_text}': {len(debug_info)}")
    for d in debug_info[:5]:
        print(f"      <{d['tag']}> click={d['clickable']} cls={d['classes'][:40]} text={d['text'][:60]}")

    # Strategy 1: Find and click any clickable element (a, button) with project name
    for d in debug_info:
        if d.get("clickable") and d.get("href"):
            print(f"    Найдена ссылка: {d['href'][:80]}")
            page.goto(d["href"], wait_until="domcontentloaded", timeout=30000)
            _human_delay_medium(3, 5)
            if _is_studio_page(page):
                print(f"    ✓ Проект открыт по ссылке")
                return True

    # Strategy 2: Click the BUTTON element with matching text (ElevenLabs uses <button class="contents cursor-pointer">)
    clicked = page.evaluate(f"""() => {{
        const searchText = "{search_text}";
        // Priority 1: find a <button> that contains the text (most reliable)
        const buttons = document.querySelectorAll('button');
        for (const btn of buttons) {{
            if (btn.innerText && btn.innerText.includes(searchText) && btn.innerText.length < 200) {{
                btn.click();
                return {{clicked: true, tag: 'BUTTON', text: btn.innerText.substring(0, 60)}};
            }}
        }}
        // Priority 2: find an <a> link with the text
        const links = document.querySelectorAll('a');
        for (const a of links) {{
            if (a.innerText && a.innerText.includes(searchText)) {{
                a.click();
                return {{clicked: true, tag: 'A', text: a.innerText.substring(0, 60)}};
            }}
        }}
        // Priority 3: any clickable-looking element
        const all = document.querySelectorAll('[role="button"], [role="link"], [class*="cursor-pointer"]');
        for (const el of all) {{
            if (el.innerText && el.innerText.includes(searchText) && el.innerText.length < 200) {{
                el.click();
                return {{clicked: true, tag: el.tagName, text: el.innerText.substring(0, 60)}};
            }}
        }}
        return {{clicked: false}};
    }}""")
    if clicked.get("clicked"):
        print(f"    Кликнул: <{clicked.get('tag')}> {clicked.get('text', '')[:50]}")
        # Wait for SPA navigation + Studio page load
        _human_delay_medium(5, 8)
        _take_screenshot(page, f"el_after_click_{clip_id}")
        if _is_studio_page(page):
            print(f"    ✓ Проект открыт кликом")
            return True
        # Maybe still loading, wait more
        _human_delay_medium(3, 5)
        if _is_studio_page(page):
            print(f"    ✓ Проект открыт кликом (после ожидания)")
            return True

    # Strategy 3: Click "..." menu on the right side of the row, then "Edit"
    print(f"    Пробую '...' меню...")
    page.goto(EL_DUBBING_URL, wait_until="domcontentloaded", timeout=30000)
    _human_delay_medium(2, 4)

    # Find all "..." buttons using broader selectors
    dots_count = page.evaluate("""() => {
        const buttons = document.querySelectorAll('button');
        let dots = [];
        buttons.forEach((b, i) => {
            const text = (b.innerText || '').trim();
            const svg = b.querySelector('svg');
            // "..." buttons often have just dots or an SVG with no text
            if (text === '...' || text === '…' || text === '⋯' || text === '•••' ||
                (svg && text.length <= 1)) {
                dots.push(i);
            }
        });
        return dots;
    }""")
    print(f"    '...' кнопок (индексы): {dots_count[:10]}")

    for btn_idx in dots_count:
        try:
            # Check if this button's row contains our project name
            is_match = page.evaluate(f"""(idx) => {{
                const btn = document.querySelectorAll('button')[idx];
                const row = btn.closest('tr') || btn.closest('[class*="row"]') || btn.parentElement.parentElement;
                return row && row.innerText.includes("{search_text}");
            }}""", btn_idx)
            if not is_match:
                continue

            print(f"    Кликаю '...' кнопку #{btn_idx}...")
            page.evaluate(f"""(idx) => document.querySelectorAll('button')[idx].click()""", btn_idx)
            _human_delay(0.5, 1.5)
            _take_screenshot(page, f"el_dots_menu_{clip_id}")

            # Look for Edit/Open in dropdown
            edit_clicked = page.evaluate("""() => {
                const items = document.querySelectorAll('[role="menuitem"], [role="option"], button, a');
                for (const item of items) {
                    const text = (item.innerText || '').trim().toLowerCase();
                    if (text === 'edit' || text === 'open' || text === 'open in studio') {
                        item.click();
                        return true;
                    }
                }
                return false;
            }""")
            if edit_clicked:
                _human_delay_medium(3, 5)
                if _is_studio_page(page):
                    print(f"    ✓ Проект открыт через '...' меню")
                    return True
            else:
                page.keyboard.press("Escape")
                _human_delay(0.3, 0.5)
        except Exception as e:
            print(f"    ... ошибка: {str(e)[:100]}")
            continue

    print(f"    ✗ Не удалось открыть проект")
    _take_screenshot(page, f"el_project_not_found_{clip_id or dubbing_id[:8]}")
    return False


def _is_studio_page(page) -> bool:
    """Check if current page is the Dubbing Studio editor (not the list)."""
    # Check for "Page not found"
    not_found = page.query_selector('text="Page not found"')
    if not_found:
        return False
    # Check for "Recent Dubs" (this is the list page, NOT studio)
    recent = page.query_selector('text="Recent Dubs"')
    if recent and recent.is_visible():
        return False
    # Check for studio-specific elements: timeline tracks, video player, speaker cards
    studio_selectors = [
        'video',                          # video player
        'text="Original sound"',          # timeline label
        'text="Foreground"',              # timeline label
        'text="Background"',              # timeline label
        'text="Export"',                   # export button
        'text="Generate Stale Audio"',    # generate button
        'text="Transcribe Audio"',        # transcribe button
        '[class*="timeline"]',
        '[class*="waveform"]',
    ]
    for sel in studio_selectors:
        el = page.query_selector(sel)
        if el:
            return True
    return False


def el_assign_voice(page, speaker_name: str, voice_id: str, emotion: dict) -> bool:
    """Assign a voice to a speaker track in Dubbing Studio.

    Steps:
    1. Find the speaker track/card by name
    2. Click the voice settings (cog icon)
    3. Select "Voice Library" option
    4. Search for voice by ID or switch to custom voice
    5. Set emotion parameters
    """
    print(f"    Назначаю голос: {speaker_name} → {voice_id[:12]}...")

    # Find speaker track — look for speaker name in the timeline/tracks area
    speaker_elements = page.query_selector_all(
        f'[class*="speaker"]:has-text("{speaker_name}"), '
        f'[class*="track"]:has-text("{speaker_name}"), '
        f'span:has-text("{speaker_name}")'
    )

    if not speaker_elements:
        print(f"      ✗ Не найден спикер {speaker_name}")
        return False

    # Click on speaker name to open settings
    speaker_el = speaker_elements[0]
    _human_click(page, speaker_el)
    _human_delay(0.5, 1)

    # Look for voice settings cog/gear icon near the speaker
    cog_btn = page.query_selector(
        '[class*="speaker"] button[aria-label*="settings"], '
        '[class*="speaker"] button[aria-label*="voice"], '
        'button[class*="cog"], button[class*="gear"], '
        '[class*="track-settings"]'
    )
    if cog_btn:
        _human_click(page, cog_btn)
        _human_delay(0.5, 1)

    # Look for voice selection — "Voice Library" or voice ID input
    # Try to find the voice ID input field
    voice_input = page.query_selector(
        'input[placeholder*="voice"], input[placeholder*="Voice"], '
        'input[placeholder*="search"], input[aria-label*="voice"]'
    )

    if voice_input:
        # Clear and type voice ID
        voice_input.fill("")
        _human_delay(0.2, 0.4)
        voice_input.fill(voice_id)
        _human_delay(1, 2)

        # Select from dropdown
        option = page.query_selector(f'[class*="option"]:first-child, [role="option"]:first-child')
        if option:
            _human_click(page, option)
            _human_delay(0.5, 1)

    # Set emotion parameters (stability, similarity, style)
    _el_set_voice_params(page, emotion)

    print(f"      ✓ {speaker_name}")
    return True


def _el_set_voice_params(page, emotion: dict):
    """Set voice parameters (stability, similarity, style) via sliders."""
    param_map = {
        "stability": emotion.get("stability", 0.5),
        "similarity": emotion.get("similarity", 0.8),
        "style": emotion.get("style", 0.35),
    }

    for param_name, value in param_map.items():
        # Find slider by label
        slider = page.query_selector(
            f'input[type="range"][aria-label*="{param_name}" i], '
            f'[class*="slider"][aria-label*="{param_name}" i], '
            f'label:has-text("{param_name}") + input[type="range"], '
            f'label:has-text("{param_name}") ~ input[type="range"]'
        )
        if slider:
            # Set slider value via JS
            page.evaluate(
                f"""(el) => {{
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value'
                    ).set;
                    nativeInputValueSetter.call(el, {value});
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}""",
                slider,
            )
            _human_delay(0.3, 0.6)


def el_switch_to_russian(page) -> bool:
    """Switch to the Russian language tab in Dubbing Studio."""
    print(f"    Переключаю на Russian...")

    # Find "Russian" tab/button
    russian_btn = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = (btn.innerText || '').trim();
            if (text === 'Russian' || text === 'Русский') {
                btn.click();
                return {clicked: true, text};
            }
        }
        return {clicked: false};
    }""")
    if russian_btn.get("clicked"):
        _human_delay_medium(2, 4)
        print(f"    ✓ Переключил на {russian_btn.get('text')}")
        return True

    print(f"    ⚠ Кнопка Russian не найдена")
    return False


def el_trigger_dub(page) -> bool:
    """Click the 'Generate Stale Audio' button to start dubbing generation.

    IMPORTANT: Must click the GLOBAL 'Generate Stale Audio' button at the bottom,
    NOT the per-speaker 'Generate Audio' button on the card.
    """
    print(f"    Запускаю генерацию...")

    # Priority 1: Click "Generate Stale Audio" (exact match — the global button)
    gen_btn = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        // Pass 1: exact "Generate Stale Audio"
        for (const btn of btns) {
            const text = (btn.innerText || '').trim();
            if (text === 'Generate Stale Audio') {
                btn.click();
                return {clicked: true, text};
            }
        }
        // Pass 2: "Dub All" or similar global generate button
        for (const btn of btns) {
            const text = (btn.innerText || '').trim();
            if (text === 'Dub All' || text === 'Dub all' || text === 'Generate All') {
                btn.click();
                return {clicked: true, text};
            }
        }
        return {clicked: false};
    }""")
    if gen_btn.get("clicked"):
        _human_delay_medium(2, 4)
        print(f"    ✓ Нажал: '{gen_btn.get('text')}'")
        return True

    print(f"    ✗ Кнопка 'Generate Stale Audio' не найдена")
    _take_screenshot(page, "el_no_generate_btn")
    return False


def el_wait_for_dub_complete(page, timeout_sec=300) -> bool:
    """Wait for dubbing generation to complete in Studio.

    After clicking 'Generate Stale Audio', the button text changes to
    a progress indicator or disappears. When done, the audio tracks
    become editable/playable and the 'Generate Stale Audio' button
    either disappears or changes.
    """
    print(f"    Жду завершения генерации (таймаут {timeout_sec}s)...")
    start = time.time()

    # First, wait a moment and check if generation is actually running
    _human_delay(3, 5)

    while time.time() - start < timeout_sec:
        elapsed = int(time.time() - start)

        try:
            gen_status = page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                let hasGenerateBtn = false;
                let hasProgressIndicator = false;
                for (const btn of btns) {
                    const text = (btn.innerText || '').trim();
                    if (text === 'Generate Stale Audio') hasGenerateBtn = true;
                    if (text.includes('Generating') || text.includes('Processing'))
                        hasProgressIndicator = true;
                }
                const spinners = document.querySelectorAll(
                    '[class*="spinner"], [class*="loading"], [role="progressbar"], ' +
                    '[class*="animate-spin"]'
                );
                return {
                    hasGenerateBtn,
                    hasProgressIndicator,
                    isLoading: spinners.length > 0
                };
            }""")
        except Exception as e:
            err_name = type(e).__name__
            if "TargetClosed" in err_name or "closed" in str(e).lower():
                print(f"    ⚠ Страница закрылась во время генерации ({elapsed}s)")
                return False
            print(f"    ⚠ Ошибка проверки: {str(e)[:100]}")
            time.sleep(5)
            continue

        if gen_status.get("hasProgressIndicator") or gen_status.get("isLoading"):
            if elapsed % 15 == 0:
                print(f"    ... генерация ({elapsed}s)...")
            time.sleep(5)
            continue

        if not gen_status.get("hasGenerateBtn") and not gen_status.get("isLoading"):
            print(f"    ✓ Генерация завершена ({elapsed}s)")
            _take_screenshot(page, "el_dub_complete")
            return True

        if elapsed > 15 and gen_status.get("hasGenerateBtn") and not gen_status.get("isLoading"):
            print(f"    ✓ Генерация завершена или не требуется ({elapsed}s)")
            _take_screenshot(page, "el_dub_maybe_complete")
            return True

        time.sleep(5)

    print(f"    ✗ Таймаут {timeout_sec}s")
    _take_screenshot(page, "el_dub_timeout")
    return False


def el_download_dubbed(page, clip_id: str) -> Path | None:
    """Download the dubbed audio/video from the Studio.

    Returns path to downloaded file.
    """
    print(f"    Скачиваю результат {clip_id}...")

    # Look for download/export button
    dl_btn = page.query_selector(
        'button:has-text("Download"), button:has-text("Скачать"), '
        'a:has-text("Download"), button:has-text("Export"), '
        'button:has-text("Экспорт")'
    )

    if not dl_btn:
        print(f"    ✗ Кнопка скачивания не найдена")
        _take_screenshot(page, f"el_no_download_{clip_id}")
        return None

    # Set up download handler
    VOICED_DIR.mkdir(parents=True, exist_ok=True)
    target_path = VOICED_DIR / f"{clip_id}_dubbed.mp4"

    with page.expect_download(timeout=120000) as download_info:
        _human_click(page, dl_btn)
        _human_delay(1, 2)

    download = download_info.value
    download.save_as(str(target_path))
    size_mb = target_path.stat().st_size / (1024 * 1024)
    print(f"    ✓ Скачано: {target_path.name} ({size_mb:.1f} MB)")
    return target_path


def cmd_dub_login():
    """Open browser for ElevenLabs login."""
    from playwright.sync_api import sync_playwright

    print("═" * 60)
    print("  DUB LOGIN: Логин в ElevenLabs Dubbing Studio")
    print("═" * 60)

    with sync_playwright() as pw:
        ctx = el_launch_browser(pw, headless=False)
        page = ctx.new_page()
        page.goto(EL_DUBBING_URL, wait_until="domcontentloaded", timeout=30000)
        _human_delay_medium(2, 4)

        if el_check_logged_in(page):
            print("\n  ✓ Уже залогинен в ElevenLabs!")
            _take_screenshot(page, "el_logged_in")
        else:
            print("\n  ⚠ Не залогинен. Залогинься в открытом браузере.")
            print("  Жду до 5 минут для логина...")

            # Wait for user to log in manually
            for i in range(300):
                time.sleep(1)
                if i > 0 and i % 30 == 0:
                    print(f"    ... жду ({i}s)...")
                if el_check_logged_in(page):
                    print(f"\n  ✓ Логин выполнен! (через {i+1}s)")
                    break
            else:
                print("\n  ✗ Таймаут логина (5 мин). Запустите --dub-login ещё раз.")

        _take_screenshot(page, "el_after_login")
        print("\n  Закрываю браузер. Сессия сохранена.")
        ctx.close()

    print(f"{'═' * 60}")


def cmd_dub(clip_id: str):
    """Automate Dubbing Studio for a single clip: assign voices + generate."""
    from playwright.sync_api import sync_playwright

    config = load_config()
    clip = next((c for c in config["clips"] if c["clip_id"] == clip_id), None)
    if not clip:
        print(f"ОШИБКА: Клип {clip_id} не найден")
        return

    dubbing_id = clip.get("dubbing_id")
    if not dubbing_id:
        print(f"ОШИБКА: Клип {clip_id} не загружен. Сначала --upload --clip {clip_id}")
        return

    if not clip["dialogues"]:
        print(f"  [{clip_id}] Нет диалогов — пропускаю (SFX уже в проекте)")
        return

    print(f"\n{'═' * 60}")
    print(f"  DUB: Автоматизация Studio для {clip_id}")
    print(f"  dubbing_id: {dubbing_id}")
    print(f"{'═' * 60}")

    with sync_playwright() as pw:
        ctx = el_launch_browser(pw, headless=False)
        page = ctx.new_page()

        # Check login
        page.goto(EL_DUBBING_URL, wait_until="domcontentloaded", timeout=30000)
        _human_delay_medium(2, 4)

        if not el_check_logged_in(page):
            print("  ✗ Не залогинен. Запустите --dub-login сначала.")
            ctx.close()
            return

        # Open project
        if not el_open_project(page, dubbing_id, clip_id):
            ctx.close()
            return

        _take_screenshot(page, f"el_studio_{clip_id}")

        # Step 1: Switch to Russian tab (where voices need to be assigned)
        el_switch_to_russian(page)
        _take_screenshot(page, f"el_russian_{clip_id}")

        # Step 2: Assign voices to speakers
        scene_desc = clip.get("scene_description_ru", "")
        speakers_done = set()
        for d in clip["dialogues"]:
            speaker = d["speaker"]
            if speaker in speakers_done:
                continue
            speakers_done.add(speaker)

            voice_id = config["voice_cast"].get(speaker, {}).get("voice_id", "")
            if not voice_id:
                print(f"    ⚠ Нет voice_id для {speaker}, пропускаю")
                continue

            emotion = analyze_emotion(d, scene_desc, clip_id)
            el_assign_voice(page, speaker, voice_id, emotion)
            _human_delay(0.5, 1)

        _take_screenshot(page, f"el_voices_assigned_{clip_id}")

        # Step 3: Generate Stale Audio (creates the dubbed Russian audio)
        if el_trigger_dub(page):
            el_wait_for_dub_complete(page, timeout_sec=300)

        _take_screenshot(page, f"el_studio_done_{clip_id}")
        ctx.close()

    print(f"\n{'═' * 60}")
    print(f"  ✓ {clip_id} обработан в Dubbing Studio")
    print(f"{'═' * 60}")


def cmd_dub_all():
    """Automate Dubbing Studio for all clips with dialogues."""
    config = load_config()
    clips_with_dub = [
        c for c in config["clips"]
        if c.get("dubbing_id") and c["dialogues"]
    ]

    if not clips_with_dub:
        print("  Нет клипов для автоматизации (нужно сначала --upload-all)")
        return

    print(f"\n{'═' * 60}")
    print(f"  DUB ALL: Автоматизация Studio для {len(clips_with_dub)} клипов")
    print(f"{'═' * 60}")

    for clip in clips_with_dub:
        cmd_dub(clip["clip_id"])
        _human_delay_medium(2, 4)

    print(f"\n{'═' * 60}")
    print(f"  ✓ Все клипы обработаны")
    print(f"{'═' * 60}")


def cmd_download(clip_id: str):
    """Download dubbed clip from ElevenLabs via Playwright (Export button).

    API download doesn't work for Studio-generated dubs, so we use the browser.
    """
    from playwright.sync_api import sync_playwright

    config = load_config()
    clip = next((c for c in config["clips"] if c["clip_id"] == clip_id), None)
    if not clip:
        print(f"ОШИБКА: Клип {clip_id} не найден")
        return None

    dubbing_id = clip.get("dubbing_id")
    if not dubbing_id:
        print(f"ОШИБКА: Клип {clip_id} не загружен")
        return None

    if not clip["dialogues"]:
        print(f"  [{clip_id}] Нет диалогов — нечего скачивать")
        return None

    print(f"\n  [{clip_id}] Скачивание через браузер...")

    with sync_playwright() as pw:
        ctx = el_launch_browser(pw, headless=False)
        page = ctx.new_page()

        # Check login
        page.goto(EL_DUBBING_URL, wait_until="domcontentloaded", timeout=30000)
        _human_delay_medium(2, 4)

        if not el_check_logged_in(page):
            print("  ✗ Не залогинен.")
            ctx.close()
            return None

        # Open project
        if not el_open_project(page, dubbing_id, clip_id):
            ctx.close()
            return None

        # Switch to Russian to make sure we export the dubbed version
        el_switch_to_russian(page)
        _human_delay(1, 2)
        _take_screenshot(page, f"el_before_export_{clip_id}")

        # Click Export button
        VOICED_DIR.mkdir(parents=True, exist_ok=True)
        target_path = VOICED_DIR / f"{clip_id}_dubbed.mp4"

        try:
            # Step 1: Click the main Export button (opens dialog)
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if ((btn.innerText || '').trim() === 'Export') { btn.click(); return; }
                }
            }""")
            _human_delay_medium(2, 4)
            _take_screenshot(page, f"el_export_dialog_{clip_id}")

            # Step 2: Check dialog content
            dialog_info = page.evaluate("""() => {
                const body = document.body.innerText;
                const btns = document.querySelectorAll('button');
                let exportBtns = [];
                for (const btn of btns) {
                    if ((btn.innerText || '').trim() === 'Export')
                        exportBtns.push(btn.getBoundingClientRect().y);
                }
                return {
                    needsRender: body.includes('must first render'),
                    exportBtnCount: exportBtns.length,
                    exportBtnYs: exportBtns
                };
            }""")
            print(f"    Dialog: render={dialog_info.get('needsRender')}, btns={dialog_info.get('exportBtnCount')}")

            if dialog_info.get("needsRender"):
                print(f"    ⚠ Audio ещё не сгенерирован. Запустите --dub --clip {clip_id} сначала")
                _take_screenshot(page, f"el_needs_render_{clip_id}")
                ctx.close()
                return None

            # Step 3: Click "Download" tab in the Export dialog
            # Find "Download" text node and click its parent element
            dl_result = page.evaluate("""() => {
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                while (walker.nextNode()) {
                    const node = walker.currentNode;
                    if (node.textContent.trim() === 'Download') {
                        let el = node.parentElement;
                        const rect = el.getBoundingClientRect();
                        // Only within dialog area (y between 150-350)
                        if (rect.y > 100 && rect.y < 400) {
                            el.click();
                            return {clicked: true, tag: el.tagName, x: rect.x, y: rect.y};
                        }
                    }
                }
                return {clicked: false};
            }""")
            print(f"    Download tab click: {dl_result}")
            if not dl_result.get("clicked"):
                # Fallback: Click by coords right of "View" button
                view_pos = page.evaluate("""() => {
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    while (walker.nextNode()) {
                        if (walker.currentNode.textContent.trim() === 'View') {
                            const el = walker.currentNode.parentElement;
                            const r = el.getBoundingClientRect();
                            return {x: r.x + r.width + 40, y: r.y + r.height / 2};
                        }
                    }
                    return null;
                }""")
                if view_pos:
                    print(f"    Координатный клик: x={view_pos['x']:.0f} y={view_pos['y']:.0f}")
                    page.mouse.click(view_pos["x"], view_pos["y"])
            _human_delay_medium(2, 3)
            _take_screenshot(page, f"el_download_tab_{clip_id}")

            # Step 4: Listen for network responses + click Export
            # ElevenLabs might render+download via API, returning a URL
            captured_urls = []
            def capture_response(response):
                url = response.url
                ct = response.headers.get("content-type", "")
                if any(x in ct for x in ["video", "audio", "octet-stream"]):
                    captured_urls.append(url)
                if "download" in url.lower() or "export" in url.lower():
                    captured_urls.append(url)
            page.on("response", capture_response)

            # Try with expect_download first, but short timeout
            download_success = False
            try:
                with page.expect_download(timeout=30000) as download_info:
                    page.evaluate("""() => {
                        const btns = document.querySelectorAll('button');
                        let exportBtns = [];
                        for (const btn of btns) {
                            if ((btn.innerText || '').trim() === 'Export')
                                exportBtns.push({btn, y: btn.getBoundingClientRect().y});
                        }
                        exportBtns.sort((a, b) => b.y - a.y);
                        if (exportBtns.length > 0) exportBtns[0].btn.click();
                    }""")
                    print(f"    Жду download event (30s)...")
                download = download_info.value
                download.save_as(str(target_path))
                download_success = True
            except Exception as e:
                print(f"    Download event не сработал: {str(e)[:80]}")
                _take_screenshot(page, f"el_after_export_click_{clip_id}")
                # Check if new tab opened or URL was captured
                print(f"    Captured URLs: {captured_urls[:3]}")

                # Check for new pages
                pages = page.context.pages
                print(f"    Открытых страниц: {len(pages)}")
                for p in pages:
                    pu = p.url
                    if pu != page.url and "dubbing" in pu:
                        print(f"    Новая страница: {pu[:80]}")

            if not download_success:
                # Fallback: Check if dialog changed to show a download link
                dl_link = page.evaluate("""() => {
                    const links = document.querySelectorAll('a[href]');
                    for (const a of links) {
                        const href = a.href;
                        if (href.includes('download') || href.includes('.mp4') || href.includes('blob:'))
                            return {href, text: (a.innerText || '').trim()};
                    }
                    // Check for blob URLs in video elements
                    const videos = document.querySelectorAll('video source, video');
                    for (const v of videos) {
                        const src = v.src || v.currentSrc;
                        if (src) return {href: src, text: 'video_element'};
                    }
                    return null;
                }""")
                if dl_link:
                    print(f"    Найдена ссылка: {dl_link}")
                    # Download via the URL
                    import urllib.request
                    urllib.request.urlretrieve(dl_link["href"], str(target_path))
                    download_success = True
                    print(f"  ✓ Скачано через ссылку")

            page.remove_listener("response", capture_response)

            if download_success and target_path.exists():
                size_mb = target_path.stat().st_size / (1024 * 1024)
                print(f"  ✓ Скачано: {target_path.name} ({size_mb:.1f} MB)")
                ctx.close()
                return target_path
            else:
                print(f"    ✗ Не удалось скачать файл")
                _take_screenshot(page, f"el_download_fail_{clip_id}")
                ctx.close()
                return None
        except Exception as e:
            print(f"    ✗ Ошибка: {str(e)[:200]}")
            _take_screenshot(page, f"el_download_error_{clip_id}")
            try:
                ctx.close()
            except Exception:
                pass
            return None


def cmd_download_all():
    """Download all dubbed clips via browser."""
    config = load_config()

    print(f"\n{'═' * 60}")
    print(f"  DOWNLOAD ALL: Скачивание озвученных клипов")
    print(f"{'═' * 60}")

    count = 0
    for clip in config["clips"]:
        if not clip.get("dubbing_id") or not clip["dialogues"]:
            continue
        result = cmd_download(clip["clip_id"])
        if result:
            count += 1
        time.sleep(2)

    print(f"\n{'═' * 60}")
    print(f"  Скачано: {count} клипов")
    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════════════════════
#  MIX: Наложение SFX + голос → финальный клип
# ══════════════════════════════════════════════════════════════════════════════

def mix_clip_audio(clip_id: str, video_path: str | None = None) -> Path | None:
    """Mix SFX background + dubbed audio onto video.

    If the clip was dubbed (has voice), overlay SFX mix as background.
    If the clip has no voice, just overlay SFX directly on video.
    """
    config = load_config()
    clip = next((c for c in config["clips"] if c["clip_id"] == clip_id), None)
    if not clip:
        print(f"ОШИБКА: Клип {clip_id} не найден")
        return None

    duration = clip["duration_sec"]

    # Find video source
    # Priority: dubbed (from ElevenLabs, has voice) > silent > original
    if video_path:
        vpath = Path(video_path)
    else:
        dubbed = VOICED_DIR / f"{clip_id}_dubbed.mp4"
        silent = CLIPS_DIR / f"{clip_id}_silent.mp4"
        silent_clip = CLIPS_DIR / f"{clip_id}_clip_silent.mp4"
        original = CLIPS_DIR / f"{clip_id}.mp4"
        clip_file = CLIPS_DIR / f"{clip_id}_clip.mp4"

        if dubbed.exists():
            vpath = dubbed  # Already has ElevenLabs voice
        elif silent.exists():
            vpath = silent  # VEO audio stripped
        elif silent_clip.exists():
            vpath = silent_clip
        elif original.exists():
            vpath = original
        elif clip_file.exists():
            vpath = clip_file
        else:
            print(f"  [{clip_id}] Видео не найдено")
            return None

    # Find SFX mix
    sfx_mix = SFX_DIR / f"{clip_id}_mix.mp3"
    has_sfx = sfx_mix.exists()

    if not has_sfx:
        print(f"  [{clip_id}] Нет SFX микса — копирую как есть")
        VOICED_DIR.mkdir(parents=True, exist_ok=True)
        target = VOICED_DIR / f"{clip_id}_final.mp4"
        subprocess.run(["cp", str(vpath), str(target)], check=True)
        return target

    VOICED_DIR.mkdir(parents=True, exist_ok=True)
    target = VOICED_DIR / f"{clip_id}_final.mp4"

    # Check if video has audio
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "a", "-show_entries",
         "stream=codec_type", "-of", "json", str(vpath)],
        capture_output=True, text=True,
    )
    has_audio = '"codec_type": "audio"' in probe.stdout

    if has_audio:
        # Video has audio (dubbed voice) — mix SFX underneath at lower volume
        cmd = [
            "ffmpeg", "-y",
            "-i", str(vpath),
            "-i", str(sfx_mix),
            "-filter_complex",
            "[1:a]volume=-8dB[sfx];"
            "[0:a][sfx]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(duration),
            str(target),
        ]
    else:
        # Video has no audio — just add SFX as audio
        cmd = [
            "ffmpeg", "-y",
            "-i", str(vpath),
            "-i", str(sfx_mix),
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(duration), "-shortest",
            str(target),
        ]

    print(f"  [{clip_id}] Микширование: {vpath.name} + {sfx_mix.name}")
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0:
        print(f"    ✗ ffmpeg ошибка: {result.stderr.decode()[:300]}")
        return None

    size_mb = target.stat().st_size / (1024 * 1024)
    print(f"    ✓ {target.name} ({size_mb:.1f} MB)")
    return target


def cmd_mix(clip_id: str, video_path: str | None = None):
    """Mix a single clip."""
    result = mix_clip_audio(clip_id, video_path)
    if result:
        print(f"\n  Готово: {result}")


def cmd_mix_all():
    """Mix all clips."""
    config = load_config()

    print(f"\n{'═' * 60}")
    print(f"  MIX ALL: Наложение SFX на все клипы")
    print(f"{'═' * 60}")

    count = 0
    for clip in config["clips"]:
        result = mix_clip_audio(clip["clip_id"])
        if result:
            count += 1

    print(f"\n{'═' * 60}")
    print(f"  Готово: {count} клипов")
    print(f"{'═' * 60}")


def cmd_assemble():
    """Assemble all final clips into one movie."""
    config = load_config()

    print(f"\n{'═' * 60}")
    print(f"  ASSEMBLE: Склейка финального ролика")
    print(f"{'═' * 60}")

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    concat_list = []

    for clip in config["clips"]:
        clip_id = clip["clip_id"]
        # Priority: final (mixed) > dubbed > silent > original
        candidates = [
            VOICED_DIR / f"{clip_id}_final.mp4",
            VOICED_DIR / f"{clip_id}_dubbed.mp4",
            CLIPS_DIR / f"{clip_id}_silent.mp4",
            CLIPS_DIR / f"{clip_id}_clip_silent.mp4",
            CLIPS_DIR / f"{clip_id}.mp4",
            CLIPS_DIR / f"{clip_id}_clip.mp4",
        ]

        for p in candidates:
            if p.exists():
                concat_list.append(p)
                print(f"  {clip_id}: {p.name}")
                break
        else:
            print(f"  {clip_id}: ✗ НЕТ ВИДЕО")

    if not concat_list:
        print("  Нет видео для сборки")
        return

    # Write concat file with absolute paths
    import tempfile
    concat_file = Path(tempfile.mktemp(suffix=".txt"))
    with open(concat_file, "w") as f:
        for p in concat_list:
            f.write(f"file '{p.resolve()}'\n")

    output_path = FINAL_DIR / "signal_episode_01.mp4"

    # Need to re-encode for concat (different sources may have different params)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_path),
    ]

    print(f"\n  Склейка {len(concat_list)} клипов...")
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    concat_file.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"  ✗ ffmpeg ошибка: {result.stderr.decode()[:500]}")
        return

    size_mb = output_path.stat().st_size / (1024 * 1024)
    duration = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", str(output_path)],
        capture_output=True, text=True,
    )
    dur_sec = 0
    try:
        dur_sec = float(json.loads(duration.stdout)["format"]["duration"])
    except Exception:
        pass

    print(f"\n{'═' * 60}")
    print(f"  ✓ Финальный ролик: {output_path}")
    print(f"  Размер: {size_mb:.1f} MB, Длительность: {dur_sec:.1f}s")
    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Озвучка мультфильма через ElevenLabs Dubbing Studio"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init", action="store_true",
                       help="Парсинг сценария → audio_config.json")
    group.add_argument("--sfx", action="store_true",
                       help="Сгенерировать фоновые звуки для клипа")
    group.add_argument("--sfx-all", action="store_true",
                       help="Сгенерировать фоновые звуки для всех клипов")
    group.add_argument("--strip-audio", action="store_true",
                       help="Удалить аудио VEO из всех видеоклипов")
    group.add_argument("--upload", action="store_true",
                       help="Загрузить клип в ElevenLabs Dubbing Studio (API)")
    group.add_argument("--upload-all", action="store_true",
                       help="Загрузить все клипы (API)")
    group.add_argument("--dub-login", action="store_true",
                       help="Логин в ElevenLabs (браузер)")
    group.add_argument("--dub", action="store_true",
                       help="Автоматизация Studio: голоса + генерация (браузер)")
    group.add_argument("--dub-all", action="store_true",
                       help="Автоматизация Studio для всех клипов")
    group.add_argument("--download", action="store_true",
                       help="Скачать озвученный клип из ElevenLabs (API)")
    group.add_argument("--download-all", action="store_true",
                       help="Скачать все озвученные клипы")
    group.add_argument("--tts", action="store_true",
                       help="Сгенерировать голоса TTS через API")
    group.add_argument("--mix", action="store_true",
                       help="Наложить SFX на видео")
    group.add_argument("--mix-all", action="store_true",
                       help="Наложить SFX на все клипы")
    group.add_argument("--mix-full", action="store_true",
                       help="Микшировать видео + SFX + голоса → финальные клипы")
    group.add_argument("--assemble", action="store_true",
                       help="Склеить все клипы в финальный ролик")
    group.add_argument("--status", action="store_true",
                       help="Показать прогресс")

    parser.add_argument("--clip", type=str,
                        help="ID клипа (напр. S05_C)")
    parser.add_argument("--video", type=str,
                        help="Путь к видеофайлу (если не в output/clips/)")

    args = parser.parse_args()

    # Check API key for commands that need it
    api_commands = (
        getattr(args, "upload", False) or getattr(args, "upload_all", False) or
        getattr(args, "sfx", False) or getattr(args, "sfx_all", False) or
        getattr(args, "tts", False) or
        getattr(args, "download", False) or getattr(args, "download_all", False)
    )
    if api_commands and not ELEVENLABS_API_KEY:
        print("ОШИБКА: ELEVENLABS_API_KEY не задан в .env")
        sys.exit(1)

    if args.init:
        init_config()
    elif args.sfx:
        if not args.clip:
            print("ОШИБКА: --sfx требует --clip")
            sys.exit(1)
        cmd_sfx(args.clip)
    elif args.sfx_all:
        cmd_sfx(None)
    elif args.strip_audio:
        cmd_strip_audio()
    elif args.upload:
        if not args.clip:
            print("ОШИБКА: --upload требует --clip")
            sys.exit(1)
        upload_clip(args.clip, args.video)
    elif args.upload_all:
        upload_all()
    elif args.dub_login:
        cmd_dub_login()
    elif args.dub:
        if not args.clip:
            print("ОШИБКА: --dub требует --clip")
            sys.exit(1)
        cmd_dub(args.clip)
    elif args.dub_all:
        cmd_dub_all()
    elif args.download:
        if not args.clip:
            print("ОШИБКА: --download требует --clip")
            sys.exit(1)
        cmd_download(args.clip)
    elif args.download_all:
        cmd_download_all()
    elif args.tts:
        cmd_tts(args.clip)
    elif args.mix:
        if not args.clip:
            print("ОШИБКА: --mix требует --clip")
            sys.exit(1)
        cmd_mix(args.clip, args.video)
    elif args.mix_all:
        cmd_mix_all()
    elif args.mix_full:
        cmd_mix_full(args.clip)
    elif args.assemble:
        cmd_assemble()
    elif args.status:
        show_status()


if __name__ == "__main__":
    main()
