#!/usr/bin/env python3
"""
Модуль 1: Парсер сценария
Разбивает текст сценария на сцены, определяет персонажей, локации, действия, диалоги.
"""

import csv
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Known character names (Russian → English mapping)
CHARACTER_NAMES = {
    "Амин": "Amin",
    "АМИН": "Amin",
    "Карим": "Karim",
    "КАРИМ": "Karim",
    "Тако": "Tako",
    "ТАКО": "Tako",
    "Мама": "Mama",
    "МАМА": "Mama",
    "Папа": "Papa",
    "ПАПА": "Papa",
    "Ая": "Aya",
    "АЯ": "Aya",
}

# Location keywords → location IDs
LOCATION_KEYWORDS = {
    "гараж": "loc_garazh",
    "ГАРАЖ": "loc_garazh",
    "кабинет": "loc_kabinet",
    "КАБИНЕТ": "loc_kabinet",
    "комната Амина": "loc_komnata_amin",
    "КОМНАТА АМИНА": "loc_komnata_amin",
    "комната Тако": "loc_komnata_tako",
    "КОМНАТА ТАКО": "loc_komnata_tako",
    "комната Аи": "loc_komnata_aya",
    "КОМНАТА АИ": "loc_komnata_aya",
    "кухня": "loc_kuhnya",
    "КУХНЯ": "loc_kuhnya",
    "гостиная": "loc_gostinaya",
    "ГОСТИНАЯ": "loc_gostinaya",
    "дом": "loc_dom_outside",
    "ДОМ": "loc_dom_outside",
    "двор": "loc_zadniy_dvor",
    "ДВОР": "loc_zadniy_dvor",
    "школа": "loc_shkola",
    "ШКОЛА": "loc_shkola",
    "улица": "loc_ulica",
    "УЛИЦА": "loc_ulica",
    "беседка": "loc_besedka",
    "БЕСЕДКА": "loc_besedka",
    "прихожая": "loc_prihozhaya",
    "ПРИХОЖАЯ": "loc_prihozhaya",
    "парк": "loc_park",
    "ПАРК": "loc_park",
}

# Mood keywords
MOOD_KEYWORDS = {
    "ночь": "night",
    "НОЧЬ": "night",
    "вечер": "evening",
    "ВЕЧЕР": "evening",
    "день": "day",
    "ДЕНЬ": "day",
    "утро": "morning",
    "УТРО": "morning",
    "темнота": "dark",
    "тишина": "quiet",
    "полутьма": "dim",
}


def load_character_reference(csv_path: Path) -> dict:
    """Load character reference CSV into a dict keyed by name_en."""
    characters = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            characters[row["name_en"]] = row
    return characters


def load_location_reference(csv_path: Path) -> dict:
    """Load location reference CSV into a dict keyed by id."""
    locations = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            locations[row["id"]] = row
    return locations


def split_into_scenes(text: str) -> list[dict]:
    """Split scenario text into raw scene blocks."""
    # Match СЦЕНА N — TITLE pattern
    scene_pattern = re.compile(
        r"СЦЕНА\s+(\d+)\s*[—–-]\s*(.+?)(?:\n|$)", re.IGNORECASE
    )

    matches = list(scene_pattern.finditer(text))
    scenes = []

    for i, match in enumerate(matches):
        scene_num = int(match.group(1))
        scene_title = match.group(2).strip()

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        scenes.append({
            "scene_number": scene_num,
            "scene_id": f"S{scene_num:02d}",
            "title_ru": scene_title,
            "body": body,
        })

    return scenes


def detect_time_of_day(title: str, body: str) -> str:
    """Detect time of day from scene title."""
    combined = (title + " " + body[:200]).upper()
    if "НОЧЬ" in combined:
        return "night"
    if "ВЕЧЕР" in combined:
        return "evening"
    if "УТРО" in combined:
        return "morning"
    if "ДЕНЬ" in combined:
        return "day"
    return "day"


