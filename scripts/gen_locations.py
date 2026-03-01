#!/usr/bin/env python3
"""Generate missing location reference images via Flow bot.

Generates 4 variants per location using NB Pro x4 mode.
Results saved to output/review/locations/{loc_name}/variant_1..4.png

Usage:
  venv/bin/python3 scripts/gen_locations.py --account 1
  venv/bin/python3 scripts/gen_locations.py --account 3 --chromium --only loc_bridge_stream.jpg
  venv/bin/python3 scripts/gen_locations.py --account 1 --subset 1  # first half
  venv/bin/python3 scripts/gen_locations.py --account 3 --subset 2  # second half
"""
import json
import sys
import time
import random
import shutil
from pathlib import Path

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent))
import flow_bot_v2
from flow_bot_v2 import (
    launch_browser, ensure_project, wait_for_flow_ready,
    switch_mode, set_image_model, set_orientation,
    _ensure_chat_view, dismiss_popups,
    generate_nb_batch, human_pause_between_generations,
    ACCOUNTS,
)

LOCATIONS_DIR = Path(__file__).parent.parent / 'локации_hq'
REVIEW_DIR = Path(__file__).parent.parent / 'output' / 'review' / 'locations'

# Prompts for missing locations — 3D Pixar-style, no characters, just environments
LOCATION_PROMPTS = {
    'loc_bridge_stream.jpg': (
        "A small weathered stone bridge over a narrow stream in a rural area. "
        "Clear shallow water flowing over rounded stones, green vegetation on the banks. "
        "The bridge has low stone railings, old and moss-covered. "
        "Middle Eastern countryside setting. Bright afternoon sunlight, water reflections. "
        "Wide establishing shot, eye-level. No people, no characters. "
        "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
    ),
    'loc_basement_dark.jpg': (
        "A dark dusty basement of an old building. Exposed brick walls, low ceiling, "
        "cobwebs in corners, dusty shelves, a few old cardboard boxes stacked against the wall. "
        "Single dim light source from above casting dramatic shadows. "
        "Atmospheric, slightly eerie but not scary. "
        "Medium shot, slightly low angle. No people, no characters. "
        "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
    ),
    'loc_night_street.jpg': (
        "An empty residential street at night in a small Middle Eastern town. "
        "Sparse amber streetlamps casting pools of warm light on the pavement. "
        "Low apartment buildings on both sides, dark windows. "
        "The street stretches into darkness. Quiet, atmospheric, film noir mood. "
        "Wide shot, low angle. No people, no characters. "
        "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
    ),
    'loc_wasteland_warehouse.jpg': (
        "An industrial wasteland at the edge of a small town. A large corrugated metal warehouse "
        "with rusty rolling gates, a white delivery van parked in front. "
        "Dry dirt ground, scattered debris, a low crumbling wall in the foreground. "
        "Late afternoon harsh sunlight, long shadows. "
        "Wide establishing shot, eye-level. No people, no characters. "
        "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
    ),
    'loc_wasteland_open.jpg': (
        "An open wasteland area near an industrial zone. Dry sandy ground, "
        "scattered rocks and rubble, a few scraggly bushes. "
        "In the distance, warehouse buildings and a chain-link fence. "
        "Bright afternoon sun, harsh shadows, desolate atmosphere. "
        "Wide shot, eye-level. No people, no characters. "
        "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
    ),
    'loc_alley_dumpsters.jpg': (
        "A narrow back alley between two buildings. Large green dumpsters against one wall, "
        "scattered boxes and debris. Concrete walls, pipes running along the ceiling. "
        "A dim light at the far end of the alley. Urban, gritty but stylized. "
        "Medium shot, eye-level. No people, no characters. "
        "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
    ),
    'loc_tower_approach.jpg': (
        "A tall concrete water tower rising above a scrubby wasteland. "
        "A dirt path leads to the base of the tower. Metal ladder visible on the side. "
        "The tower is old but solid, cylindrical with a wider tank at the top. "
        "Bright morning sunlight, clear blue sky, a few clouds. "
        "Wide shot, low angle looking up. No people, no characters. "
        "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
    ),
    'loc_tower_ladder.jpg': (
        "Close-up of a metal ladder on the side of a concrete water tower, "
        "looking straight up along the rungs. Rust and peeling paint on the metal. "
        "Blue sky visible beyond the top. Vertigo-inducing perspective. "
        "Close-up, extreme low angle looking directly up. No people, no characters. "
        "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
    ),
    'loc_tower_top_view.jpg': (
        "Panoramic view from the top of a water tower looking down over a small Middle Eastern town. "
        "Flat rooftops with satellite dishes, narrow streets, trees scattered between buildings, "
        "a minaret visible in the distance. Concrete platform with a metal railing in the foreground. "
        "Bright morning sunlight, vast open sky, sense of height. "
        "Wide panoramic shot, high angle looking down and out. No people, no characters. "
        "No text, no watermarks. 3D Pixar-style, family-friendly, cinematic."
    ),
}

