#!/usr/bin/env python3
"""
Generate output/status.json from review manifests and local files.
Run after each generation session, before committing to Git.

Usage:
    venv/bin/python3 scripts/update_status.py
"""

import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PROMPTS_FILE = BASE_DIR / "output" / "prompts" / "all_prompts.json"
REVIEW_DIR = BASE_DIR / "output" / "review"
FRAMES_DIR = BASE_DIR / "output" / "frames"
CLIPS_DIR = BASE_DIR / "output" / "clips"
STATUS_FILE = BASE_DIR / "output" / "status.json"


def main():
    with open(PROMPTS_FILE, encoding="utf-8") as f:
        clips = json.load(f)

    result = {}

    for clip in clips:
        cid = clip["clip_id"]
        manifest_path = REVIEW_DIR / cid / "manifest.json"

        nb_first = "pending"
        nb_last = "pending"
        veo = "pending"

        # Read from manifest if exists
        if manifest_path.exists():
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            components = manifest.get("components", {})
            nb_first = components.get("nb_first", {}).get("status", "pending")
            nb_last = components.get("nb_last", {}).get("status", "pending")
            veo = components.get("veo", {}).get("status", "pending")

        # Cross-check with actual files on disk
        has_first = (FRAMES_DIR / f"{cid}_first.png").exists()
        has_last = (FRAMES_DIR / f"{cid}_last.png").exists()
        has_clip = (CLIPS_DIR / f"{cid}_clip.mp4").exists()

        # If file exists but manifest says pending, upgrade to accepted
        if has_first and nb_first == "pending":
            nb_first = "accepted"
        if has_last and nb_last == "pending":
            nb_last = "accepted"
        if has_clip and veo == "pending":
            veo = "accepted"

        # Overall status
        all_accepted = (nb_first == "accepted" and nb_last == "accepted" and veo == "accepted")
        any_accepted = (nb_first == "accepted" or nb_last == "accepted" or veo == "accepted")

        if all_accepted:
            status = "done"
        elif any_accepted:
            status = "partial"
        else:
            status = "todo"

        result[cid] = {
            "nb_first": nb_first,
            "nb_last": nb_last,
            "veo": veo,
            "status": status,
        }

    output = {
        "last_updated": datetime.now().isoformat(timespec="seconds"),
        "clips": result,
    }

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Print summary
    statuses = [v["status"] for v in result.values()]
    print(f"status.json updated: {statuses.count('done')} done, "
          f"{statuses.count('partial')} partial, "
          f"{statuses.count('todo')} todo")
    for cid, info in result.items():
        icon = {"done": "🟢", "partial": "🟡", "todo": "🔴"}[info["status"]]
        print(f"  {icon} {cid}: first={info['nb_first']}, last={info['nb_last']}, veo={info['veo']}")


if __name__ == "__main__":
    main()
