"""
СИГНАЛ — Production Dashboard
Streamlit-дашборд для анимационного проекта
v3.0 — interactive review page with phase workflow
"""

import json
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st

# Add scripts/ to path for r2_storage import
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
import r2_storage

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# Series definitions
# ---------------------------------------------------------------------------
SERIES = {
    "signal": {
        "id": "signal",
        "title": "Сигнал",
        "icon": "📡",
        "color": "#E8B849",
        "output_dir": "output",
        "prompts_file": "output/prompts/all_prompts.json",
        "scenario_file": "scenario_signal.txt",
        "chars_dir": "персонажи_hq",
        "chars_dir_fallback": "персонажи",
        "locs_dir": "локации_hq",
        "locs_dir_fallback": "локации",
        "scene_colors": {
            "S01": "#E8B849", "S02": "#49B6E8", "S03": "#E85A49",
            "S04": "#6BE849", "S05": "#C149E8", "S06": "#E89849",
            "S07": "#49E8D6", "S08": "#E84980", "S09": "#8B49E8",
            "S10": "#B8E849", "S11": "#E8D649", "S12": "#4998E8",
        },
        "scene_labels": {
            "S01": "Сцена 1 — Кухня, ужин",
            "S02": "Сцена 2 — Гараж, радиоприёмник",
            "S03": "Сцена 3 — Магазин, велосипед",
            "S04": "Сцена 4 — Парк, поиски",
            "S05": "Сцена 5 — Мост через ручей",
            "S06": "Сцена 6 — Школа, перемена",
            "S07": "Сцена 7 — Гараж, задача",
            "S08": "Сцена 8 — Пустырь, склад",
            "S09": "Сцена 9 — Кабинет папы",
            "S10": "Сцена 10 — Водонапорная башня",
            "S11": "Сцена 11 — Кабинет папы, линза",
            "S12": "Сцена 12 — Комната Тако, ночь",
        },
        "char_display": {
            "Amin": "Амин", "Karim": "Карим", "Tako": "Тако",
            "Papa": "Папа", "Mama": "Мама", "Aya": "Ая",
            "Hasan": "Хасан", "Rami": "Рами", "Samir": "Самир",
            "Shaki": "Шаки",
        },
    },
    "sosed": {
        "id": "sosed",
        "title": "Сосед",
        "icon": "🏠",
        "color": "#49B6E8",
        "output_dir": "output_sosed",
        "prompts_file": "output_sosed/prompts/all_prompts.json",
        "scenario_file": "scenario_sosed.txt",
        "chars_dir": "sosed_персонажи_hq",
        "chars_dir_fallback": "sosed_персонажи",
        "locs_dir": "sosed_локации_hq",
        "locs_dir_fallback": "sosed_локации",
        "scene_colors": {
            "S01": "#E8B849", "S02": "#49B6E8", "S03": "#E85A49",
            "S04": "#6BE849", "S05": "#C149E8", "S06": "#E89849",
            "S07": "#49E8D6", "S08": "#E84980", "S09": "#8B49E8",
            "S10": "#B8E849", "S11": "#E8D649", "S12": "#4998E8",
            "S13": "#E8B849", "S14": "#49B6E8", "S15": "#E85A49",
            "S16": "#6BE849", "S17": "#C149E8", "S18": "#E89849",
            "S19": "#49E8D6", "S20": "#E84980", "S21": "#8B49E8",
        },
        "scene_labels": {
            "S01": "С1 — Улица, новый сосед",
            "S02": "С2 — Гараж, обсуждение",
            "S03": "С3 — Дом Джамиля, плов",
            "S04": "С4 — Двор Джамиля, чай",
            "S05": "С5 — Кухня, разговор",
            "S06": "С6 — Гараж, карта города",
            "S07": "С7 — Улицы, расследование",
            "S08": "С8 — Стройка, камера",
            "S09": "С9 — Библиотека, подшивки",
            "S10": "С10 — Гараж, связи на доске",
            "S11": "С11 — Забор, разговор",
            "S12": "С12 — Старый квартал",
            "S13": "С13 — Паркинг за мечетью",
            "S14": "С14 — Ночь, слежка",
            "S15": "С15 — Пожар, спасение",
            "S16": "С16 — После пожара",
            "S17": "С17 — Автомойка, улики",
            "S18": "С18 — Подземный город",
            "S19": "С19 — Возвращение",
            "S20": "С20 — Признание Джамиля",
            "S21": "С21 — Финал",
        },
        "char_display": {
            "Amin": "Амин", "Karim": "Карим", "Tako": "Тако",
            "Papa": "Папа", "Mama": "Мама", "Aya": "Ая",
            "Jamil": "Джамиль", "Simba": "Симба",
        },
    },
}

DEFAULT_SERIES = "signal"


def _get_series_config() -> dict:
    """Get current series config from session state."""
    sid = st.session_state.get("current_series", DEFAULT_SERIES)
    return SERIES.get(sid, SERIES[DEFAULT_SERIES])


def _series_paths(cfg: dict) -> dict:
    """Resolve all paths for a series config."""
    output_dir = BASE_DIR / cfg["output_dir"]
    chars_dir = BASE_DIR / cfg["chars_dir"]
    if not chars_dir.exists():
        chars_dir = BASE_DIR / cfg["chars_dir_fallback"]
    locs_dir = BASE_DIR / cfg["locs_dir"]
    if not locs_dir.exists():
        locs_dir = BASE_DIR / cfg["locs_dir_fallback"]
    return {
        "prompts_file": BASE_DIR / cfg["prompts_file"],
        "frames_dir": output_dir / "frames",
        "clips_dir": output_dir / "clips",
        "review_dir": output_dir / "review",
        "status_file": output_dir / "status.json",
        "commands_file": output_dir / "commands.json",
        "scenario_file": BASE_DIR / cfg["scenario_file"],
        "chars_dir": chars_dir,
        "locs_dir": locs_dir,
    }


# Active series paths (set in main(), used by all pages)
PROMPTS_FILE = BASE_DIR / "output" / "prompts" / "all_prompts.json"
FRAMES_DIR = BASE_DIR / "output" / "frames"
CLIPS_DIR = BASE_DIR / "output" / "clips"
REVIEW_DIR = BASE_DIR / "output" / "review"
SCENE_DIR = BASE_DIR / "output" / "scene"
CHARS_DIR = BASE_DIR / "персонажи_hq" if (BASE_DIR / "персонажи_hq").exists() else BASE_DIR / "персонажи"
LOCS_DIR = BASE_DIR / "локации_hq" if (BASE_DIR / "локации_hq").exists() else BASE_DIR / "локации"
SCENARIO_FILE = BASE_DIR / "scenario_signal.txt"
STATUS_FILE = BASE_DIR / "output" / "status.json"
COMMANDS_FILE = BASE_DIR / "output" / "commands.json"

# These globals are updated by _apply_series() in main()
SCENE_COLORS: dict = {}
SCENE_LABELS: dict = {}
CHAR_DISPLAY: dict = {}

# R2 state
_R2_OK = r2_storage.is_configured()


def _r2_key(local_path) -> str:
    """Convert local path to R2 key relative to BASE_DIR."""
    try:
        return str(Path(local_path).relative_to(BASE_DIR))
    except ValueError:
        return str(local_path)


def _r2_image_url(local_path) -> str | None:
    """Get R2 public URL for an image/video file. Returns None if R2 not configured."""
    if not _R2_OK:
        return None
    return r2_storage.public_url(_r2_key(local_path))


