#!/usr/bin/env python3
"""
Модуль 3: Ревью-интерфейс (CLI)
Показывает таблицу промптов, позволяет копировать, экспортировать.
"""

import json
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_prompts(prompts_path: Path) -> list[dict]:
    """Load prompts from JSON file."""
    with open(prompts_path, encoding="utf-8") as f:
        return json.load(f)


def print_separator(width=100):
    print("─" * width)


def print_table_header():
    print_separator()
    print(
        f"{'Clip':<10} {'Mode':<22} {'Dur':<5} {'Characters':<20} "
        f"{'Ingredients':<3} {'Minor':<6}"
    )
    print_separator()


def print_clip_row(clip: dict):
    chars = ", ".join(clip.get("characters", []))[:18]
    n_ing = len(clip.get("ingredients", []))
    minor = "⚠ YES" if clip.get("minor_speech_warning") else ""

    print(
        f"{clip['clip_id']:<10} {clip['mode']:<22} {clip['duration']:<5} "
        f"{chars:<20} {n_ing:<3} {minor:<6}"
    )


def copy_to_clipboard(text: str) -> bool:
    """Copy text to macOS clipboard."""
    try:
        process = subprocess.Popen(
            ["pbcopy"], stdin=subprocess.PIPE, text=True
        )
        process.communicate(text)
        return process.returncode == 0
    except FileNotFoundError:
        return False


def display_all(clips: list[dict]):
    """Display all clips in a summary table."""
    print(f"\n📋 VEO 3.1 Prompt Review — {len(clips)} clips\n")
    print_table_header()

    for clip in clips:
        print_clip_row(clip)

    print_separator()


def display_clip_detail(clip: dict):
    """Display full detail of a single clip."""
    print_separator()
    print(f"  Clip: {clip['clip_id']}")
    print(f"  Scene: {clip['scene_id']} | Location: {clip['location']} | Time: {clip['time_of_day']}")
    print(f"  Characters: {', '.join(clip.get('characters', []))}")
    print(f"  Mode: {clip['mode']} | Duration: {clip['duration']}s")
    print(f"  Ingredients: {', '.join(clip.get('ingredients', [])) or 'none'}")
    print()
    print(f"  PROMPT:")
    print(f"  {clip['prompt']}")
    print()
    print(f"  Audio: {clip.get('audio_note', '')}")
    if clip.get("minor_speech_warning"):
        print(f"  ⚠ MINOR SPEECH: Dialogue must be added in post-production")
    if clip.get("description_ru"):
        print(f"  RU: {clip['description_ru'][:150]}")
    print_separator()


def interactive_review(clips: list[dict]):
    """Interactive CLI review loop."""
    display_all(clips)

    print("\nCommands:")
    print("  [number]   — show clip detail (e.g. '1' for first clip)")
    print("  c [number] — copy prompt to clipboard")
    print("  ca         — copy ALL prompts to clipboard")
    print("  e          — export prompts to text file")
    print("  q          — quit")
    print()

    while True:
        try:
            cmd = input("review> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not cmd:
            continue

        if cmd.lower() == "q":
            break

        if cmd.lower() == "ca":
            all_prompts = "\n\n".join(
                f"[{c['clip_id']}] ({c['mode']})\n{c['prompt']}"
                for c in clips
            )
            if copy_to_clipboard(all_prompts):
                print(f"✓ Copied all {len(clips)} prompts to clipboard")
            else:
                print("✗ Failed to copy (pbcopy not available)")
            continue

        if cmd.lower() == "e":
            export_path = PROJECT_ROOT / "output" / "prompts" / "prompts_export.txt"
            with open(export_path, "w", encoding="utf-8") as f:
                for clip in clips:
                    f.write(f"[{clip['clip_id']}] Mode: {clip['mode']}\n")
                    f.write(f"Ingredients: {', '.join(clip.get('ingredients', []))}\n")
                    f.write(f"Duration: {clip['duration']}s\n")
                    f.write(f"Prompt: {clip['prompt']}\n")
                    f.write(f"Audio: {clip.get('audio_note', '')}\n")
                    if clip.get("minor_speech_warning"):
                        f.write("⚠ MINOR SPEECH WARNING\n")
                    f.write("\n---\n\n")
            print(f"✓ Exported to {export_path}")
            continue

        if cmd.lower().startswith("c "):
            try:
                idx = int(cmd.split()[1]) - 1
                if 0 <= idx < len(clips):
                    if copy_to_clipboard(clips[idx]["prompt"]):
                        print(f"✓ Copied prompt for {clips[idx]['clip_id']}")
                    else:
                        print("✗ Failed to copy")
                else:
                    print(f"Invalid clip number (1-{len(clips)})")
            except (ValueError, IndexError):
                print("Usage: c [number]")
            continue

        try:
            idx = int(cmd) - 1
            if 0 <= idx < len(clips):
                display_clip_detail(clips[idx])
            else:
                print(f"Invalid clip number (1-{len(clips)})")
        except ValueError:
            print("Unknown command. Type 'q' to quit.")


def main():
    prompts_path = PROJECT_ROOT / "output" / "prompts" / "all_prompts.json"

    # Allow specifying a different file via CLI arg
    if len(sys.argv) > 1:
        prompts_path = Path(sys.argv[1])

    if not prompts_path.exists():
        print(f"Error: prompts not found: {prompts_path}")
        print("Run parse_scenario.py and generate_prompts.py first.")
        sys.exit(1)

    clips = load_prompts(prompts_path)

    if not clips:
        print("No clips found in prompts file.")
        sys.exit(1)

    # Non-interactive mode if stdin is not a terminal
    if not sys.stdin.isatty():
        display_all(clips)
        for clip in clips:
            display_clip_detail(clip)
        return

    interactive_review(clips)


if __name__ == "__main__":
    main()
