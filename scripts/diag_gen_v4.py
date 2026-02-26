#!/usr/bin/env python3
"""Diagnostic v4: test generation with NO scrolling during poll.

Key insights from v2/v3:
- New Flow UI uses VIRTUAL SCROLLING — elements outside viewport are removed from DOM
- Scrolling to bottom removes generated results from DOM
- Generated images appear as chat messages after the prompt
- During generation: gray placeholder divs appear
- After generation: img elements with alt="Сгенерированное изображение" replace them
- So we should NOT scroll, just poll for new img elements in current view
"""

import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / '.session'
FLOW_PROJECT_URL = 'https://labs.google/fx/ru/tools/flow/project/38f939b2-1f84-4503-8a12-09fc19e4c4a4'
SCREENSHOT_DIR = PROJECT_ROOT / 'output' / 'screenshots'
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def count_all_elements(page):
    """Count ALL img elements and other indicators."""
    return page.evaluate("""() => {
        const data = {};
        // Count generated images
        const imgs = [];
        document.querySelectorAll('img').forEach(el => {
            const alt = (el.alt || '').trim();
            const rect = el.getBoundingClientRect();
            if (el.src && rect.width > 50) {
                imgs.push({
                    alt: alt,
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                    y: Math.round(rect.y),
                    src: el.src.substring(0, 80)
                });
            }
        });
        data.imgs = imgs;
        data.total_imgs = imgs.length;
        data.generated = imgs.filter(i => i.alt === 'Сгенерированное изображение').length;

        // Count loading placeholders (divs with gray backgrounds, pulsing, etc.)
        let placeholders = 0;
        document.querySelectorAll('div, span').forEach(el => {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            const cls = (el.className || '');
            // Look for placeholder-like elements near the prompt
            if (rect.width > 200 && rect.height > 100 && rect.y > 50) {
                const bg = style.backgroundColor;
                if ((bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent' &&
                     !bg.includes('255') && rect.width < 800 && rect.height < 500) ||
                    cls.includes('pulse') || cls.includes('shimmer') || cls.includes('loading') ||
                    cls.includes('Pulse') || cls.includes('Shimmer') || cls.includes('Loading')) {
                    placeholders++;
                }
            }
        });
        data.placeholders = placeholders;

        // Check for visible progress/loading text
        const body = (document.body.textContent || '');
        data.has_generating_text = body.includes('Генерация') || body.includes('генерируем') ||
                                   body.includes('Generating') || body.includes('Создание');

        // Check prompt field state
        const field = document.querySelector('[role="textbox"]');
        data.prompt_field_empty = field ? (field.textContent || '').trim() === '' : null;

        // Links with download attribute (new UI may use <a> wrappers)
        let links = 0;
        document.querySelectorAll('a').forEach(a => {
            const cls = (a.className || '');
            const rect = a.getBoundingClientRect();
            if (rect.width > 100 && rect.height > 100 && a.href && a.href.includes('media')) {
                links++;
            }
        });
        data.media_links = links;

        return data;
    }""")


