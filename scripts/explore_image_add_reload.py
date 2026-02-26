#!/usr/bin/env python3
"""Try: click + then reload page, check if ingredient panel appears."""

import time
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
    return page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('*').forEach(el => {
            const text = (el.textContent || '').trim();
            const tag = el.tagName.toLowerCase();
            if (tag === 'html' || tag === 'body') return;
            if (text.includes('Загрузить') || text.includes('ингредиент') || text.includes('ingredient') || text.includes('референс')) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 20 && rect.height > 20 && text.length < 150) {
                    results.push({
                        tag, text,
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            }
        });
        return results;
    }""")


def dump_bottom(page, label):
    """Dump all elements in bottom half of page."""
    elements = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('button, [role="menu"], input, div[role], a').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 10 && rect.y > 400 && rect.y < 900) {
                results.push({
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    text: (el.textContent || '').trim().substring(0, 100),
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                });
            }
        });
        return results;
    }""")
    seen = set()
    print(f"\n  {label} — bottom elements ({len(elements)}):")
    for el in elements:
        key = f"{el['tag']}-{el['x']}-{el['y']}-{el['w']}"
        if key not in seen:
            seen.add(key)
            print(f"    [{el['tag']:<8}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}: {el['text'][:70]}")


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

        # === Approach 1: Click + then reload WITHOUT clicking + again ===
        print("\n=== Approach 1: Click +, reload, wait ===")
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
        time.sleep(2)
        screenshot(page, "80_after_add_before_reload")

        print("  Reloading...")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector("textarea", timeout=60000)

        for sec in range(30):
            time.sleep(1)
            elements = check_for_upload(page)
            if elements:
                print(f"\n  FOUND after reload at {sec+1}s!")
                for el in elements:
                    print(f"    [{el['tag']}] ({el['x']},{el['y']}) {el['w']}x{el['h']}: {el['text'][:60]}")
                screenshot(page, f"81_found_after_reload_{sec+1}s")
                dump_bottom(page, "After reload")
                break
            if (sec + 1) % 10 == 0:
                print(f"  ...{sec+1}s")
                screenshot(page, f"81_reload_wait_{sec+1}s")
        else:
            print("  Not found after 30s")
            screenshot(page, "81_reload_timeout")
            dump_bottom(page, "After reload timeout")

        # === Approach 2: Navigate fresh to project, just click + and wait very long ===
        print("\n=== Approach 2: Fresh navigate, click +, wait 90s ===")
        page.goto(AUTO_PROJECT_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_selector("textarea", timeout=60000)
        time.sleep(10)  # let SPA fully settle

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

        for sec in range(90):
            time.sleep(1)
            elements = check_for_upload(page)
            if elements:
                print(f"\n  FOUND at {sec+1}s!")
                for el in elements:
                    print(f"    [{el['tag']}] ({el['x']},{el['y']}) {el['w']}x{el['h']}: {el['text'][:60]}")
                screenshot(page, f"82_found_{sec+1}s")
                dump_bottom(page, "After long wait")
                break
            if (sec + 1) % 15 == 0:
                print(f"  ...{sec+1}s")
                screenshot(page, f"82_wait_{sec+1}s")
        else:
            print("  Not found after 90s")
            screenshot(page, "82_final_timeout")

        print("\n=== Browser open 30s for manual check ===")
        time.sleep(30)
        ctx.close()


if __name__ == "__main__":
    main()
