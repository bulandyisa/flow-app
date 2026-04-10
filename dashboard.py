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

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

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
    "sosed_v2": {
        "id": "sosed_v2",
        "title": "Сосед v2",
        "icon": "🏠",
        "color": "#3A9BD5",
        "output_dir": "output_sosed_v2",
        "prompts_file": "output_sosed_v2/prompts/all_prompts.json",
        "scenario_file": "scenario_sosed.txt",
        "chars_dir": "sosed_персонажи_hq",
        "chars_dir_fallback": "sosed_персонажи",
        "locs_dir": "sosed_локации_hq",
        "locs_dir_fallback": "sosed_локации",
        "scene_colors": "auto",
        "scene_labels": "auto",
        "char_display": {
            "Amin": "Амин", "Karim": "Карим", "Tako": "Тако",
            "Papa": "Папа", "Mama": "Мама", "Aya": "Ая",
            "Jamil": "Джамиль", "Simba": "Симба",
        },
    },
    "sosed_v3": {
        "id": "sosed_v3",
        "title": "Сосед v3 (Ч.1)",
        "icon": "🏠",
        "color": "#2E86C1",
        "output_dir": "output_sosed_v3",
        "prompts_file": "output_sosed_v3/prompts/all_prompts.json",
        "scenario_file": "sosed_final_v3.docx",
        "chars_dir": "sosed_персонажи_hq",
        "chars_dir_fallback": "sosed_персонажи",
        "locs_dir": "sosed_локации_hq",
        "locs_dir_fallback": "sosed_локации",
        "scene_colors": "auto",
        "scene_labels": "auto",
        "char_display": {
            "Amin": "Амин", "Karim": "Карим", "Tako": "Тако",
            "Papa": "Папа", "Mama": "Мама", "Aya": "Ая",
            "Jamil": "Джамиль", "Simba": "Симба",
        },
    },
    "sosed_v3_p2": {
        "id": "sosed_v3_p2",
        "title": "Сосед v3 (Ч.2)",
        "icon": "🏠",
        "color": "#1ABC9C",
        "output_dir": "output_sosed_v3_part2",
        "prompts_file": "output_sosed_v3_part2/prompts/all_prompts.json",
        "scenario_file": "sosed_final_v3.docx",
        "chars_dir": "sosed_персонажи_hq",
        "chars_dir_fallback": "sosed_персонажи",
        "locs_dir": "sosed_локации_hq",
        "locs_dir_fallback": "sosed_локации",
        "scene_colors": "auto",
        "scene_labels": "auto",
        "char_display": {
            "Amin": "Амин", "Karim": "Карим", "Tako": "Тако",
            "Papa": "Папа", "Mama": "Мама", "Aya": "Ая",
            "Jamil": "Джамиль", "Simba": "Симба",
        },
    },
    "camera": {
        "id": "camera",
        "title": "Камера",
        "icon": "📷",
        "color": "#E74C3C",
        "output_dir": "output_camera",
        "prompts_file": "output_camera/prompts/all_prompts.json",
        "scenario_file": "«КАМЕРА» .docx",
        "chars_dir": "camera_персонажи_hq",
        "chars_dir_fallback": "camera_персонажи_hq",
        "locs_dir": "camera_локации_hq",
        "locs_dir_fallback": "camera_локации_hq",
        "scene_colors": "auto",
        "scene_labels": "auto",
        "char_display": {
            "Amin": "Амин", "Karim": "Карим", "Tako": "Тако",
            "Aya": "Ая", "Papa": "Папа", "Mama": "Мама",
            "Jamil": "Джамиль", "Simba": "Симба",
            "Starik": "Старик", "Farid": "Фарид",
            "Hozyaika": "Хозяйка", "Collector": "Коллекционер",
        },
    },
}

# Default to the last series in the dict (most recent)
DEFAULT_SERIES = list(SERIES.keys())[-1]


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
_AUTO_SCENES: bool = False

# Russian labels for location file stems (used in refs page & review)
_LOC_LABELS: dict[str, str] = {
    # Сосед
    "loc_kitchen": "Кухня",
    "loc_fence": "Забор",
    "loc_gazebo": "Беседка",
    "loc_besedka": "Беседка",
    "loc_carwash": "Автомойка",
    "loc_jamil_house_front": "Дом Джамиля — фасад",
    "loc_jamil_house_door": "Дом Джамиля — дверь",
    "loc_jamil_house_fence": "Дом Джамиля — забор",
    "loc_jamil_house_street": "Дом Джамиля — улица",
    "loc_jamil_yard": "Двор Джамиля",
    "loc_jamil_corridor": "Коридор Джамиля",
    "loc_jamil_van": "Фургон Джамиля",
    "loc_night_jamil": "Ночь у дома Джамиля",
    "loc_library": "Библиотека",
    "loc_old_quarter": "Старый квартал",
    "loc_old_mill": "Старая мельница",
    "loc_parking_mosque": "Парковка у мечети",
    "loc_strojka": "Стройка",
    "loc_underground_corridor": "Подземный коридор",
    "loc_underground_hall": "Подземный зал",
    # Камера
    "loc_garazh": "Гараж",
    "loc_amin_room": "Комната Амина",
    "loc_amin_porch": "Крыльцо Амина",
    "loc_kabinet": "Кабинет Папы",
    "loc_dom": "Дом (экстерьер)",
    "loc_farid_room": "Комната Фарида",
    "loc_photo_studio": "Фотоателье",
    "loc_night_street": "Ночная улица",
    "loc_night_alley": "Ночной переулок",
    "loc_night_hiding": "Ночь — укрытие",
    "loc_night_path": "Ночная тропа",
    "loc_well": "Колодец",
    "loc_outskirts": "Окрестности",
    "loc_alley": "Переулок",
    "loc_quarter": "Старый квартал (доп.)",
    # Общие
    "loc_hallway": "Прихожая",
    "loc_bridge": "Мост",
    "loc_park": "Парк",
    "loc_school": "Школа",
    "loc_shop": "Магазин",
    "loc_tower": "Башня",
    "loc_wasteland": "Пустырь",
    "loc_tako_room": "Комната Тако",
    "loc_basement": "Подвал",
}


def _loc_group(stem: str) -> str:
    """Find the best matching Russian label for a location file stem."""
    parts = stem.split("_")
    for end in range(len(parts), 1, -1):
        candidate = "_".join(parts[:end])
        if candidate in _LOC_LABELS:
            return _LOC_LABELS[candidate]
    return stem.replace("loc_", "").replace("_", " ").capitalize()



