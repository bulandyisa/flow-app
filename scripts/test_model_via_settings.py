#!/usr/bin/env python3
"""
Try opening model selector via Settings panel or by different click targets.
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

    # Approach 1: Try clicking Settings icon (tune) and look for model selector
    print("=== Approach 1: Settings panel ===")
    settings_result = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim().toLowerCase();
            const rect = btn.getBoundingClientRect();
            if ((text.includes('tune') || text === 'tune' ||
                 text.includes('settings') || text.includes('настройки')) &&
                rect.y > 600 && rect.width < 100) {
                btn.click();
                return {clicked: true, text: text, y: Math.round(rect.y), x: Math.round(rect.x)};
            }
        }
        // Try by icon class
        const icons = document.querySelectorAll('[class*="icon"], .material-icons, .material-symbols');
        for (const icon of icons) {
            const text = icon.textContent.trim().toLowerCase();
            const rect = icon.getBoundingClientRect();
            if ((text === 'tune' || text === 'settings') && rect.y > 600) {
                icon.click();
                return {clicked: true, text: text, y: Math.round(rect.y), x: Math.round(rect.x), via: 'icon'};
            }
        }
        return {clicked: false};
    }""")
    print(f"  Settings click: {settings_result}")
    time.sleep(2)
    page.screenshot(path=str(SCREENSHOTS_DIR / "model_settings_panel.png"))

    # Look for model selector in settings panel
    model_in_settings = page.evaluate("""() => {
        const items = [];
        const allEls = document.querySelectorAll('*');
        for (const el of allEls) {
            const text = (el.textContent || '').trim();
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            if (text.length > 80) continue;
            if (text.includes('Imagen') || (text.includes('Nano Banana') && !text.includes('Pro') && text.length < 30)) {
                items.push({
                    text: text,
                    tag: el.tagName,
                    role: el.getAttribute('role') || '',
                    y: Math.round(rect.y),
                    x: Math.round(rect.x),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height)
                });
            }
        }
        return items;
    }""")
    print(f"  Model elements in panel: {model_in_settings}")

    # Close settings
    page.keyboard.press("Escape")
    time.sleep(1)

    # Approach 2: List ALL elements near the prompt bar area (y 700-850)
    print("\n=== Approach 2: All elements near prompt bar ===")
    elements = page.evaluate("""() => {
        const items = [];
        const allEls = document.querySelectorAll('button, [role="button"], [role="tab"], [role="radio"], div[class*="chip"], span[class*="chip"]');
        for (const el of allEls) {
            const rect = el.getBoundingClientRect();
            if (rect.y < 700 || rect.y > 860) continue;
            if (rect.width === 0) continue;
            const text = (el.textContent || '').trim().replace(/\\n/g, ' ').replace(/\\s+/g, ' ');
            if (text.length > 60) continue;
            items.push({
                text: text,
                tag: el.tagName,
                role: el.getAttribute('role') || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                title: el.getAttribute('title') || '',
                y: Math.round(rect.y),
                x: Math.round(rect.x),
                w: Math.round(rect.width),
                h: Math.round(rect.height),
                id: el.id || ''
            });
        }
        return items;
    }""")
    print(f"  Elements near prompt bar ({len(elements)}):")
    for el in elements:
        print(f"    [{el['x']},{el['y']}] {el['w']}x{el['h']} {el['tag']} role={el['role']} '{el['text']}' aria='{el['ariaLabel']}'")

    # Approach 3: Try clicking the model button text (not the button element, but the inner text div)
    print("\n=== Approach 3: Click inner model text elements ===")
    inner_clicks = page.evaluate("""() => {
        const results = [];
        const allEls = document.querySelectorAll('div, span');
        for (const el of allEls) {
            const text = (el.textContent || '').trim();
            const rect = el.getBoundingClientRect();
            if (text === '🍌 Nano Banana Pro' && rect.y > 700 && rect.y < 800 && rect.width < 200) {
                // Don't click yet, just record
                results.push({
                    text: text,
                    tag: el.tagName,
                    y: Math.round(rect.y),
                    x: Math.round(rect.x),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                    hasChildren: el.children.length,
                    parentTag: el.parentElement?.tagName || '',
                    parentRole: el.parentElement?.getAttribute('role') || ''
                });
            }
        }
        return results;
    }""")
    print(f"  Inner model elements: {inner_clicks}")

    # Approach 4: Try right-click or long-press on model button
    if inner_clicks:
        target = inner_clicks[0]
        print(f"\n  Trying right-click on model text...")
        page.mouse.click(target['x'] + target['w']//2, target['y'] + target['h']//2, button="right")
        time.sleep(2)
        page.screenshot(path=str(SCREENSHOTS_DIR / "model_rightclick.png"))

        # Check for context menu
        ctx_menu = page.evaluate("""() => {
            const menus = document.querySelectorAll('[role="menu"], [role="listbox"], [class*="menu"], [class*="context"]');
            return Array.from(menus).filter(m => m.getBoundingClientRect().height > 0).map(m => ({
                text: (m.textContent || '').substring(0, 200),
                tag: m.tagName,
                role: m.getAttribute('role') || ''
            }));
        }""")
        print(f"  Context menus: {ctx_menu}")

        # Close context menu
        page.keyboard.press("Escape")
        time.sleep(0.5)

    # Approach 5: Scroll down or look above the prompt bar for a model selector
    print("\n=== Approach 5: Check for model selector above/in settings area ===")

    # Open settings again and take full-page screenshot
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim().toLowerCase();
            const rect = btn.getBoundingClientRect();
            if ((text.includes('tune') || text === 'tune') && rect.y > 600 && rect.width < 100) {
                btn.click();
                return true;
            }
        }
        return false;
    }""")
    time.sleep(2)

    # Full page content scan for model names
    full_scan = page.evaluate("""() => {
        const results = [];
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {
            const text = walker.currentNode.textContent.trim();
            if (text.includes('Imagen') || text === 'Nano Banana' || text === 'Nano Banana Pro') {
                const parent = walker.currentNode.parentElement;
                if (parent) {
                    const rect = parent.getBoundingClientRect();
                    results.push({
                        text: text,
                        parentTag: parent.tagName,
                        visible: rect.width > 0 && rect.height > 0,
                        y: Math.round(rect.y),
                        x: Math.round(rect.x)
                    });
                }
            }
        }
        return results;
    }""")
    print(f"  All model text nodes on page:")
    for item in full_scan:
        print(f"    '{item['text']}' tag={item['parentTag']} visible={item['visible']} at ({item['x']},{item['y']})")

    page.screenshot(path=str(SCREENSHOTS_DIR / "model_settings_full.png"))
    page.keyboard.press("Escape")

    ctx.close()
    p.stop()
    print("\nDone.")


if __name__ == "__main__":
    main()
