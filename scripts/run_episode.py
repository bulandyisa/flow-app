#!/usr/bin/env python3
"""
Пошаговый оркестратор эпизода — утилита для Claude Code.

Этот скрипт НЕ вызывает внешние API. Вся оценка качества делается
Claude Code визуально (через Read tool для просмотра изображений).

Команды:
  # Статус всех клипов:
  python scripts/run_episode.py --status

  # Генерация вариантов (все клипы или один):
  python scripts/run_episode.py --generate
  python scripts/run_episode.py --generate --clip S01_A

  # Показать файлы вариантов для визуальной оценки:
  python scripts/run_episode.py --show-variants --clip S01_A --component nb_first
  python scripts/run_episode.py --show-variants --clip S01_A --component veo --attempt 1

  # Извлечь кадры из видео для оценки:
  python scripts/run_episode.py --extract --clip S01_A --attempt 1

  # Собрать финальную сцену:
  python scripts/run_episode.py --scene

Workflow для Claude Code:
  1. --generate → генерирует варианты
  2. --show-variants → показывает пути к файлам
  3. Claude Code читает изображения через Read tool и оценивает визуально
  4. Claude Code вызывает flow_bot.py --select/--fail напрямую
  5. Повтор пока все компоненты не приняты
  6. --scene → собирает финальный видеоролик
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOT_SCRIPT = PROJECT_ROOT / "scripts" / "flow_bot.py"
VENV_PYTHON = PROJECT_ROOT / "venv" / "bin" / "python3"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
PROMPTS_PATH = PROJECT_ROOT / "output" / "prompts" / "all_prompts.json"
REVIEW_DIR = PROJECT_ROOT / "output" / "review"
FRAMES_DIR = PROJECT_ROOT / "output" / "frames"
CLIPS_DIR = PROJECT_ROOT / "output" / "clips"
SCENE_DIR = PROJECT_ROOT / "output" / "scene"

# ─── Config ───────────────────────────────────────────────────────────────────

MAX_ATTEMPTS = 3
SCORE_THRESHOLD = 9.0
SCORE_CRITERIA = ["char", "comp", "loc", "anim", "artifacts", "overall", "style"]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def run_bot(*args, check: bool = True) -> subprocess.CompletedProcess:
    """Call flow_bot.py with given arguments."""
    cmd = [PYTHON, str(BOT_SCRIPT)] + list(args)
    print(f"\n  > {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT))
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            print(f"    {line}")
    if result.returncode != 0 and check:
        if result.stderr:
            print(f"  STDERR: {result.stderr[:500]}")
        print(f"  Bot command failed with exit code {result.returncode}")
    return result


def load_clips(clip_filter: str | None = None) -> list[dict]:
    """Load clips from all_prompts.json."""
    with open(PROMPTS_PATH, encoding="utf-8") as f:
        clips = json.load(f)
    if clip_filter:
        clips = [c for c in clips if c["clip_id"] == clip_filter]
    return clips


def load_manifest(clip_id: str) -> dict | None:
    """Load manifest for a clip. Returns None if not found."""
    path = REVIEW_DIR / clip_id / "manifest.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


# ─── Status ───────────────────────────────────────────────────────────────────

def do_status(clip_filter: str | None = None):
    """Show status of all clips and their components."""
    clips = load_clips(clip_filter)
    if not clips:
        print("No clips found.")
        return

    print(f"\n{'=' * 72}")
    print(f"  EPISODE STATUS — {len(clips)} clips")
    print(f"  {'CLIP':<10} {'NB_FIRST':<14} {'NB_LAST':<14} {'VEO':<14} {'ATTEMPT'}")
    print(f"  {'-' * 10} {'-' * 14} {'-' * 14} {'-' * 14} {'-' * 7}")

    all_done = True
    for clip in clips:
        clip_id = clip["clip_id"]
        manifest = load_manifest(clip_id)

        if not manifest:
            print(f"  {clip_id:<10} {'—':<14} {'—':<14} {'—':<14} no review")
            all_done = False
            continue

        row = f"  {clip_id:<10}"
        for comp in ["nb_first", "nb_last", "veo"]:
            status = manifest["components"][comp]["status"]
            n_attempts = len(manifest["components"][comp]["attempts"])
            label = f"{status}({n_attempts})"
            row += f" {label:<14}"
            if status != "accepted":
                all_done = False
        print(row)

    print(f"{'=' * 72}")
    if all_done:
        print("  All clips accepted! Ready for --scene")
    else:
        pending = []
        for clip in clips:
            manifest = load_manifest(clip["clip_id"])
            if not manifest:
                pending.append(clip["clip_id"])
                continue
            for comp in ["nb_first", "nb_last", "veo"]:
                if manifest["components"][comp]["status"] != "accepted":
                    pending.append(f"{clip['clip_id']}/{comp}")
        print(f"  Pending: {', '.join(pending)}")


# ─── Generate ─────────────────────────────────────────────────────────────────

def do_generate(clip_filter: str | None = None):
    """Generate variants for pending clips via --review."""
    print(f"\n  Generating variants...")
    args = ["--review"]
    if clip_filter:
        args += ["--clip", clip_filter]
    result = run_bot(*args)
    if result.returncode == 0:
        print("\n  Generation complete. Use --show-variants to see files for evaluation.")
    return result.returncode == 0


# ─── Show variants ────────────────────────────────────────────────────────────

def do_show_variants(clip_id: str, component: str | None = None,
                     attempt: int | None = None):
    """Show file paths for variant images/frames for Claude Code to read."""
    manifest = load_manifest(clip_id)
    if not manifest:
        print(f"  No manifest for {clip_id}. Run --generate first.")
        return

    clip_data = None
    for c in load_clips():
        if c["clip_id"] == clip_id:
            clip_data = c
            break

    components = [component] if component else ["nb_first", "nb_last", "veo"]

    for comp in components:
        comp_data = manifest["components"][comp]
        status = comp_data["status"]
        n_attempts = len(comp_data["attempts"])

        print(f"\n{'─' * 60}")
        print(f"  {clip_id}/{comp} — status: {status}, attempts: {n_attempts}")

        if status == "accepted":
            sel = comp_data.get("selected_variant", {})
            print(f"  Already accepted: variant {sel.get('variant_index')}, "
                  f"avg={sel.get('average_score', 0):.1f}")
            # Show accepted file
            if comp == "veo":
                accepted = CLIPS_DIR / f"{clip_id}.mp4"
            else:
                suffix = "first" if comp == "nb_first" else "last"
                accepted = FRAMES_DIR / f"{clip_id}_{suffix}.png"
            if accepted.exists():
                print(f"  Accepted file: {accepted}")
            continue

        if n_attempts == 0:
            print(f"  No attempts yet. Run --generate first.")
            continue

        # Show reference images
        if clip_data and comp in ["nb_first", "nb_last"]:
            refs = clip_data.get("nano_banana_ingredient_roles", [])
            if refs:
                print(f"\n  Reference images:")
                for ref in refs:
                    ref_path = PROJECT_ROOT / ref["file"]
                    exists = "✓" if ref_path.exists() else "✗"
                    print(f"    [{exists}] {ref_path}  ({ref['role']})")

        # Show prompt
        if clip_data:
            if comp == "nb_first":
                print(f"\n  Prompt: {clip_data.get('nano_banana_prompt_first', '?')[:100]}...")
            elif comp == "nb_last":
                print(f"\n  Prompt: {clip_data.get('nano_banana_prompt_last', '?')[:100]}...")
            elif comp == "veo":
                print(f"\n  VEO prompt: {clip_data.get('veo_prompt', '?')[:100]}...")
                print(f"  Duration: {clip_data.get('veo_duration', 8)}s")

        # Show attempts
        target_attempts = [attempt] if attempt else range(1, n_attempts + 1)
        for att_num in target_attempts:
            if att_num > n_attempts:
                continue
            att = comp_data["attempts"][att_num - 1]
            print(f"\n  Attempt {att_num}:")

            attempt_dir = REVIEW_DIR / clip_id / comp / f"attempt_{att_num}"
            if not attempt_dir.exists():
                print(f"    Directory not found: {attempt_dir}")
                continue

            if comp in ["nb_first", "nb_last"]:
                variants = sorted(attempt_dir.glob("variant_*.png"))
                if variants:
                    print(f"    Image variants ({len(variants)}):")
                    for v in variants:
                        print(f"      {v}")
                else:
                    print(f"    No variant PNGs found in {attempt_dir}")
            else:
                # VEO — show video files and frame dirs
                videos = sorted(attempt_dir.glob("variant_*.mp4"))
                if videos:
                    print(f"    Video variants ({len(videos)}):")
                    for v in videos:
                        size_kb = v.stat().st_size / 1024
                        print(f"      {v}  ({size_kb:.0f} KB)")

                frame_dirs = sorted(attempt_dir.glob("variant_*_frames"))
                if frame_dirs:
                    print(f"    Extracted frames:")
                    for fd in frame_dirs:
                        frames = sorted(fd.glob("frame_*.png"))
                        print(f"      {fd}/  ({len(frames)} frames)")
                        for fr in frames:
                            print(f"        {fr}")
                elif videos:
                    print(f"    No extracted frames. Run: --extract --clip {clip_id} --attempt {att_num}")

        # Show scoring instructions
        print(f"\n  ─── Scoring guide ───")
        print(f"  Score criteria (1-10): {', '.join(SCORE_CRITERIA)}")
        print(f"  Threshold: avg >= {SCORE_THRESHOLD} (excluding zero-scored)")
        if comp in ["nb_first", "nb_last"]:
            print(f"  Note: anim=0 for still images")
            print(f"\n  After evaluation, run:")
            print(f"    Accept: python3 scripts/flow_bot.py --select --clip {clip_id} "
                  f"--component {comp} --attempt N --variant V "
                  f"--scores '{{\"char\":N,\"comp\":N,...}}'")
            print(f"    Reject: python3 scripts/flow_bot.py --fail --clip {clip_id} "
                  f"--component {comp} --attempt N")
        else:
            print(f"\n  After evaluation, run:")
            print(f"    Accept: python3 scripts/flow_bot.py --select --clip {clip_id} "
                  f"--component veo --attempt N --variant V "
                  f"--scores '{{...}}' --trim-start S --trim-end E")
            print(f"    Reject: python3 scripts/flow_bot.py --fail --clip {clip_id} "
                  f"--component veo --attempt N")


# ─── Extract frames ──────────────────────────────────────────────────────────

def do_extract(clip_id: str, attempt: int):
    """Extract frames from VEO video variants for visual evaluation."""
    run_bot("--extract-frames", "--clip", clip_id, "--component", "veo",
            "--attempt", str(attempt))
    print(f"\n  Frames extracted. Use --show-variants to see paths.")


# ─── Scene ────────────────────────────────────────────────────────────────────

def do_scene():
    """Build final scene from all accepted clips."""
    print(f"\n  Building scene...")
    result = run_bot("--scene")
    if result.returncode == 0:
        scene_path = SCENE_DIR / "full_scene.mp4"
        if scene_path.exists():
            size_mb = scene_path.stat().st_size / (1024 * 1024)
            print(f"\n  DONE! Final scene: {scene_path} ({size_mb:.1f} MB)")
        else:
            print(f"\n  Scene build ran but file not found at {scene_path}")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Episode helper — step-by-step workflow for Claude Code"
    )
    parser.add_argument("--status", action="store_true",
                        help="Show status of all clips")
    parser.add_argument("--generate", action="store_true",
                        help="Generate variants for pending clips (calls --review)")
    parser.add_argument("--show-variants", action="store_true",
                        help="Show variant file paths for evaluation")
    parser.add_argument("--extract", action="store_true",
                        help="Extract frames from VEO video variants")
    parser.add_argument("--scene", action="store_true",
                        help="Build final scene")

    parser.add_argument("--clip", type=str, default=None,
                        help="Filter to specific clip (e.g. S01_A)")
    parser.add_argument("--component", type=str, default=None,
                        choices=["nb_first", "nb_last", "veo"],
                        help="Filter to specific component")
    parser.add_argument("--attempt", type=int, default=None,
                        help="Attempt number")

    args = parser.parse_args()

    if not PROMPTS_PATH.exists():
        print(f"Error: prompts not found: {PROMPTS_PATH}")
        print("Run parse_scenario.py and generate_prompts.py first.")
        sys.exit(1)

    if args.status:
        do_status(args.clip)
    elif args.generate:
        do_generate(args.clip)
    elif args.show_variants:
        if not args.clip:
            print("Error: --show-variants requires --clip")
            sys.exit(1)
        do_show_variants(args.clip, args.component, args.attempt)
    elif args.extract:
        if not args.clip or not args.attempt:
            print("Error: --extract requires --clip and --attempt")
            sys.exit(1)
        do_extract(args.clip, args.attempt)
    elif args.scene:
        do_scene()
    else:
        parser.print_help()
        print("\n  Workflow:")
        print("    1. python3 scripts/run_episode.py --status")
        print("    2. python3 scripts/run_episode.py --generate --clip S01_A")
        print("    3. python3 scripts/run_episode.py --show-variants --clip S01_A")
        print("    4. Claude Code reads images, evaluates, calls --select/--fail")
        print("    5. Repeat until all components accepted")
        print("    6. python3 scripts/run_episode.py --scene")


if __name__ == "__main__":
    main()