def _apply_series():
    """Apply current series config to global variables."""
    global PROMPTS_FILE, FRAMES_DIR, CLIPS_DIR, REVIEW_DIR, CHARS_DIR, LOCS_DIR
    global SCENARIO_FILE, STATUS_FILE, COMMANDS_FILE, SCENE_COLORS, SCENE_LABELS, CHAR_DISPLAY, _AUTO_SCENES

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
    SCENE_COLORS = cfg["scene_colors"] if cfg["scene_colors"] != "auto" else {}
    SCENE_LABELS = cfg["scene_labels"] if cfg["scene_labels"] != "auto" else {}
    _AUTO_SCENES = cfg["scene_colors"] == "auto" or cfg["scene_labels"] == "auto"
    CHAR_DISPLAY = cfg["char_display"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _show_local_image(path, **kwargs):
    """Show image by reading bytes — works reliably in all Streamlit versions."""
    p = Path(path) if not isinstance(path, Path) else path
    if p.exists():
        try:
            st.image(p.read_bytes(), **kwargs)
        except Exception as e:
            st.warning(f"Не удалось открыть изображение: {p.name} ({e})")
    elif isinstance(path, str) and path.startswith("http"):
        st.image(path, **kwargs)
    else:
        st.warning(f"Файл не найден: {p}")


def _show_image_with_lightbox(path, caption="", width="100%"):
    """Show image as HTML <img> with base64 data URI — supports lightbox zoom."""
    import base64
    p = Path(path) if not isinstance(path, Path) else path
    if not p.exists():
        st.warning(f"Файл не найден: {p}")
        return
    data = p.read_bytes()
    b64 = base64.b64encode(data).decode()
    ext = p.suffix.lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}.get(ext, "image/png")
    cap_html = f'<br><small>{caption}</small>' if caption else ""
    st.markdown(
        f'<img src="data:{mime};base64,{b64}" style="width:{width};border-radius:4px;cursor:pointer;" />{cap_html}',
        unsafe_allow_html=True,
    )

@st.cache_data(ttl=60)
def _load_clips_cached(prompts_local: str) -> list[dict]:
    """Load clip data from local JSON file."""
    p = Path(prompts_local)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return []


def load_clips() -> list[dict]:
    clips = _load_clips_cached(str(PROMPTS_FILE))
    if _AUTO_SCENES and clips:
        _build_auto_scene_maps(clips)
    return clips


def _build_auto_scene_maps(clips: list[dict]):
    """Auto-generate SCENE_COLORS and SCENE_LABELS from clips data."""
    global SCENE_COLORS, SCENE_LABELS
    if SCENE_COLORS and SCENE_LABELS:
        return  # already built
    palette = [
        "#E8B849", "#49B6E8", "#E85A49", "#6BE849", "#C149E8",
        "#E89849", "#49E8D6", "#E84980", "#8B49E8", "#B8E849",
        "#E8D649", "#4998E8", "#49E8A0", "#E86B49", "#A349E8",
    ]
    seen = {}
    for clip in clips:
        sid = clip.get("scene_id", "")
        if sid and sid not in seen:
            desc = clip.get("scene_description_ru", "")
            short = desc[:50] + "…" if len(desc) > 50 else desc
            seen[sid] = short
    SCENE_COLORS = {sid: palette[i % len(palette)] for i, sid in enumerate(seen)}
    SCENE_LABELS = {sid: f"{sid} — {desc}" for sid, desc in seen.items()}


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


@st.cache_resource(ttl=300)
def _batch_scan_variants(review_dir_str: str) -> dict:
    """Batch-scan review directory once. Returns {clip_id: {comp: [(attempt_num, [file_str])]}}."""
    review_dir = Path(review_dir_str)
    if not review_dir.exists():
        return {}
    result = {}
    try:
        clip_dirs = sorted(review_dir.iterdir())
    except OSError:
        return {}
    for clip_dir in clip_dirs:
        if not clip_dir.is_dir():
            continue
        cid = clip_dir.name
        clip_data = {}
        try:
            comp_dirs = list(clip_dir.iterdir())
        except OSError:
            continue
        for comp_dir in comp_dirs:
            if not comp_dir.is_dir():
                continue
            comp = comp_dir.name
            if comp not in ("nb_first", "nb_mid", "nb_last", "veo"):
                continue
            attempts = []
            try:
                attempt_dirs = sorted(comp_dir.iterdir())
            except OSError:
                continue
            for attempt_dir in attempt_dirs:
                if not attempt_dir.is_dir() or not attempt_dir.name.startswith("attempt_"):
                    continue
                try:
                    attempt_num = int(attempt_dir.name.replace("attempt_", ""))
                except ValueError:
                    continue
                ext = ".mp4" if comp == "veo" else ".png"
                files = sorted(str(f) for f in attempt_dir.iterdir() if f.is_file() and f.suffix == ext)
                if not files:
                    pa = attempt_dir / "prompt_a"
                    if pa.exists():
                        files = sorted(str(f) for f in pa.iterdir() if f.is_file() and f.suffix == ext)
                if files:
                    attempts.append((attempt_num, files))
            if attempts:
                clip_data[comp] = attempts
        if clip_data:
            result[cid] = clip_data
    return result


@st.cache_resource(ttl=300)
def _batch_load_manifests_local(review_dir_str: str) -> dict:
    """Batch-load all local manifests. Returns {clip_id: manifest_dict}."""
    review_dir = Path(review_dir_str)
    if not review_dir.exists():
        return {}
    result = {}
    for manifest_path in review_dir.glob("*/manifest.json"):
        try:
            with open(manifest_path) as f:
                m = json.load(f)
            cid = m.get("clip_id", manifest_path.parent.name)
            result[cid] = _normalize_manifest(m)
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return result


def _clear_local_caches():
    """Clear batch caches after accept/reject actions."""
    _batch_scan_variants.clear()
    _batch_load_manifests_local.clear()


def get_all_attempt_variants(clip_id: str, component: str) -> list[tuple[int, list]]:
    """Get variants for ALL attempts. Returns [(attempt_num, [path_or_url]), ...].

    On Railway (R2 mode): builds URLs from manifest data.
    Locally: uses batch-scanned cache for speed.
    """
    # Try local filesystem (batch-cached)
    cache = _batch_scan_variants(str(REVIEW_DIR))
    clip_data = cache.get(clip_id, {})
    local_result = clip_data.get(component, [])
    if local_result:
        return local_result

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

