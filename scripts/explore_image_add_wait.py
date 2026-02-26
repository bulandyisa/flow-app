#!/usr/bin/env python3
"""Click + in image mode and wait for the ingredient panel to load."""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
EXPLORE_DIR = PROJECT_ROOT / "output" / "explore"
AUTO_PROJECT_URL = "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869"


def screenshot(page, name):
    path = EXPLORE_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  Screenshot: {path.name}")


def check_for_upload(page):
    """Check if 'Загрузить' button or upload elements appeared."""
    result = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('*').forEach(el => {
            const text = (el.textContent || '').trim();
            if (text === 'Загрузить' || text.startsWith('uploadЗагрузить') ||
                text === 'upload' || text.includes('Загрузить')) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 20 && rect.height > 20 && el.tagName !== 'HTML' && el.tagName !== 'BODY') {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        text: text.substring(0, 100),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            }
        });
        // Also check for role=menu
        document.querySelectorAll('[role="menu"]').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0) {
                results.push({
                    tag: 'menu',
                    text: (el.textContent || '').trim().substring(0, 100),
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                });
            }
        });
        return results;
    }""")
    return result


def main():
    EXPLORE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()

        print("Opening project...")
        page.goto(AUTO_PROJECT_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_selector("textarea", timeout=60000)
        time.sleep(8)

        # Ensure image mode
        combo = page.query_selector('button[role="combobox"]')
        if combo:
            t = combo.text_content() or ""
            if "Создать изображение" not in t:
                combo.click()
                time.sleep(1)
                opt = page.query_selector('div[role="option"]:has-text("Создать изображение")')
                if opt:
                    opt.click()
                    time.sleep(2)

        # Click +
        print("\n=== Clicking + ===")
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                if (btn.textContent.trim() === 'add' && rect.y > 700) {
                    btn.click();
                    return;
                }
            }
        }""")

        # Poll for up to 60 seconds for upload panel to appear
        print("  Waiting for ingredient panel to load...")
        for sec in range(60):
            time.sleep(1)
            elements = check_for_upload(page)
            if elements:
                print(f"\n  FOUND at {sec+1}s!")
                for el in elements:
                    print(f"    [{el['tag']}] ({el['x']},{el['y']}) {el['w']}x{el['h']}: {el['text'][:60]}")
                screenshot(page, f"75_ingredient_panel_{sec+1}s")
                break
            if (sec + 1) % 10 == 0:
                print(f"  ...{sec+1}s")
                screenshot(page, f"75_waiting_{sec+1}s")
        else:
            print("  Panel did not appear in 60s.")
            screenshot(page, "75_timeout")

            # Try approach 2: reload page, click + again
            print("\n=== Reloading page and trying again ===")
            page.reload(wait_until="domcontentloaded")
            page.wait_for_selector("textarea", timeout=60000)
            time.sleep(8)

            # Click + again
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    const rect = btn.getBoundingClientRect();
                    if (btn.textContent.trim() === 'add' && rect.y > 700) {
                        btn.click();
                        return;
                    }
                }
            }""")

            print("  Waiting after reload...")
            for sec in range(60):
                time.sleep(1)
                elements = check_for_upload(page)
                if elements:
                    print(f"\n  FOUND at {sec+1}s after reload!")
                    for el in elements:
                        print(f"    [{el['tag']}] ({el['x']},{el['y']}) {el['w']}x{el['h']}: {el['text'][:60]}")
                    screenshot(page, f"76_ingredient_panel_reload_{sec+1}s")
                    break
                if (sec + 1) % 10 == 0:
                    print(f"  ...{sec+1}s")
            else:
                print("  Still no panel after reload.")
                screenshot(page, "76_timeout_reload")

        # If we found the panel, dump all elements
        elements = check_for_upload(page)
        if elements:
            print("\n=== Full element dump with ingredient panel visible ===")
            all_els = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('button, input, [role="menu"], [role="dialog"]').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.y > 400 && rect.y < 900) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            role: el.getAttribute('role') || '',
                            text: (el.textContent || '').trim().substring(0, 120),
                            type: el.getAttribute('type') || '',
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                });
                return results;
            }""")
            for el in all_els:
                print(f"    [{el['tag']:<8}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}: {el['text'][:80]}")

        print("\n=== Done. Browser open 20s ===")
        time.sleep(20)
        ctx.close()


if __name__ == "__main__":
    main()