def detect_location(title: str, body: str) -> str | None:
    """Detect location ID from scene title and body."""
    combined = title + " " + body[:600]
    combined_lower = combined.lower()

    # Check longer phrases first
    sorted_keywords = sorted(LOCATION_KEYWORDS.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword.lower() in combined_lower:
            return LOCATION_KEYWORDS[keyword]

    return None


def detect_characters(body: str) -> list[str]:
    """Detect character names mentioned in the scene body."""
    found = set()

    # Check for "X один" (X alone) pattern — only that character is present
    alone_pattern = re.compile(r"(\w+)\s+одна?\.?\s", re.IGNORECASE)
    alone_match = alone_pattern.search(body[:200])
    alone_char = None
    if alone_match:
        name_ru = alone_match.group(1)
        for ru, en in CHARACTER_NAMES.items():
            if name_ru.lower() == ru.lower():
                alone_char = en
                break

    # Find characters in dialogue headers (definitive presence)
    dialogue_pattern = re.compile(r"^([А-ЯЁ]+)\s*(?:\([^)]+\))?\s*:", re.MULTILINE)
    for match in dialogue_pattern.finditer(body):
        speaker_ru = match.group(1)
        if speaker_ru in CHARACTER_NAMES:
            found.add(CHARACTER_NAMES[speaker_ru])

    # Find characters in narrative text (but skip indirect references)
    indirect_patterns = [
        r"что\s+\w+\s+бросил",       # "что Амин бросил"
        r"к\s+дому\s+\w+",            # "к дому Амина"
        r"у\s+дома\s+\w+",            # "у дома Амина"
    ]

    for ru_name, en_name in CHARACTER_NAMES.items():
        # Check if name appears in a dialogue header (already handled above)
        # Check narrative mentions
        pattern = rf'\b{re.escape(ru_name)}\b'
        for match in re.finditer(pattern, body, re.IGNORECASE):
            # Get surrounding context to check for indirect reference
            start = max(0, match.start() - 30)
            end = min(len(body), match.end() + 30)
            context = body[start:end]

            is_indirect = False
            for indirect in indirect_patterns:
                if re.search(indirect, context, re.IGNORECASE):
                    is_indirect = True
                    break

            if not is_indirect:
                found.add(en_name)

    # If "alone" pattern detected and that character is found, return only them
    if alone_char and alone_char in found:
        return [alone_char]

    return sorted(found)


def extract_dialogues(body: str) -> list[dict]:
    """Extract dialogue lines from scene body."""
    dialogues = []
    # Match patterns like "АМИН: text" or "КАРИМ (шёпотом): text"
    dialogue_pattern = re.compile(
        r"^([А-ЯЁ]+)\s*(?:\(([^)]+)\))?\s*:\s*(.+)$", re.MULTILINE
    )

    for match in dialogue_pattern.finditer(body):
        speaker_ru = match.group(1)
        modifier = match.group(2) or ""
        text = match.group(3).strip()

        speaker_en = CHARACTER_NAMES.get(speaker_ru, speaker_ru)
        dialogues.append({
            "speaker": speaker_en,
            "modifier": modifier,
            "text_ru": text,
        })

    return dialogues


def extract_action_descriptions(body: str) -> list[str]:
    """Extract narrative/action lines (non-dialogue)."""
    actions = []
    lines = body.split("\n")

    dialogue_pattern = re.compile(r"^[А-ЯЁ]+\s*(?:\([^)]+\))?\s*:")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if dialogue_pattern.match(line):
            continue
        if line.startswith("ТИТР:"):
            continue
        if line.startswith("[") and line.endswith("]"):
            # Stage direction in brackets
            actions.append(line[1:-1].strip())
        elif line.startswith("Эта сцена не обязательная"):
            continue
        else:
            actions.append(line)

    return actions


def detect_mood(title: str, body: str) -> str:
    """Detect general mood of the scene."""
    combined = (title + " " + body[:500]).lower()

    if any(w in combined for w in ["шёпот", "темнота", "полутьм", "тайн"]):
        mood = "mysterious"
    elif any(w in combined for w in ["бежим", "срыва", "сердце колот"]):
        mood = "tense"
    elif any(w in combined for w in ["смеётся", "весёл", "торжеств"]):
        mood = "cheerful"
    elif any(w in combined for w in ["скуча", "лежит", "потолок"]):
        mood = "melancholic"
    elif any(w in combined for w in ["тишина", "спокойн", "тёпл", "тепл"]):
        mood = "calm"
    else:
        mood = "neutral"

    return mood


def has_observer_shot(body: str) -> bool:
    """Check if scene has an observer/surveillance camera shot."""
    return "[Кадр «наблюдателя»" in body or "[Кадр наблюдателя" in body


def parse_scenario(scenario_path: Path, char_csv: Path, loc_csv: Path) -> list[dict]:
    """Parse full scenario into structured scene data."""
    text = scenario_path.read_text(encoding="utf-8")
    characters_ref = load_character_reference(char_csv)
    locations_ref = load_location_reference(loc_csv)

    raw_scenes = split_into_scenes(text)
    parsed_scenes = []

    for raw in raw_scenes:
        location_id = detect_location(raw["title_ru"], raw["body"])
        time_of_day = detect_time_of_day(raw["title_ru"], raw["body"])
        chars = detect_characters(raw["body"])
        dialogues = extract_dialogues(raw["body"])
        actions = extract_action_descriptions(raw["body"])
        mood = detect_mood(raw["title_ru"], raw["body"])

        # Get location description
        location_desc_en = ""
        location_name_en = ""
        location_files = []
        if location_id and location_id in locations_ref:
            loc = locations_ref[location_id]
            location_desc_en = loc["description_en"]
            location_name_en = loc["name_en"]
            location_files = [
                f.strip() for f in loc["files"].split(",") if f.strip()
            ]

        # Get character details
        char_details = []
        for char_name in chars:
            if char_name in characters_ref:
                ref = characters_ref[char_name]
                char_details.append({
                    "name": char_name,
                    "id": ref["id"],
                    "description_en": ref["description_en"],
                    "file_full": ref["file_full"],
                    "file_face": ref.get("file_face", ""),
                    "file_extra": ref.get("file_extra", ""),
                })

        scene = {
            "scene_id": raw["scene_id"],
            "scene_number": raw["scene_number"],
            "title_ru": raw["title_ru"],
            "location_id": location_id,
            "location_name_en": location_name_en,
            "location_description_en": location_desc_en,
            "location_files": location_files,
            "time_of_day": time_of_day,
            "characters": char_details,
            "dialogues": dialogues,
            "actions": actions,
            "mood": mood,
            "has_observer_shot": has_observer_shot(raw["body"]),
            "is_optional": "не обязательная" in raw["body"].lower(),
        }
        parsed_scenes.append(scene)

    return parsed_scenes


def main():
    scenario_path = PROJECT_ROOT / "scenario_signal.txt"
    char_csv = PROJECT_ROOT / "character_reference.csv"
    loc_csv = PROJECT_ROOT / "location_reference.csv"

    if not scenario_path.exists():
        print(f"Error: scenario file not found: {scenario_path}")
        sys.exit(1)

    scenes = parse_scenario(scenario_path, char_csv, loc_csv)

    # Filter by scene numbers if provided via CLI args
    if len(sys.argv) > 1:
        filter_scenes = [int(x) for x in sys.argv[1:]]
        scenes = [s for s in scenes if s["scene_number"] in filter_scenes]

    output_path = PROJECT_ROOT / "output" / "parsed_scenes.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(scenes, f, ensure_ascii=False, indent=2)

    print(f"Parsed {len(scenes)} scenes → {output_path}")
    for s in scenes:
        chars = ", ".join(c["name"] for c in s["characters"])
        print(
            f"  {s['scene_id']}: {s['title_ru']}"
            f" | Location: {s['location_name_en'] or '?'}"
            f" | Characters: {chars}"
            f" | Time: {s['time_of_day']}"
            f" | Mood: {s['mood']}"
        )


if __name__ == "__main__":
    main()
