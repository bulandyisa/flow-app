#!/usr/bin/env python3
"""Careful exploration of the '+' button in image mode — wait longer, take multiple screenshots."""

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

        print("\n=== BEFORE clicking + ===")
        screenshot(page, "70_before_add")

        # Use page.click with force to bypass any intercept
        print("\n=== Clicking + with JavaScript click ===")
        clicked = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                if (btn.textContent.trim() === 'add' && rect.y > 700) {
                    btn.click();
                    return {text: btn.textContent.trim(), x: rect.x, y: rect.y};
                }
            }
            return null;
        }""")
        print(f"  Clicked: {clicked}")

        # Take screenshots at intervals
        for i in range(6):
            time.sleep(1)
            screenshot(page, f"71_after_add_{i+1}s")

        # Now check the ENTIRE page DOM for anything new — especially look for
        # elements that might have appeared with animation (opacity 0 initially)
        print("\n=== Full DOM scan after + click ===")
        all_interactive = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button, [role="menu"], [role="dialog"], [role="menuitem"], input[type="file"], a[download]').forEach(el => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                results.push({
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    type: el.getAttribute('type') || '',
                    text: (el.textContent || '').trim().substring(0, 120),
                    display: style.display,
                    visibility: style.visibility,
                    opacity: parseFloat(style.opacity),
                    pointerEvents: style.pointerEvents,
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                });
            });
            return results;
        }""")

        # Filter to elements near the prompt bar or that appeared new
        print(f"  Total interactive elements: {len(all_interactive)}")
        for el in all_interactive:
            if el['y'] > 500 or el['display'] == 'none' or el['opacity'] < 1 or el['role'] in ('menu', 'dialog', 'menuitem'):
                vis = f"d={el['display']} v={el['visibility']} o={el['opacity']}"
                print(f"    [{el['tag']:<8}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3} {vis}: {el['text'][:60]}")

        # Check if the button text actually changed
        print("\n=== Button text check ===")
        bottom_btns = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button').forEach(btn => {
                const rect = btn.getBoundingClientRect();
                if (rect.y > 700 && rect.x < 600) {
                    // Get the actual icon/text content
                    const spans = btn.querySelectorAll('span, i, svg');
                    let icon = '';
                    spans.forEach(s => icon += s.textContent.trim() + ' ');
                    results.push({
                        text: btn.textContent.trim(),
                        icon: icon.trim(),
                        innerHTML: btn.innerHTML.substring(0, 300),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        for btn in bottom_btns:
            print(f"  Button ({btn['x']},{btn['y']}) {btn['w']}x{btn['h']}:")
            print(f"    text: '{btn['text']}'")
            print(f"    icon: '{btn['icon']}'")
            print(f"    html: {btn['innerHTML'][:200]}")

        # Try clicking the actual button element (maybe the Playwright click was intercepted)
        print("\n=== Try Playwright force click ===")
        # Reset first — click the X/close if it appeared
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                if ((btn.textContent.trim() === 'close' || btn.textContent.trim() === 'add') && rect.y > 700 && rect.x < 500) {
                    btn.click();
                    return;
                }
            }
        }""")
        time.sleep(2)

        # Now use Playwright's click with force
        add_btn = None
        for btn in page.query_selector_all('button'):
            text = (btn.text_content() or "").strip()
            box = btn.bounding_box()
            if text == "add" and box and box['y'] > 700:
                add_btn = btn
                break

        if add_btn:
            print("  Force clicking add button...")
            add_btn.click(force=True)
            time.sleep(5)
            screenshot(page, "72_after_force_click")

            # Check again
            new_elements = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('[role="menu"], [role="dialog"], [role="listbox"]').forEach(el => {
                    results.push({
                        role: el.getAttribute('role'),
                        text: (el.textContent || '').trim().substring(0, 200),
                        visible: el.getBoundingClientRect().width > 0,
                    });
                });
                // Also check for any upload-related elements
                document.querySelectorAll('*').forEach(el => {
                    const text = (el.textContent || '').trim();
                    if (text === 'Загрузить' || text === 'upload') {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0) {
                            results.push({
                                tag: el.tagName.toLowerCase(),
                                text: text,
                                x: Math.round(rect.x), y: Math.round(rect.y),
                            });
                        }
                    }
                });
                return results;
            }""")
            print(f"  New elements after force click: {json.dumps(new_elements, indent=2, ensure_ascii=False)}")

        print("\n=== Browser open 20s ===")
        time.sleep(20)
        ctx.close()


if __name__ == "__main__":
    main()