# Split into two subsets for parallel generation on two bots
SUBSET_1 = ['loc_bridge_stream.jpg', 'loc_basement_dark.jpg', 'loc_night_street.jpg',
            'loc_wasteland_warehouse.jpg', 'loc_wasteland_open.jpg']
SUBSET_2 = ['loc_alley_dumpsters.jpg', 'loc_tower_approach.jpg',
            'loc_tower_ladder.jpg', 'loc_tower_top_view.jpg']


def generate_location_batch(page, name, prompt, dest_dir, max_retries=3):
    """Generate 4 variants for a single location using NB x4 mode, with retries."""
    final_dest = LOCATIONS_DIR / name
    if final_dest.exists():
        print(f'  SKIP {name} — already exists in локации_hq/')
        return True

    print(f'\n{"="*60}')
    print(f'  LOCATION: {name}')
    print(f'{"="*60}')

    retry_pauses = [45, 60, 90]

    for attempt in range(1, max_retries + 1):
        _ensure_chat_view(page)
        dismiss_popups(page)
        switch_mode(page, 'Создать изображение')
        set_image_model(page, 'Nano Banana Pro')
        set_orientation(page, 'horizontal')

        loc_review_dir = dest_dir / name.replace('.jpg', '')
        saved = generate_nb_batch(
            page,
            clip_id=f'LOC_{name.replace(".jpg", "")}',
            component='location',
            prompt=prompt,
            attempt=attempt,
            ingredients=[],
            dest_dir=loc_review_dir,
            num_variants=4,
        )

        if saved:
            print(f'  Generated {len(saved)} variants for {name}')
            return True
        else:
            if attempt < max_retries:
                pause = retry_pauses[attempt - 1]
                print(f'  RETRY {attempt}/{max_retries} — waiting {pause}s...')
                time.sleep(pause)
            else:
                print(f'  FAILED to generate {name} after {max_retries} attempts')
                return False
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate missing location images')
    parser.add_argument('--account', type=int, default=1, help='Bot account (1-4)')
    parser.add_argument('--chromium', action='store_true', help='Use builtin Chromium')
    parser.add_argument('--only', type=str, default=None, help='Generate only this location filename')
    parser.add_argument('--subset', type=int, default=0, choices=[0, 1, 2],
                        help='0=all, 1=first half, 2=second half')
    args = parser.parse_args()

    flow_bot_v2._current_account_idx = args.account - 1

    # Determine which locations to generate
    if args.only:
        locations = {k: v for k, v in LOCATION_PROMPTS.items() if k == args.only}
    elif args.subset == 1:
        locations = {k: LOCATION_PROMPTS[k] for k in SUBSET_1}
    elif args.subset == 2:
        locations = {k: LOCATION_PROMPTS[k] for k in SUBSET_2}
    else:
        locations = LOCATION_PROMPTS

    if not locations:
        print('No locations to generate!')
        return

    print(f'Generating {len(locations)} locations...')
    for n in locations:
        print(f'  - {n}')

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        ctx = launch_browser(pw, account=args.account - 1,
                             use_builtin_chromium=args.chromium)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # Console logging for debugging
        def _on_console(msg):
            if msg.type in ('error', 'warning'):
                text = msg.text[:300]
                print(f'  [CONSOLE {msg.type.upper()}] {text}')
        page.on('console', _on_console)

        print('  Page ready, navigating to project...')
        ensure_project(page)
        wait_for_flow_ready(page)
        dismiss_popups(page)
        print(f'  Page URL: {page.url[:90]}')
        print(f'  Flow workspace ready.\n')

        generated = 0
        failed = 0
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)

        loc_names = list(locations.keys())
        for i, name in enumerate(loc_names):
            prompt = locations[name]
            ok = generate_location_batch(page, name, prompt, REVIEW_DIR)
            if ok:
                generated += 1
            else:
                failed += 1
            if i < len(loc_names) - 1:
                human_pause_between_generations()

        print(f'\n{"="*60}')
        print(f'  Locations: {generated} generated, {failed} failed')
        print(f'  Review dir: {REVIEW_DIR}')
        print(f'  Final dir: {LOCATIONS_DIR}')
        print(f'{"="*60}')

        ctx.close()


if __name__ == '__main__':
    main()
