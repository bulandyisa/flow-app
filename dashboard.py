"""
СИГНАЛ — Production Dashboard
Streamlit-дашборд для анимационного проекта
"""

import json
import os
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
PROMPTS_FILE = BASE_DIR / "output" / "prompts" / "all_prompts.json"
FRAMES_DIR = BASE_DIR / "output" / "frames"
CLIPS_DIR = BASE_DIR / "output" / "clips"
REVIEW_DIR = BASE_DIR / "output" / "review"
SCENE_DIR = BASE_DIR / "output" / "scene"
CHARS_DIR = BASE_DIR / "персонажи"
LOCS_DIR = BASE_DIR / "локации"
SCENARIO_FILE = BASE_DIR / "scenario_signal.txt"
STATUS_FILE = BASE_DIR / "output" / "status.json"

SCENE_COLORS = {
    "S01": "#E8B849",  # gold
    "S02": "#49B6E8",  # blue
    "S03": "#E85A49",  # red
    "S04": "#6BE849",  # green
    "S05": "#C149E8",  # purple
}

SCENE_LABELS = {
    "S01": "Сцена 1 — Холодное открытие",
    "S02": "Сцена 2 — Гараж, 4 дня назад",
    "S03": "Сцена 3 — Дом Амина, вечер",
    "S04": "Сцена 4 — Гараж, 3 дня назад",
    "S05": "Сцена 5 — Гараж, вечер",
}

CHAR_DISPLAY = {
    "Amin": "Амин",
    "Karim": "Карим",
    "Tako": "Тако",
    "Papa": "Папа",
    "Mama": "Мама",
    "Aya": "Ая",
    "Hasan": "Хасан",
    "Rami": "Рами",
    "Samir": "Самир",
    "Shaki": "Шаки",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def load_clips() -> list[dict]:
    """Load clip data from all_prompts.json."""
    with open(PROMPTS_FILE, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=60)
def load_status() -> dict:
    """Load clip statuses from status.json (for Streamlit Cloud compatibility)."""
    if STATUS_FILE.exists():
        with open(STATUS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_status(clip_id: str) -> str:
    """Determine clip status from status.json, with local file fallback."""
    status_data = load_status()
    clip_status = status_data.get("clips", {}).get(clip_id)
    if clip_status:
        return clip_status["status"]

    # Fallback: check local files (works only when running locally)
    has_first = (FRAMES_DIR / f"{clip_id}_first.png").exists() or (FRAMES_DIR / clip_id / "first.png").exists()
    has_last = (FRAMES_DIR / f"{clip_id}_last.png").exists() or (FRAMES_DIR / clip_id / "last.png").exists()
    has_clip = (CLIPS_DIR / f"{clip_id}_clip.mp4").exists()
    has_veo_review = (REVIEW_DIR / clip_id / "veo").exists() and any((REVIEW_DIR / clip_id / "veo").glob("attempt_*/*.mp4")) if (REVIEW_DIR / clip_id / "veo").exists() else False
    if not has_veo_review and (REVIEW_DIR / clip_id / "veo").exists():
        has_veo_review = any((REVIEW_DIR / clip_id / "veo").glob("attempt_*/*/*.mp4"))

    if has_first and has_last and has_clip:
        return "done"
    elif has_first or has_last or has_clip or has_veo_review:
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

    # --- Row 5: Video (accepted + VEO variants) ---
    st.markdown("**Видео**")
    clip_video = CLIPS_DIR / f"{clip_id}_clip.mp4"
    if clip_video.exists():
        st.video(str(clip_video))
        download_button_for_file(clip_video, "Скачать видео", f"dl_video_{clip_id}")

    # VEO review variants (always show if available)
    render_veo_variants(clip_id)

    # If no accepted video and no VEO variants, show placeholder
    if not clip_video.exists():
        veo_review_dir = REVIEW_DIR / clip_id / "veo"
        has_veo_variants = False
        if veo_review_dir.exists():
            for ad in veo_review_dir.glob("attempt_*"):
                if list(ad.glob("*.mp4")) or list(ad.glob("*/*.mp4")):
                    has_veo_variants = True
                    break
        if not has_veo_variants:
            veo_st = comp_status.get("veo", "pending")
            if veo_st == "accepted":
                st.markdown(
                    '<div style="background:#1B3A1B;border:1px solid #2E7D32;border-radius:8px;'
                    'padding:40px;text-align:center;color:#A5D6A7;">'
                    '✅ Видео — принято (файл доступен локально)</div>',
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


def page_timeline():
    """Visual timeline of all clips."""
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
        dur = clip.get("veo_duration", 0)
        chars = ", ".join(CHAR_DISPLAY.get(c, c) for c in clip["characters"])

        # Timeline row
        cols = st.columns([1, 3, 1, 1])
        with cols[0]:
            st.markdown(f"**{status_icon} {clip_id}**")
        with cols[1]:
            st.markdown(clip["scene_description_ru"])
        with cols[2]:
            st.markdown(f"{chars}")
        with cols[3]:
            st.markdown(f"{dur}с")

        # Show frames inline if they exist
        first_frame = FRAMES_DIR / f"{clip_id}_first.png"
        if not first_frame.exists():
            first_frame = FRAMES_DIR / clip_id / "first.png"
        last_frame = FRAMES_DIR / f"{clip_id}_last.png"
        if not last_frame.exists():
            last_frame = FRAMES_DIR / clip_id / "last.png"
        if first_frame.exists() or last_frame.exists():
            thumb_cols = st.columns([1, 2, 2, 1])
            with thumb_cols[1]:
                if first_frame.exists():
                    st.image(str(first_frame), width=200, caption="First")
            with thumb_cols[2]:
                if last_frame.exists():
                    st.image(str(last_frame), width=200, caption="Last")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title="СИГНАЛ — Dashboard",
        page_icon="📡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_css()

    # --- Sidebar header ---
    st.sidebar.markdown(
        '<h1 style="text-align:center;color:#E8B849;">📡 СИГНАЛ</h1>'
        '<p style="text-align:center;color:#888;font-size:0.85em;">'
        'Production Dashboard</p>',
        unsafe_allow_html=True,
    )

    # --- Navigation ---
    page = st.sidebar.radio(
        "Навигация",
        ["Клипы", "Таймлайн", "Сценарий", "Референсы"],
        label_visibility="collapsed",
    )

    # --- Page routing ---
    if page == "Клипы":
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
        'СИГНАЛ / Signal<br>3D Pixar-style Animation<br>'
        'Nano Banana Pro + VEO 3.1</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
