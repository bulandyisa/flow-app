#!/usr/bin/env python3
"""Generate all_prompts.json for Sosed series from compact clip definitions."""
import json
import sys
from pathlib import Path

# === Character and location references ===
CHARS = {
    "amin":   {"path": "персонажи_hq/char_amin_full.jpeg",  "clothing": "a grey hoodie"},
    "aya":    {"path": "персонажи_hq/char_aya_full.jpeg",    "clothing": "a pink dress and dark navy striped hijab"},
    "tako":   {"path": "персонажи_hq/char_tako_full.jpeg",   "clothing": "a red-and-white striped shirt and red cap"},
    "karim":  {"path": "персонажи_hq/char_karim_full.jpeg",  "clothing": "a black hoodie"},
    "papa":   {"path": "персонажи_hq/char_papa_full.jpeg",   "clothing": "a black turtleneck sweater and glasses"},
    "mama":   {"path": "персонажи_hq/char_mama_full.jpeg",   "clothing": "a black hijab and black abaya"},
    "jamil":  {"path": "sosed_персонажи_hq/jamil.png",       "clothing": "a light shirt with rolled sleeves"},
    "simba":  {"path": "sosed_персонажи_hq/simba.png",       "clothing": None},  # animal, no clothing
}

LOCS = {
    "house_front":      "локации_hq/loc_dom_outside_front.jpg",
    "garage":           "локации_hq/loc_garazh_wide.jpg",
    "kitchen":          "локации_hq/loc_kitchen_full.jpg",
    "kabinet":          "локации_hq/loc_kabinet_full.jpg",
    "amin_room":        "локации_hq/loc_amin_room_full.jpg",
    "night_street":     "локации_hq/loc_night_street.jpg",
    "tako_room":        "локации_hq/loc_tako_room_desk.jpg",
    "jamil_yard":       "sosed_локации_hq/loc_jamil_yard.png",
    "jamil_corridor":   "sosed_локации_hq/loc_jamil_corridor.png",
    "jamil_house_front":"sosed_локации_hq/loc_jamil_house_front.png",
    "fence":            "sosed_локации_hq/loc_fence.png",
    "strojka":          "sosed_локации_hq/loc_strojka.png",
    "library":          "sosed_локации_hq/loc_library.png",
    "carwash":          "sosed_локации_hq/loc_carwash.png",
    "old_quarter":      "sosed_локации_hq/loc_old_quarter.png",
    "parking_mosque":   "sosed_локации_hq/loc_parking_mosque.png",
    "underground_hall": "sosed_локации_hq/loc_underground_hall.png",
    "underground_corr": "sosed_локации_hq/loc_underground_corridor.png",
    "night_jamil":      "sosed_локации_hq/loc_night_jamil.png",
}

STYLE = "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."


def build_prompt(char_actions: list, loc_img: int | None, camera: str, lighting: str, extra: str = "") -> str:
    """Build a full NB Pro prompt.

    char_actions: list of (img_num, clothing_or_None, action_text)
      - img_num: 1-based Image reference number
      - clothing_or_None: clothing string for identity separation, or None for animals
      - action_text: what the character does (no trailing period)
    loc_img: image number for location reference, or None
    camera: e.g. "Medium shot, eye-level"
    lighting: e.g. "Golden hour, warm light"
    extra: any extra text before style tag
    """
    parts = []
    for i, (img_num, clothing, action) in enumerate(char_actions):
        # Multi-character prefix
        if len(char_actions) > 1:
            prefix = "First, " if i == 0 else "Then, "
        else:
            prefix = ""

        # Identity lock
        if clothing:
            identity = f"the exact character in {clothing} from Image {img_num}"
        else:
            identity = f"the exact animal from Image {img_num}"

        # Full identity only for first character
        if i == 0:
            identity += ", preserving identical facial features and proportions"

        parts.append(f"{prefix}{identity}, {action}.")

    if loc_img is not None:
        parts.append(f"Use Image {loc_img} as the exact background location.")

    tail = f"{camera}. {lighting}."
    if extra:
        tail += f" {extra}"
    tail += f" {STYLE}"
    parts.append(tail)

    return " ".join(parts)