def inject_lightbox():
    """Inject a JS lightbox overlay for variant images with keyboard navigation."""
    import streamlit.components.v1 as components
    components.html("""
    <script>
    (function() {
        const doc = window.parent.document;
        if (doc.getElementById('lb-overlay')) return;

        // --- Create overlay ---
        const overlay = doc.createElement('div');
        overlay.id = 'lb-overlay';
        overlay.style.cssText = 'display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.92); z-index:999999; align-items:center; justify-content:center; cursor:pointer; flex-direction:column;';

        const img = doc.createElement('img');
        img.id = 'lb-img';
        img.style.cssText = 'max-width:92vw; max-height:82vh; object-fit:contain; cursor:default; border-radius:6px; box-shadow:0 0 40px rgba(0,0,0,0.5);';
        overlay.appendChild(img);

        const counter = doc.createElement('div');
        counter.id = 'lb-counter';
        counter.style.cssText = 'position:absolute; bottom:18px; left:50%; transform:translateX(-50%); color:#ccc; font-size:16px; font-family:monospace; background:rgba(0,0,0,0.6); padding:4px 16px; border-radius:12px;';
        overlay.appendChild(counter);

        const caption = doc.createElement('div');
        caption.id = 'lb-caption';
        caption.style.cssText = 'position:absolute; top:16px; left:50%; transform:translateX(-50%); color:#fff; font-size:14px; font-family:monospace; background:rgba(0,0,0,0.6); padding:4px 16px; border-radius:12px; max-width:80vw; text-align:center;';
        overlay.appendChild(caption);

        function makeArrow(text, side) {
            const btn = doc.createElement('div');
            btn.textContent = text;
            btn.style.cssText = 'position:absolute; top:50%; ' + side + ':16px; transform:translateY(-50%); color:white; font-size:56px; cursor:pointer; user-select:none; padding:8px 14px; opacity:0.5; transition:opacity 0.15s;';
            btn.onmouseover = function() { btn.style.opacity = '1'; };
            btn.onmouseout = function() { btn.style.opacity = '0.5'; };
            return btn;
        }
        const prevBtn = makeArrow('\\u2039', 'left');
        const nextBtn = makeArrow('\\u203A', 'right');
        overlay.appendChild(prevBtn);
        overlay.appendChild(nextBtn);

        doc.body.appendChild(overlay);

        let images = [];
        let captions = [];
        let idx = 0;

        function show() {
            overlay.style.display = 'flex';
            img.src = images[idx];
            counter.textContent = (idx + 1) + ' / ' + images.length;
            caption.textContent = captions[idx] || '';
        }
        function close() { overlay.style.display = 'none'; }
        function nav(dir) { idx = (idx + dir + images.length) % images.length; show(); }

        overlay.onclick = function(e) { if (e.target === overlay) close(); };
        prevBtn.onclick = function(e) { e.stopPropagation(); nav(-1); };
        nextBtn.onclick = function(e) { e.stopPropagation(); nav(1); };

        doc.addEventListener('keydown', function(e) {
            if (overlay.style.display === 'flex') {
                if (e.key === 'ArrowLeft')  { nav(-1); e.preventDefault(); }
                if (e.key === 'ArrowRight') { nav(1);  e.preventDefault(); }
                if (e.key === 'Escape')     { close(); e.preventDefault(); }
            }
        });

        // --- Attach click handlers to Streamlit images ---
        function attach() {
            var allImgs = doc.querySelectorAll('[data-testid="stImage"] img, [data-testid="stImageContainer"] img');
            if (!allImgs.length) {
                allImgs = doc.querySelectorAll('img[style*="width"]');
            }
            allImgs.forEach(function(el) {
                if (el.dataset.lbReady) return;
                if (!el.src || el.src.indexOf('data:') === 0 && el.src.length < 200) return;
                el.dataset.lbReady = '1';
                el.style.cursor = 'zoom-in';
                el.addEventListener('click', function(e) {
                    e.stopPropagation();
                    // Find sibling images — walk up DOM to find the best container
                    // Keep climbing to find the container with the MOST images (not just first with >1)
                    var container = null;
                    var bestCount = 0;
                    var walk = el.parentElement;
                    for (var d = 0; d < 20 && walk; d++) {
                        // Stop at major boundaries
                        if (walk.tagName === 'MAIN' || walk === doc.body) break;
                        var testId = walk.getAttribute('data-testid');
                        if (testId === 'stVerticalBlockBorderWrapper' || testId === 'stExpander' || walk.tagName === 'DETAILS') {
                            var cnt = walk.querySelectorAll('img[data-lb-ready="1"]').length;
                            if (cnt > bestCount) { container = walk; bestCount = cnt; }
                            break;
                        }
                        var cnt = walk.querySelectorAll('img[data-lb-ready="1"]').length;
                        if (cnt > bestCount) { container = walk; bestCount = cnt; }
                        walk = walk.parentElement;
                    }
                    if (!container) container = el.closest('main') || doc.body;
                    var siblings = container ? container.querySelectorAll('img[data-lb-ready="1"]') : [el];
                    images = [];
                    captions = [];
                    idx = 0;
                    siblings.forEach(function(sib, i) {
                        images.push(sib.src);
                        // Try to find caption text
                        var cap = sib.parentElement.querySelector('[data-testid="stCaptionContainer"]');
                        if (!cap) {
                            var next = sib.closest('[data-testid="stImage"], [data-testid="stImageContainer"]');
                            if (next) cap = next.nextElementSibling;
                        }
                        captions.push(cap ? cap.textContent.trim() : '');
                        if (sib === el) idx = i;
                    });
                    if (images.length === 0) { images = [el.src]; captions = ['']; idx = 0; }
                    show();
                });
            });
        }

        attach();
        var obs = new MutationObserver(function() { setTimeout(attach, 300); });
        obs.observe(doc.body, { childList: true, subtree: true });
    })();
    </script>
    """, height=0)


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
                    _show_local_image(vpath, use_container_width=True)
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


def _load_manifest(clip_id: str) -> dict:
    """Load manifest.json for a clip from local batch cache."""
    batch = _batch_load_manifests_local(str(REVIEW_DIR))
    if clip_id in batch:
        return batch[clip_id]
    return _default_manifest(clip_id)


def _save_manifest(clip_id: str, manifest: dict):
    """Save manifest.json locally."""
    path = REVIEW_DIR / clip_id / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    _clear_local_caches()


def _chain_select_variant(clip_id: str, component: str, attempt: int, variant_idx: int):
    """Accept a variant: update manifest + copy to frames/clips."""
    suffixes = {"nb_first": "first", "nb_mid": "mid", "nb_last": "last"}
    manifest = _load_manifest(clip_id)

    attempt_dir = REVIEW_DIR / clip_id / component / f"attempt_{attempt}"
    if component in suffixes:
        ext = ".png"
        variant_file = attempt_dir / f"variant_{variant_idx + 1}{ext}"
        if not variant_file.exists():
            variant_file = attempt_dir / "prompt_a" / f"variant_{variant_idx + 1}{ext}"
        dest = FRAMES_DIR / f"{clip_id}_{suffixes[component]}{ext}"
    elif component == "veo":
        ext = ".mp4"
        variant_file = attempt_dir / f"variant_{variant_idx + 1}{ext}"
        if not variant_file.exists():
            variant_file = attempt_dir / "prompt_a" / f"variant_{variant_idx + 1}{ext}"
        dest = CLIPS_DIR / f"{clip_id}_clip{ext}"
    else:
        dest = None

    if dest and variant_file.exists():
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


def _manual_upload_frame(clip_id: str, component: str, uploaded_file):
    """Save a manually uploaded frame and mark component as accepted.

    Supports nb_first and nb_last.  Converts any image format to PNG.
    """
    from PIL import Image
    import io

    suffixes = {"nb_first": "first", "nb_last": "last"}
    suffix = suffixes.get(component)
    if not suffix:
        raise ValueError(f"Manual upload not supported for {component}")

    # Save to review directory under a special 'manual' attempt
    attempt_dir = REVIEW_DIR / clip_id / component / "manual"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    dest_review = attempt_dir / "variant_1.png"
    img = Image.open(io.BytesIO(uploaded_file.getvalue()))
    img.save(str(dest_review), "PNG")

    # Copy to frames directory
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    dest_frame = FRAMES_DIR / f"{clip_id}_{suffix}.png"
    shutil.copy2(dest_review, dest_frame)

    # Update manifest
    manifest = _load_manifest(clip_id)
    comp = manifest["components"][component]
    comp["status"] = "accepted"
    comp["selected_variant_a"] = {"attempt": "manual", "variant": 0}
    comp["attempts"].append({
        "attempt": "manual",
        "prompt": "manual_upload",
        "variants": [{"file": "variant_1.png", "scores": None, "avg": None}],
        "best_variant": 0,
        "best_avg": None,
    })
    _save_manifest(clip_id, manifest)


