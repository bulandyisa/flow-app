#!/usr/bin/env python3
"""
Модуль 2: Генератор промптов — двухэтапный пайплайн

Для каждого клипа генерируются ТРИ промпта:
1. Nano Banana Pro — первый кадр (начальная позиция/действие)
2. Nano Banana Pro — последний кадр (конечная позиция/действие)
3. VEO 3.1 (Frames to Video, First + Last Frame) — анимация между кадрами
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ─── Constants ───────────────────────────────────────────────────────────────

NB_STYLE = "3D Pixar-style animation, soft volumetric lighting, cinematic."
VEO_STYLE = "Smooth cinematic motion, 3D Pixar-style animation."

MINOR_CHARACTERS = {"Amin", "Aya", "Tako", "Karim"}

# Short descriptors for Nano Banana prompts (appearance-focused)
CHAR_SHORT = {
    "Amin": "a tall 15-year-old boy with dark wavy shoulder-length hair, brown eyes, gray hoodie, black pants, white sneakers",
    "Karim": "a 15-year-old boy with short brown hair, brown eyes, black hoodie with a white star on the chest, jeans, white sneakers",
    "Tako": "a chubby 7-year-old boy with curly brown hair, burgundy backwards cap, red-white striped t-shirt, jeans, big brown eyes",
    "Mama": "a woman in a black hijab and long black abaya, brown eyes, warm smile",
    "Papa": "a tall man with dark graying hair, thick graying beard, round glasses, black turtleneck, blue pants",
    "Aya": "a 12-year-old girl in a pink long dress with a dark blue striped hijab, brown eyes",
}

# Ingredient role labels for Nano Banana
CHAR_ROLE = {
    "Amin": "Use this image for the tall teen boy's appearance",
    "Karim": "Use this image for the boy in the black hoodie's appearance",
    "Tako": "Use this image for the little boy's appearance",
    "Mama": "Use this image for the mother's appearance",
    "Papa": "Use this image for the father's appearance",
    "Aya": "Use this image for the girl's appearance",
}

LOC_ROLE = {
    "Garage": "Use this image for the garage environment and layout",
}

TIME_LIGHTING = {
    "night": "Dim single-lamp lighting, deep shadows",
    "evening": "Warm golden evening light, long soft shadows",
    "day": "Bright natural daylight from the open garage door",
    "morning": "Soft morning light, gentle shadows",
}

LOCATION_ENV = {
    "Garage": "spacious garage with sectional door, workbench with tools, pegboard with wrenches, bicycles against the wall, shelving with containers",
}


# ─── Clip templates: Nano Banana (frame) + VEO (motion) ─────────────────────

SCENE_CLIP_TEMPLATES = {
    "S01": [
        {
            "chars": ["Karim"],
            "nano_banana_first": (
                "Extreme close-up of a homemade radio receiver on a wooden workbench. "
                "Wires, exposed circuit boards, a small blinking green indicator light. "
                "A hand reaches for the tuning dial. The garage around is almost invisible in darkness, "
                "lit only by the faint glow of the indicator. "
                "{lighting}. {style}"
            ),
            "nano_banana_last": (
                "Extreme close-up of a homemade radio receiver on a wooden workbench. "
                "A hand grips the tuning dial, mid-turn. The green indicator light glows brighter. "
                "Sound waves seem to ripple through the air. The garage around is almost invisible in darkness. "
                "{lighting}. {style}"
            ),
            "veo": (
                "The hand slowly turns the tuning dial. Static and crackling fill the air. "
                "The indicator light pulses. Fragments of distant voices break through the noise, "
                "then a monotone mechanical voice reading numbers emerges from the static. "
                "Camera holds steady on the receiver. {veo_style}"
            ),
            "description_ru": "Крупный план приёмника на верстаке. Рука крутит ручку настройки. Шум, треск, голос с цифрами.",
        },
        {
            "chars": ["Karim"],
            "nano_banana_first": (
                "Wide shot of a dim garage interior at night. "
                "Using the character reference: {Karim} sits at a workbench facing a homemade radio receiver, "
                "eyes wide open with shock, mouth slightly parted. "
                "The only light source is a single desk lamp casting harsh shadows. "
                "Tools and wires scattered on the bench. Deep darkness beyond the lamp's reach. "
                "{lighting}. {style}"
            ),
            "nano_banana_last": (
                "Wide shot of a dim garage interior at night. "
                "Using the character reference: {Karim} has turned away from the workbench toward the camera, "
                "his expression frozen in disbelief, lips parted as if whispering. "
                "The desk lamp flickers behind him. The radio receiver glows faintly on the bench. "
                "Deep darkness fills the garage. "
                "{lighting}. {style}"
            ),
            "veo": (
                "Camera slowly pulls back to reveal more of the dark garage. "
                "The boy slowly turns toward the camera, his expression frozen in disbelief. "
                "He whispers something barely audible. The lamp flickers once. Fade to black. {veo_style}"
            ),
            "description_ru": "Камера отъезжает. Карим сидит перед приёмником, глаза широко раскрыты. Поворачивается к камере, шепчет.",
        },
    ],
    "S02": [
        {
            "chars": ["Amin", "Karim"],
            "nano_banana_first": (
                "Establishing wide shot inside a sunlit garage. "
                "Using the character references: {Amin} lies on an old worn sofa in the corner, "
                "legs draped over the armrest, staring at the ceiling with a blank, listless expression. "
                "{Karim} stands in the open garage doorway with his backpack, just arriving. "
                "{lighting}. "
                "Background: {location}. {style}"
            ),
            "nano_banana_last": (
                "Establishing wide shot inside a sunlit garage. "
                "Using the character references: {Amin} lies on an old worn sofa in the corner, "
                "legs draped over the armrest, staring at the ceiling with a blank, listless expression. "
                "{Karim} stands by the workbench, backpack on the floor, looking at dust on his fingertip "
                "after running it across a disassembled circuit board. A thin layer of dust covers the tools. "
                "{lighting}. "
                "Background: {location}. {style}"
            ),
            "veo": (
                "The boy in the black hoodie walks in from outside, sets down his backpack, and approaches the dusty workbench. "
                "He runs his finger across the circuit board and looks at the dust on his fingertip. "
                "The boy on the sofa doesn't move, still staring at the ceiling. "
                "Dust particles float in the sunlight from the garage door. {veo_style}"
            ),
            "description_ru": "Амин лежит на диване, смотрит в потолок. Карим заходит, видит пыль на верстаке.",
        },
        {
            "chars": ["Tako"],
            "nano_banana_first": (
                "Medium shot inside a sunlit garage. "
                "Using the character reference: {Tako} stands in the doorway, grinning widely, "
                "holding an enormous homemade antenna — a wild contraption of wooden sticks, wire, and duct tape "
                "that's almost bigger than him. The antenna catches on the door frame. "
                "The garage interior is visible behind him: workbench, tools, bicycles. "
                "{lighting}. {style}"
            ),
            "nano_banana_last": (
                "Medium shot inside a sunlit garage. "
                "Using the character reference: {Tako} stands inside the garage, rubbing his forehead with one hand. "
                "The enormous homemade antenna sits on the workbench, slightly tilted, propped against a book. "
                "A proud but slightly pained grin on his face. "
                "The garage interior: workbench, tools, bicycles. "
                "{lighting}. {style}"
            ),
            "veo": (
                "The little boy tries to squeeze through the doorway with the huge antenna. "
                "It catches on the frame — he yanks it — the wire snaps back and hits him on the forehead. "
                "He rubs his head, then proudly places the antenna on the workbench. "
                "It wobbles and slowly tips over. He catches it and props it up with a book. {veo_style}"
            ),
            "description_ru": "Тако влетает с огромной самодельной антенной. Она застревает в двери, бьёт его по лбу.",
        },
        {
            "chars": ["Amin", "Tako", "Karim"],
            "nano_banana_first": (
                "Medium shot in the garage, daytime. Three boys visible. "
                "Using the character references: {Amin} lies on the sofa staring at the ceiling. "
                "{Tako} stands in the middle of the garage beaming, antenna proudly on the workbench. "
                "{Karim} stands by the workbench watching. "
                "Background: {location}. {lighting}. {style}"
            ),
            "nano_banana_last": (
                "Medium shot in the garage, daytime. Three boys visible. "
                "Using the character references: {Amin} lies on the sofa turned on his side facing the wall, "
                "back to the others. {Tako} sits alone in the corner of the garage, "
                "antenna leaning against the wall beside him, looking deflated and small. "
                "{Karim} stands by the workbench with a slight shrug, helpless expression. "
                "The mood is heavy despite the bright daylight. "
                "Background: {location}. {lighting}. {style}"
            ),
            "veo": (
                "The boy on the sofa turns on his side to face the wall without saying a word. "
                "The little boy with the antenna looks at the boy by the workbench, who just shrugs. "
                "The little boy quietly picks up his antenna and retreats to the corner, subdued. "
                "The energy drains from the room. Contemplative silence. {veo_style}"
            ),
            "description_ru": "Амин отворачивается к стене. Тако смотрит на Карима, тот пожимает плечами. Тако тихо уходит в угол.",
        },
    ],
    "S04": [
        {
            "chars": ["Karim"],
            "nano_banana_first": (
                "Medium shot inside a garage in warm evening light. "
                "Using the character reference: {Karim} sits alone at the workbench, hunched over a circuit board, "
                "soldering iron in hand, concentrating intently. Components and wires neatly arranged around him. "
                "A partially assembled radio receiver in front of him. "
                "{lighting} falls across the workbench. "
                "Background: {location}. {style}"
            ),
            "nano_banana_last": (
                "Medium shot inside a garage in warm evening light. "
                "Using the character reference: {Karim} sits alone at the workbench, "
                "one hand on the tuning dial of the completed radio receiver. "
                "A small green indicator light glows on the receiver. "
                "The soldering iron is put aside. His expression is focused anticipation. "
                "{lighting} falls across the workbench. "
                "Background: {location}. {style}"
            ),
            "veo": (
                "The boy carefully solders the last connections on the circuit board. "
                "He puts down the iron, connects a power cable. The indicator light blinks to life. "
                "He reaches for the tuning dial and slowly turns it — static, crackling, "
                "fragments of music drift through. His expression shifts to focused anticipation. {veo_style}"
            ),
            "description_ru": "Карим один, паяет. Доделывает приёмник. Подключает, крутит ручку настройки.",
        },
        {
            "chars": ["Karim"],
            "nano_banana_first": (
                "Close-up of {Karim} sitting at the workbench, face lit by warm evening light from one side. "
                "His eyes are wide with surprise, mouth slightly open. "
                "One hand on the tuning dial of the radio receiver, the other reaching for a pen. "
                "A notepad and the glowing receiver in front of him. "
                "Dramatic contrast between the warm light and the dark garage behind. {style}"
            ),
            "nano_banana_last": (
                "Close-up of {Karim} sitting at the workbench, face lit by warm evening light from one side. "
                "He stares down at the notepad, which now has rows of numbers written on it. "
                "His expression is stunned, processing what he just heard. "
                "The receiver is silent, indicator light steady. Pen still in hand. "
                "Dramatic contrast between the warm light and the dark garage behind. {style}"
            ),
            "veo": (
                "Through the static — a rhythmic signal emerges, then a monotone voice reading numbers. "
                "The boy's eyes widen. He grabs a pen and writes numbers on the notepad, "
                "listening carefully. The signal repeats — he checks his notes. "
                "Then the signal stops abruptly. Silence. He stares at the paper. {veo_style}"
            ),
            "description_ru": "Загадочный сигнал с цифрами. Карим записывает. Сигнал прекращается.",
        },
        {
            "chars": ["Karim"],
            "nano_banana_first": (
                "Medium shot of {Karim} standing up from the workbench, clutching a piece of paper. "
                "His expression is urgent, excited. The garage door is open, "
                "golden evening light and a suburban driveway visible outside. "
                "The radio receiver glows on the workbench behind him. "
                "{lighting} outside, long shadows on the driveway. {style}"
            ),
            "nano_banana_last": (
                "Medium shot from inside the garage looking outward. "
                "{Karim} is mid-stride running out through the open garage door into the golden evening light, "
                "piece of paper clutched in his hand, seen from behind. "
                "The suburban driveway stretches ahead. The empty workbench and radio receiver visible behind. "
                "{lighting} outside, long shadows on the driveway. {style}"
            ),
            "veo": (
                "The boy stands up abruptly, grabs the paper, and runs out of the garage into the evening light. "
                "Camera tracks him as he sprints across the driveway toward a house. "
                "His footsteps echo. Urgent, excited energy. {veo_style}"
            ),
            "description_ru": "Карим хватает бумагу и бежит к дому Амина.",
        },
    ],
    "S05": [
        {
            "chars": ["Amin", "Karim"],
            "nano_banana_first": (
                "Medium shot inside the garage in warm evening light. "
                "Using the character references: {Amin} stands just inside the doorway, "
                "hands in his hoodie pockets, slouched posture, bored expression, mid-yawn. "
                "{Karim} sits at the workbench with the radio receiver, one hand on the tuning dial, "
                "looking at him expectantly. "
                "{lighting}. Background: {location}. {style}"
            ),
            "nano_banana_last": (
                "Medium shot inside the garage in warm evening light. "
                "Using the character references: {Amin} stands near the garage door with his back half-turned, "
                "one foot toward the exit, looking bored and ready to leave. "
                "{Karim} sits at the workbench, slumped, hand still on the silent radio dial, "
                "expression disappointed. "
                "{lighting}. Background: {location}. {style}"
            ),
            "veo": (
                "The boy at the workbench turns the radio dial — static fills the garage, "
                "crackling, nothing meaningful. The tall boy in the hoodie yawns, "
                "turns away from the workbench and takes a step toward the exit, looking bored. "
                "Defeated atmosphere. {veo_style}"
            ),
            "description_ru": "Амин заходит скучающий. Карим крутит приёмник — ничего. Амин поворачивается к выходу.",
        },
        {
            "chars": ["Amin"],
            "nano_banana_first": (
                "Over-the-shoulder shot from behind {Amin}, who stands facing the open garage door, "
                "about to leave. His hands are in his pockets. In the background, the workbench with "
                "the radio receiver is visible, its indicator light glowing. "
                "{lighting} from outside silhouettes him. "
                "Tense, electric moment frozen in time. {style}"
            ),
            "nano_banana_last": (
                "Medium shot at the workbench. {Amin} sits in front of the radio receiver, "
                "leaning forward with intense focus, hands on the table. "
                "His expression has completely changed — alert, captivated, alive. "
                "The indicator light glows on the receiver. "
                "{lighting}. {style}"
            ),
            "veo": (
                "Suddenly — a rhythmic signal cuts through the static behind him. A monotone voice reads numbers. "
                "The boy freezes mid-step. His shoulders tense. He slowly turns around, "
                "walks back, and sits down in front of the receiver, listening intently. "
                "The numbers repeat three times. Then silence. His expression has completely changed. {veo_style}"
            ),
            "description_ru": "Сигнал возвращается. Амин замирает, медленно поворачивается, садится, слушает.",
        },
        {
            "chars": ["Amin"],
            "nano_banana_first": (
                "Close-up at the workbench: {Amin} leans forward, face and hands filling the frame. "
                "He grips a pen, writing numbers on a notepad with intensity. "
                "An old worn paper atlas lies closed on the shelf nearby. "
                "His eyes are sharp and focused — a new energy visible in his expression. "
                "Warm evening light catches the pages. {style}"
            ),
            "nano_banana_last": (
                "Close-up at the workbench: {Amin} leans over an open worn paper atlas "
                "showing a local area map. His finger points to a specific location on the map. "
                "A notepad with rows of numbers lies beside the atlas. "
                "His eyes are wide with realization — he has found something. "
                "Warm evening light catches the worn pages. {style}"
            ),
            "veo": (
                "The boy looks up with sudden intensity. He writes two rows of numbers quickly. "
                "He pulls an old atlas from the shelf, opens it, and traces coordinates on the map with his finger. "
                "His eyes widen as he realizes the location is nearby. "
                "Focused, awakening curiosity. {veo_style}"
            ),
            "description_ru": "Амин записывает цифры, открывает атлас, сопоставляет координаты — это рядом.",
        },
        {
            "chars": ["Amin", "Karim"],
            "nano_banana_first": (
                "Medium shot inside the garage. "
                "Using the character references: {Amin} and {Karim} stand on opposite sides of the workbench, "
                "facing each other. An open atlas lies between them on the bench. "
                "The tall boy's expression is determined, alive — a stark contrast to his earlier apathy. "
                "The other boy looks at him with quiet hope. "
                "{lighting}. {style}"
            ),
            "nano_banana_last": (
                "Medium shot inside the garage, looking toward the open garage door. "
                "Using the character references: {Amin} walks out through the doorway into the evening light, "
                "seen from behind — back straight, stride purposeful, determined. "
                "{Karim} stands by the workbench watching him leave, a quiet smile on his face. "
                "The open atlas lies on the bench. "
                "{lighting}. {style}"
            ),
            "veo": (
                "The two boys look at each other across the workbench, the atlas open between them. "
                "The tall boy nods, then turns and walks out of the garage. "
                "But his step is different now — quicker, back straighter. Something has switched on inside him. "
                "Camera holds on the empty doorway for a beat. A quiet turning point. {veo_style}"
            ),
            "description_ru": "Амин и Карим смотрят друг на друга. Амин уходит — шаг другой, быстрее, спина прямее.",
        },
    ],
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def capitalize_after_period(text: str) -> str:
    """Capitalize first letter after sentence boundaries."""
    result = list(text)
    for i in range(2, len(result)):
        if text[i-2:i] == '. ' and text[i].islower():
            result[i] = text[i].upper()
    return "".join(result)


def build_nano_banana_prompt(template: dict, chars: list, time_of_day: str,
                             frame_type: str = "first") -> str:
    """Build Nano Banana prompt for a static frame.

    frame_type: "first" for starting frame, "last" for ending frame.
    """
    key = f"nano_banana_{frame_type}"
    text = template[key]

    # Substitute character placeholders
    for char_name in chars:
        placeholder = "{" + char_name + "}"
        text = text.replace(placeholder, CHAR_SHORT.get(char_name, char_name))

    # Substitute environment placeholders
    text = text.replace("{lighting}", TIME_LIGHTING.get(time_of_day, "Natural lighting"))
    text = text.replace("{location}", LOCATION_ENV.get("Garage", "garage interior"))
    text = text.replace("{style}", NB_STYLE)

    return capitalize_after_period(text)


def build_veo_prompt(template: dict, clip_id: str = "") -> str:
    """Build VEO prompt for animating a frame. No character descriptions — just motion."""
    text = template["veo"]
    text = text.replace("{veo_style}", VEO_STYLE)

    # Validate: no character names should leak into VEO prompts
    for name in CHAR_SHORT:
        if name in text:
            print(f"  ⚠ WARNING [{clip_id}]: VEO prompt contains character name '{name}' — VEO can't use names!")

    return capitalize_after_period(text)


def collect_nano_ingredients(chars: list, scene_characters: list, location_files: list) -> list[str]:
    """Collect all reference images for Nano Banana (up to 14)."""
    ingredients = []

    for char_name in chars:
        for c in scene_characters:
            if c["name"] == char_name:
                if c.get("file_full"):
                    ingredients.append(f"персонажи/{c['file_full']}")
                if c.get("file_face"):
                    ingredients.append(f"персонажи/{c['file_face']}")
                if c.get("file_extra"):
                    ingredients.append(f"персонажи/{c['file_extra']}")
                break

    for loc_file in location_files:
        if loc_file:
            ingredients.append(f"локации/{loc_file}")

    return ingredients


def build_ingredient_roles(chars: list, location_name: str, ingredients: list) -> list[dict]:
    """Build role labels for each ingredient image."""
    roles = []
    for ing in ingredients:
        filename = ing.split("/")[-1]
        role = ""

        # Match to character
        for char_name in chars:
            for c_data in [("char_amin", "Amin"), ("char_karim", "Karim"),
                          ("char_tako", "Tako"), ("char_mama", "Mama"),
                          ("char_papa", "Papa"), ("char_aya", "Aya")]:
                if filename.startswith(c_data[0]) and c_data[1] == char_name:
                    role = CHAR_ROLE.get(char_name, f"Character reference: {char_name}")
                    break

        # Match to location
        if filename.startswith("loc_"):
            role = LOC_ROLE.get(location_name, f"Use this image for the {location_name.lower()} environment")

        roles.append({"file": ing, "role": role})
    return roles


def has_minor_speech(dialogues: list) -> bool:
    return any(d["speaker"] in MINOR_CHARACTERS for d in dialogues)


def build_audio_note(segment: dict, minor_speech: bool) -> str:
    notes = []

    if segment.get("dialogues_raw"):
        speakers = set(d["speaker"] for d in segment["dialogues_raw"])
        notes.append(f"Dialogue: {', '.join(speakers)}")

    if minor_speech:
        notes.append("WARNING: VEO cannot generate speech for minors — add voiceover in post.")

    desc = segment.get("description_ru", "").lower()
    if "треск" in desc or "помехи" in desc or "шум" in desc:
        notes.append("SFX: radio static, crackling")
    if "тишина" in desc:
        notes.append("Ambient: silence")
    if "сигнал" in desc:
        notes.append("SFX: mysterious number station signal")

    return " | ".join(notes) if notes else "Ambient sound only"


def segment_actions(actions: list[str], dialogues: list[dict]) -> list[dict]:
    """Segment scene actions for dialogue/audio matching."""
    segments = []
    if not actions:
        return [{"dialogues_raw": [], "description_ru": ""}]

    chunk_size = 3
    dialogue_idx = 0

    for i in range(0, len(actions), chunk_size):
        chunk = actions[i : i + chunk_size]
        description_ru = " ".join(chunk)

        segment_dialogues = []
        for d in dialogues[dialogue_idx:]:
            for line in chunk:
                if d["speaker"].upper() in line.upper():
                    segment_dialogues.append(d)
                    dialogue_idx += 1
                    break

        segments.append({
            "dialogues_raw": segment_dialogues,
            "description_ru": description_ru,
        })

    return segments if segments else [{"dialogues_raw": [], "description_ru": ""}]


# ─── Main generation ────────────────────────────────────────────────────────

def generate_clips_for_scene(scene: dict) -> list[dict]:
    """Generate dual-prompt clips (Nano Banana + VEO) for a scene."""
    clips = []
    scene_id = scene["scene_id"]
    characters = scene["characters"]
    location_name = scene["location_name_en"]
    location_files = scene["location_files"]
    time_of_day = scene["time_of_day"]

    templates = SCENE_CLIP_TEMPLATES.get(scene_id)
    if not templates:
        return clips

    segments = segment_actions(scene["actions"], scene["dialogues"])

    for idx, template in enumerate(templates):
        clip_id = f"{scene_id}_{chr(65 + idx)}"
        chars = template["chars"]
        segment = segments[idx] if idx < len(segments) else segments[-1] if segments else {}

        # Nano Banana prompts — first and last frames
        nb_prompt_first = build_nano_banana_prompt(template, chars, time_of_day, "first")
        nb_prompt_last = build_nano_banana_prompt(template, chars, time_of_day, "last")
        nb_ingredients = collect_nano_ingredients(chars, characters, location_files)
        nb_roles = build_ingredient_roles(chars, location_name, nb_ingredients)

        # VEO prompt (motion only, no appearance)
        veo_prompt = build_veo_prompt(template, clip_id)

        # Audio
        clip_dialogues = segment.get("dialogues_raw", [])
        minor_speech = has_minor_speech(clip_dialogues)

        clip = {
            "scene_id": scene_id,
            "scene_number": scene["scene_number"],
            "clip_id": clip_id,
            "scene_description_ru": template.get("description_ru", segment.get("description_ru", "")),
            "characters": chars,
            "location": location_name,
            "time_of_day": time_of_day,
            "nano_banana_prompt_first": nb_prompt_first,
            "nano_banana_prompt_last": nb_prompt_last,
            "nano_banana_ingredients": [r["file"] for r in nb_roles],
            "nano_banana_ingredient_roles": nb_roles,
            "nano_banana_model": "Nano Banana Pro (Gemini 3 Pro Image)",
            "veo_prompt": veo_prompt,
            "veo_mode": "frames_to_video_first_last",
            "veo_model": "Veo 3.1 - Fast",
            "veo_duration": 8,
            "veo_aspect_ratio": "16:9",
            "audio_note": build_audio_note(segment, minor_speech),
            "minor_speech_warning": minor_speech,
        }
        clips.append(clip)

    return clips


def generate_prompts(scenes: list[dict]) -> list[dict]:
    all_clips = []
    for scene in scenes:
        all_clips.extend(generate_clips_for_scene(scene))
    return all_clips


def main():
    parsed_path = PROJECT_ROOT / "output" / "parsed_scenes.json"

    if not parsed_path.exists():
        print(f"Error: parsed scenes not found: {parsed_path}")
        print("Run parse_scenario.py first.")
        sys.exit(1)

    with open(parsed_path, encoding="utf-8") as f:
        scenes = json.load(f)

    clips = generate_prompts(scenes)

    output_path = PROJECT_ROOT / "output" / "prompts" / "all_prompts.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clips, f, ensure_ascii=False, indent=2)

    # Individual scene files
    scenes_grouped = {}
    for clip in clips:
        sid = clip["scene_id"]
        scenes_grouped.setdefault(sid, []).append(clip)

    for sid, scene_clips in scenes_grouped.items():
        scene_path = PROJECT_ROOT / "output" / "prompts" / f"{sid}_prompts.json"
        with open(scene_path, "w", encoding="utf-8") as f:
            json.dump(scene_clips, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(clips)} clips for {len(scenes_grouped)} scenes → {output_path.parent}\n")

    for clip in clips:
        print(f"  ╔══ {clip['clip_id']} | {clip['location']} | {clip['time_of_day']} ══╗")
        print(f"  ║ {clip['scene_description_ru']}")
        print(f"  ╟── NANO BANANA (first frame) ──")
        print(f"  ║ {clip['nano_banana_prompt_first'][:150]}...")
        print(f"  ╟── NANO BANANA (last frame) ──")
        print(f"  ║ {clip['nano_banana_prompt_last'][:150]}...")
        print(f"  ║ Ingredients ({len(clip['nano_banana_ingredients'])}): {clip['nano_banana_ingredients']}")
        print(f"  ╟── VEO 3.1 (first + last frame) ──")
        print(f"  ║ {clip['veo_prompt'][:150]}...")
        print(f"  ║ Mode: {clip['veo_mode']} | Duration: {clip['veo_duration']}s")
        print(f"  ╟── Audio: {clip['audio_note']}")
        if clip["minor_speech_warning"]:
            print(f"  ║ Minor speech — voiceover needed")
        print(f"  ╚{'═' * 60}")
        print()


if __name__ == "__main__":
    main()
