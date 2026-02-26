#!/usr/bin/env python3
"""
Test: generate with exactly 1 ingredient to isolate the issue.
Then try 2 ingredients.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "screenshots"
INGREDIENTS_DIR = PROJECT_ROOT

ACCOUNT = {
    "session_dir": PROJECT_ROOT / ".session_2",
    "project_url": "https://labs.google/fx/ru/tools/flow/project/492b843c-217a-4c83-8c2d-4e0b0f0b1dc8",
}

PROMPT = "Extreme close-up of a homemade radio receiver on a workbench. A hand reaches for the tuning dial. Wires, exposed circuit boards, a small blinking green indicator light. Dim single-lamp lighting, deep shadows. 3D Pixar-style animation, soft volumetric lighting, cinematic."


def upload_ingredient(page, file_path):
    """Upload a single ingredient image."""
    # Click the '+' ingredient button
    clicked = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim();
            const rect = btn.getBoundingClientRect();
            if (text === 'add' && rect.y > 750 && rect.width > 40 && rect.width < 100) {
                btn.click();
                return {y: Math.round(rect.y), w: Math.round(rect.width)};
            }
        }
        return null;
    }""")

    if not clicked:
        print("  '+' button not found!")
        return False

    print(f"  Clicked '+' button (y={clicked['y']})")
    time.sleep(2)

    # Wait for ingredient panel
    for attempt in range(3):
        panel_loaded = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = btn.textContent.trim();
                if (text.includes('Загрузить') || text.includes('Upload')) {
                    return true;
                }
            }
            return false;
        }""")
        if panel_loaded:
            break
        time.sleep(2)

    # Upload via input[type=file]
    file_input = page.query_selector('input[type="file"]')
    if file_input:
        file_input.set_input_files(str(file_path))
        print(f"  Uploaded: {file_path.name}")
        time.sleep(2)

        # Handle crop dialog
        crop_btn = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = btn.textContent.trim();
                if (text.includes('Кадрировать и сохранить') || text.includes('Crop and save') || text.includes('Сохранить')) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }""")
        if crop_btn:
            print("  Crop dialog: saved")
        time.sleep(2)
        return True
    else:
        print("  File input not found!")
        page.keyboard.press("Escape")
        return False


def try_generate(page, prefix):
    """Generate and wait for result."""
    textarea = page.query_selector("textarea")
    textarea.fill("")
    time.sleep(0.3)
    textarea.fill(PROMPT)
    time.sleep(0.5)

    gen_btn = page.query_selector('button:has-text("Генерировать")')
    if not gen_btn:
        gen_btn = page.query_selector('button:has-text("Generate")')
    if gen_btn:
        gen_btn.click()
        print("  Clicked Generate")
    else:
        print("  Generate button not found!")
        return False

    for i in range(24):
        time.sleep(5)
        err = page.evaluate("""() => {
            const els = document.querySelectorAll('div, span, p');
            for (const el of els) {
                const text = (el.textContent || '').trim();
                const rect = el.getBoundingClientRect();
                if ((text === 'Что-то пошло не так.' || text === 'Something went wrong') &&
                    rect.height > 0 && rect.height < 200) {
                    return text;
                }
            }
            return null;
        }""")
        if err:
            print(f"  ERROR after {(i+1)*5}s: {err}")
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{prefix}_error.png"))
            close_btn = page.query_selector('button:has-text("Закрыть")')
            if close_btn:
                close_btn.click()
                time.sleep(1)
            return False

        loading = page.query_selector('[class*="loading"], [class*="spinner"], [role="progressbar"]')
        if not loading and i > 2:
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{prefix}_success.png"))
            print(f"  SUCCESS after ~{(i+1)*5}s!")
            return True

    print(f"  TIMEOUT")
    return False


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
    page.wait_for_load_state("networkidle", timeout=30000)
    time.sleep(3)
    print("Flow opened on account 2")

    # Ensure image mode
    combo = page.query_selector('button[role="combobox"]')
    if combo:
        current = (combo.text_content() or "").replace("arrow_drop_down", "").strip()
        if "изображение" not in current.lower():
            combo.click()
            time.sleep(1)
            opt = page.query_selector('div[role="option"]:has-text("Создать изображение")')
            if opt:
                opt.click()
                time.sleep(2)

    # Test 1: One ingredient (character)
    print("\n=== TEST 1: 1 ingredient (char_karim_full.jpeg) ===")
    char_file = INGREDIENTS_DIR / "персонажи" / "char_karim_full.jpeg"
    if char_file.exists():
        upload_ingredient(page, char_file)
        result1 = try_generate(page, "test_1ing")
    else:
        print(f"  File not found: {char_file}")
        result1 = False

    # Reload page to clear state for test 2
    if result1:
        print("\n=== TEST 2: 2 ingredients (char + location) ===")
        page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(3)

        loc_file = INGREDIENTS_DIR / "локации" / "loc_garazh_inside.jpg"
        upload_ingredient(page, char_file)
        time.sleep(1)
        upload_ingredient(page, loc_file)
        result2 = try_generate(page, "test_2ing")
    else:
        # If 1 ingredient fails, try with 0 again to confirm baseline
        print("\n1 ingredient FAILED. Reload and try with 0...")
        page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(3)
        result0 = try_generate(page, "test_0ing_confirm")

    ctx.close()
    p.stop()
    print("\nDone.")


if __name__ == "__main__":
    main()
