"""Test VEO video generation in the same project where photos were generated."""
import sys, time
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from pathlib import Path
from flow_bot_v2 import (
    launch_browser, ensure_project, wait_for_flow_ready,
    switch_mode, set_variant_count, set_orientation,
    upload_frame_for_veo, clear_veo_frame_slots,
    clear_prompt, fill_prompt, click_generate, poll_generation,
    download_last_video, _count_errors,
    human_delay, human_delay_long, take_screenshot, dismiss_popups,
    sanitize_prompt, GENERATION_TIMEOUT,
)
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def main():
    # Use two generated first-frame variants as first/last frames for VEO
    first_frame = PROJECT_ROOT / 'output' / 'review' / 'S01_A' / 'nb_first' / 'attempt_1' / 'prompt_a' / 'variant_1.png'
    last_frame = PROJECT_ROOT / 'output' / 'review' / 'S01_A' / 'nb_first' / 'attempt_1' / 'prompt_a' / 'variant_2.png'

    if not first_frame.exists() or not last_frame.exists():
        print(f'ERROR: Frame files not found')
        print(f'  first: {first_frame} exists={first_frame.exists()}')
        print(f'  last: {last_frame} exists={last_frame.exists()}')
        sys.exit(1)

    # Simple VEO test prompt
    veo_prompt = sanitize_prompt(
        "3D Pixar-style animation, family-friendly. "
        "A boy in a red-and-white striped shirt and red cap sits at a kitchen table. "
        "He reaches across the table with an excited expression. "
        "A woman in a hijab sits across from him, smiling warmly. "
        "Warm kitchen lighting, gentle camera movement, smooth animation."
    )

    with sync_playwright() as pw:
        ctx = launch_browser(pw, account=0)
        page = ctx.pages[0]

        # Enter the SAME project where photos were generated (helper1)
        # Navigate directly to the project URL instead of ensure_project()
        old_project = 'https://labs.google/fx/ru/tools/flow/project/30ef5dbf-fe01-44af-8a3e-63e36b476730'
        page.goto(old_project, timeout=120000, wait_until='domcontentloaded')
        wait_for_flow_ready(page)

        print('\n' + '='*60)
        print('  TEST VEO VIDEO GENERATION')
        print('='*60)

        # Step 1: Switch to Video + Frames mode
        print('\n=== Step 1: Switch to Video + Frames ===')
        switch_mode(page, 'Видео по кадрам')
        human_delay_long(2, 4)
        take_screenshot(page, 'test_veo_frames_mode')

        # Step 2: Set orientation and x4
        print('\n=== Step 2: Settings ===')
        set_orientation(page, 'horizontal')
        set_variant_count(page, 4)

        # Step 3: Upload first and last frames
        print('\n=== Step 3: Upload frames ===')
        clear_veo_frame_slots(page)
        ok1 = upload_frame_for_veo(page, first_frame, 0)
        ok2 = upload_frame_for_veo(page, last_frame, 1)
        print(f'  First frame: {"OK" if ok1 else "FAILED"}')
        print(f'  Last frame: {"OK" if ok2 else "FAILED"}')
        take_screenshot(page, 'test_veo_frames_uploaded')

        if not ok1:
            print('ERROR: Could not upload first frame')
            ctx.close()
            sys.exit(1)

        # Step 4: Fill prompt and generate
        print('\n=== Step 4: Generate video ===')
        clear_prompt(page)
        fill_prompt(page, veo_prompt)
        take_screenshot(page, 'test_veo_prompt_filled')

        errors_before = _count_errors(page)
        click_generate(page)
        result = poll_generation(page, errors_before=errors_before, timeout_sec=GENERATION_TIMEOUT, media='video')
        print(f'  Generation result: {result}')

        if result == 'success':
            # Step 5: Download video
            print('\n=== Step 5: Download video ===')
            dest = PROJECT_ROOT / 'output' / 'review' / 'test_veo' / 'variant_1.mp4'
            dest.parent.mkdir(parents=True, exist_ok=True)
            saved = download_last_video(page, dest)
            if saved:
                size = dest.stat().st_size
                print(f'  SUCCESS: {dest.name} ({size} bytes)')
            else:
                print('  FAILED: Could not download video')
            take_screenshot(page, 'test_veo_done')
        else:
            take_screenshot(page, 'test_veo_failed')
            print(f'  FAILED: {result}')

        print('\n=== Test complete ===')
        ctx.close()

if __name__ == '__main__':
    main()
