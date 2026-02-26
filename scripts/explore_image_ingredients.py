#!/usr/bin/env python3
"""Explore how ingredients work in image generation mode (Создать изображение)."""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
EXPLORE_DIR = PROJECT_ROOT / "output" / "explore"
REFS_DIR = PROJECT_ROOT / "refs"

AUTO_PROJECT_URL = "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869"


def screenshot(page, name):
    path = EXPLORE_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=False)
    print(f"  Screenshot: {path}")


def dump(page, name):
    elements = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('button, [role="button"], input, textarea, [role="combobox"], [role="option"], [role="menu"], [role="dialog"], [role="menuitem"], div[class], label').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) return;
            const text = (el.textContent || '').trim().substring(0, 150);
            if (!text && el.tagName !== 'INPUT') return;
            results.push({
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role') || '',
                text,
                ariaLabel: el.getAttribute('aria-label') || '',
                placeholder: el.getAttribute('placeholder') || '',
                x: Math.round(rect.x), y: Math.round(rect.y),
                w: Math.round(rect.width), h: Math.round(rect.height),
            });
        });
        return results;
    }""")
    path = EXPLORE_DIR / f"{name}_elements.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(elements, f, ensure_ascii=False, indent=2)
    # Filter to bottom area (prompt bar) elements
    bottom = [el for el in elements if el['y'] > 500]
    print(f"  Bottom area elements ({len(bottom)}):")
    for el in bottom:
        print(f"    [{el['tag']:<8}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}  {el['text'][:80]}")


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
        time.sleep(8)

        # Make sure we're in image mode
        combo = page.query_selector('button[role="combobox"]')
        if combo:
            combo_text = combo.text_content() or ""
            if "Создать изображение" not in combo_text:
                combo.click()
                time.sleep(1)
                opt = page.query_selector('div[role="option"]:has-text("Создать изображение")')
                if opt:
                    opt.click()
                    time.sleep(2)

        print("\n=== Image mode — before clicking + ===")
        screenshot(page, "40_image_mode_before_add")
        dump(page, "40_image_mode_before_add")

        # Click the "+" button
        print("\n=== Clicking + button ===")
        add_btn = page.query_selector('button:has-text("add")')
        # Find the correct one (near bottom)
        for btn in page.query_selector_all('button'):
            text = (btn.text_content() or "").strip()
            box = btn.bounding_box()
            if text == "add" and box and box['y'] > 700:
                print(f"  Clicking add at ({box['x']:.0f}, {box['y']:.0f})")
                btn.click()
                time.sleep(3)
                break

        print("\n=== After clicking + ===")
        screenshot(page, "41_image_after_add")
        dump(page, "41_image_after_add")

        # Look for any new elements that appeared (popup, panel, menu)
        print("\n=== Looking for upload/ingredient elements ===")
        new_elements = page.evaluate("""() => {
            const results = [];
            // Search ALL elements for upload-related content or new panels
            document.querySelectorAll('*').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;
                const text = (el.textContent || '').trim();
                const role = el.getAttribute('role') || '';
                // Check if it's a menu, dialog, popup, or has upload text
                if (role === 'menu' || role === 'dialog' || role === 'menuitem' ||
                    text.includes('Загруз') || text.includes('upload') ||
                    text.includes('ингредиент') || text.includes('ingredient')) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        role,
                        text: text.substring(0, 200),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"  Found {len(new_elements)} upload/ingredient elements:")
        for el in new_elements:
            print(f"    [{el['tag']}] role={el['role']} ({el['x']},{el['y']}) {el['w']}x{el['h']}: {el['text'][:80]}")

        # Check for file inputs
        file_inputs = page.query_selector_all('input[type="file"]')
        print(f"\n  File input elements: {len(file_inputs)}")
        for fi in file_inputs:
            print(f"    accept={fi.get_attribute('accept')} multiple={fi.get_attribute('multiple')}")

        # Maybe the "+" in image mode opens an ingredient area ABOVE the prompt bar
        # Let me check for elements between y=400 and y=800
        mid_elements = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button, div[role], input, img').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;
                if (rect.y > 400 && rect.y < 800) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        role: el.getAttribute('role') || '',
                        text: (el.textContent || '').trim().substring(0, 100),
                        src: el.getAttribute('src') || '',
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"\n  Mid-page elements (y 400-800): {len(mid_elements)}")
        for el in mid_elements:
            extra = f" src={el['src'][:50]}" if el['src'] else ""
            print(f"    [{el['tag']}] ({el['x']},{el['y']}) {el['w']}x{el['h']}: {el['text'][:60]}{extra}")

        # Close the ingredient area (click X)
        print("\n=== Closing ingredient area ===")
        close_btn = None
        for btn in page.query_selector_all('button'):
            text = (btn.text_content() or "").strip()
            box = btn.bounding_box()
            if text == "close" and box and box['y'] > 700:
                close_btn = btn
                break
        if close_btn:
            close_btn.click()
            time.sleep(1)
            print("  Closed.")

        # === Now try a DIFFERENT approach: use "Видео по образцам" mode (Ingredients to Video) ===
        # This mode might have a more explicit ingredient upload UI
        print("\n=== Switching to 'Видео по образцам' (Ingredients to Video) ===")
        combo = page.query_selector('button[role="combobox"]')
        if combo:
            combo.click()
            time.sleep(1)
            opt = page.query_selector('div[role="option"]:has-text("Видео по образцам")')
            if opt:
                opt.click()
                time.sleep(2)
                screenshot(page, "42_ingredients_video_mode")
                dump(page, "42_ingredients_video_mode")

                # Click + in this mode
                for btn in page.query_selector_all('button'):
                    text = (btn.text_content() or "").strip()
                    box = btn.bounding_box()
                    if text == "add" and box and box['y'] > 700:
                        print(f"  Clicking add in ingredients mode at ({box['x']:.0f}, {box['y']:.0f})")
                        btn.click()
                        time.sleep(3)
                        screenshot(page, "43_ingredients_after_add")
                        dump(page, "43_ingredients_after_add")
                        break

        # Wait for manual observation
        print("\n=== Browser open for 30s ===")
        time.sleep(30)
        ctx.close()
        print("Done.")


if __name__ == "__main__":
    main()
