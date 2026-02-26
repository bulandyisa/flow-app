#!/usr/bin/env python3
"""
Test: click the Nano Banana Pro button to see if there are other model options.
Also try VEO modes to list available video models.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS = [
    {
        "session_dir": PROJECT_ROOT / ".session",
        "project_url": "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869",
    },
    {
        "session_dir": PROJECT_ROOT / ".session_2",
        "project_url": "https://labs.google/fx/ru/tools/flow/project/492b843c-217a-4c83-8c2d-4e0b0f0b1dc8",
    },
]
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "screenshots"


def launch_browser(account_idx=1):
    acct = ACCOUNTS[account_idx]
    p = sync_playwright().start()
    ctx = p.chromium.launch_persistent_context(
        str(acct["session_dir"]),
        headless=False,
        viewport={"width": 1280, "height": 900},
        locale="ru-RU",
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(acct["project_url"], wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)
    time.sleep(3)
    print(f"Opened Flow on account {account_idx + 1}")
    return p, ctx, page


def click_model_button(page):
    """Click the 'Nano Banana Pro' button near the prompt bar to see model options."""
    # This button is at y=729, x=703 based on previous scan
    result = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = (btn.textContent || '').trim();
            const rect = btn.getBoundingClientRect();
            if (text.includes('Nano Banana') && rect.y > 700 && rect.y < 800 && rect.x > 600) {
                btn.click();
                return {clicked: true, text: text, y: Math.round(rect.y), x: Math.round(rect.x)};
            }
        }
        return {clicked: false};
    }""")
    print(f"Click model button: {result}")
    time.sleep(1.5)

    # Screenshot after click
    page.screenshot(path=str(SCREENSHOTS_DIR / "test_model_selector.png"))

    # List any new options/dropdowns that appeared
    options = page.evaluate("""() => {
        const items = [];
        // Check for any dropdown, menu, dialog, or overlay that appeared
        const overlays = document.querySelectorAll(
            '[role="menu"], [role="listbox"], [role="dialog"], ' +
            '[class*="dropdown"], [class*="menu"], [class*="popup"], ' +
            '[class*="overlay"], [class*="popover"], [class*="modal"]'
        );
        for (const ol of overlays) {
            const rect = ol.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                items.push({
                    tag: ol.tagName,
                    role: ol.getAttribute('role') || '',
                    className: (ol.className || '').substring(0, 100),
                    text: (ol.textContent || '').substring(0, 500),
                    y: Math.round(rect.y),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height)
                });
            }
        }

        // Also check for role="option" items
        const opts = document.querySelectorAll('[role="option"], [role="menuitem"], [role="menuitemradio"]');
        for (const opt of opts) {
            const rect = opt.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                items.push({
                    tag: opt.tagName,
                    role: opt.getAttribute('role'),
                    text: (opt.textContent || '').trim().substring(0, 200),
                    y: Math.round(rect.y),
                    w: Math.round(rect.width),
                    type: 'option'
                });
            }
        }

        return items;
    }""")

    print(f"\nНовые элементы после клика ({len(options)}):")
    for item in options:
        print(f"  {item}")

    return result


def explore_video_modes(page):
    """Switch to each video mode and list available models."""
    video_modes = [
        "Видео по описанию",
        "Видео по кадрам",
        "Видео по образцам"
    ]

    for mode in video_modes:
        print(f"\n--- Режим: {mode} ---")
        combo = page.query_selector('button[role="combobox"]')
        if combo:
            combo.click()
            time.sleep(1)
            option = page.query_selector(f'div[role="option"]:has-text("{mode}")')
            if option:
                option.click()
                time.sleep(2)
            else:
                page.keyboard.press("Escape")
                print(f"  Не найден: {mode}")
                continue

        # Screenshot
        page.screenshot(path=str(SCREENSHOTS_DIR / f"test_mode_{mode[:10]}.png"))

        # Look for model name near prompt bar
        model_info = page.evaluate("""() => {
            const items = [];
            const allEls = document.querySelectorAll('button, div, span');
            const keywords = ['veo', 'nano', 'gemini', 'imagen', 'fast', 'pro', 'lower'];
            for (const el of allEls) {
                const text = (el.textContent || '').trim().toLowerCase();
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.width > 300 || text.length > 80) continue;
                if (rect.y < 600 || rect.y > 850) continue;
                for (const kw of keywords) {
                    if (text.includes(kw)) {
                        items.push({
                            text: el.textContent.trim(),
                            tag: el.tagName,
                            clickable: el.tagName === 'BUTTON',
                            y: Math.round(rect.y),
                            x: Math.round(rect.x),
                            w: Math.round(rect.width)
                        });
                        break;
                    }
                }
            }
            // Deduplicate
            const seen = new Set();
            return items.filter(i => {
                const key = i.text + i.y;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
        }""")

        print(f"  Модели: {model_info}")

        # Try clicking the model button if found
        for mi in model_info:
            if mi.get('clickable') and ('veo' in mi['text'].lower() or 'nano' in mi['text'].lower()):
                print(f"  Кликаю на кнопку модели: {mi['text']}")
                page.evaluate(f"""() => {{
                    const btns = document.querySelectorAll('button');
                    for (const btn of btns) {{
                        const text = (btn.textContent || '').trim();
                        const rect = btn.getBoundingClientRect();
                        if (text.includes('{mi["text"][:20]}') && Math.abs(rect.y - {mi['y']}) < 10) {{
                            btn.click();
                            return true;
                        }}
                    }}
                    return false;
                }}""")
                time.sleep(1.5)
                page.screenshot(path=str(SCREENSHOTS_DIR / f"test_model_click_{mode[:10]}.png"))

                # Check for dropdown options
                opts = page.query_selector_all('[role="option"], [role="menuitem"], [role="menuitemradio"]')
                if opts:
                    print(f"  Опции: {[o.text_content().strip() for o in opts]}")

                page.keyboard.press("Escape")
                time.sleep(0.5)
                break


def main():
    account_idx = 1
    if "--account" in sys.argv:
        idx = sys.argv.index("--account")
        account_idx = int(sys.argv[idx + 1]) - 1

    p, ctx, page = launch_browser(account_idx)

    try:
        # Step 1: Click the Nano Banana Pro model button in image mode
        print("\n=== ТЕСТ ВЫБОРА МОДЕЛИ ===")
        print("\n--- Image mode: клик на Nano Banana Pro ---")
        click_model_button(page)

        # Close any dropdown
        page.keyboard.press("Escape")
        time.sleep(1)

        # Step 2: Explore video modes
        print("\n--- Video modes ---")
        explore_video_modes(page)

    finally:
        ctx.close()
        p.stop()


if __name__ == "__main__":
    main()