def _apply_series():
    """Apply current series config to global variables."""
    global PROMPTS_FILE, FRAMES_DIR, CLIPS_DIR, REVIEW_DIR, CHARS_DIR, LOCS_DIR
    global SCENARIO_FILE, STATUS_FILE, COMMANDS_FILE, SCENE_COLORS, SCENE_LABELS, CHAR_DISPLAY

    cfg = _get_series_config()
    paths = _series_paths(cfg)
    PROMPTS_FILE = paths["prompts_file"]
    FRAMES_DIR = paths["frames_dir"]
    CLIPS_DIR = paths["clips_dir"]
    REVIEW_DIR = paths["review_dir"]
    STATUS_FILE = paths["status_file"]
    COMMANDS_FILE = paths["commands_file"]
    SCENARIO_FILE = paths["scenario_file"]
    CHARS_DIR = paths["chars_dir"]
    LOCS_DIR = paths["locs_dir"]
    SCENE_COLORS = cfg["scene_colors"]
    SCENE_LABELS = cfg["scene_labels"]
    CHAR_DISPLAY = cfg["char_display"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def _load_clips_cached(prompts_r2_key: str, prompts_local: str) -> list[dict]:
    """Load clip data — R2 first, local fallback. Keyed by path for cache."""
    if _R2_OK and prompts_r2_key:
        data = r2_storage.read_json(prompts_r2_key)
        if data is not None:
            return data
    p = Path(prompts_local)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return []


def load_clips() -> list[dict]:
    return _load_clips_cached(_r2_key(PROMPTS_FILE), str(PROMPTS_FILE))


@st.cache_data(ttl=60)
def load_status() -> dict:
    """Load clip statuses from status.json (for Streamlit Cloud compatibility)."""
    if STATUS_FILE.exists():
        with open(STATUS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_status(clip_id: str) -> str:
    """Determine clip status from status.json component statuses."""
    status_data = load_status()
    clip_status = status_data.get("clips", {}).get(clip_id)
    if clip_status:
        # clip_status is {nb_first: "accepted", nb_last: "pending", veo: "pending", ...}
        if isinstance(clip_status, dict) and "status" in clip_status:
            return clip_status["status"]
        # Derive overall status from component statuses
        comps = clip_status if isinstance(clip_status, dict) else {}
        vals = [v for v in comps.values() if isinstance(v, str)]
        accepted = sum(1 for v in vals if v == "accepted")
        if accepted >= 3:  # nb_first + nb_last + veo
            return "done"
        elif accepted >= 1:
            return "partial"
        return "todo"

    # Fallback: check local files
    has_first = (FRAMES_DIR / f"{clip_id}_first.png").exists() or (FRAMES_DIR / clip_id / "first.png").exists()
    has_last = (FRAMES_DIR / f"{clip_id}_last.png").exists() or (FRAMES_DIR / clip_id / "last.png").exists()
    has_clip = (CLIPS_DIR / f"{clip_id}_clip.mp4").exists()

    if has_first and has_last and has_clip:
        return "done"
    elif has_first or has_last or has_clip:
        return "partial"
    return "todo"


def get_component_status(clip_id: str) -> dict:
    """Get per-component status (nb_first, nb_last, veo) from status.json."""
    status_data = load_status()
    return status_data.get("clips", {}).get(clip_id, {})


STATUS_MAP = {
    "done": ("Готово", "🟢"),
    "partial": ("Частично", "🟡"),
    "todo": ("Не начато", "🔴"),
}


def scene_badge(scene_id: str) -> str:
    """Return HTML badge for a scene."""
    color = SCENE_COLORS.get(scene_id, "#888")
    return (
        f'<span style="background:{color};color:#000;padding:2px 8px;'
        f'border-radius:4px;font-weight:600;font-size:0.85em;">{scene_id}</span>'
    )


def download_button_for_file(filepath: Path, label: str, key: str):
    """Render a download button if file exists."""
    if filepath.exists():
        data = filepath.read_bytes()
        suffix = filepath.suffix.lstrip(".")
        mime = "image/png" if suffix == "png" else f"video/{suffix}"
        st.download_button(label, data, file_name=filepath.name, mime=mime, key=key)


def char_thumbnail(char_name: str, size: int = 60) -> str | None:
    """Find a character reference image for thumbnail."""
    name_lower = char_name.lower()
    for pattern in [f"char_{name_lower}_full*", f"char_{name_lower}_face*"]:
        matches = list(CHARS_DIR.glob(pattern))
        if matches:
            return str(matches[0])
    return None


def loc_thumbnail(location: str) -> str | None:
    """Find a location reference image for thumbnail."""
    loc_map = {
        "Garage": "loc_garazh_inside",
        "Amin room": "loc_amin_room_full",
        "Papa office": "loc_kabinet_full",
    }
    key = loc_map.get(location, "")
    if key:
        matches = list(LOCS_DIR.glob(f"{key}*"))
        if matches:
            return str(matches[0])
    return None


# ---------------------------------------------------------------------------
# Phase workflow helpers
# ---------------------------------------------------------------------------

PHASE_LABELS = {
    "nb_first": "Первые кадры",
    "nb_last": "Последние кадры",
    "veo": "Видео",
}

PHASE_NUMBERS = {"nb_first": 1, "nb_last": 2, "veo": 3}


def load_commands() -> dict:
    """Load current phase commands from commands.json."""
    if COMMANDS_FILE.exists():
        with open(COMMANDS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_commands(cmd: dict):
    """Save commands.json."""
    with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(cmd, f, indent=2, ensure_ascii=False)


def get_review_variants(clip_id: str, component: str) -> list[Path]:
    """Get variant files for the latest attempt. Supports flat and prompt_a/ formats."""
    comp_dir = REVIEW_DIR / clip_id / component
    if not comp_dir.exists():
        return []

    attempts = sorted(comp_dir.glob("attempt_*"))
    if not attempts:
        return []

    latest = attempts[-1]
    ext = "*.mp4" if component == "veo" else "*.png"

    # Flat format first (new)
    flat = sorted(latest.glob(ext))
    if flat:
        return flat

    # Fallback: prompt_a + prompt_b (old format)
    result = []
    for batch in ["prompt_a", "prompt_b"]:
        batch_dir = latest / batch
        if batch_dir.exists():
            result.extend(sorted(batch_dir.glob(ext)))
    return result


def get_all_attempt_variants(clip_id: str, component: str) -> list[tuple[int, list]]:
    """Get variants for ALL attempts. Returns [(attempt_num, [path_or_url]), ...].

    On Railway (R2 mode): builds URLs from manifest data.
    Locally: scans filesystem as before.
    """
    # Try local filesystem first
    comp_dir = REVIEW_DIR / clip_id / component
    has_local = comp_dir.exists()

    if has_local:
        result = []
        for attempt_dir in sorted(comp_dir.glob("attempt_*")):
            try:
                attempt_num = int(attempt_dir.name.replace("attempt_", ""))
            except ValueError:
                continue
            ext = "*.mp4" if component == "veo" else "*.png"
            files = sorted(attempt_dir.glob(ext))
            if not files:
                pa = attempt_dir / "prompt_a"
                if pa.exists():
                    files = sorted(pa.glob(ext))
            if files:
                result.append((attempt_num, files))
        if result:
            return result

    # R2 mode: build paths from manifest
    if _R2_OK:
        manifest = _load_manifest(clip_id)
        comp_data = manifest.get("components", {}).get(component, {})
        result = []
        for att in comp_data.get("attempts", []):
            attempt_num = att.get("attempt", 0)
            variants = att.get("variants", [])
            urls = []
            for v in variants:
                vfile = v.get("file", "")
                # Build the R2 key from the review directory structure
                local_path = REVIEW_DIR / clip_id / component / f"attempt_{attempt_num}" / vfile
                url = r2_storage.public_url(_r2_key(local_path))
                if url:
                    urls.append(url)
            if urls:
                result.append((attempt_num, urls))
        return result

    return []


def do_local_select(phase: str, selections: dict):
    """Copy selected variants to output/frames or output/clips. Runs in dashboard process."""
    suffixes = {"nb_first": "first", "nb_mid": "mid", "nb_last": "last"}
    count = 0

    for clip_id, info in selections.items():
        if info.get("status") != "selected":
            continue

        variant_idx = info["variant"]
        attempt = info.get("attempt", 1)

        attempt_dir = REVIEW_DIR / clip_id / phase / f"attempt_{attempt}"

        if phase in suffixes:
            variant_file = attempt_dir / f"variant_{variant_idx + 1}.png"
            if not variant_file.exists():
                variant_file = attempt_dir / "prompt_a" / f"variant_{variant_idx + 1}.png"

            if variant_file.exists():
                FRAMES_DIR.mkdir(parents=True, exist_ok=True)
                dest = FRAMES_DIR / f"{clip_id}_{suffixes[phase]}.png"
                shutil.copy2(variant_file, dest)
                count += 1

        elif phase == "veo":
            variant_file = attempt_dir / f"variant_{variant_idx + 1}.mp4"
            if not variant_file.exists():
                variant_file = attempt_dir / "prompt_a" / f"variant_{variant_idx + 1}.mp4"

            if variant_file.exists():
                CLIPS_DIR.mkdir(parents=True, exist_ok=True)
                dest = CLIPS_DIR / f"{clip_id}_clip.mp4"
                shutil.copy2(variant_file, dest)
                count += 1

    return count


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def inject_css():
    st.markdown("""
    <style>
    /* Global */
    .block-container { max-width: 1200px; }

    /* Scene badge */
    .scene-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.85em;
        color: #000;
    }

    /* Clip card */
    .clip-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 4px;
    }
    .clip-header h3 { margin: 0; }

    /* Status pill */
    .status-pill {
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: 600;
    }
    .status-done { background: #1B5E20; color: #A5D6A7; }
    .status-partial { background: #E65100; color: #FFE0B2; }
    .status-todo { background: #B71C1C; color: #FFCDD2; }

    /* Prompt blocks */
    .prompt-block {
        background: #1A1D26;
        border-left: 3px solid #E8B849;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        margin: 6px 0;
        font-size: 0.9em;
        line-height: 1.5;
    }
    .prompt-label {
        color: #E8B849;
        font-weight: 700;
        font-size: 0.78em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }

    /* Ref gallery */
    .ref-gallery {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }
    .ref-card {
        text-align: center;
        font-size: 0.78em;
        color: #aaa;
    }
    .ref-card img {
        border-radius: 6px;
        border: 1px solid #333;
    }

    /* Stats */
    .stat-card {
        background: #1A1D26;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .stat-card .number {
        font-size: 2em;
        font-weight: 700;
        color: #E8B849;
    }
    .stat-card .label {
        font-size: 0.85em;
        color: #999;
    }

    /* Ingredient role badge */
    .role-badge {
        display: inline-block;
        background: #2A2D36;
        padding: 1px 6px;
        border-radius: 3px;
        font-size: 0.72em;
        color: #bbb;
    }

    /* Mobile */
    @media (max-width: 768px) {
        .block-container { padding: 0.5rem 1rem; }
    }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def page_review():
    """Interactive review page — user selects/rejects variants per clip."""
    all_clips = load_clips()
    cmd = load_commands()

    # Determine current phase
    phase = cmd.get("phase", "nb_first")
    phase_label = PHASE_LABELS.get(phase, phase)
    phase_num = PHASE_NUMBERS.get(phase, 1)
    bot_running = cmd.get("bot_running", False)
    clip_commands = cmd.get("clips", {})

    # --- Scene filter ---
    all_scene_ids = list(dict.fromkeys(c["scene_id"] for c in all_clips))  # preserve order
    scene_options = {sid: SCENE_LABELS.get(sid, sid) for sid in all_scene_ids}

    selected_scenes = st.multiselect(
        "Сцены",
        all_scene_ids,
        default=all_scene_ids,
        format_func=lambda x: scene_options[x],
        key="scene_filter",
    )

    if selected_scenes:
        clips = [c for c in all_clips if c["scene_id"] in selected_scenes]
    else:
        clips = all_clips

    # Count stats (filtered)
    total = len(clips)
    accepted_count = sum(
        1 for c in clips
        if clip_commands.get(c["clip_id"], {}).get("status") == "accepted"
    )
    generated_count = sum(
        1 for c in clips
        if clip_commands.get(c["clip_id"], {}).get("status") == "generated"
    )

    # --- Header ---
    st.header(f"Фаза {phase_num}: {phase_label}")

    hcol1, hcol2, hcol3 = st.columns([4, 1, 1])
    with hcol1:
        st.progress(accepted_count / total if total else 0)
    with hcol2:
        st.metric("Принято", f"{accepted_count}/{total}")
    with hcol3:
        st.metric("На ревью", str(generated_count))

    if bot_running:
        st.warning("Бот сейчас работает. Дождитесь завершения генерации.")

    # --- Action buttons ---
    btn_cols = st.columns(4)

    with btn_cols[0]:
        can_start = not bot_running and not cmd.get("action")
        if can_start and generated_count == 0 and accepted_count < total:
            if st.button("Запустить генерацию", type="primary", key="btn_start"):
                new_cmd = {
                    "version": 1,
                    "phase": phase,
                    "action": "generate",
                    "bot_running": False,
                    "created_at": datetime.now().isoformat(),
                    "clips": {
                        c["clip_id"]: {"status": "pending", "attempt": 1}
                        for c in clips
                        if clip_commands.get(c["clip_id"], {}).get("status") != "accepted"
                    },
                }
                # Preserve accepted clips
                for cid, info in clip_commands.items():
                    if info.get("status") == "accepted":
                        new_cmd["clips"][cid] = info
                save_commands(new_cmd)
                st.success("Команда записана. Запустите бота: `./scripts/run_safe.sh --phase --account 1`")
                st.rerun()

    with btn_cols[1]:
        # "Submit" button — process selections and rejections
        pass  # Rendered below after gathering decisions

    with btn_cols[2]:
        if accepted_count == total and total > 0 and phase == "nb_first":
            if st.button("Последние кадры", type="primary", key="btn_next_last"):
                new_cmd = {
                    "version": 1,
                    "phase": "nb_last",
                    "action": "generate",
                    "bot_running": False,
                    "created_at": datetime.now().isoformat(),
                    "clips": {c["clip_id"]: {"status": "pending", "attempt": 1} for c in clips},
                }
                # Preserve clips outside current filter
                for c in all_clips:
                    cid = c["clip_id"]
                    if cid not in new_cmd["clips"] and cid in clip_commands:
                        new_cmd["clips"][cid] = clip_commands[cid]
                save_commands(new_cmd)
                st.success("Фаза 2 начата. Запустите бота: `./scripts/run_safe.sh --phase --account 1`")
                st.rerun()

        if accepted_count == total and total > 0 and phase == "nb_last":
            if st.button("Сгенерить видео", type="primary", key="btn_next_veo"):
                new_cmd = {
                    "version": 1,
                    "phase": "veo",
                    "action": "generate",
                    "bot_running": False,
                    "created_at": datetime.now().isoformat(),
                    "clips": {c["clip_id"]: {"status": "pending", "attempt": 1} for c in clips},
                }
                for c in all_clips:
                    cid = c["clip_id"]
                    if cid not in new_cmd["clips"] and cid in clip_commands:
                        new_cmd["clips"][cid] = clip_commands[cid]
                save_commands(new_cmd)
                st.success("Фаза 3 начата. Запустите бота: `./scripts/run_safe.sh --phase --account 1`")
                st.rerun()

    with btn_cols[3]:
        # Phase selector
        new_phase = st.selectbox(
            "Фаза", list(PHASE_LABELS.keys()),
            index=list(PHASE_LABELS.keys()).index(phase),
            format_func=lambda x: PHASE_LABELS[x],
            key="phase_select",
            label_visibility="collapsed",
        )
        if new_phase != phase:
            cmd["phase"] = new_phase
            save_commands(cmd)
            st.rerun()

    st.markdown("---")

    # --- Clip variant grid ---
    current_scene = None
    has_decisions = False

    for clip in clips:
        clip_id = clip["clip_id"]

        # Scene header
        if clip["scene_id"] != current_scene:
            current_scene = clip["scene_id"]
            color = SCENE_COLORS.get(current_scene, "#888")
            label = SCENE_LABELS.get(current_scene, current_scene)
            st.markdown(
                f'<h4 style="border-left:4px solid {color};padding-left:12px;'
                f'margin-top:20px;margin-bottom:8px;">{label}</h4>',
                unsafe_allow_html=True,
            )

        clip_cmd = clip_commands.get(clip_id, {})
        clip_status = clip_cmd.get("status", "")

        # Already accepted — show green thumbnail
        if clip_status == "accepted":
            acc_col1, acc_col2 = st.columns([1, 9])
            with acc_col1:
                st.markdown(f"**{clip_id}**")
            with acc_col2:
                if phase in ("nb_first", "nb_mid", "nb_last"):
                    suffix = {"nb_first": "first", "nb_mid": "mid", "nb_last": "last"}[phase]
                    frame_path = FRAMES_DIR / f"{clip_id}_{suffix}.png"
                    if frame_path.exists():
                        st.image(str(frame_path), width=200, caption="Принято")
                    else:
                        st.success("Принято")
                else:
                    st.success("Принято")
            continue

        # Not generated yet
        all_attempts = get_all_attempt_variants(clip_id, phase)
        if not all_attempts:
            st.markdown(f"**{clip_id}** — *варианты ещё не сгенерированы*")
            continue

        # Show description
        desc = clip.get("scene_description_ru", "")
        st.markdown(f"**{clip_id}** — {desc[:100]}")

        # Show variants from latest attempt
        latest_attempt, variants = all_attempts[-1]

        if phase == "veo":
            # Video variants
            cols = st.columns(min(len(variants), 4))
            for vi, vpath in enumerate(variants):
                with cols[vi % 4]:
                    st.video(str(vpath))
                    st.caption(f"Вариант {vi + 1}")
        else:
            # Image variants
            cols = st.columns(min(len(variants), 4))
            for vi, vpath in enumerate(variants):
                with cols[vi % 4]:
                    st.image(str(vpath), use_container_width=True)
                    st.caption(f"Вариант {vi + 1}")

        # Selection controls
        sel_col, rej_col = st.columns([3, 1])
        with sel_col:
            options = [f"Вариант {i+1}" for i in range(len(variants))] + ["Не выбрано"]
            # Restore previous selection if any
            default_idx = len(options) - 1
            prev_decision = st.session_state.get(f"decision_{clip_id}")
            if isinstance(prev_decision, tuple) and prev_decision[0] == "selected":
                sel_idx = prev_decision[1]
                if sel_idx < len(variants):
                    default_idx = sel_idx

            choice = st.radio(
                f"Выбор для {clip_id}", options, index=default_idx,
                key=f"radio_{clip_id}", horizontal=True, label_visibility="collapsed",
            )

        with rej_col:
            reject = st.checkbox("Отклонить", key=f"rej_{clip_id}")

        # Feedback text area (shown when rejecting)
        if reject:
            prev_feedback = clip_cmd.get("feedback", "")
            feedback = st.text_area(
                f"Что исправить в {clip_id}?",
                value=prev_feedback,
                placeholder="Например: персонажи одного роста, Тако должен быть ниже Амина",
                key=f"feedback_{clip_id}",
                height=68,
            )
        else:
            feedback = ""

        # Store decision in session state
        if reject:
            st.session_state[f"decision_{clip_id}"] = ("rejected", feedback)
            has_decisions = True
        elif choice != "Не выбрано":
            variant_idx = int(choice.split()[-1]) - 1
            st.session_state[f"decision_{clip_id}"] = ("selected", variant_idx, latest_attempt)
            has_decisions = True

        st.divider()

    # --- Submit button (after all clips rendered) ---
    if has_decisions or generated_count > 0:
        st.markdown("---")
        if st.button("Отправить решения", type="primary", key="btn_submit", use_container_width=True):
            selections = {}
            rejections = {}

            for clip in clips:
                cid = clip["clip_id"]
                decision = st.session_state.get(f"decision_{cid}")
                if isinstance(decision, tuple) and decision[0] == "rejected":
                    feedback_text = decision[1] if len(decision) > 1 else ""
                    rej_entry = {
                        "status": "rejected",
                        "attempt": clip_commands.get(cid, {}).get("attempt", 1),
                    }
                    if feedback_text:
                        rej_entry["feedback"] = feedback_text
                    rejections[cid] = rej_entry
                elif isinstance(decision, tuple) and decision[0] == "selected":
                    selections[cid] = {
                        "status": "selected",
                        "variant": decision[1],
                        "attempt": decision[2],
                    }

            # 1. Instantly copy selected variants to output/frames
            if selections:
                count = do_local_select(phase, selections)
                st.success(f"Принято: {count} клипов")

            # 2. Update commands.json
            for cid, info in selections.items():
                clip_commands[cid] = {"status": "accepted", "attempt": info["attempt"], "variant": info["variant"]}
            for cid, info in rejections.items():
                clip_commands[cid] = info

            if rejections:
                feedback_count = sum(1 for r in rejections.values() if r.get("feedback"))
                cmd.update({
                    "phase": phase,
                    "action": "regenerate",
                    "bot_running": False,
                    "created_at": datetime.now().isoformat(),
                    "clips": clip_commands,
                })
                save_commands(cmd)
                msg = f"Отклонено: {len(rejections)} клипов."
                if feedback_count:
                    msg += f" Комментарии: {feedback_count}."
                msg += " Запустите бота для перегенерации."
                st.warning(msg)
            else:
                cmd["clips"] = clip_commands
                save_commands(cmd)

            # Clear decisions from session state
            for clip in clips:
                cid = clip["clip_id"]
                st.session_state.pop(f"decision_{cid}", None)

            st.rerun()


def _default_manifest(clip_id: str) -> dict:
    return {
        "clip_id": clip_id,
        "components": {
            c: {"attempts": [], "selected_variant_a": None, "selected_variant_b": None, "status": "pending"}
            for c in ("nb_first", "nb_mid", "nb_last", "veo")
        },
    }


def _normalize_manifest(m: dict) -> dict:
    for c in ("nb_first", "nb_mid", "nb_last", "veo"):
        comp = m.get("components", {}).get(c, {})
        comp.setdefault("selected_variant_a", None)
        comp.setdefault("selected_variant_b", None)
        comp.setdefault("attempts", [])
        comp.setdefault("status", "pending")
        m.setdefault("components", {})[c] = comp
    return m


# Cache for R2 manifests — avoids per-clip requests
_r2_manifest_cache: dict = {}
_r2_cache_loaded: bool = False


@st.cache_data(ttl=30, show_spinner="Загрузка манифестов из R2...")
def _fetch_all_manifests_r2(prefix: str) -> dict:
    """Fetch all manifests from R2 (cached 30s by Streamlit)."""
    keys = r2_storage.list_prefix(prefix)
    manifest_keys = [k for k in keys if k.endswith("/manifest.json")]
    result = {}
    for mk in manifest_keys:
        m = r2_storage.read_json(mk)
        if m and "clip_id" in m:
            result[m["clip_id"]] = _normalize_manifest(m)
    return result


def _load_all_manifests_r2():
    """Bulk-load all manifests from R2 into cache."""
    global _r2_manifest_cache, _r2_cache_loaded
    if _r2_cache_loaded:
        return
    _r2_cache_loaded = True
    if not _R2_OK:
        return
    prefix = _r2_key(REVIEW_DIR) + "/"
    _r2_manifest_cache = _fetch_all_manifests_r2(prefix)


def _load_manifest(clip_id: str) -> dict:
    """Load manifest.json for a clip — from R2 cache (primary) or local fallback."""
    # Try R2 cache
    if _R2_OK:
        if not _r2_cache_loaded:
            _load_all_manifests_r2()
        if clip_id in _r2_manifest_cache:
            return _r2_manifest_cache[clip_id]
        # Single fetch fallback
        r2_key = _r2_key(REVIEW_DIR / clip_id / "manifest.json")
        m = r2_storage.read_json(r2_key)
        if m:
            return _normalize_manifest(m)
    # Local fallback
    path = REVIEW_DIR / clip_id / "manifest.json"
    if path.exists():
        with open(path) as f:
            m = json.load(f)
        return _normalize_manifest(m)
    return _default_manifest(clip_id)


def _save_manifest(clip_id: str, manifest: dict):
    """Save manifest.json — to R2 (primary) and local."""
    if _R2_OK:
        r2_key = _r2_key(REVIEW_DIR / clip_id / "manifest.json")
        r2_storage.write_json(r2_key, manifest)
        _r2_manifest_cache[clip_id] = manifest
        _fetch_all_manifests_r2.clear()  # invalidate Streamlit cache
    path = REVIEW_DIR / clip_id / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def _chain_select_variant(clip_id: str, component: str, attempt: int, variant_idx: int):
    """Accept a variant: update manifest + copy to frames/clips (local + R2)."""
    suffixes = {"nb_first": "first", "nb_mid": "mid", "nb_last": "last"}
    manifest = _load_manifest(clip_id)

    # Determine source and destination paths
    attempt_dir = REVIEW_DIR / clip_id / component / f"attempt_{attempt}"
    if component in suffixes:
        ext = ".png"
        variant_file = attempt_dir / f"variant_{variant_idx + 1}{ext}"
        if not variant_file.exists() and not _R2_OK:
            variant_file = attempt_dir / "prompt_a" / f"variant_{variant_idx + 1}{ext}"
        dest = FRAMES_DIR / f"{clip_id}_{suffixes[component]}{ext}"
    elif component == "veo":
        ext = ".mp4"
        variant_file = attempt_dir / f"variant_{variant_idx + 1}{ext}"
        if not variant_file.exists() and not _R2_OK:
            variant_file = attempt_dir / "prompt_a" / f"variant_{variant_idx + 1}{ext}"
        dest = CLIPS_DIR / f"{clip_id}_clip{ext}"
    else:
        dest = None

    # Copy: R2-to-R2 (on Railway) or local copy
    if dest and _R2_OK:
        src_key = _r2_key(variant_file)
        dest_key = _r2_key(dest)
        r2_storage.copy_object(src_key, dest_key)
    elif dest and variant_file.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(variant_file, dest)

    # Update manifest
    manifest["components"][component]["status"] = "accepted"
    manifest["components"][component]["selected_variant_a"] = {
        "attempt": attempt, "variant": variant_idx,
    }
    _save_manifest(clip_id, manifest)


def _chain_reject_variant(clip_id: str, component: str, feedback: str = ""):
    """Reject all variants of latest attempt."""
    manifest = _load_manifest(clip_id)
    manifest["components"][component]["status"] = "rejected"
    if feedback:
        manifest["components"][component]["feedback"] = feedback
    _save_manifest(clip_id, manifest)


def page_chain_review():
    """Chain review page — shows clips by manifest status, not commands.json.

    Works with --chain mode: each clip can be at a different stage.
    Shows only clips that need review (have generated variants not yet accepted).
    """
    all_clips = load_clips()

    # --- Scene filter ---
    all_scene_ids = list(dict.fromkeys(c["scene_id"] for c in all_clips))
    scene_options = {sid: SCENE_LABELS.get(sid, sid) for sid in all_scene_ids}

    filter_col1, filter_col2 = st.columns([3, 1])

    with filter_col1:
        selected_scenes = st.multiselect(
            "Сцены",
            all_scene_ids,
            default=all_scene_ids,
            format_func=lambda x: scene_options[x],
            key="chain_scene_filter",
        )

    with filter_col2:
        view_mode = st.selectbox(
            "Показать",
            ["Ожидает ревью", "Все клипы", "Принятые", "Заблокированные"],
            key="chain_view_mode",
        )

    if selected_scenes:
        clips = [c for c in all_clips if c["scene_id"] in selected_scenes]
    else:
        clips = all_clips

    # --- Load all manifests and classify ---
    needs_review = []  # has variants, not accepted
    accepted_clips = []
    blocked_clips = []  # no variants yet
    all_manifests = {}

    for clip in clips:
        cid = clip["clip_id"]
        manifest = _load_manifest(cid)
        all_manifests[cid] = manifest

        # Check each component
        clip_info = {"clip": clip, "manifest": manifest, "review_items": []}

        for comp in ("nb_first", "nb_last"):
            comp_data = manifest["components"].get(comp, {})
            status = comp_data.get("status", "pending")
            attempts = comp_data.get("attempts", [])

            if status == "accepted":
                continue

            # Has generated variants waiting for review?
            all_attempts = get_all_attempt_variants(cid, comp)
            if all_attempts:
                clip_info["review_items"].append((comp, all_attempts))

        if clip_info["review_items"]:
            needs_review.append(clip_info)
        else:
            # Check if all components are accepted
            first_ok = manifest["components"]["nb_first"].get("status") == "accepted"
            last_ok = manifest["components"]["nb_last"].get("status") == "accepted"
            if first_ok and last_ok:
                accepted_clips.append(clip_info)
            elif first_ok:
                accepted_clips.append(clip_info)
            else:
                blocked_clips.append(clip_info)

    # --- Stats ---
    total = len(clips)
    total_first_accepted = sum(
        1 for c in clips
        if all_manifests[c["clip_id"]]["components"]["nb_first"].get("status") == "accepted"
    )
    total_last_accepted = sum(
        1 for c in clips
        if all_manifests[c["clip_id"]]["components"]["nb_last"].get("status") == "accepted"
    )
    total_both = sum(
        1 for c in clips
        if all_manifests[c["clip_id"]]["components"]["nb_first"].get("status") == "accepted"
        and all_manifests[c["clip_id"]]["components"]["nb_last"].get("status") == "accepted"
    )

    st.header("Chain Ревью")

    # Debug info
    with st.expander("Debug R2", expanded=True):
        st.write(f"HAS_BOTO3: {r2_storage.HAS_BOTO3}")
        st.write(f"_ACCOUNT_ID len: {len(r2_storage._ACCOUNT_ID)}, val: {r2_storage._ACCOUNT_ID[:8]}...")
        st.write(f"_ACCESS_KEY len: {len(r2_storage._ACCESS_KEY)}")
        st.write(f"_SECRET_KEY len: {len(r2_storage._SECRET_KEY)}")
        st.write(f"_BUCKET: {r2_storage._BUCKET}")
        st.write(f"_PUBLIC_URL: {r2_storage._PUBLIC_URL}")
        st.write(f"is_configured(): {r2_storage.is_configured()}")
        st.write(f"_R2_OK (module): {_R2_OK}")
        st.write(f"ENV keys with R2: {[k for k in os.environ if 'R2' in k]}")
        st.write(f"Cache: loaded={_r2_cache_loaded}, manifests={len(_r2_manifest_cache)}")
        st.write(f"needs_review={len(needs_review)}, accepted={len(accepted_clips)}, blocked={len(blocked_clips)}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Всего клипов", total)
    with col2:
        st.metric("First принято", f"{total_first_accepted}/{total}")
    with col3:
        st.metric("Last принято", f"{total_last_accepted}/{total}")
    with col4:
        st.metric("Ожидает ревью", len(needs_review))

    # Progress bar
    progress = total_both / total if total else 0
    st.progress(progress, text=f"Полностью готовы: {total_both}/{total} ({progress:.0%})")

    st.markdown("---")

    # --- Determine which clips to show ---
    if view_mode == "Ожидает ревью":
        display_items = needs_review
        if not display_items:
            st.info("Нет клипов, ожидающих ревью. Запустите бота: `./scripts/run_safe.sh --chain --account 1`")
    elif view_mode == "Принятые":
        display_items = accepted_clips
        if not display_items:
            st.info("Пока нет принятых клипов.")
    elif view_mode == "Заблокированные":
        display_items = blocked_clips
        if not display_items:
            st.info("Нет заблокированных клипов.")
    else:
        display_items = needs_review + accepted_clips + blocked_clips

    # --- Render clips ---
    current_scene = None
    has_decisions = False

    for item in display_items:
        clip = item["clip"]
        cid = clip["clip_id"]
        manifest = item["manifest"]

        # Scene header
        if clip["scene_id"] != current_scene:
            current_scene = clip["scene_id"]
            color = SCENE_COLORS.get(current_scene, "#49B6E8")
            label = SCENE_LABELS.get(current_scene, current_scene)
            st.markdown(
                f'<h4 style="border-left:4px solid {color};padding-left:12px;'
                f'margin-top:24px;margin-bottom:8px;">{label}</h4>',
                unsafe_allow_html=True,
            )

        # Component status badges
        first_status = manifest["components"]["nb_first"].get("status", "pending")
        last_status = manifest["components"]["nb_last"].get("status", "pending")

        status_icons = {"accepted": "🟢", "pending": "⚪", "rejected": "🔴", "generated": "🟡"}
        status_labels = {"accepted": "Принято", "pending": "Ожидание", "rejected": "Отклонено", "generated": "На ревью"}

        desc = clip.get("scene_description_ru", "")[:120]
        st.markdown(
            f"**{cid}** — {desc} &nbsp; "
            f"`first:` {status_icons.get(first_status, '⚪')} {status_labels.get(first_status, first_status)} &nbsp; "
            f"`last:` {status_icons.get(last_status, '⚪')} {status_labels.get(last_status, last_status)}"
        )

        # Show accepted frames as thumbnails
        if first_status == "accepted":
            first_frame = FRAMES_DIR / f"{cid}_first.png"
            first_src = _r2_image_url(first_frame) or (str(first_frame) if first_frame.exists() else None)
            if first_src:
                fc1, fc2 = st.columns([1, 5])
                with fc1:
                    st.image(first_src, width=150, caption="First (принято)")
                if last_status == "accepted":
                    last_frame = FRAMES_DIR / f"{cid}_last.png"
                    last_src = _r2_image_url(last_frame) or (str(last_frame) if last_frame.exists() else None)
                    if last_src:
                        with fc2:
                            st.image(last_src, width=150, caption="Last (принято)")

        # Show review items (variants awaiting selection)
        review_items = item.get("review_items", [])
        for comp, all_attempts in review_items:
            comp_label = {"nb_first": "Первый кадр", "nb_last": "Последний кадр"}.get(comp, comp)
            latest_attempt_num, variants = all_attempts[-1]

            st.markdown(f"**{comp_label}** — попытка {latest_attempt_num} ({len(variants)} вариантов)")

            # Show variant images (vpath can be Path or URL string)
            cols = st.columns(min(len(variants), 4))
            for vi, vpath in enumerate(variants):
                with cols[vi % 4]:
                    src = str(vpath)
                    if src.endswith(".mp4"):
                        st.video(src)
                    else:
                        st.image(src, use_container_width=True)
                    st.caption(f"Вариант {vi + 1}")

            # Selection controls
            sel_col, rej_col = st.columns([3, 1])
            with sel_col:
                options = [f"Вариант {i+1}" for i in range(len(variants))] + ["Не выбрано"]
                default_idx = len(options) - 1
                prev = st.session_state.get(f"chain_decision_{cid}_{comp}")
                if isinstance(prev, tuple) and prev[0] == "selected":
                    if prev[1] < len(variants):
                        default_idx = prev[1]

                choice = st.radio(
                    f"Выбор для {cid}/{comp}", options, index=default_idx,
                    key=f"chain_radio_{cid}_{comp}", horizontal=True, label_visibility="collapsed",
                )

            with rej_col:
                reject = st.checkbox("Отклонить", key=f"chain_rej_{cid}_{comp}")

            if reject:
                feedback = st.text_area(
                    f"Что исправить в {cid}/{comp}?",
                    placeholder="Опишите проблему...",
                    key=f"chain_feedback_{cid}_{comp}",
                    height=68,
                )
                st.session_state[f"chain_decision_{cid}_{comp}"] = ("rejected", feedback)
                has_decisions = True
            elif choice != "Не выбрано":
                variant_idx = int(choice.split()[-1]) - 1
                st.session_state[f"chain_decision_{cid}_{comp}"] = ("selected", variant_idx, latest_attempt_num)
                has_decisions = True

        if review_items:
            st.divider()

    # --- Submit decisions ---
    if has_decisions:
        st.markdown("---")
        if st.button("Отправить решения", type="primary", key="chain_btn_submit", use_container_width=True):
            selected_count = 0
            rejected_count = 0

            for item in display_items:
                cid = item["clip"]["clip_id"]
                for comp, all_attempts in item.get("review_items", []):
                    decision = st.session_state.get(f"chain_decision_{cid}_{comp}")
                    if isinstance(decision, tuple):
                        if decision[0] == "selected":
                            _chain_select_variant(cid, comp, decision[2], decision[1])
                            selected_count += 1
                        elif decision[0] == "rejected":
                            feedback = decision[1] if len(decision) > 1 else ""
                            _chain_reject_variant(cid, comp, feedback)
                            rejected_count += 1

                    # Clear decision
                    st.session_state.pop(f"chain_decision_{cid}_{comp}", None)

            msg_parts = []
            if selected_count:
                msg_parts.append(f"Принято: {selected_count}")
            if rejected_count:
                msg_parts.append(f"Отклонено: {rejected_count}")
            if msg_parts:
                st.success(" | ".join(msg_parts))

            st.rerun()


def page_clips():
    """Main clips dashboard page."""
    clips = load_clips()

    # --- Sidebar filters ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Фильтры")

    # Scene filter
    scene_ids = sorted(set(c["scene_id"] for c in clips))
    scene_options = ["Все"] + scene_ids
    selected_scene = st.sidebar.selectbox("Сцена", scene_options)

    # Status filter
    status_options = ["Все", "Готово", "Частично", "Не начато"]
    selected_status = st.sidebar.selectbox("Статус", status_options)

    # Character filter (only if clips have characters field)
    all_chars = sorted(set(ch for c in clips for ch in c.get("characters", [])))
    selected_char = None
    if all_chars:
        selected_char = st.sidebar.selectbox(
            "Персонаж", ["Все"] + all_chars,
            format_func=lambda x: CHAR_DISPLAY.get(x, x) if x != "Все" else "Все"
        )

    # --- Apply filters ---
    filtered = clips
    if selected_scene != "Все":
        filtered = [c for c in filtered if c["scene_id"] == selected_scene]
    if selected_status != "Все":
        status_key = {"Готово": "done", "Частично": "partial", "Не начато": "todo"}[selected_status]
        filtered = [c for c in filtered if get_status(c["clip_id"]) == status_key]
    if selected_char and selected_char != "Все":
        filtered = [c for c in filtered if selected_char in c.get("characters", [])]

    # --- Sidebar stats ---
    st.sidebar.markdown("---")
    all_statuses = [get_status(c["clip_id"]) for c in clips]
    done_count = all_statuses.count("done")
    partial_count = all_statuses.count("partial")
    total = len(clips)
    st.sidebar.markdown(f"**Готово:** {done_count}/{total} клипов")
    st.sidebar.markdown(f"**Частично:** {partial_count}/{total} клипов")
    st.sidebar.progress(done_count / total if total else 0)

    # --- Overview stats ---
    # Count total VEO review videos
    total_veo_videos = 0
    for c in clips:
        cid = c["clip_id"]
        veo_dir = REVIEW_DIR / cid / "veo"
        if veo_dir.exists():
            total_veo_videos += len(list(veo_dir.glob("attempt_*/*.mp4")))
            total_veo_videos += len(list(veo_dir.glob("attempt_*/*/*.mp4")))

    # Count clips with both frames
    frames_done = sum(
        1 for c in clips
        if ((FRAMES_DIR / f"{c['clip_id']}_first.png").exists() or (FRAMES_DIR / c['clip_id'] / "first.png").exists())
        and ((FRAMES_DIR / f"{c['clip_id']}_last.png").exists() or (FRAMES_DIR / c['clip_id'] / "last.png").exists())
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""<div class="stat-card">
            <div class="number">{total}</div>
            <div class="label">Всего клипов</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="stat-card">
            <div class="number">{frames_done}/{total}</div>
            <div class="label">Кадры готовы</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="stat-card">
            <div class="number">{total_veo_videos}</div>
            <div class="label">VEO видео</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="stat-card">
            <div class="number">{done_count}</div>
            <div class="label">🟢 Принято</div>
        </div>""", unsafe_allow_html=True)
    with col5:
        total_dur = sum(c.get("veo_duration", 0) or 0 for c in clips)
        st.markdown(f"""<div class="stat-card">
            <div class="number">{total_dur}с</div>
            <div class="label">Длительность</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # --- Clip cards ---
    if not filtered:
        st.info("Нет клипов по выбранным фильтрам.")
        return

    current_scene = None
    for clip in filtered:
        # Scene header
        if clip["scene_id"] != current_scene:
            current_scene = clip["scene_id"]
            color = SCENE_COLORS.get(current_scene, "#888")
            label = SCENE_LABELS.get(current_scene, current_scene)
            st.markdown(
                f'<h3 style="border-bottom:2px solid {color};padding-bottom:6px;'
                f'margin-top:24px;">{label}</h3>',
                unsafe_allow_html=True,
            )

        status = get_status(clip["clip_id"])
        status_label, status_icon = STATUS_MAP[status]
        status_class = f"status-{status}"

        # Expander per clip
        header_text = (
            f'{status_icon} {clip["clip_id"]} — {clip["scene_description_ru"]}'
        )
        with st.expander(header_text, expanded=False):
            render_clip_card(clip, status, status_label, status_class)


def render_nb_review_variants(clip_id: str, component: str = "nb_first"):
    """Render NB photo variants from the review directory."""
    review_dir = REVIEW_DIR / clip_id / component
    if not review_dir.exists():
        return

    attempt_dirs = sorted(review_dir.glob("attempt_*"))
    if not attempt_dirs:
        return

    comp_label = {"nb_first": "First Frame", "nb_mid": "Mid Frame", "nb_last": "Last Frame"}.get(component, component)
    total_imgs = sum(
        len(list(ad.glob("*.png"))) + len(list(ad.glob("*/*.png")))
        for ad in attempt_dirs
    )
    if total_imgs == 0:
        return

    st.markdown(f"**{comp_label} варианты** ({total_imgs} фото)")

    for attempt_dir in attempt_dirs:
        attempt_num = attempt_dir.name.replace("attempt_", "")

        batches = []
        for batch_name in ["prompt_a", "prompt_b"]:
            batch_dir = attempt_dir / batch_name
            if batch_dir.exists():
                imgs = sorted(batch_dir.glob("*.png"))
                if imgs:
                    batches.append((batch_name, imgs))

        flat_imgs = sorted(attempt_dir.glob("*.png"))
        if flat_imgs and not batches:
            batches.append(("variants", flat_imgs))

        if not batches:
            continue

        total_in_attempt = sum(len(imgs) for _, imgs in batches)
        with st.expander(f"Попытка {attempt_num} — {total_in_attempt} фото", expanded=(len(attempt_dirs) == 1)):
            for batch_name, imgs in batches:
                label = "Промпт A" if batch_name == "prompt_a" else (
                    "Промпт B" if batch_name == "prompt_b" else "Варианты"
                )
                st.markdown(f'<div class="prompt-label">{label} ({len(imgs)} фото)</div>',
                            unsafe_allow_html=True)
                cols = st.columns(4)
                for i, ipath in enumerate(imgs):
                    with cols[i % 4]:
                        st.image(str(ipath), use_container_width=True)
                        st.caption(ipath.name)


def render_veo_variants(clip_id: str):
    """Render all VEO video variants from the review directory."""
    review_clip_dir = REVIEW_DIR / clip_id / "veo"
    if not review_clip_dir.exists():
        return

    # Find all attempt directories
    attempt_dirs = sorted(review_clip_dir.glob("attempt_*"))
    if not attempt_dirs:
        return

    # Count total videos across all attempts
    all_videos_count = 0
    for ad in attempt_dirs:
        all_videos_count += len(list(ad.glob("*.mp4")))
        all_videos_count += len(list(ad.glob("*/*.mp4")))

    if all_videos_count == 0:
        return

    # Collect all videos from all attempts into groups (Pair A, Pair B, etc.)
    all_groups = []
    for attempt_dir in attempt_dirs:
        for batch_name in ["prompt_a", "prompt_b"]:
            batch_dir = attempt_dir / batch_name
            if batch_dir.exists():
                videos = sorted(batch_dir.glob("*.mp4"))
                if videos:
                    all_groups.append(videos)
        # Also check for flat structure (videos directly in attempt dir)
        flat_videos = sorted(attempt_dir.glob("*.mp4"))
        if flat_videos:
            all_groups.append(flat_videos)

    if not all_groups:
        return

    # Show videos grouped as Pair A, Pair B, etc.
    pair_labels = ["Пара A", "Пара B", "Пара C", "Пара D"]
    for idx, videos in enumerate(all_groups):
        label = pair_labels[idx] if idx < len(pair_labels) else f"Группа {idx + 1}"
        st.markdown(f'<div class="prompt-label">{label} ({len(videos)} видео)</div>',
                    unsafe_allow_html=True)
        cols = st.columns(4)
        for i, vpath in enumerate(videos):
            with cols[i % 4]:
                st.video(str(vpath))
                st.caption(vpath.name)


def render_clip_card(clip: dict, status: str, status_label: str, status_class: str):
    """Render the full clip card inside an expander."""
    clip_id = clip["clip_id"]

    # --- Row 1: Status + Meta ---
    meta_cols = st.columns([1, 1, 1, 1])
    with meta_cols[0]:
        st.markdown(
            f'<span class="status-pill {status_class}">{status_label}</span>',
            unsafe_allow_html=True,
        )
    with meta_cols[1]:
        chars = clip.get("characters", [])
        if chars:
            chars_display = ", ".join(CHAR_DISPLAY.get(c, c) for c in chars)
            st.markdown(f"**Персонажи:** {chars_display}")
    with meta_cols[2]:
        loc = clip.get("location", "")
        if loc:
            st.markdown(f"**Локация:** {loc}")
    with meta_cols[3]:
        tod = clip.get("time_of_day", "")
        if tod:
            st.markdown(f"**Время:** {tod}")

    st.markdown("---")

    # --- Row 2: Character & location thumbnails ---
    st.markdown("**Референсы (ингредиенты)**")
    ingredients = clip.get("nano_banana_ingredient_roles") or clip.get("nano_banana_ingredients", [])
    if ingredients:
        cols = st.columns(min(len(ingredients), 4))
        for i, ing in enumerate(ingredients):
            # Support both dict format (with "file" and "role") and string format
            if isinstance(ing, dict):
                filepath = BASE_DIR / ing["file"]
                role = ing.get("role", "")
                fname = Path(ing["file"]).name
            else:
                filepath = BASE_DIR / ing
                role = ""
                fname = Path(ing).name
            with cols[i % len(cols)]:
                if filepath.exists():
                    st.image(str(filepath), width=120)
                st.markdown(
                    f'<span class="role-badge">{role}</span><br>'
                    f'<span style="font-size:0.72em;color:#666;">{fname}</span>',
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    # --- Row 3: Prompts ---
    st.markdown("**Промпты**")

    # NB First Frame prompts (A + B)
    prompt_first_a = clip.get("nano_banana_prompt_first", "")
    prompt_first_b = clip.get("nano_banana_prompt_first_b", "")
    if prompt_first_a:
        st.markdown('<div class="prompt-label">NB First Frame — Prompt A</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="prompt-block">{prompt_first_a}</div>', unsafe_allow_html=True)
    if prompt_first_b and prompt_first_b != prompt_first_a:
        st.markdown('<div class="prompt-label">NB First Frame — Prompt B</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="prompt-block">{prompt_first_b}</div>', unsafe_allow_html=True)

    # NB Last Frame prompts (A + B)
    prompt_last_a = clip.get("nano_banana_prompt_last", "")
    prompt_last_b = clip.get("nano_banana_prompt_last_b", "")
    if prompt_last_a:
        st.markdown('<div class="prompt-label">NB Last Frame — Prompt A</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="prompt-block">{prompt_last_a}</div>', unsafe_allow_html=True)
    if prompt_last_b and prompt_last_b != prompt_last_a:
        st.markdown('<div class="prompt-label">NB Last Frame — Prompt B</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="prompt-block">{prompt_last_b}</div>', unsafe_allow_html=True)

    # VEO prompts (A + B)
    veo_a = clip.get("veo_prompt", "")
    veo_b = clip.get("veo_prompt_b", "")
    veo_parts = []
    if clip.get("veo_duration"): veo_parts.append(f'{clip["veo_duration"]}с')
    if clip.get("veo_aspect_ratio"): veo_parts.append(clip["veo_aspect_ratio"])
    if clip.get("veo_model"): veo_parts.append(clip["veo_model"])
    veo_info = " | ".join(veo_parts) if veo_parts else "VEO 3.1 Fast"
    if veo_a:
        st.markdown(f'<div class="prompt-label">VEO — Prompt A ({veo_info})</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="prompt-block">{veo_a}</div>', unsafe_allow_html=True)
    if veo_b and veo_b != veo_a:
        st.markdown(f'<div class="prompt-label">VEO — Prompt B</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="prompt-block">{veo_b}</div>', unsafe_allow_html=True)

    if clip.get("audio_note"):
        st.markdown('<div class="prompt-label">Audio</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="prompt-block">{clip["audio_note"]}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # --- Row 4: Generated frames ---
    st.markdown("**Сгенерированные кадры**")
    # Support both old format (CLIP_first.png) and new format (CLIP/first.png)
    first_frame = FRAMES_DIR / f"{clip_id}_first.png"
    if not first_frame.exists():
        first_frame = FRAMES_DIR / clip_id / "first.png"
    last_frame = FRAMES_DIR / f"{clip_id}_last.png"
    if not last_frame.exists():
        last_frame = FRAMES_DIR / clip_id / "last.png"
    comp_status = get_component_status(clip_id)

    fcol1, fcol2 = st.columns(2)
    with fcol1:
        if first_frame.exists():
            st.image(str(first_frame), caption="First frame", use_container_width=True)
            download_button_for_file(first_frame, "Скачать first frame", f"dl_first_{clip_id}")
        else:
            first_st = comp_status.get("nb_first", "pending")
            if first_st == "accepted":
                st.markdown(
                    '<div style="background:#1B3A1B;border:1px solid #2E7D32;border-radius:8px;'
                    'padding:40px;text-align:center;color:#A5D6A7;">'
                    '✅ First frame — принят</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="background:#1A1D26;border:1px dashed #333;border-radius:8px;'
                    'padding:40px;text-align:center;color:#555;">First frame — не сгенерирован</div>',
                    unsafe_allow_html=True,
                )
    with fcol2:
        if last_frame.exists():
            st.image(str(last_frame), caption="Last frame", use_container_width=True)
            download_button_for_file(last_frame, "Скачать last frame", f"dl_last_{clip_id}")
        else:
            last_st = comp_status.get("nb_last", "pending")
            if last_st == "accepted":
                st.markdown(
                    '<div style="background:#1B3A1B;border:1px solid #2E7D32;border-radius:8px;'
                    'padding:40px;text-align:center;color:#A5D6A7;">'
                    '✅ Last frame — принят</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="background:#1A1D26;border:1px dashed #333;border-radius:8px;'
                    'padding:40px;text-align:center;color:#555;">Last frame — не сгенерирован</div>',
                    unsafe_allow_html=True,
                )

    # --- Row 5: Video (accepted clip + VEO review variants) ---
    st.markdown("**Видео**")
    clip_video = CLIPS_DIR / f"{clip_id}_clip.mp4"
    has_accepted_video = clip_video.exists()
    if has_accepted_video:
        st.video(str(clip_video))
        download_button_for_file(clip_video, "Скачать видео", f"dl_video_{clip_id}")

    # Check for VEO review variants
    veo_review_dir = REVIEW_DIR / clip_id / "veo"
    has_veo_variants = False
    if veo_review_dir.exists():
        for ad in veo_review_dir.glob("attempt_*"):
            if list(ad.glob("*.mp4")) or list(ad.glob("*/*.mp4")):
                has_veo_variants = True
                break

    if has_veo_variants:
        if not has_accepted_video:
            st.markdown("*VEO варианты для ревью:*")
        render_veo_variants(clip_id)
    elif not has_accepted_video:
        veo_st = comp_status.get("veo", "pending")
        if veo_st == "accepted":
            st.markdown(
                '<div style="background:#1B3A1B;border:1px solid #2E7D32;border-radius:8px;'
                'padding:40px;text-align:center;color:#A5D6A7;">'
                '✅ Видео — принято</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:#1A1D26;border:1px dashed #333;border-radius:8px;'
                'padding:40px;text-align:center;color:#555;">Видео — не сгенерировано</div>',
                unsafe_allow_html=True,
            )

    # --- Row 6: NB Review Variants ---
    for comp in ['nb_first', 'nb_mid', 'nb_last']:
        render_nb_review_variants(clip_id, comp)


def page_scenario():
    """Scenario page — full script text."""
    st.header("Сценарий")

    if SCENARIO_FILE.exists():
        text = SCENARIO_FILE.read_text(encoding="utf-8")
        # Split into scenes for better navigation
        st.download_button(
            "Скачать сценарий",
            text.encode("utf-8"),
            file_name="scenario_signal.txt",
            mime="text/plain",
            key="dl_scenario",
        )
        st.markdown("---")

        # Try to split by scene markers (INT./EXT. or numbered scenes)
        lines = text.split("\n")
        current_block = []
        blocks = []
        for line in lines:
            # Detect scene headers (lines that are all caps or start with INT./EXT.)
            stripped = line.strip()
            if stripped and (
                stripped.startswith("СЦЕНА")
                or stripped.startswith("INT.")
                or stripped.startswith("EXT.")
                or (stripped.isupper() and len(stripped) > 10)
            ):
                if current_block:
                    blocks.append("\n".join(current_block))
                current_block = [line]
            else:
                current_block.append(line)
        if current_block:
            blocks.append("\n".join(current_block))

        if len(blocks) > 1:
            for block in blocks:
                first_line = block.strip().split("\n")[0].strip()
                if first_line:
                    with st.expander(first_line[:80], expanded=False):
                        st.text(block)
        else:
            st.text(text)
    else:
        st.warning("Файл сценария не найден (scenario_signal.txt)")


def page_references():
    """Reference gallery — characters and locations."""
    st.header("Референсы")

    tab_chars, tab_locs = st.tabs(["Персонажи", "Локации"])

    with tab_chars:
        st.subheader("Персонажи")
        if CHARS_DIR.exists():
            files = sorted(CHARS_DIR.glob("char_*"))
            if files:
                # Group by character name
                groups: dict[str, list[Path]] = {}
                for f in files:
                    # Extract character name: char_amin_full.png -> amin
                    parts = f.stem.split("_")
                    if len(parts) >= 2:
                        char_key = parts[1]  # e.g. "amin", "karim"
                        groups.setdefault(char_key, []).append(f)

                for char_key in sorted(groups):
                    display_name = CHAR_DISPLAY.get(
                        char_key.capitalize(), char_key.capitalize()
                    )
                    st.markdown(f"#### {display_name}")
                    char_files = groups[char_key]
                    cols = st.columns(min(len(char_files), 4))
                    for i, fpath in enumerate(char_files):
                        with cols[i % len(cols)]:
                            st.image(str(fpath), caption=fpath.name, use_container_width=True)
            else:
                st.info("Нет файлов персонажей.")
        else:
            st.warning("Папка персонажей не найдена.")

    with tab_locs:
        st.subheader("Локации")
        if LOCS_DIR.exists():
            files = sorted(LOCS_DIR.glob("loc_*"))
            if files:
                # Group by location name
                groups: dict[str, list[Path]] = {}
                for f in files:
                    parts = f.stem.split("_")
                    if len(parts) >= 2:
                        loc_key = parts[1]  # e.g. "garazh", "amin", "kabinet"
                        groups.setdefault(loc_key, []).append(f)

                loc_display = {
                    "garazh": "Гараж",
                    "amin": "Комната Амина",
                    "kabinet": "Кабинет Папы",
                    "besedka": "Беседка",
                    "dom": "Дом (экстерьер)",
                }
                for loc_key in sorted(groups):
                    display_name = loc_display.get(loc_key, loc_key.capitalize())
                    st.markdown(f"#### {display_name}")
                    loc_files = groups[loc_key]
                    cols = st.columns(min(len(loc_files), 4))
                    for i, fpath in enumerate(loc_files):
                        with cols[i % len(cols)]:
                            st.image(str(fpath), caption=fpath.name, use_container_width=True)
            else:
                st.info("Нет файлов локаций.")
        else:
            st.warning("Папка локаций не найдена.")


def page_keyframe_pairs():
    """Overview of all clips with first+last keyframe pairs for quick review."""
    st.header("Пары кадров")

    clips = load_clips()

    # Stats
    total = len(clips)
    pairs_done = sum(
        1 for c in clips
        if (FRAMES_DIR / f"{c['clip_id']}_first.png").exists()
        and (FRAMES_DIR / f"{c['clip_id']}_last.png").exists()
    )
    veo_done = 0
    for c in clips:
        veo_dir = REVIEW_DIR / c["clip_id"] / "veo"
        if veo_dir.exists():
            for ad in veo_dir.glob("attempt_*"):
                if list(ad.glob("*.mp4")) or list(ad.glob("*/*.mp4")):
                    veo_done += 1
                    break

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Пары кадров", f"{pairs_done}/{total}")
    with col2:
        st.metric("VEO видео", f"{veo_done}/{total}")
    with col3:
        st.progress(pairs_done / total if total else 0)

    st.markdown("---")

    # Group by scene
    current_scene = None
    for clip in clips:
        if clip["scene_id"] != current_scene:
            current_scene = clip["scene_id"]
            color = SCENE_COLORS.get(current_scene, "#888")
            label = SCENE_LABELS.get(current_scene, current_scene)
            st.markdown(
                f'<h4 style="border-left:4px solid {color};padding-left:12px;'
                f'margin-top:20px;margin-bottom:8px;">{label}</h4>',
                unsafe_allow_html=True,
            )

        clip_id = clip["clip_id"]
        first_frame = FRAMES_DIR / f"{clip_id}_first.png"
        last_frame = FRAMES_DIR / f"{clip_id}_last.png"

        has_first = first_frame.exists()
        has_last = last_frame.exists()
        has_veo = False
        veo_count = 0
        veo_dir = REVIEW_DIR / clip_id / "veo"
        if veo_dir.exists():
            for ad in veo_dir.glob("attempt_*"):
                vids = list(ad.glob("*.mp4")) + list(ad.glob("*/*.mp4"))
                veo_count += len(vids)
            has_veo = veo_count > 0

        # Status badge
        if has_first and has_last and has_veo:
            badge = '<span style="background:#1B5E20;color:#A5D6A7;padding:2px 8px;border-radius:4px;font-size:0.8em;">VEO готово</span>'
        elif has_first and has_last:
            badge = '<span style="background:#E65100;color:#FFE0B2;padding:2px 8px;border-radius:4px;font-size:0.8em;">Кадры готовы</span>'
        elif has_first or has_last:
            badge = '<span style="background:#4A148C;color:#CE93D8;padding:2px 8px;border-radius:4px;font-size:0.8em;">Частично</span>'
        else:
            badge = '<span style="background:#B71C1C;color:#FFCDD2;padding:2px 8px;border-radius:4px;font-size:0.8em;">Не начато</span>'

        # Row: clip_id | first | last | status
        cols = st.columns([1.5, 3, 3, 2])
        with cols[0]:
            veo_info = f" ({veo_count} vid)" if has_veo else ""
            st.markdown(f"**{clip_id}**{veo_info}")
        with cols[1]:
            if has_first:
                st.image(str(first_frame), use_container_width=True, caption="First")
            else:
                st.markdown(
                    '<div style="background:#1A1D26;border:1px dashed #333;border-radius:6px;'
                    'padding:30px;text-align:center;color:#555;font-size:0.8em;">—</div>',
                    unsafe_allow_html=True,
                )
        with cols[2]:
            if has_last:
                st.image(str(last_frame), use_container_width=True, caption="Last")
            else:
                st.markdown(
                    '<div style="background:#1A1D26;border:1px dashed #333;border-radius:6px;'
                    'padding:30px;text-align:center;color:#555;font-size:0.8em;">—</div>',
                    unsafe_allow_html=True,
                )
        with cols[3]:
            st.markdown(badge, unsafe_allow_html=True)
            desc = clip.get("scene_description_ru", "")
            if desc:
                st.markdown(f'<span style="font-size:0.75em;color:#888;">{desc[:60]}...</span>',
                            unsafe_allow_html=True)


def _find_veo_videos(clip_id):
    """Find all VEO mp4 files for a clip, newest attempt first."""
    veo_dir = REVIEW_DIR / clip_id / "veo"
    if not veo_dir.exists():
        return []
    videos = []
    # Find the latest attempt
    attempts = sorted(veo_dir.glob("attempt_*"), reverse=True)
    if not attempts:
        return []
    latest = attempts[0]
    # Two formats: with prompt_a/prompt_b subdirs or flat
    for mp4 in sorted(latest.rglob("*.mp4")):
        videos.append(mp4)
    return videos


def page_timeline():
    """Visual timeline with VEO videos."""
    st.header("Таймлайн")

    clips = load_clips()
    current_scene = None

    for clip in clips:
        if clip["scene_id"] != current_scene:
            current_scene = clip["scene_id"]
            color = SCENE_COLORS.get(current_scene, "#888")
            label = SCENE_LABELS.get(current_scene, current_scene)
            st.markdown(
                f'<h4 style="color:{color};margin-top:20px;">{label}</h4>',
                unsafe_allow_html=True,
            )

        clip_id = clip["clip_id"]
        status = get_status(clip_id)
        _, status_icon = STATUS_MAP[status]

        # Header row
        cols = st.columns([1.5, 5, 0.5])
        with cols[0]:
            st.markdown(f"**{status_icon} {clip_id}**")
        with cols[1]:
            st.markdown(clip["scene_description_ru"])

        # VEO videos — max 2 per row for comfortable viewing
        videos = _find_veo_videos(clip_id)
        if videos:
            for row_start in range(0, len(videos), 2):
                row_videos = videos[row_start:row_start + 2]
                vid_cols = st.columns(2)
                for i, vpath in enumerate(row_videos):
                    with vid_cols[i]:
                        st.video(str(vpath))
        else:
            # Fallback: show keyframes if no videos
            first_frame = FRAMES_DIR / f"{clip_id}_first.png"
            last_frame = FRAMES_DIR / f"{clip_id}_last.png"
            if first_frame.exists() or last_frame.exists():
                thumb_cols = st.columns(2)
                with thumb_cols[0]:
                    if first_frame.exists():
                        st.image(str(first_frame), caption="First")
                with thumb_cols[1]:
                    if last_frame.exists():
                        st.image(str(last_frame), caption="Last")

        st.divider()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="Путь Амина — Dashboard",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_css()

    # --- Sidebar header ---
    st.sidebar.markdown(
        '<h1 style="text-align:center;color:#E8B849;">🎬 Путь Амина</h1>',
        unsafe_allow_html=True,
    )

    # --- Series selector ---
    series_options = list(SERIES.keys())
    series_labels = {k: f'{v["icon"]} {v["title"]}' for k, v in SERIES.items()}

    if "current_series" not in st.session_state:
        st.session_state.current_series = DEFAULT_SERIES

    selected_series = st.sidebar.selectbox(
        "Серия",
        series_options,
        index=series_options.index(st.session_state.current_series),
        format_func=lambda x: series_labels[x],
        key="series_select",
    )
    if selected_series != st.session_state.current_series:
        st.session_state.current_series = selected_series
        global _r2_cache_loaded, _r2_manifest_cache
        _r2_cache_loaded = False
        _r2_manifest_cache = {}
        st.rerun()

    # Apply series config to globals
    _apply_series()
    cfg = _get_series_config()

    # --- Check if series is configured ---
    prompts_available = PROMPTS_FILE.exists()
    if not prompts_available and _R2_OK:
        prompts_available = r2_storage.file_exists(_r2_key(PROMPTS_FILE))
    if not prompts_available:
        st.sidebar.markdown("---")
        st.header(f'{cfg["icon"]} Серия: {cfg["title"]}')
        st.info(
            f'Серия **{cfg["title"]}** ещё не настроена.\n\n'
            f'Для начала работы нужно:\n'
            f'1. Добавить сценарий: `{cfg["scenario_file"]}`\n'
            f'2. Создать промпты: `{cfg["prompts_file"]}`\n'
            f'3. Загрузить референсы персонажей и локаций'
        )
        return

    # --- Navigation ---
    page = st.sidebar.radio(
        "Навигация",
        ["Chain Ревью", "Ревью", "Пары кадров", "Клипы", "Таймлайн", "Сценарий", "Референсы"],
        label_visibility="collapsed",
    )

    # --- Page routing ---
    if page == "Chain Ревью":
        page_chain_review()
    elif page == "Ревью":
        page_review()
    elif page == "Пары кадров":
        page_keyframe_pairs()
    elif page == "Клипы":
        st.title("Клипы")
        page_clips()
    elif page == "Таймлайн":
        page_timeline()
    elif page == "Сценарий":
        page_scenario()
    elif page == "Референсы":
        page_references()

    # --- Footer ---
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<p style="text-align:center;color:#555;font-size:0.75em;">'
        'Путь Амина<br>3D Pixar-style Animation<br>'
        'Nano Banana Pro + VEO 3.1</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
