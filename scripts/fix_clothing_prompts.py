#!/usr/bin/env python3
"""
Adds clothing descriptions to character references in all_prompts.json.
Uses simple two-pass approach:
1. Find all "the exact character from Image N" occurrences
2. Check if clothing already follows — if not, insert it
"""

import json
import re
from pathlib import Path

PROMPTS_FILE = Path(__file__).parent.parent / "output" / "prompts" / "all_prompts.json"

CLOTHING = {
    "char_amin_full":  "in a grey hoodie",
    "char_karim_full": "in a black hoodie",
    "char_tako_full":  "in a red-and-white striped shirt and red cap",
    "char_rami_full":  "in a green hoodie and brown cargo pants",
    "char_hasan_full": "in a light blue polo shirt",
    "char_mama_full":  "in a black hijab and black abaya",
    "char_papa_full":  "in a black turtleneck sweater and glasses",
    "char_aya_full":   "in a pink dress and dark navy striped hijab",
}

def get_char_key(path: str) -> str | None:
    fname = Path(path).stem
    return fname if fname.startswith("char_") else None


def add_clothing(prompt: str, img_map: dict[int, str]) -> str:
    if not prompt:
        return prompt

    # Find all "the exact character from Image N" and check what follows
    # Pattern: "the exact character from Image N" followed by either:
    #   - ", " (no clothing)  → insert
    #   - " in a " (has clothing) → skip
    #   - " wearing a " (has clothing) → skip

    pattern = re.compile(r'the exact character from Image (\d+)')

    result = []
    last_end = 0

    for m in pattern.finditer(prompt):
        img_num = int(m.group(1))
        clothing = img_map.get(img_num)

        # Get text after match to check for existing clothing
        after_text = prompt[m.end():m.end()+20]

        # Already has clothing?
        has_clothing = bool(re.match(r'\s+(in a |wearing a )', after_text))

        if clothing and not has_clothing:
            # Insert clothing before "from"
            result.append(prompt[last_end:m.start()])
            result.append(f"the exact character {clothing} from Image {img_num}")
            last_end = m.end()
        # else: keep original

    result.append(prompt[last_end:])
    return ''.join(result)


def process_clips(clips):
    total_fields = 0
    clips_modified = 0

    prompt_keys = [
        "nano_banana_prompt_first", "nano_banana_prompt_first_b",
        "nano_banana_prompt_mid", "nano_banana_prompt_mid_b",
        "nano_banana_prompt_last", "nano_banana_prompt_last_b",
    ]

    for clip in clips:
        clip_id = clip["clip_id"]
        ingredients = clip.get("nano_banana_ingredients", [])

        img_map = {}
        for i, ing in enumerate(ingredients):
            char_key = get_char_key(ing)
            if char_key and char_key in CLOTHING:
                img_map[i + 1] = CLOTHING[char_key]

        if not img_map:
            continue

        clip_changed = False
        for key in prompt_keys:
            old_val = clip.get(key)
            if not old_val:
                continue

            new_val = add_clothing(old_val, img_map)
            if new_val != old_val:
                clip[key] = new_val
                total_fields += 1
                clip_changed = True
                print(f"  {clip_id}/{key}: updated")

        if clip_changed:
            clips_modified += 1

    return total_fields, clips_modified


def main():
    print(f"Reading {PROMPTS_FILE}")
    with open(PROMPTS_FILE) as f:
        clips = json.load(f)

    print(f"Processing {len(clips)} clips...\n")
    total, modified = process_clips(clips)

    print(f"\n=== Summary ===")
    print(f"  Clips modified: {modified}/{len(clips)}")
    print(f"  Prompt fields updated: {total}")

    if modified > 0:
        with open(PROMPTS_FILE, 'w') as f:
            json.dump(clips, f, indent=2, ensure_ascii=False)
        print(f"  Saved: {PROMPTS_FILE}")

        # Verify
        with open(PROMPTS_FILE) as f:
            text = f.read()
        doubles = re.findall(r'in a [\w-]+.*?from Image \d+\s+(in a |wearing a )', text)
        if doubles:
            print(f"\n  WARNING: {len(doubles)} double-clothing instances!")
        else:
            print("  Verification OK: no double-clothing.")
    else:
        print("  No changes needed.")


if __name__ == "__main__":
    main()