def main():
    print("Generation test v4 (no scrolling)...")

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
            for sel in ['button:has-text("Закрыть")', 'button:has-text("OK")', 'button:has-text("Понятно")']:
                try:
                    btn = page.query_selector(sel)
                    if btn:
                        btn.click()
                        time.sleep(0.5)
                except:
                    pass

        page.wait_for_selector('[role="textbox"], [contenteditable="true"]', timeout=15000)
        time.sleep(2)

        # Setup: Image mode, x4
        chip = page.query_selector('button:has-text("Nano Banana")') or \
               page.query_selector('button:has-text("Imagen")')
        if chip:
            chip.click()
            time.sleep(1)
            page.evaluate("""() => {
                const tabs = document.querySelectorAll('button[role="tab"]');
                for (const tab of tabs) {
                    if (tab.textContent.includes('Image')) { tab.click(); break; }
                }
            }""")
            time.sleep(0.3)
            page.evaluate("""() => {
                const tabs = document.querySelectorAll('button[role="tab"]');
                for (const tab of tabs) {
                    if (tab.textContent.trim() === 'x4') { tab.click(); break; }
                }
            }""")
            time.sleep(0.3)
            page.keyboard.press('Escape')
            time.sleep(1)

        # Type prompt
        field = page.query_selector('[role="textbox"]')
        if field:
            field.click()
            time.sleep(0.3)
            page.keyboard.press('Meta+a')
            page.keyboard.press('Delete')
            time.sleep(0.3)
            prompt = "A cute 3D Pixar-style cartoon orange tabby cat sitting on a windowsill, watching a butterfly outside. Warm golden sunlight, cinematic."
            page.keyboard.type(prompt, delay=15)
            time.sleep(0.5)

        # BEFORE snapshot
        before = count_all_elements(page)
        before_generated = before['generated']
        before_links = before['media_links']
        before_urls = set()
        for img in before['imgs']:
            if img['alt'] == 'Сгенерированное изображение':
                before_urls.add(img['src'])
        print(f"\n  BEFORE: {before_generated} generated imgs, {before_links} media links, {before['total_imgs']} total imgs")
        page.screenshot(path=str(SCREENSHOT_DIR / 'diag4_before.png'))

        # CLICK GENERATE
        gen_btn = page.query_selector('button:has-text("arrow_forward")')
        if gen_btn:
            gen_btn.click()
            print("  Clicked generate (arrow_forward)")
        else:
            print("  ERROR: arrow_forward not found!")
            browser.close()
            return

        # Wait 2 seconds then take screenshot to see placeholders
        time.sleep(2)
        page.screenshot(path=str(SCREENSHOT_DIR / 'diag4_placeholders.png'))

        # POLL WITHOUT SCROLLING
        print("\n=== Polling (NO scroll) ===")
        start_time = time.time()
        generation_complete = False

        while time.time() - start_time < 300:  # 5 min max
            time.sleep(5)
            elapsed = int(time.time() - start_time)

            state = count_all_elements(page)
            new_generated = state['generated'] - before_generated
            new_links = state['media_links'] - before_links

            status_parts = [
                f"[{elapsed:3d}s]",
                f"gen_imgs={state['generated']}(+{new_generated})",
                f"links={state['media_links']}(+{new_links})",
                f"total_imgs={state['total_imgs']}",
            ]
            if state['has_generating_text']:
                status_parts.append("GENERATING...")
            if state['prompt_field_empty']:
                status_parts.append("PROMPT_EMPTY")
            print(f"  {' '.join(status_parts)}")

            # Take screenshots at key moments
            if elapsed in (5, 10, 20, 30, 60, 90, 120):
                page.screenshot(path=str(SCREENSHOT_DIR / f'diag4_{elapsed}s.png'))

            # Check if generation completed
            if new_generated >= 4:
                print(f"\n  ★ SUCCESS! {new_generated} new generated images found at {elapsed}s!")
                generation_complete = True
                page.screenshot(path=str(SCREENSHOT_DIR / 'diag4_success.png'))

                # Dump all new images
                for img in state['imgs']:
                    if img['alt'] == 'Сгенерированное изображение' and img['src'] not in before_urls:
                        print(f"    NEW: y={img['y']} {img['w']}x{img['h']} src={img['src']}")
                break

            if new_generated > 0 and new_generated < 4:
                print(f"    Partial results: {new_generated} of 4 expected")

            # If prompt field emptied = generation submitted
            # If media links increased = generation completing
            if elapsed > 120 and new_generated == 0 and new_links == 0:
                print("    No changes after 2 min, maybe stuck. Screenshot...")
                page.screenshot(path=str(SCREENSHOT_DIR / f'diag4_stuck_{elapsed}s.png'))
                if elapsed > 180:
                    print("    Giving up.")
                    break

        # Final
        page.screenshot(path=str(SCREENSHOT_DIR / 'diag4_final.png'))
        final = count_all_elements(page)
        print(f"\n  FINAL STATE:")
        print(f"    Generated imgs: {final['generated']} (was {before_generated})")
        print(f"    Media links: {final['media_links']} (was {before_links})")
        print(f"    Total imgs: {final['total_imgs']}")
        print(f"    Prompt empty: {final['prompt_field_empty']}")

        if not generation_complete:
            # Try scrolling UP to find results
            print("\n  Scrolling UP to find results...")
            page.evaluate("""() => {
                const els = document.querySelectorAll('*');
                for (const el of els) {
                    if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                        const rect = el.getBoundingClientRect();
                        if (rect.x < 400 && rect.width > 200) {
                            // Scroll up by one viewport
                            el.scrollTop = Math.max(0, el.scrollTop - el.clientHeight);
                            return true;
                        }
                    }
                }
            }""")
            time.sleep(2)
            page.screenshot(path=str(SCREENSHOT_DIR / 'diag4_scroll_up.png'))
            after_scroll = count_all_elements(page)
            print(f"  After scroll up: {after_scroll['generated']} generated, {after_scroll['media_links']} links")

            # Dump all images after scroll
            for img in after_scroll['imgs']:
                if img['alt'] == 'Сгенерированное изображение':
                    in_before = '(old)' if img['src'] in before_urls else '(NEW!)'
                    print(f"    IMG: y={img['y']} {img['w']}x{img['h']} {in_before} src={img['src']}")

        browser.close()
        print("\nDone!")


if __name__ == '__main__':
    main()
