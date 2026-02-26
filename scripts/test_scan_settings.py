#!/usr/bin/env python3
"""Scan settings panel to find exact model dropdown element."""

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

    # Open settings
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

    # Scan ALL visible elements in the settings area (y > 500, overlay region)
    elements = page.evaluate("""() => {
        const items = [];
        const allEls = document.querySelectorAll('*');
        for (const el of allEls) {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            // Focus on the settings panel area
            if (rect.y < 500 || rect.y > 850) continue;
            // Skip huge containers
            if (rect.width > 800 && rect.height > 200) continue;

            const text = (el.textContent || '').trim();
            if (text.length > 120) continue;

            // Include if it has text content relevant to settings
            const role = el.getAttribute('role') || '';
            const tag = el.tagName;
            const ariaExpanded = el.getAttribute('aria-expanded') || '';
            const ariaHaspopup = el.getAttribute('aria-haspopup') || '';

            if (text.includes('Модель') || text.includes('Model') ||
                text.includes('Banana') || text.includes('Imagen') ||
                text.includes('Результат') || text.includes('Соотношение') ||
                text.includes('Горизонтальн') || text.includes('credits') ||
                text.includes('кредит') ||
                role === 'combobox' || role === 'listbox' || role === 'button' ||
                ariaHaspopup || ariaExpanded ||
                tag === 'SELECT' || tag === 'BUTTON') {

                items.push({
                    text: text.replace(/\\n/g, ' ').replace(/\\s+/g, ' ').substring(0, 80),
                    tag: tag,
                    role: role,
                    ariaExpanded: ariaExpanded,
                    ariaHaspopup: ariaHaspopup,
                    y: Math.round(rect.y),
                    x: Math.round(rect.x),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                    className: (el.className || '').toString().substring(0, 60)
                });
            }
        }

        // Sort by y position
        items.sort((a, b) => a.y - b.y);
        return items;
    }""")

    print(f"Settings panel elements ({len(elements)}):")
    print(f"{'Y':>4} {'X':>4} {'W':>4}x{'H':<4} {'TAG':<8} {'ROLE':<12} {'TEXT'}")
    print("-" * 100)
    for el in elements:
        extra = ""
        if el['ariaExpanded']:
            extra += f" expanded={el['ariaExpanded']}"
        if el['ariaHaspopup']:
            extra += f" haspopup={el['ariaHaspopup']}"
        print(f"{el['y']:>4} {el['x']:>4} {el['w']:>4}x{el['h']:<4} {el['tag']:<8} {el['role']:<12} {el['text'][:60]}{extra}")

    page.screenshot(path=str(SCREENSHOTS_DIR / "settings_scan.png"))

    # Now try to find and click the model dropdown specifically
    print("\n\nLooking for model dropdown...")

    # The model dropdown should be a clickable element containing 'Nano Banana'
    # that is in the settings panel (not in the gallery)
    model_dropdown = page.evaluate("""() => {
        const allEls = document.querySelectorAll('*');

        // First find 'Модель' text
        let modelLabelY = null;
        for (const el of allEls) {
            const directText = Array.from(el.childNodes)
                .filter(n => n.nodeType === Node.TEXT_NODE)
                .map(n => n.textContent.trim())
                .join('');
            if (directText === 'Модель' || directText === 'Model') {
                const rect = el.getBoundingClientRect();
                if (rect.height > 0 && rect.y > 500) {
                    modelLabelY = rect.y;
                    break;
                }
            }
        }

        if (!modelLabelY) {
            // Try broader search
            for (const el of allEls) {
                const text = (el.textContent || '').trim();
                if ((text === 'Модель' || text.startsWith('Модель')) && text.length < 15) {
                    const rect = el.getBoundingClientRect();
                    if (rect.height > 0 && rect.height < 40 && rect.y > 500) {
                        modelLabelY = rect.y;
                        break;
                    }
                }
            }
        }

        if (!modelLabelY) return {error: 'Model label not found'};

        // Now find the dropdown BELOW the model label (within ~80px)
        const candidates = [];
        for (const el of allEls) {
            const rect = el.getBoundingClientRect();
            if (rect.y < modelLabelY || rect.y > modelLabelY + 80) continue;
            if (rect.width < 100 || rect.height < 20 || rect.height > 80) continue;

            const text = (el.textContent || '').trim();
            if (text.includes('Banana') || text.includes('Imagen')) {
                candidates.push({
                    text: text.substring(0, 50),
                    tag: el.tagName,
                    role: el.getAttribute('role') || '',
                    y: Math.round(rect.y),
                    x: Math.round(rect.x),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height),
                    clickable: el.tagName === 'BUTTON' || el.tagName === 'SELECT' ||
                               el.getAttribute('role') === 'combobox' || el.getAttribute('role') === 'listbox' ||
                               el.getAttribute('tabindex') !== null
                });
            }
        }

        return {modelLabelY: Math.round(modelLabelY), candidates: candidates};
    }""")

    print(f"  Model dropdown search: {model_dropdown}")

    # If we found candidates, try clicking
    if model_dropdown.get('candidates'):
        # Pick the most clickable one
        target = None
        for c in model_dropdown['candidates']:
            if c.get('clickable'):
                target = c
                break
        if not target:
            target = model_dropdown['candidates'][0]

        print(f"\n  Clicking model dropdown at ({target['x']}, {target['y']})...")
        page.mouse.click(target['x'] + target['w'] // 2, target['y'] + target['h'] // 2)
        time.sleep(2)

        page.screenshot(path=str(SCREENSHOTS_DIR / "model_dropdown_clicked.png"))

        # Check what opened
        new_elements = page.evaluate("""() => {
            const items = [];
            const allEls = document.querySelectorAll('[role="option"], [role="menuitem"], [role="radio"], [role="listbox"], option');
            for (const el of allEls) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    items.push({
                        text: (el.textContent || '').trim().substring(0, 50),
                        tag: el.tagName,
                        role: el.getAttribute('role') || '',
                        checked: el.getAttribute('aria-checked') || el.getAttribute('aria-selected') || '',
                        y: Math.round(rect.y)
                    });
                }
            }
            return items;
        }""")
        print(f"  Dropdown options: {new_elements}")

        # Also check for any new visible text containing model names
        model_texts = page.evaluate("""() => {
            const items = [];
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            while (walker.nextNode()) {
                const text = walker.currentNode.textContent.trim();
                if ((text.includes('Imagen') || text === 'Nano Banana' || text === 'Nano Banana Pro') && text.length < 30) {
                    const parent = walker.currentNode.parentElement;
                    const rect = parent ? parent.getBoundingClientRect() : {y:0, x:0, width:0, height:0};
                    items.push({text: text, y: Math.round(rect.y), x: Math.round(rect.x), visible: rect.width > 0});
                }
            }
            return items;
        }""")
        print(f"  Model text nodes visible: {model_texts}")

    page.keyboard.press("Escape")
    ctx.close()
    p.stop()
    print("\nDone.")


if __name__ == "__main__":
    main()
