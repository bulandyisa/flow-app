#!/usr/bin/env python3
"""
Debug: click model button, screenshot, analyze the dropdown/popup.
Then try to select Imagen 4.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "screenshots"

ACCOUNT = {
    "session_dir": PROJECT_ROOT / ".session_2",
    "project_url": "https://labs.google/fx/ru/tools/flow/project/492b843c-217a-4c83-8c2d-4e0b0f0b1dc8",
}


def main():
    p = sync_playwright().start()
    ctx = p.chromium.launch_persistent_context(
        str(ACCOUNT["session_dir"]),
        headless=False,
        viewport={"width": 1280, "height": 900},
        locale="ru-RU",
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(5)
    print("Flow ready\n")

    # Step 1: Click the model button
    print("Step 1: Click model button...")
    clicked = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = (btn.textContent || '').trim();
            const rect = btn.getBoundingClientRect();
            if ((text.includes('Nano Banana') || text.includes('Imagen')) &&
                rect.y > 700 && rect.y < 800 && rect.x > 600) {
                btn.click();
                return {text: text, y: Math.round(rect.y), x: Math.round(rect.x), w: Math.round(rect.width)};
            }
        }
        return null;
    }""")
    print(f"  Clicked: {clicked}")
    time.sleep(2)

    # Step 2: Screenshot
    page.screenshot(path=str(SCREENSHOTS_DIR / "model_switch_after_click.png"))
    print("  Screenshot saved")

    # Step 3: Analyze what appeared
    popups = page.evaluate("""() => {
        const items = [];

        // Check all elements on page for radio buttons, options, menu items
        const allEls = document.querySelectorAll('*');
        for (const el of allEls) {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;

            const role = el.getAttribute('role') || '';
            const type = el.getAttribute('type') || '';
            const ariaChecked = el.getAttribute('aria-checked') || '';
            const text = (el.textContent || '').trim();

            // Radio buttons or options
            if (role === 'radio' || role === 'radiogroup' || role === 'option' ||
                role === 'menuitem' || role === 'menuitemradio' ||
                type === 'radio') {
                items.push({
                    text: text.substring(0, 80),
                    tag: el.tagName,
                    role: role,
                    type: type,
                    checked: ariaChecked,
                    y: Math.round(rect.y),
                    x: Math.round(rect.x),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height)
                });
            }

            // Also check for elements containing model names in popup-like containers
            if (text.includes('Imagen') && !text.includes('Сгенерируйте') && text.length < 30) {
                items.push({
                    text: text,
                    tag: el.tagName,
                    role: role,
                    y: Math.round(rect.y),
                    x: Math.round(rect.x),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                    note: 'contains Imagen'
                });
            }
        }

        // Deduplicate
        const seen = new Set();
        return items.filter(i => {
            const key = `${i.tag}_${i.y}_${i.text.substring(0, 20)}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }""")

    print(f"\nFound {len(popups)} relevant elements:")
    for item in popups:
        print(f"  {item}")

    # Step 4: Check for any overlay/dialog
    overlays = page.evaluate("""() => {
        const items = [];
        const candidates = document.querySelectorAll(
            '[role="dialog"], [role="menu"], [role="listbox"], [role="radiogroup"], ' +
            '[class*="popover"], [class*="dropdown"], [class*="popup"], [class*="overlay"], [class*="modal"]'
        );
        for (const el of candidates) {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                items.push({
                    tag: el.tagName,
                    role: el.getAttribute('role') || '',
                    className: (el.className || '').toString().substring(0, 80),
                    text: (el.textContent || '').substring(0, 200),
                    y: Math.round(rect.y),
                    x: Math.round(rect.x),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height)
                });
            }
        }
        return items;
    }""")

    print(f"\nOverlays/dialogs ({len(overlays)}):")
    for item in overlays:
        print(f"  tag={item['tag']} role={item['role']} y={item['y']} w={item['w']}x{item['h']}")
        print(f"    text: {item['text'][:100]}")

    # Step 5: Try clicking directly with coordinate approach
    # From user screenshot: radio buttons with model names, vertically stacked
    # Let's try finding by 'Imagen' text near the dropdown area
    print("\n\nStep 5: Try to find and click Imagen 4...")

    # Look for any element with exact text 'Imagen 4' visible on screen
    found = page.evaluate("""() => {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        const results = [];
        while (walker.nextNode()) {
            const text = walker.currentNode.textContent.trim();
            if (text === 'Imagen 4' || text.includes('Imagen 4')) {
                const parent = walker.currentNode.parentElement;
                if (parent) {
                    const rect = parent.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        results.push({
                            text: text,
                            parentTag: parent.tagName,
                            parentRole: parent.getAttribute('role') || '',
                            y: Math.round(rect.y),
                            x: Math.round(rect.x),
                            w: Math.round(rect.width),
                            h: Math.round(rect.height)
                        });
                    }
                }
            }
        }
        return results;
    }""")
    print(f"  'Imagen 4' text nodes: {found}")

    if found:
        # Click the first one
        target = found[0]
        print(f"  Clicking at ({target['x'] + target['w']//2}, {target['y'] + target['h']//2})")
        page.mouse.click(target['x'] + target['w'] // 2, target['y'] + target['h'] // 2)
        time.sleep(2)
        page.screenshot(path=str(SCREENSHOTS_DIR / "model_switch_imagen4.png"))
        print("  Screenshot after Imagen 4 click saved")

    # Escape
    page.keyboard.press("Escape")
    time.sleep(1)

    ctx.close()
    p.stop()
    print("\nDone.")


if __name__ == "__main__":
    main()
