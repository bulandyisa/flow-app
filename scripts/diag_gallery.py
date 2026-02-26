#!/usr/bin/env python3
"""Diagnostic: dump all <img> elements before/after generation to understand gallery detection."""

import sys, time, json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / '.session'
FLOW_PROJECT_URL = 'https://labs.google/fx/ru/tools/flow/project/38f939b2-1f84-4503-8a12-09fc19e4c4a4'
SCREENSHOT_DIR = PROJECT_ROOT / 'output' / 'screenshots'
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def dump_all_imgs(page, label=""):
    """Dump ALL <img> elements with position, size, src."""
    imgs = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('img').forEach((el, i) => {
            const rect = el.getBoundingClientRect();
            results.push({
                index: i,
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                w: Math.round(rect.width),
                h: Math.round(rect.height),
                src: (el.src || '').substring(0, 120),
                alt: (el.alt || '').substring(0, 50),
                visible: rect.width > 0 && rect.height > 0
            });
        });
        return results;
    }""")
    print(f"\n=== ALL <img> elements ({label}) — {len(imgs)} total ===")
    for img in imgs:
        marker = ""
        if img['w'] > 100 and img['y'] > 100 and img['y'] < 800:
            marker = " ◀ MATCHES gallery filter"
        vis = "VIS" if img['visible'] else "HID"
        print(f"  [{img['index']:2d}] {vis} pos=({img['x']:4d},{img['y']:4d}) size={img['w']:4d}x{img['h']:4d}{marker}")
        print(f"       src={img['src']}")
        if img['alt']:
            print(f"       alt={img['alt']}")

    # Also count matching
    matching = [i for i in imgs if i['w'] > 100 and i['y'] > 100 and i['y'] < 800]
    print(f"\n  → {len(matching)} images match gallery filter (w>100, 100<y<800)")
    matching_urls = set(i['src'] for i in matching)
    return matching_urls


def main():
    print("Starting gallery diagnostic...")

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

        # Navigate to project
        print(f"\nNavigating to: {FLOW_PROJECT_URL}")
        page.goto(FLOW_PROJECT_URL, timeout=30000, wait_until='domcontentloaded')
        time.sleep(5)

        # Dismiss popups
        for _ in range(3):
            close_btns = page.query_selector_all('button:has-text("Закрыть"), button:has-text("Close"), button:has-text("OK"), button:has-text("Понятно")')
            for btn in close_btns:
                try:
                    btn.click()
                    time.sleep(0.5)
                except:
                    pass
            time.sleep(0.5)

        # Wait for prompt field
        try:
            page.wait_for_selector('[role="textbox"], [contenteditable="true"]', timeout=15000)
            print("Prompt field found!")
        except:
            print("WARNING: Prompt field not found")

        time.sleep(2)

        # Screenshot initial state
        page.screenshot(path=str(SCREENSHOT_DIR / 'diag_initial.png'))

        # STEP 1: Dump all images in initial state
        urls_before = dump_all_imgs(page, "INITIAL STATE")

        # STEP 2: Check gallery tabs
        print("\n=== Gallery tabs ===")
        tabs = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button[role="radio"], button[role="tab"]').forEach(btn => {
                const text = (btn.textContent || '').trim();
                const rect = btn.getBoundingClientRect();
                const selected = btn.getAttribute('aria-selected') || btn.getAttribute('aria-checked');
                if (rect.y > 50 && rect.y < 200) {
                    results.push({text: text.substring(0, 40), y: Math.round(rect.y), selected: selected});
                }
            });
            return results;
        }""")
        for t in tabs:
            print(f"  Tab: '{t['text']}' y={t['y']} selected={t.get('selected')}")

        # STEP 3: Click Изображения tab if visible
        img_tab = page.query_selector('button[role="radio"]:has-text("Изображения")')
        if img_tab:
            img_tab.click()
            time.sleep(2)
            print("\nClicked 'Изображения' tab")
            urls_after_tab = dump_all_imgs(page, "AFTER CLICKING IMAGES TAB")

        # STEP 4: Open settings popup and set x4
        print("\n=== Setting up generation (Image mode, x4, Nano Banana Pro) ===")
        chip = page.query_selector('button:has-text("Nano Banana")') or \
               page.query_selector('button:has-text("Imagen")') or \
               page.query_selector('button:has-text("Veo")')
        if chip:
            chip.click()
            time.sleep(1)

            # Set Image mode
            page.evaluate("""() => {
                const tabs = document.querySelectorAll('button[role="tab"]');
                for (const tab of tabs) {
                    if (tab.textContent.includes('Image')) { tab.click(); break; }
                }
            }""")
            time.sleep(0.5)

            # Set x4
            page.evaluate("""() => {
                const tabs = document.querySelectorAll('button[role="tab"]');
                for (const tab of tabs) {
                    if (tab.textContent.trim() === 'x4') { tab.click(); break; }
                }
            }""")
            time.sleep(0.5)

            # Verify what's selected
            selected = page.evaluate("""() => {
                const tabs = document.querySelectorAll('button[role="tab"]');
                const result = [];
                for (const tab of tabs) {
                    if (tab.getAttribute('aria-selected') === 'true') {
                        result.push(tab.textContent.trim().substring(0, 20));
                    }
                }
                return result;
            }""")
            print(f"  Selected tabs: {selected}")

            page.keyboard.press('Escape')
            time.sleep(1)

        # STEP 5: Fill a test prompt and generate
        field = page.query_selector('[role="textbox"]') or page.query_selector('[contenteditable="true"]')
        if field:
            field.click()
            time.sleep(0.3)
            # Clear
            page.keyboard.press('Meta+a')
            time.sleep(0.2)
            page.keyboard.press('Delete')
            time.sleep(0.3)

            test_prompt = "A cute cartoon cat sitting on a windowsill, looking at a butterfly. 3D Pixar-style animation, warm sunlight, cinematic."
            page.keyboard.type(test_prompt, delay=15)
            time.sleep(0.5)
            print(f"\n  Typed prompt: {test_prompt[:60]}...")

        # Take snapshot BEFORE generation
        urls_before_gen = dump_all_imgs(page, "BEFORE GENERATION")
        page.screenshot(path=str(SCREENSHOT_DIR / 'diag_before_gen.png'))

        # Click generate
        clicked = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = (btn.textContent || '').trim();
                const rect = btn.getBoundingClientRect();
                if ((text.includes('arrow_forward') || text === '→' ||
                     text.includes('Создать') || text.includes('Генерировать') ||
                     text.includes('Generate')) &&
                    rect.width > 0 && rect.height > 0) {
                    btn.click();
                    return text.substring(0, 30);
                }
            }
            return null;
        }""")
        print(f"\n  Clicked generate button: '{clicked}'")

        # STEP 6: Poll every 5 seconds for 3 minutes, dump images each time
        print("\n=== Polling gallery for new images ===")
        start_time = time.time()
        poll_count = 0
        found_new = False

        while time.time() - start_time < 180:  # 3 minute max
            time.sleep(5)
            poll_count += 1
            elapsed = int(time.time() - start_time)

            current_urls = dump_all_imgs(page, f"POLL #{poll_count} ({elapsed}s)")
            new_urls = current_urls - urls_before_gen

            if new_urls:
                print(f"\n  ★★★ FOUND {len(new_urls)} NEW URLS at {elapsed}s ★★★")
                for u in new_urls:
                    print(f"    NEW: {u}")

                page.screenshot(path=str(SCREENSHOT_DIR / f'diag_new_found_{elapsed}s.png'))

                if not found_new:
                    found_new = True
                    print("  Continuing to poll for more variants...")

                # Keep polling for a bit to see if more variants appear
                if len(new_urls) >= 4:
                    print(f"  Found {len(new_urls)} variants — looks complete!")
                    break
            else:
                print(f"  No new URLs at {elapsed}s")

            # Check for errors
            error = page.evaluate("""() => {
                const els = document.querySelectorAll('*');
                for (const el of els) {
                    const text = (el.textContent || '').trim();
                    if ((text.includes('Не удалось') || text.includes('Произошла ошибка') ||
                         text.includes('Что-то пошло')) && text.length < 200) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 100) return text.substring(0, 100);
                    }
                }
                return null;
            }""")
            if error:
                print(f"  ERROR: {error}")
                page.screenshot(path=str(SCREENSHOT_DIR / f'diag_error_{elapsed}s.png'))
                break

        # Final state
        urls_final = dump_all_imgs(page, "FINAL STATE")
        page.screenshot(path=str(SCREENSHOT_DIR / 'diag_final.png'))

        total_new = urls_final - urls_before_gen
        print(f"\n{'='*60}")
        print(f"  SUMMARY: {len(total_new)} new URLs detected")
        print(f"  Before generation: {len(urls_before_gen)} matching images")
        print(f"  After generation: {len(urls_final)} matching images")
        for u in total_new:
            print(f"    {u}")
        print(f"{'='*60}")

        time.sleep(2)
        browser.close()
        print("\nDone!")


if __name__ == '__main__':
    main()
