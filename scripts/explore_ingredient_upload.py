#!/usr/bin/env python3
"""Explore the ingredient upload flow and generation result flow in Flow."""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
EXPLORE_DIR = PROJECT_ROOT / "output" / "explore"
REFS_DIR = PROJECT_ROOT / "refs"

AUTO_PROJECT_URL = "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869"


def take_screenshot(page, name: str):
    path = EXPLORE_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"  Screenshot: {path}")


def dump_elements(page, name: str):
    elements = page.evaluate("""() => {
        const results = [];
        const selectors = 'button, [role="button"], a[href], input, textarea, [contenteditable="true"], select, [role="tab"], [role="menuitem"], [role="option"], [role="combobox"], [role="listbox"], [role="radio"], [role="switch"], [role="slider"], [role="dialog"], [role="menu"], label, [data-testid]';
        document.querySelectorAll(selectors).forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) return;
            results.push({
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role') || '',
                type: el.getAttribute('type') || '',
                text: (el.textContent || '').trim().substring(0, 200),
                ariaLabel: el.getAttribute('aria-label') || '',
                href: el.getAttribute('href') || '',
                placeholder: el.getAttribute('placeholder') || '',
                contentEditable: el.getAttribute('contenteditable') || '',
                className: el.className?.toString?.()?.substring(0, 150) || '',
                x: Math.round(rect.x), y: Math.round(rect.y),
                w: Math.round(rect.width), h: Math.round(rect.height),
            });
        });
        return results;
    }""")
    path = EXPLORE_DIR / f"{name}_elements.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(elements, f, ensure_ascii=False, indent=2)
    print(f"  Elements ({len(elements)}):")
    for el in elements:
        label = el['text'][:80] or el['ariaLabel'][:80] or el['placeholder'][:80] or '?'
        extra = ""
        if el['role']:
            extra += f" role={el['role']}"
        print(f"    [{el['tag']:<10}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}  {label}{extra}")


