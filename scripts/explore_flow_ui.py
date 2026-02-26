#!/usr/bin/env python3
"""Scan workspace of project "Автоматизация" for all UI selectors."""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
EXPLORE_DIR = PROJECT_ROOT / "output" / "explore"

AUTO_PROJECT_URL = "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869"


def take_screenshot(page, name: str):
    path = EXPLORE_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"  Screenshot: {path}")


def dump_elements(page, name: str):
    elements = page.evaluate("""() => {
        const results = [];
        const selectors = 'button, [role="button"], a[href], input, textarea, [contenteditable="true"], select, [role="tab"], [role="menuitem"], [role="option"], [role="combobox"], [role="listbox"], [role="radio"], [role="switch"], [role="slider"]';
        document.querySelectorAll(selectors).forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) return;
            results.push({
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role') || '',
                type: el.getAttribute('type') || '',
                text: (el.textContent || '').trim().substring(0, 150),
                ariaLabel: el.getAttribute('aria-label') || '',
                href: el.getAttribute('href') || '',
                placeholder: el.getAttribute('placeholder') || '',
                contentEditable: el.getAttribute('contenteditable') || '',
                x: Math.round(rect.x), y: Math.round(rect.y),
                w: Math.round(rect.width), h: Math.round(rect.height),
            });
        });
        return results;
    }""")
    path = EXPLORE_DIR / f"{name}_elements.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(elements, f, ensure_ascii=False, indent=2)
    print(f"  Elements ({len(elements)})")
    for el in elements:
        label = el['text'][:60] or el['ariaLabel'][:60] or el['placeholder'][:60] or '?'
        extra = ""
        if el['contentEditable'] == 'true':
            extra = " [EDITABLE]"
        if el['role']:
            extra += f" role={el['role']}"
        print(f"    [{el['tag']:<10}] {label:<60}{extra}")


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

        # Open project "Автоматизация"
        print("=" * 60)
        print("Opening project 'Автоматизация'")
        print("=" * 60)
        page.goto(AUTO_PROJECT_URL, timeout=60000, wait_until="domcontentloaded")
        time.sleep(10)
        take_screenshot(page, "20_auto_workspace")
        dump_elements(page, "20_auto_workspace")

        # Now click on the mode combobox to see available modes
        print("\n" + "=" * 60)
        print("Clicking mode combobox to see options...")
        print("=" * 60)
        combo = page.query_selector('button[role="combobox"]')
        if combo:
            combo.click()
            time.sleep(2)
            take_screenshot(page, "21_mode_dropdown")
            dump_elements(page, "21_mode_dropdown")
            # Close dropdown
            page.keyboard.press("Escape")
            time.sleep(1)

        # Click the "+" (add ingredient) button near the prompt bar
        print("\n" + "=" * 60)
        print("Clicking '+' add button near prompt bar...")
        print("=" * 60)
        # The add button near prompt bar is the last "add" button
        add_btns = page.query_selector_all('button:has-text("add")')
        if add_btns:
            # Click the one closest to the textarea (bottom of page)
            last_add = add_btns[-2] if len(add_btns) > 1 else add_btns[-1]  # -1 is "Создать", -2 is "+"
            # Actually find the add button near textarea
            for btn in reversed(add_btns):
                box = btn.bounding_box()
                if box and box['y'] > 800:  # bottom area
                    text = btn.text_content().strip()
                    if text == 'add':
                        print(f"  Clicking add button at y={box['y']}")
                        btn.click()
                        time.sleep(3)
                        take_screenshot(page, "22_after_add_click")
                        dump_elements(page, "22_after_add_click")
                        break

        # Wait for manual exploration
        print("\n" + "=" * 60)
        print("Browser open for 60s...")
        print("=" * 60)
        time.sleep(60)
        take_screenshot(page, "29_final")

        ctx.close()
        print("Done.")


if __name__ == "__main__":
    main()
