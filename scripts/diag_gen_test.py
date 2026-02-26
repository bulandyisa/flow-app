#!/usr/bin/env python3
"""Diagnostic: test fixed click_generate and gallery detection."""

import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / '.session'
FLOW_PROJECT_URL = 'https://labs.google/fx/ru/tools/flow/project/38f939b2-1f84-4503-8a12-09fc19e4c4a4'
SCREENSHOT_DIR = PROJECT_ROOT / 'output' / 'screenshots'
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def get_generated_image_urls(page):
    """Get all generated image URLs (new method: filter by alt text)."""
    return page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('img').forEach(el => {
            const alt = (el.alt || '').trim();
            if (el.src && el.getBoundingClientRect().width > 100 &&
                (alt === 'Сгенерированное изображение' || alt === 'Generated image')) {
                results.push(el.src);
            }
        });
        return results;
    }""")


def scroll_chat_to_bottom(page):
    """Scroll chat container to bottom."""
    page.evaluate("""() => {
        const els = document.querySelectorAll('*');
        for (const el of els) {
            if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                const rect = el.getBoundingClientRect();
                if (rect.x < 400 && rect.width > 200) {
                    el.scrollTop = el.scrollHeight;
                    return true;
                }
            }
        }
        return false;
    }""")


def main():
    print("Generation test with fixed click_generate...")

    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            str(SESSION_DIR),
            headless=False,
            viewport={'width': 1440, 'height': 900},
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--disable-background-timer-throttling',
            ]
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        print(f"\nNavigating to: {FLOW_PROJECT_URL}")
        page.goto(FLOW_PROJECT_URL, timeout=30000, wait_until='domcontentloaded')
        time.sleep(5)

        # Dismiss popups
        for _ in range(3):
            for sel in ['button:has-text("Закрыть")', 'button:has-text("Close")', 'button:has-text("OK")', 'button:has-text("Понятно")']:
                try:
                    btn = page.query_selector(sel)
                    if btn:
                        btn.click()
                        time.sleep(0.5)
                except:
                    pass

        page.wait_for_selector('[role="textbox"], [contenteditable="true"]', timeout=15000)
        time.sleep(2)

        # Setup: Image mode, x4, Nano Banana Pro
        chip = page.query_selector('button:has-text("Nano Banana")') or \
               page.query_selector('button:has-text("Imagen")') or \
               page.query_selector('button:has-text("Veo")')
        if chip:
            chip.click()
            time.sleep(1)
            # Image mode
            page.evaluate("""() => {
                const tabs = document.querySelectorAll('button[role="tab"]');
                for (const tab of tabs) {
                    if (tab.textContent.includes('Image')) { tab.click(); break; }
                }
            }""")
            time.sleep(0.5)
            # x4
            page.evaluate("""() => {
                const tabs = document.querySelectorAll('button[role="tab"]');
                for (const tab of tabs) {
                    if (tab.textContent.trim() === 'x4') { tab.click(); break; }
                }
            }""")
            time.sleep(0.5)
            page.keyboard.press('Escape')
            time.sleep(1)
            print("  Settings: Image mode, x4")

        # Type prompt
        field = page.query_selector('[role="textbox"]') or page.query_selector('[contenteditable="true"]')
        if field:
            field.click()
            time.sleep(0.3)
            page.keyboard.press('Meta+a')
            time.sleep(0.2)
            page.keyboard.press('Delete')
            time.sleep(0.3)
            prompt = "A cute 3D Pixar-style cartoon cat sitting on a windowsill, watching a butterfly outside. Warm sunlight, cinematic lighting, soft ambient occlusion."
            page.keyboard.type(prompt, delay=15)
            time.sleep(0.5)
            print(f"  Typed prompt: {prompt[:60]}...")

        # Take snapshot BEFORE generation
        before_urls = set(get_generated_image_urls(page))
        print(f"\n  Generated images BEFORE: {len(before_urls)}")
        page.screenshot(path=str(SCREENSHOT_DIR / 'diag3_before.png'))

        # CLICK GENERATE — using fixed method (Playwright native click, prioritize arrow_forward)
        print("\n  Clicking generate button...")

        # Priority 1: arrow_forward
        gen_btn = page.query_selector('button:has-text("arrow_forward")')
        if gen_btn:
            box = gen_btn.bounding_box()
            if box and box['width'] > 0:
                gen_btn.click()
                print(f"  ✓ Clicked 'arrow_forward' button at ({box['x']:.0f}, {box['y']:.0f})")
            else:
                print("  arrow_forward button found but not visible")
                gen_btn = None

        if not gen_btn:
            # Priority 2: Генерировать
            gen_btn = page.query_selector('button:has-text("Генерировать")')
            if gen_btn:
                gen_btn.click()
                print("  ✓ Clicked 'Генерировать' button")

        if not gen_btn:
            print("  ERROR: No generate button found!")
            browser.close()
            return

        time.sleep(2)
        page.screenshot(path=str(SCREENSHOT_DIR / 'diag3_after_click.png'))

        # POLL for new images
        print("\n=== Polling for new generated images ===")
        start_time = time.time()

        while time.time() - start_time < 240:  # 4 minutes max
            time.sleep(5)
            elapsed = int(time.time() - start_time)

            # Scroll to bottom to see new results
            scroll_chat_to_bottom(page)
            time.sleep(0.5)

            current_urls = set(get_generated_image_urls(page))
            new_urls = current_urls - before_urls
            print(f"  [{elapsed:3d}s] generated imgs: {len(current_urls)} (new: {len(new_urls)})")

            if new_urls:
                print(f"  ★ FOUND {len(new_urls)} NEW GENERATED IMAGES!")
                for u in new_urls:
                    print(f"    {u[:100]}")
                page.screenshot(path=str(SCREENSHOT_DIR / f'diag3_new_{elapsed}s.png'))

                if len(new_urls) >= 4:
                    print("  All 4 variants found!")
                    break

            # Take periodic screenshots
            if elapsed in (5, 15, 30, 60, 120):
                page.screenshot(path=str(SCREENSHOT_DIR / f'diag3_poll_{elapsed}s.png'))

            # Check for errors
            if elapsed >= 15:
                error = page.evaluate("""() => {
                    const body = (document.body.textContent || '').substring(0, 2000);
                    if (body.includes('Не удалось сгенерировать')) return 'content_filter';
                    if (body.includes('Что-то пошло не так')) return 'server_error';
                    return null;
                }""")
                if error:
                    print(f"  ERROR: {error}")
                    page.screenshot(path=str(SCREENSHOT_DIR / f'diag3_error_{elapsed}s.png'))
                    break

        # Final state
        page.screenshot(path=str(SCREENSHOT_DIR / 'diag3_final.png'))
        final_urls = set(get_generated_image_urls(page))
        total_new = final_urls - before_urls
        print(f"\n  FINAL: {len(total_new)} new generated images")
        print(f"  Total generated images: {len(final_urls)}")

        time.sleep(2)
        browser.close()
        print("\nDone!")


if __name__ == '__main__':
    main()