def dump_all_visible(page, name: str):
    """Dump ALL visible elements including divs to find overlay/popup content."""
    elements = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('*').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) return;
            if (rect.width < 20 && rect.height < 20) return;
            const text = (el.textContent || '').trim().substring(0, 100);
            if (!text) return;
            const tag = el.tagName.toLowerCase();
            // Only elements that might be UI components
            if (['div', 'span', 'p', 'button', 'a', 'input', 'label', 'li', 'ul'].includes(tag)) {
                const zIndex = window.getComputedStyle(el).zIndex;
                if (zIndex !== 'auto' && parseInt(zIndex) > 0) {
                    results.push({
                        tag, text,
                        role: el.getAttribute('role') || '',
                        zIndex,
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            }
        });
        return results;
    }""")
    path = EXPLORE_DIR / f"{name}_overlay.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(elements, f, ensure_ascii=False, indent=2)
    print(f"  Overlay elements ({len(elements)}):")
    for el in elements:
        print(f"    [{el['tag']:<6}] z={el['zIndex']:>4} ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}  {el['text'][:60]}")


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

        # Open project
        print("=" * 60)
        print("Opening project 'Автоматизация'")
        print("=" * 60)
        page.goto(AUTO_PROJECT_URL, timeout=60000, wait_until="domcontentloaded")
        time.sleep(8)

        # === EXPLORE 1: Click "+" button and see what appears ===
        print("\n" + "=" * 60)
        print("STEP 1: Click '+' button near prompt bar")
        print("=" * 60)

        add_btns = page.query_selector_all('button')
        for btn in add_btns:
            text = (btn.text_content() or "").strip()
            box = btn.bounding_box()
            if text == "add" and box and box['y'] > 700:
                print(f"  Found 'add' button at ({box['x']:.0f}, {box['y']:.0f})")
                btn.click()
                time.sleep(3)
                break

        take_screenshot(page, "30_after_add_click")
        dump_elements(page, "30_after_add_click")
        dump_all_visible(page, "30_after_add_click")

        # === EXPLORE 2: Look for "Загрузить" or upload-related buttons ===
        print("\n" + "=" * 60)
        print("STEP 2: Looking for upload-related elements...")
        print("=" * 60)

        # Search for any upload/загрузить text
        upload_elements = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const text = (el.textContent || '').trim().toLowerCase();
                if (text.includes('загруз') || text.includes('upload') || text.includes('файл') ||
                    text.includes('file') || text.includes('browse') || text.includes('обзор') ||
                    text.includes('ингредиент') || text.includes('ingredient')) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: (el.textContent || '').trim().substring(0, 200),
                            role: el.getAttribute('role') || '',
                            type: el.getAttribute('type') || '',
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"  Upload-related elements ({len(upload_elements)}):")
        for el in upload_elements:
            print(f"    [{el['tag']}] ({el['x']}, {el['y']}) {el['w']}x{el['h']}: {el['text'][:80]}")

        # Also check for file input elements
        file_inputs = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('input[type="file"]').forEach(el => {
                results.push({
                    accept: el.getAttribute('accept') || '',
                    multiple: el.multiple,
                    name: el.name,
                    id: el.id,
                });
            });
            return results;
        }""")
        print(f"\n  File inputs: {json.dumps(file_inputs, indent=2)}")

        # === EXPLORE 3: Try clicking in the '+' area more precisely ===
        # Maybe we need to look for a popup/menu that appeared
        print("\n" + "=" * 60)
        print("STEP 3: Check for popups/menus/overlays")
        print("=" * 60)

        popups = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('[role="dialog"], [role="menu"], [role="listbox"], .popup, .overlay, .modal, .dropdown').forEach(el => {
                const rect = el.getBoundingClientRect();
                results.push({
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    className: el.className?.toString?.().substring(0, 100) || '',
                    text: (el.textContent || '').trim().substring(0, 200),
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                });
            });
            return results;
        }""")
        print(f"  Popup/dialog elements ({len(popups)}):")
        for p in popups:
            print(f"    [{p['tag']}] role={p['role']} class={p['className'][:50]}")
            print(f"      text: {p['text'][:100]}")

        # === EXPLORE 4: Close the '+' and try the mode dropdown for video mode ===
        print("\n" + "=" * 60)
        print("STEP 4: Close ingredient panel, switch to video mode")
        print("=" * 60)

        # Close if X button is visible
        close_btn = page.query_selector('button:has-text("close")')
        if close_btn:
            close_btn.click()
            time.sleep(1)

        # Click mode combobox
        combo = page.query_selector('button[role="combobox"]')
        if combo:
            combo.click()
            time.sleep(2)
            take_screenshot(page, "31_mode_dropdown")

            # Select "Видео по кадрам" (Frames to Video)
            option = page.query_selector('div[role="option"]:has-text("Видео по кадрам")')
            if option:
                print("  Found 'Видео по кадрам' option — clicking...")
                option.click()
                time.sleep(3)
                take_screenshot(page, "32_video_frames_mode")
                dump_elements(page, "32_video_frames_mode")
            else:
                print("  'Видео по кадрам' option not found!")
                page.keyboard.press("Escape")

        # === EXPLORE 5: Check video mode UI - model selection ===
        print("\n" + "=" * 60)
        print("STEP 5: Explore video mode - model selector")
        print("=" * 60)

        # Look for model button in video mode
        model_btns = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button').forEach(el => {
                const text = (el.textContent || '').trim();
                if (text.includes('Veo') || text.includes('veo') || text.includes('VEO') ||
                    text.includes('Banana') || text.includes('model') || text.includes('Модель')) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            text: text.substring(0, 100),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"  Model-related buttons:")
        for btn in model_btns:
            print(f"    ({btn['x']}, {btn['y']}) {btn['w']}x{btn['h']}: {btn['text']}")

        # === EXPLORE 6: Switch back to image mode, try entering prompt and generating ===
        print("\n" + "=" * 60)
        print("STEP 6: Switch back to image mode, test basic generation")
        print("=" * 60)

        combo = page.query_selector('button[role="combobox"]')
        if combo:
            combo.click()
            time.sleep(1)
            option = page.query_selector('div[role="option"]:has-text("Создать изображение")')
            if option:
                option.click()
                time.sleep(2)

        # Enter a test prompt
        textarea = page.query_selector('textarea')
        if textarea:
            textarea.fill("Test prompt - a simple red ball on a white background")
            time.sleep(1)
            take_screenshot(page, "33_with_test_prompt")

            # Check Generate button state
            gen_btn = page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent.includes('Создать') || btn.textContent.includes('arrow_forward')) {
                        const rect = btn.getBoundingClientRect();
                        return {
                            text: btn.textContent.trim().substring(0, 50),
                            disabled: btn.disabled,
                            x: Math.round(rect.x), y: Math.round(rect.y),
                        };
                    }
                }
                return null;
            }""")
            print(f"  Generate button: {gen_btn}")

            # Clear the test prompt
            textarea.fill("")
            time.sleep(1)

        # === EXPLORE 7: Settings dialog ===
        print("\n" + "=" * 60)
        print("STEP 7: Open Settings dialog")
        print("=" * 60)
        settings_btn = page.query_selector('button:has-text("tune")')
        if settings_btn:
            settings_btn.click()
            time.sleep(2)
            take_screenshot(page, "34_settings_dialog")
            dump_elements(page, "34_settings_dialog")
            page.keyboard.press("Escape")
            time.sleep(1)

        # Wait for manual observation
        print("\n" + "=" * 60)
        print("Browser open for 30s for manual observation...")
        print("=" * 60)
        time.sleep(30)
        take_screenshot(page, "39_final")

        ctx.close()
        print("Done.")


if __name__ == "__main__":
    main()