def page_chain_review():
    """Chain review page — shows clips by manifest status, not commands.json.

    Works with --chain mode: each clip can be at a different stage.
    Shows only clips that need review (have generated variants not yet accepted).
    """
    import time as _t
    _timers = {}
    _timers["start"] = _t.time()

    # Show notification from previous submit (survives st.rerun)
    if "_chain_notify" in st.session_state:
        msg = st.session_state.pop("_chain_notify")
        st.toast(msg)

    all_clips = load_clips()
    _timers["load_clips"] = _t.time()

    # --- Warning: missing locations ---
    locations_spec = _load_locations_spec()
    if locations_spec:
        ready, total = _locations_ready_count(locations_spec)
        if ready < total:
            st.warning(
                f"Не все локации сгенерированы ({ready}/{total}). "
                f"Сначала подготовьте все референсы в разделе Референсы > Генерация локаций."
            )

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
            ["Ревью фото", "Ревью видео", "Ожидает ревью", "Все фото", "Все видео", "Все клипы", "Принятые", "Заблокированные"],
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

        skip_last = manifest.get("skip_last", True)

        for comp in ("nb_first", "nb_last", "veo"):
            # Skip nb_last entirely when skip_last is enabled
            if comp == "nb_last" and skip_last:
                continue

            comp_data = manifest["components"].get(comp, {})
            status = comp_data.get("status", "pending")

            if status == "accepted":
                continue

            # VEO only reviewable when required frames are accepted
            if comp == "veo":
                first_ok = manifest["components"]["nb_first"].get("status") == "accepted"
                if skip_last:
                    if not first_ok:
                        continue
                else:
                    last_ok = manifest["components"]["nb_last"].get("status") == "accepted"
                    if not (first_ok and last_ok):
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
            last_ok = manifest["components"]["nb_last"].get("status") == "accepted" or manifest.get("skip_last", True)
            veo_ok = manifest["components"].get("veo", {}).get("status") == "accepted"
            if first_ok and last_ok and veo_ok:
                accepted_clips.append(clip_info)
            elif first_ok:
                accepted_clips.append(clip_info)
            else:
                blocked_clips.append(clip_info)

    _timers["classification"] = _t.time()

    # --- Stats ---
    total = len(clips)
    total_first_accepted = sum(
        1 for c in clips
        if all_manifests[c["clip_id"]]["components"]["nb_first"].get("status") == "accepted"
    )
    total_last_accepted = sum(
        1 for c in clips
        if all_manifests[c["clip_id"]]["components"]["nb_last"].get("status") == "accepted"
        or all_manifests[c["clip_id"]].get("skip_last", True)
    )
    total_both = sum(
        1 for c in clips
        if all_manifests[c["clip_id"]]["components"]["nb_first"].get("status") == "accepted"
        and (all_manifests[c["clip_id"]]["components"]["nb_last"].get("status") == "accepted"
             or all_manifests[c["clip_id"]].get("skip_last", True))
    )

    st.header("Chain Ревью")

    # Debug info
    with st.expander("Debug", expanded=False):
        st.write(f"needs_review={len(needs_review)}, accepted={len(accepted_clips)}, blocked={len(blocked_clips)}")

    # Count unique scenes and first-clips-per-scene
    scene_ids = sorted(set(c.get("scene_id", c["clip_id"][:5]) for c in clips))
    num_scenes = len(scene_ids)
    # First clip of each scene = the one that can be generated without dependencies
    first_clip_per_scene = {}
    for c in clips:
        sid = c.get("scene_id", c["clip_id"][:5])
        if sid not in first_clip_per_scene:
            first_clip_per_scene[sid] = c["clip_id"]
    first_clip_ids = set(first_clip_per_scene.values())
    first_clips_generated = sum(
        1 for cid in first_clip_ids
        if all_manifests[cid]["components"]["nb_first"].get("status") in ("generated", "accepted", "rejected")
    )
    first_clips_accepted = sum(
        1 for cid in first_clip_ids
        if all_manifests[cid]["components"]["nb_first"].get("status") == "accepted"
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Всего клипов", total)
    with col2:
        st.metric("Сцен (SC)", num_scenes, help="Первый проход = first-кадр первого клипа каждой SC")
    with col3:
        st.metric("First принято", f"{total_first_accepted}/{total}")
    with col4:
        st.metric("Last принято", f"{total_last_accepted}/{total}")
    with col5:
        st.metric("Ожидает ревью", len(needs_review))

    # Current pass info
    if first_clips_accepted < num_scenes:
        st.caption(f"🔄 **Текущий проход:** first-кадры первых клипов — {first_clips_generated}/{num_scenes} сгенерировано, {first_clips_accepted}/{num_scenes} принято. После принятия → генерация last-кадров.")
    elif total_first_accepted < total:
        st.caption(f"🔄 **Текущий проход:** last-кадры + first-кадры следующих клипов в цепочке.")
    else:
        st.caption(f"🔄 **Текущий проход:** VEO-видео для принятых пар first+last.")

    # Progress bar
    progress = total_both / total if total else 0
    st.progress(progress, text=f"Полностью готовы: {total_both}/{total} ({progress:.0%})")

    st.markdown("---")

    # --- Determine which clips to show ---
    # Helper: filter review_items to only photo or video components
    def _filter_review_items(items, keep):
        """Filter clip list, keeping only review_items matching 'keep' ('photo' or 'video')."""
        filtered = []
        for item in items:
            if keep == "photo":
                ri = [(c, a) for c, a in item.get("review_items", []) if c in ("nb_first", "nb_last")]
            else:
                ri = [(c, a) for c, a in item.get("review_items", []) if c == "veo"]
            if ri:
                filtered.append({**item, "review_items": ri})
        return filtered

    if view_mode == "Ревью фото":
        display_items = _filter_review_items(needs_review, "photo")
        if not display_items:
            st.info("Нет фото, ожидающих ревью.")
    elif view_mode == "Ревью видео":
        display_items = _filter_review_items(needs_review, "video")
        if not display_items:
            st.info("Нет видео, ожидающих ревью.")
    elif view_mode == "Ожидает ревью":
        display_items = needs_review
        if not display_items:
            st.info("Нет клипов, ожидающих ревью. Запустите бота: `./scripts/run_safe.sh --chain --account 1`")
    elif view_mode == "Все фото":
        # Show all clips but only photo review items (hide video variants)
        all_items = needs_review + accepted_clips + blocked_clips
        display_items = []
        for item in all_items:
            ri = [(c, a) for c, a in item.get("review_items", []) if c in ("nb_first", "nb_last")]
            display_items.append({**item, "review_items": ri})
    elif view_mode == "Все видео":
        # Show all clips but only video review items (hide photo variants)
        all_items = needs_review + accepted_clips + blocked_clips
        display_items = []
        for item in all_items:
            ri = [(c, a) for c, a in item.get("review_items", []) if c == "veo"]
            display_items.append({**item, "review_items": ri})
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

    # --- Pagination ---
    CLIPS_PER_PAGE = 40
    total_pages = max(1, (len(display_items) + CLIPS_PER_PAGE - 1) // CLIPS_PER_PAGE)

    st.sidebar.markdown("---")
    page_num = st.sidebar.number_input(
        f"Страница (из {total_pages})",
        min_value=1, max_value=total_pages, value=1,
        key="chain_page_num",
    )
    submit_all = st.sidebar.button("Отправить решения", type="primary", use_container_width=True)

    start_idx = (page_num - 1) * CLIPS_PER_PAGE
    page_items = display_items[start_idx:start_idx + CLIPS_PER_PAGE]

    # --- Collect review_items_map for submit processing ---
    review_items_map = {}  # cid -> [(comp, latest_attempt_num, variants)]
    upload_map = {}  # cid -> (component, uploaded_file) for manual uploads

    # --- Render clips (display only, no saves on interaction) ---
    current_scene = None

    for item in page_items:
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
        veo_status = manifest["components"].get("veo", {}).get("status", "pending")
        is_skip_last = manifest.get("skip_last", True)  # default: skip last

        status_icons = {"accepted": "🟢", "pending": "⚪", "rejected": "🔴", "generated": "🟡", "skipped": "⏭"}
        status_labels = {"accepted": "Принято", "pending": "Ожидание", "rejected": "Отклонено", "generated": "На ревью", "skipped": "Пропущен"}

        desc = clip.get("scene_description_ru", "")[:120]
        veo_badge = ""
        veo_ready = first_status == "accepted" and (last_status == "accepted" or is_skip_last)
        if veo_ready:
            veo_badge = f" &nbsp; `veo:` {status_icons.get(veo_status, '⚪')} {status_labels.get(veo_status, veo_status)}"

        if is_skip_last:
            last_badge = f"`last:` ⏭ Пропущен"
        else:
            last_badge = f"`last:` {status_icons.get(last_status, '⚪')} {status_labels.get(last_status, last_status)}"

        st.markdown(
            f"**{cid}** — {desc} &nbsp; "
            f"`first:` {status_icons.get(first_status, '⚪')} {status_labels.get(first_status, first_status)} &nbsp; "
            f"{last_badge}"
            f"{veo_badge}"
        )

        # "Needs last frame" checkbox (inverted: unchecked = skip_last=True)
        st.checkbox(
            "Нужен последний кадр",
            value=not is_skip_last,
            key=f"needs_last_{cid}",
        )

        # Manual upload for first frame (when not yet accepted)
        if first_status != "accepted" and view_mode not in ("Ревью видео", "Все видео"):
            uploaded = st.file_uploader(
                "Загрузить first кадр вручную",
                type=["png", "jpg", "jpeg"],
                key=f"upload_{cid}_nb_first",
            )
            if uploaded:
                upload_map[cid] = ("nb_first", uploaded)

        # Show accepted frames as thumbnails (skip in video-only modes)
        if first_status == "accepted" and view_mode not in ("Ревью видео", "Все видео"):
            first_frame = FRAMES_DIR / f"{cid}_first.png"
            last_frame = FRAMES_DIR / f"{cid}_last.png"
            frames_to_show = []
            if first_frame.exists():
                frames_to_show.append((first_frame, "First (принято)"))
            if last_status == "accepted" and last_frame.exists():
                frames_to_show.append((last_frame, "Last (принято)"))
            if frames_to_show:
                cols = st.columns(max(len(frames_to_show), 2))
                for idx, (fpath, label_text) in enumerate(frames_to_show):
                    with cols[idx]:
                        _show_image_with_lightbox(fpath, caption=label_text, width="250px")

        # Show review items (variants awaiting selection)
        review_items = item.get("review_items", [])
        for comp, all_attempts in review_items:
            comp_label = {"nb_first": "Первый кадр", "nb_last": "Последний кадр", "veo": "Видео"}.get(comp, comp)
            latest_attempt_num, variants = all_attempts[-1]

            # Store for submit processing
            review_items_map.setdefault(cid, []).append((comp, latest_attempt_num, variants))

            st.markdown(f"**{comp_label}** — попытка {latest_attempt_num} ({len(variants)} вариантов)")

            # Show variants with checkbox under each
            is_video = comp == "veo"
            for row_start in range(0, len(variants), 2):
                row_items = variants[row_start:row_start+2]
                cols = st.columns(2)
                for j, vpath in enumerate(row_items):
                    vi = row_start + j
                    with cols[j]:
                        if is_video:
                            st.video(str(vpath))
                            vpath_p = Path(vpath) if not isinstance(vpath, Path) else vpath
                            if vpath_p.exists():
                                with open(vpath_p, "rb") as vf:
                                    st.download_button(
                                        f"📥 Скачать",
                                        vf.read(),
                                        file_name=vpath_p.name,
                                        mime="video/mp4",
                                        key=f"dl_{cid}_{comp}_{vi}",
                                    )
                        else:
                            _show_local_image(vpath, use_container_width=True)
                        st.checkbox(
                            f"Выбрать вариант {vi+1}",
                            key=f"chk_{cid}_{comp}_{vi}",
                        )

            # Feedback field
            st.text_area(
                "Фидбек (заполни чтобы отклонить):",
                placeholder="Оставь пустым чтобы принять выбранный вариант",
                key=f"chain_feedback_{cid}_{comp}",
                height=68,
            )

        if review_items:
            st.divider()

    # --- Process all decisions on submit ---
    if submit_all:
        accepted_count = 0
        rejected_count = 0
        errors = []

        # Process needs_last changes for ALL displayed clips
        for item in page_items:
            cid = item["clip"]["clip_id"]
            manifest = item["manifest"]
            old_skip = manifest.get("skip_last", True)
            needs_last = st.session_state.get(f"needs_last_{cid}", False)
            new_skip = not needs_last
            if new_skip != old_skip:
                manifest["skip_last"] = new_skip
                if new_skip:
                    manifest["components"]["nb_last"]["status"] = "skipped"
                else:
                    if manifest["components"]["nb_last"].get("status") == "skipped":
                        manifest["components"]["nb_last"]["status"] = "pending"
                _save_manifest(cid, manifest)

        # Process manual uploads
        for cid, (comp, uploaded_file) in upload_map.items():
            try:
                _manual_upload_frame(cid, comp, uploaded_file)
                accepted_count += 1
            except Exception as e:
                errors.append(f"{cid}/загрузка: {e}")

        # Process review decisions
        for cid, comp_items in review_items_map.items():
            manifest = all_manifests[cid]
            for comp, latest_attempt_num, variants in comp_items:
                comp_label = {"nb_first": "Первый кадр", "nb_last": "Последний кадр", "veo": "Видео"}.get(comp, comp)
                feedback = st.session_state.get(f"chain_feedback_{cid}_{comp}", "").strip()
                if feedback:
                    try:
                        manifest["components"][comp]["status"] = "rejected"
                        manifest["components"][comp]["feedback"] = feedback
                        _save_manifest(cid, manifest)
                        rejected_count += 1
                    except Exception as e:
                        errors.append(f"{cid}/{comp_label}: {e}")
                else:
                    selected_vi = None
                    for vi in range(len(variants)):
                        if st.session_state.get(f"chk_{cid}_{comp}_{vi}", False):
                            selected_vi = vi
                            break
                    if selected_vi is not None:
                        try:
                            _chain_select_variant(cid, comp, latest_attempt_num, selected_vi)
                            accepted_count += 1
                        except Exception as e:
                            errors.append(f"{cid}/{comp_label}: {e}")

        parts = []
        if accepted_count:
            parts.append(f"✅ Принято: {accepted_count}")
        if rejected_count:
            parts.append(f"❌ Отклонено: {rejected_count}")
        if errors:
            parts.append(f"⚠️ Ошибки: {len(errors)}")
        if parts:
            st.session_state["_chain_notify"] = " | ".join(parts)
        if errors:
            for err in errors:
                st.error(err)
        _clear_local_caches()
        st.rerun()

    _timers["render"] = _t.time()
    # Show timing debug
    t0 = _timers["start"]
    timing_parts = []
    prev = t0
    for label in ("load_clips", "classification", "render"):
        if label in _timers:
            dt = (_timers[label] - prev) * 1000
            timing_parts.append(f"{label}: {dt:.0f}ms")
            prev = _timers[label]
    total = (_timers.get("render", t0) - t0) * 1000
    st.caption(f"⏱ {' | '.join(timing_parts)} | **total: {total:.0f}ms**")


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
    # Count total VEO review videos (from batch cache)
    total_veo_videos = 0
    _variants_cache = _batch_scan_variants(str(REVIEW_DIR))
    for c in clips:
        cid = c["clip_id"]
        veo_attempts = _variants_cache.get(cid, {}).get("veo", [])
        for _att_num, files in veo_attempts:
            total_veo_videos += len(files)

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
                for row_start in range(0, len(imgs), 2):
                    cols = st.columns(2)
                    for j, ipath in enumerate(imgs[row_start:row_start+2]):
                        with cols[j]:
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
        # Read text — handle .docx and plain text
        if str(SCENARIO_FILE).endswith(".docx"):
            try:
                import docx
                doc = docx.Document(str(SCENARIO_FILE))
                text = "\n".join(p.text for p in doc.paragraphs)
            except Exception as e:
                st.error(f"Ошибка чтения .docx: {e}")
                return
            dl_name = SCENARIO_FILE.stem + ".txt"
        else:
            text = SCENARIO_FILE.read_text(encoding="utf-8")
            dl_name = SCENARIO_FILE.name

        # Split into scenes for better navigation
        st.download_button(
            "Скачать сценарий",
            text.encode("utf-8"),
            file_name=dl_name,
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
        st.warning(f"Файл сценария не найден ({SCENARIO_FILE.name})")


def _load_ref_manifest(ref_type: str, name: str) -> dict:
    """Load manifest for a reference (character or location) variant review."""
    cfg = _get_series_config()
    base = BASE_DIR / cfg.get("output_dir", "output")
    manifest_path = base / "ref_review" / ref_type / name / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    return {}

def _save_ref_manifest(ref_type: str, name: str, data: dict):
    cfg = _get_series_config()
    base = BASE_DIR / cfg.get("output_dir", "output")
    manifest_path = base / "ref_review" / ref_type / name / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _render_location_generation_tab(locations_spec: list, cfg: dict):
    """Render the location generation/review tab content."""
    st.subheader("Референсы локаций")

    base = BASE_DIR / cfg.get("output_dir", "output")
    review_locs_dir = base / "review" / "locations"
    manifest = _load_locations_manifest()
    prompts_dir = (BASE_DIR / cfg["prompts_file"]).parent
    spec_path = prompts_dir / "locations_spec.json"

    # Classify locations
    ready_locs = []
    needs_review_locs = []
    missing_locs = []

    for loc in locations_spec:
        loc_id = loc["location_id"]
        file_path = Path(loc["file_path"])
        if not file_path.is_absolute():
            file_path = BASE_DIR / file_path

        if file_path.exists():
            ready_locs.append((loc, file_path))
        else:
            # Check if variants exist in review
            loc_review_dir = review_locs_dir / loc_id
            variants = sorted(loc_review_dir.glob("variant_*.png")) if loc_review_dir.exists() else []
            loc_manifest = manifest.get(loc_id, {})
            if variants and loc_manifest.get("status") != "rejected":
                needs_review_locs.append((loc, variants, loc_manifest))
            else:
                missing_locs.append(loc)

    total = len(locations_spec)
    ready_count = len(ready_locs)
    review_count = len(needs_review_locs)
    missing_count = len(missing_locs)

    # Progress bar
    progress = ready_count / total if total else 0
    st.progress(progress, text=f"{ready_count} из {total} локаций готовы")

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Готово", ready_count)
    with col2:
        st.metric("На ревью", review_count)
    with col3:
        st.metric("Не сгенерировано", missing_count)
    with col4:
        st.metric("Всего", total)

    # Generate command
    if missing_count > 0:
        st.markdown("---")
        st.warning(
            f"Не все локации сгенерированы ({missing_count} осталось). "
            f"Запустите бота для генерации недостающих."
        )
        output_dir = cfg.get("output_dir", "output")
        cmd = (
            f"./scripts/run_safe.sh --generate-locations --account 1 --chromium "
            f"--prompts {spec_path.relative_to(BASE_DIR)} --output-dir {output_dir}"
        )
        st.code(cmd, language="bash")

    st.markdown("---")

    # --- Locations needing review ---
    if needs_review_locs:
        st.markdown("### На ревью")
        submit_loc = st.button(
            "Отправить решения по локациям",
            type="primary",
            key="btn_submit_locs",
            use_container_width=True,
        )

        for loc, variants, loc_manifest in needs_review_locs:
            loc_id = loc["location_id"]
            desc = loc.get("description_ru", loc_id)

            st.markdown(f"**{loc_id}** -- {desc}")

            # Show variants in a row
            num_variants = len(variants)
            cols = st.columns(min(num_variants, 4))
            for vi, vpath in enumerate(variants):
                with cols[vi % 4]:
                    _show_local_image(vpath, use_container_width=True)
                    st.checkbox(
                        f"Выбрать {vi+1}",
                        key=f"loc_chk_{loc_id}_{vi}",
                    )

            # Feedback field for rejection
            st.text_area(
                "Фидбек (заполни чтобы отк��онить):",
                placeholder="Оставь пустым чтобы принять выбранный вариант",
                key=f"loc_feedback_{loc_id}",
                height=68,
            )
            st.divider()

        # Process decisions on submit
        if submit_loc:
            accepted_count = 0
            rejected_count = 0

            for loc, variants, loc_manifest_data in needs_review_locs:
                loc_id = loc["location_id"]
                feedback = st.session_state.get(f"loc_feedback_{loc_id}", "").strip()

                if feedback:
                    # Reject
                    if loc_id not in manifest:
                        manifest[loc_id] = {"status": "rejected", "attempts": []}
                    manifest[loc_id]["status"] = "rejected"
                    manifest[loc_id]["feedback"] = feedback
                    rejected_count += 1
                else:
                    # Find selected variant
                    selected_vi = None
                    for vi in range(len(variants)):
                        if st.session_state.get(f"loc_chk_{loc_id}_{vi}", False):
                            selected_vi = vi
                            break

                    if selected_vi is not None:
                        # Accept: copy variant to target file_path
                        src = variants[selected_vi]
                        file_path = Path(loc["file_path"])
                        if not file_path.is_absolute():
                            file_path = BASE_DIR / file_path
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, file_path)

                        # Update manifest
                        if loc_id not in manifest:
                            manifest[loc_id] = {"status": "accepted", "attempts": []}
                        manifest[loc_id]["status"] = "accepted"
                        manifest[loc_id]["selected_variant"] = selected_vi
                        accepted_count += 1

            _save_locations_manifest(manifest)

            parts = []
            if accepted_count:
                parts.append(f"Принято: {accepted_count}")
            if rejected_count:
                parts.append(f"Отклонено: {rejected_count}")
            if parts:
                st.success(" | ".join(parts))
            st.rerun()

    # --- Ready locations grid ---
    if ready_locs:
        st.markdown("### Готовые локации")
        for row_start in range(0, len(ready_locs), 4):
            row = ready_locs[row_start:row_start + 4]
            cols = st.columns(4)
            for i, (loc, fpath) in enumerate(row):
                with cols[i]:
                    desc = loc.get("description_ru", loc["location_id"])
                    _show_local_image(
                        fpath,
                        caption=f"{loc['location_id']}\n{desc}",
                        use_container_width=True,
                    )

    # --- Missing locations list ---
    if missing_locs:
        st.markdown("### Не сгенерированы")
        for row_start in range(0, len(missing_locs), 4):
            row = missing_locs[row_start:row_start + 4]
            cols = st.columns(4)
            for i, loc in enumerate(row):
                with cols[i]:
                    desc = loc.get("description_ru", loc["location_id"])
                    st.markdown(
                        f'<div style="background:#1A1D26;border:2px dashed #B71C1C;'
                        f'border-radius:8px;padding:30px 10px;text-align:center;'
                        f'min-height:120px;display:flex;flex-direction:column;'
                        f'justify-content:center;align-items:center;">'
                        f'<span style="color:#EF5350;font-weight:600;font-size:0.85em;">'
                        f'Не сгенерирована</span><br>'
                        f'<span style="color:#888;font-size:0.75em;">{loc["location_id"]}</span><br>'
                        f'<span style="color:#666;font-size:0.7em;">{desc}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )


def _load_locations_spec() -> list | None:
    """Load locations_spec.json for the current series (if it exists)."""
    cfg = _get_series_config()
    prompts_dir = (BASE_DIR / cfg["prompts_file"]).parent
    spec_path = prompts_dir / "locations_spec.json"
    if spec_path.exists():
        try:
            with open(spec_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _load_locations_manifest() -> dict:
    """Load locations_manifest.json for the current series."""
    cfg = _get_series_config()
    base = BASE_DIR / cfg.get("output_dir", "output")
    manifest_path = base / "review" / "locations" / "locations_manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_locations_manifest(manifest: dict):
    """Save locations_manifest.json for the current series."""
    cfg = _get_series_config()
    base = BASE_DIR / cfg.get("output_dir", "output")
    manifest_path = base / "review" / "locations" / "locations_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def _locations_ready_count(spec: list) -> tuple[int, int]:
    """Return (ready_count, total_count) for locations in spec."""
    total = len(spec)
    ready = 0
    for loc in spec:
        file_path = Path(loc["file_path"])
        if not file_path.is_absolute():
            file_path = BASE_DIR / file_path
        if file_path.exists():
            ready += 1
    return ready, total


def page_references():
    """Reference gallery — characters and locations with variant review."""
    st.header("Референсы")

    cfg = _get_series_config()
    base = BASE_DIR / cfg.get("output_dir", "output")
    ref_review_dir = base / "ref_review"

    # Determine tabs based on whether locations_spec.json exists
    locations_spec = _load_locations_spec()
    if locations_spec:
        tab_chars, tab_locs, tab_loc_gen, tab_review = st.tabs(
            ["Персонажи", "Локации", "Генерация локаций", "Ревью вариантов"]
        )
    else:
        tab_chars, tab_locs, tab_review = st.tabs(["Персонажи", "Локации", "Ревью вариантов"])

    # --- Accepted references ---
    with tab_chars:
        st.subheader("Персонажи")
        if CHARS_DIR.exists():
            files = sorted(CHARS_DIR.glob("char_*"))
            if files:
                groups: dict[str, list[Path]] = {}
                for f in files:
                    parts = f.stem.split("_")
                    if len(parts) >= 2:
                        char_key = parts[1]
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
                groups: dict[str, list[Path]] = {}
                for f in files:
                    group_name = _loc_group(f.stem)
                    groups.setdefault(group_name, []).append(f)
                for group_name in sorted(groups):
                    st.markdown(f"#### {group_name}")
                    loc_files = groups[group_name]
                    cols = st.columns(min(len(loc_files), 4))
                    for i, fpath in enumerate(loc_files):
                        with cols[i % len(cols)]:
                            st.image(str(fpath), caption=fpath.name, use_container_width=True)
            else:
                st.info("Нет файлов локаций.")
        else:
            st.warning("Папка локаций не найдена.")

    # --- Location generation tab (only if locations_spec.json exists) ---
    if locations_spec:
        with tab_loc_gen:
            _render_location_generation_tab(locations_spec, cfg)

    # --- Variant review tab ---
    with tab_review:
        st.subheader("Ревью вариантов")

        if not ref_review_dir.exists():
            st.info("Нет вариантов для ревью. Боты ещё не генерировали референсы.")
            return

        # Collect all pending reviews
        for ref_type_label, ref_type_key in [("Персонажи", "chars"), ("Локации", "locs")]:
            type_dir = ref_review_dir / ref_type_key
            if not type_dir.exists():
                continue

            items = sorted(type_dir.iterdir())
            if not items:
                continue

            st.markdown(f"### {ref_type_label}")

            for item_dir in items:
                if not item_dir.is_dir():
                    continue
                name = item_dir.name
                manifest = _load_ref_manifest(ref_type_key, name)
                status = manifest.get("status", "pending")

                # Display name (Russian for locations, character names for chars)
                if ref_type_key == "locs":
                    display = _loc_group(name)
                else:
                    display = CHAR_DISPLAY.get(name.capitalize(), name.replace("_", " ").title())
                status_badge = {"accepted": "✅", "rejected": "❌", "pending": "⏳"}.get(status, "⏳")
                st.markdown(f"#### {status_badge} {display}")

                if manifest.get("prompt_a"):
                    st.caption(f"Промпт A: {manifest['prompt_a'][:120]}...")
                if manifest.get("prompt_b"):
                    st.caption(f"Промпт B: {manifest['prompt_b'][:120]}...")

                # Find variant images
                variants_a = sorted(item_dir.glob("prompt_a/variant_*.png"))
                variants_b = sorted(item_dir.glob("prompt_b/variant_*.png"))

                if not variants_a and not variants_b:
                    # Try flat structure
                    variants_a = sorted(item_dir.glob("variant_*.png"))

                if not variants_a and not variants_b:
                    st.warning("Нет вариантов")
                    continue

                # Build combined variant list
                all_variants = [(f"A-{i+1}", vpath) for i, vpath in enumerate(variants_a)] + \
                               [(f"B-{i+1}", vpath) for i, vpath in enumerate(variants_b)]

                # Show prompt A variants with accept buttons under each
                if variants_a:
                    st.markdown("**Промпт A:**")
                    cols = st.columns(min(len(variants_a), 4))
                    for i, vpath in enumerate(variants_a):
                        with cols[i % len(cols)]:
                            st.image(str(vpath), caption=f"A-{i+1}", use_container_width=True)
                            if status == "pending":
                                if st.button(f"Принять A-{i+1}", key=f"ref_acc_{ref_type_key}_{name}_a{i}"):
                                    import shutil
                                    target_dir = CHARS_DIR if ref_type_key == "chars" else LOCS_DIR
                                    target_dir.mkdir(parents=True, exist_ok=True)
                                    target_name = f"{name}_full.png" if ref_type_key == "chars" else f"{name}.png"
                                    target_path = target_dir / target_name
                                    shutil.copy2(vpath, target_path)
                                    manifest["status"] = "accepted"
                                    manifest["selected_variant"] = f"A-{i+1}"
                                    _save_ref_manifest(ref_type_key, name, manifest)
                                    st.rerun()

                # Show prompt B variants with accept buttons under each
                if variants_b:
                    st.markdown("**Промпт B:**")
                    cols = st.columns(min(len(variants_b), 4))
                    for i, vpath in enumerate(variants_b):
                        with cols[i % len(cols)]:
                            st.image(str(vpath), caption=f"B-{i+1}", use_container_width=True)
                            if status == "pending":
                                if st.button(f"Принять B-{i+1}", key=f"ref_acc_{ref_type_key}_{name}_b{i}"):
                                    import shutil
                                    target_dir = CHARS_DIR if ref_type_key == "chars" else LOCS_DIR
                                    target_dir.mkdir(parents=True, exist_ok=True)
                                    target_name = f"{name}_full.png" if ref_type_key == "chars" else f"{name}.png"
                                    target_path = target_dir / target_name
                                    shutil.copy2(vpath, target_path)
                                    manifest["status"] = "accepted"
                                    manifest["selected_variant"] = f"B-{i+1}"
                                    _save_ref_manifest(ref_type_key, name, manifest)
                                    st.rerun()

                # Reject button + feedback (only for pending)
                if status == "pending":
                    reject_key = f"ref_rejecting_{ref_type_key}_{name}"
                    if st.button("Отклонить все", key=f"ref_rej_btn_{ref_type_key}_{name}"):
                        st.session_state[reject_key] = True
                    if st.session_state.get(reject_key, False):
                        with st.form(f"ref_reject_form_{ref_type_key}_{name}"):
                            feedback = st.text_area("Фидбек (для перегенерации)", key=f"ref_fb_{ref_type_key}_{name}", height=80)
                            if st.form_submit_button("Отправить"):
                                manifest["status"] = "rejected"
                                manifest["feedback"] = feedback
                                _save_ref_manifest(ref_type_key, name, manifest)
                                st.session_state.pop(reject_key, None)
                                st.rerun()
                elif status == "accepted":
                    st.success(f"Принят: {manifest.get('selected_variant', '?')}")
                elif status == "rejected":
                    fb = manifest.get("feedback", "")
                    st.error(f"Отклонён. Фидбек: {fb}")
                    if st.button(f"Сбросить статус", key=f"ref_reset_{ref_type_key}_{name}"):
                        manifest["status"] = "pending"
                        _save_ref_manifest(ref_type_key, name, manifest)
                        st.rerun()

                st.markdown("---")


def page_keyframe_pairs():
    """Overview of all clips with first+last keyframe pairs for quick review."""
    st.header("Пары кадров")

    clips = load_clips()

    # Stats (use batch cache)
    total = len(clips)
    pairs_done = sum(
        1 for c in clips
        if (FRAMES_DIR / f"{c['clip_id']}_first.png").exists()
        and (FRAMES_DIR / f"{c['clip_id']}_last.png").exists()
    )
    _vc = _batch_scan_variants(str(REVIEW_DIR))
    veo_done = sum(1 for c in clips if _vc.get(c["clip_id"], {}).get("veo"))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Пары кадров", f"{pairs_done}/{total}")
    with col2:
        st.metric("VEO видео", f"{veo_done}/{total}")
    with col3:
        st.progress(pairs_done / total if total else 0)

    st.markdown("---")

    # --- Pagination ---
    KP_PER_PAGE = 20
    total_clips = len(clips)
    total_kp_pages = max(1, (total_clips + KP_PER_PAGE - 1) // KP_PER_PAGE)
    if total_clips > KP_PER_PAGE:
        kp_col1, kp_col2 = st.columns([3, 1])
        with kp_col1:
            kp_page = st.number_input(
                f"Страница (всего {total_kp_pages}, по {KP_PER_PAGE} клипов)",
                min_value=1, max_value=total_kp_pages, value=1,
                key="kp_page",
            )
        with kp_col2:
            st.markdown(f"**{total_clips}** клипов")
        kp_start = (kp_page - 1) * KP_PER_PAGE
        page_clips_list = clips[kp_start:kp_start + KP_PER_PAGE]
    else:
        page_clips_list = clips

    # Group by scene
    current_scene = None
    for clip in page_clips_list:
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
        veo_attempts = _vc.get(clip_id, {}).get("veo", [])
        veo_count = sum(len(files) for _, files in veo_attempts)
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


def _find_accepted_veo_video(clip_id):
    """Find the accepted VEO video for a clip. Returns path or None."""
    manifest = _load_manifest(clip_id)
    veo_comp = manifest["components"].get("veo", {})
    if veo_comp.get("status") != "accepted":
        return None
    sel = veo_comp.get("selected_variant_a")
    if not sel:
        return None
    attempt = sel["attempt"]
    variant_idx = sel["variant"]
    attempt_dir = REVIEW_DIR / clip_id / "veo" / f"attempt_{attempt}"
    if not attempt_dir.exists():
        return None
    # Find variant file
    attempts_data = veo_comp.get("attempts", [])
    if attempt <= len(attempts_data):
        entry = attempts_data[attempt - 1]
        variants = entry.get("variants", [])
        if variant_idx < len(variants):
            vfile = variants[variant_idx].get("file", "")
            vpath = attempt_dir / vfile
            if vpath.exists():
                return vpath
    # Fallback: find by index in sorted mp4s
    mp4s = sorted(attempt_dir.rglob("*.mp4"))
    if variant_idx < len(mp4s):
        return mp4s[variant_idx]
    return None


def page_timeline():
    """Visual timeline — only accepted VEO videos."""
    st.header("Таймлайн")

    clips = load_clips()

    # Collect clips that have accepted VEO videos
    video_clips = []
    for clip in clips:
        clip_id = clip["clip_id"]
        video_path = _find_accepted_veo_video(clip_id)
        if video_path:
            video_clips.append((clip, video_path))

    if not video_clips:
        st.info("Пока нет принятых VEO-видео. Выберите видео в Chain Ревью, и они появятся здесь.")
        return

    # --- Pagination ---
    TL_PER_PAGE = 30
    total_pages = max(1, (len(video_clips) + TL_PER_PAGE - 1) // TL_PER_PAGE)

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Таймлайн:** {len(video_clips)} видео, {total_pages} стр.")

    # Page selector — selectbox for direct page jump
    page_options = [f"Страница {i}" for i in range(1, total_pages + 1)]
    selected = st.sidebar.selectbox(
        "Перейти на страницу",
        options=page_options,
        index=0,
        key="tl_page_select",
    )
    page_num = page_options.index(selected) + 1

    start_idx = (page_num - 1) * TL_PER_PAGE
    page_video_clips = video_clips[start_idx:start_idx + TL_PER_PAGE]

    st.caption(f"Страница {page_num} из {total_pages} (клипы {start_idx + 1}–{start_idx + len(page_video_clips)} из {len(video_clips)})")

    # --- Render ---
    current_scene = None
    for clip, video_path in page_video_clips:
        if clip["scene_id"] != current_scene:
            current_scene = clip["scene_id"]
            color = SCENE_COLORS.get(current_scene, "#888")
            label = SCENE_LABELS.get(current_scene, current_scene)
            st.markdown(
                f'<h4 style="color:{color};margin-top:20px;">{label}</h4>',
                unsafe_allow_html=True,
            )

        clip_id = clip["clip_id"]
        desc = clip.get("scene_description_ru", "")[:120]
        st.markdown(f"**{clip_id}** — {desc}")
        st.video(str(video_path))
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
    inject_lightbox()

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
        _clear_local_caches()
        st.rerun()

    # Apply series config to globals
    _apply_series()
    cfg = _get_series_config()

    # --- Check if series is configured ---
    prompts_available = PROMPTS_FILE.exists()
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