def make_clip(clip_id, scene_id, desc_ru, char_keys, loc_key,
              first_a, first_b, last_a, last_b):
    """Create a clip entry.

    char_keys: list of character keys from CHARS dict
    loc_key: location key from LOCS dict, or None
    first_a/b, last_a/b: each is a dict with:
        actions: list of (action_text,) per character (same order as char_keys)
        camera: str
        lighting: str
        extra: str (optional)
    """
    # Build ingredients list
    ingredients = []
    for ck in char_keys:
        ingredients.append(CHARS[ck]["path"])
    if loc_key:
        ingredients.append(LOCS[loc_key])

    # Map char_keys to image numbers (1-based)
    def make_char_actions(actions_def):
        result = []
        for i, ck in enumerate(char_keys):
            img_num = i + 1
            clothing = CHARS[ck]["clothing"]
            action = actions_def["actions"][i]
            result.append((img_num, clothing, action))
        return result

    loc_img = len(char_keys) + 1 if loc_key else None

    def gen(prompt_def):
        return build_prompt(
            make_char_actions(prompt_def),
            loc_img,
            prompt_def["camera"],
            prompt_def["lighting"],
            prompt_def.get("extra", "")
        )

    return {
        "clip_id": clip_id,
        "scene_id": scene_id,
        "scene_description_ru": desc_ru,
        "nano_banana_ingredients": ingredients,
        "nano_banana_prompt_first": gen(first_a),
        "nano_banana_prompt_first_b": gen(first_b),
        "nano_banana_prompt_mid": None,
        "nano_banana_prompt_mid_b": None,
        "nano_banana_prompt_last": gen(last_a),
        "nano_banana_prompt_last_b": gen(last_b),
        "veo_prompt": None,
        "veo_prompt_b": None,
        "veo_mode": "frames",
        "veo_variant_count": 4
    }


def make_clip_simple(clip_id, scene_id, desc_ru, ingredients_raw,
                     first_a_text, first_b_text, last_a_text, last_b_text):
    """Create a clip with raw prompt text (for complex/non-standard clips)."""
    return {
        "clip_id": clip_id,
        "scene_id": scene_id,
        "scene_description_ru": desc_ru,
        "nano_banana_ingredients": ingredients_raw,
        "nano_banana_prompt_first": first_a_text,
        "nano_banana_prompt_first_b": first_b_text,
        "nano_banana_prompt_mid": None,
        "nano_banana_prompt_mid_b": None,
        "nano_banana_prompt_last": last_a_text,
        "nano_banana_prompt_last_b": last_b_text,
        "veo_prompt": None,
        "veo_prompt_b": None,
        "veo_mode": "frames",
        "veo_variant_count": 4
    }


if __name__ == "__main__":
    # Import clip definitions from the data files
    from gen_prompts_data import ALL_CLIPS
    from gen_prompts_data_ext import EXT_CLIPS
    ALL_CLIPS = ALL_CLIPS + EXT_CLIPS

    # Load existing prompts (S01-S02)
    existing_path = Path(__file__).parent.parent / "output_sosed" / "prompts" / "all_prompts.json"
    if existing_path.exists():
        with open(existing_path) as f:
            existing = json.load(f)
        existing_ids = {c["clip_id"] for c in existing}
    else:
        existing = []
        existing_ids = set()

    # Add new clips (skip duplicates)
    new_count = 0
    for clip in ALL_CLIPS:
        if clip["clip_id"] not in existing_ids:
            existing.append(clip)
            new_count += 1

    # Sort by clip_id
    def sort_key(c):
        cid = c["clip_id"]
        # S01_A -> (1, 0), S01_B -> (1, 1), S10_A -> (10, 0)
        parts = cid.split("_", 1)
        scene_num = int(parts[0][1:])
        letter_num = ord(parts[1]) - ord('A') if len(parts) > 1 else 0
        return (scene_num, letter_num)

    existing.sort(key=sort_key)

    # Write
    with open(existing_path, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    print(f"Total clips: {len(existing)} ({new_count} new)")

    # Scene breakdown
    scenes = {}
    for c in existing:
        s = c["scene_id"]
        scenes[s] = scenes.get(s, 0) + 1
    for s in sorted(scenes, key=lambda x: int(x[1:])):
        print(f"  {s}: {scenes[s]} clips")
