#!/usr/bin/env python3
"""Generate a location reference image via Flow NB Pro.

NB Pro generates 4 variants in a single API call (batchGenerateImages).
This script runs ONE generation and downloads all 4 results.

Uses Playwright's built-in Chromium (not system Chrome) so it can run
in parallel with the main bot that uses channel='chrome'.

Usage:
    venv/bin/python3 scripts/gen_location.py --account 3 \
        --prompt "3D Pixar-style render of a sunlit park..." \
        --output локации_hq/loc_park_trees.jpg
"""
import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flow_bot_v2 import (
    ACCOUNTS, ensure_project, wait_for_flow_ready,
    _ensure_chat_view, dismiss_popups, switch_mode, set_image_model,
    set_orientation, clear_prompt, fill_prompt, click_generate,
    poll_generation, NbNetworkCapture, _scroll_chat_bottom, _count_errors,
)


def main():
    parser = argparse.ArgumentParser(description='Generate location reference image')
    parser.add_argument('--account', type=int, required=True)
    parser.add_argument('--login', action='store_true', help='Open browser for manual login')
    parser.add_argument('--prompt', type=str, default=None)
    parser.add_argument('--output', type=str, default=None)
    parser.add_argument('--project', type=str, default=None)
    args = parser.parse_args()

    acct = ACCOUNTS[args.account - 1]
    session_dir = acct['session_dir']
    session_dir.mkdir(parents=True, exist_ok=True)

    # Remove stale lock files
    for f in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'):
        p = session_dir / f
        if p.exists():
            p.unlink()

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        vp_w = 1440 + random.randint(-20, 20)
        vp_h = 900 + random.randint(-15, 15)
        print(f'  Launching Chromium (builtin), session: {session_dir.name}, viewport: {vp_w}x{vp_h}')
        ctx = pw.chromium.launch_persistent_context(
            str(session_dir),
            headless=False,
            viewport={'width': vp_w, 'height': vp_h},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        if args.login:
            page.goto('https://myaccount.google.com/')
            print('  Browser open. Log in and close the window when ready.')
            page.wait_for_event('close', timeout=0)
            print('  Session saved!')
            ctx.close()
            return

        if not args.prompt or not args.output:
            print('ERROR: --prompt and --output required for generation')
            ctx.close()
            return

        ensure_project(page, project_id=args.project)
        wait_for_flow_ready(page)
        _ensure_chat_view(page)
        dismiss_popups(page)
        switch_mode(page, 'Создать изображение')
        set_image_model(page, 'Nano Banana Pro')
        set_orientation(page, 'horizontal')

        output_dir = Path(args.output).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(args.output).stem
        suffix = Path(args.output).suffix or '.jpg'

        # Start network capture
        capture = NbNetworkCapture()
        capture.start(page)

        # Single generation = 4 variants from NB Pro
        clear_prompt(page)
        fill_prompt(page, args.prompt)
        _scroll_chat_bottom(page)
        time.sleep(1)
        errors_before = _count_errors(page)
        click_generate(page)
        result = poll_generation(page, errors_before=errors_before)

        if result == 'success':
            # Download all captured images
            import requests
            for i, img in enumerate(capture.images):
                fife_url = img.get('url')
                if not fife_url:
                    continue
                dest = output_dir / f'{stem}_{i+1}{suffix}'
                resp = requests.get(fife_url, timeout=30)
                if resp.ok:
                    dest.write_bytes(resp.content)
                    print(f'  Saved: {dest} ({len(resp.content)} bytes)')
                else:
                    print(f'  Download failed: {dest.name} HTTP {resp.status_code}')
            print(f'\nDone: {len(capture.images)} variants captured.')
        else:
            print(f'  Generation failed: {result}')

        capture.stop(page)
        ctx.close()


if __name__ == '__main__':
    main()
