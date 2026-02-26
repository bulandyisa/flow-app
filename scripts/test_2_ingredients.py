#!/usr/bin/env python3
"""
Test: upload exactly 2 ingredients vs 1 location-only to pinpoint the issue.
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

PROMPT = "A boy sitting at a workbench with a radio. 3D Pixar-style animation, cinematic."

CHAR_FILE = PROJECT_ROOT / "персонажи" / "char_karim_full.jpeg"
LOC_FILE = PROJECT_ROOT / "локации" / "loc_garazh_inside.jpg"


def upload_ingredient(page, file_path):
    """Upload one ingredient using JS clicks."""
    # Click '+' button
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim();
            const rect = btn.getBoundingClientRect();
            if (text === 'add' && rect.y > 750 && rect.width > 40 && rect.width < 100) {
                btn.click();
                return true;
            }
        }
        return false;
    }""")
    time.sleep(2)

    # Wait for panel
    for _ in range(5):
        has = page.evaluate("""() => {
            const inp = document.querySelector('input[type="file"]');
            return !!inp;
        }""")
        if has:
            break
        time.sleep(1)

    # Upload
    file_input = page.query_selector('input[type="file"]')
    if file_input:
        file_input.set_input_files(str(file_path))
        print(f"  Uploaded: {file_path.name}")
    else:
        print(f"  ERROR: file input not found for {file_path.name}")
        # Try reopening panel
        page.keyboard.press("Escape")
        time.sleep(1)
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = btn.textContent.trim();
                const rect = btn.getBoundingClientRect();
                if (text === 'add' && rect.y > 750 && rect.width > 40 && rect.width < 100) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }""")
        time.sleep(2)
        file_input = page.query_selector('input[type="file"]')
        if file_input:
            file_input.set_input_files(str(file_path))
            print(f"  Uploaded (retry): {file_path.name}")
        else:
            print(f"  FAILED to upload {file_path.name}")
            return False

    time.sleep(2)

    # Handle crop dialog
    for _ in range(10):
        saved = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = btn.textContent.trim();
                if (text.includes('Кадрировать и сохранить') || text.includes('Crop and save')) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }""")
        if saved:
            print(f"  Crop saved")
            break
        time.sleep(1)

    time.sleep(2)
    return True


def try_generate(page, prompt, prefix):
    """Fill prompt and generate."""
    # Close any overlay first
    page.keyboard.press("Escape")
    time.sleep(0.5)

    textarea = page.query_selector("textarea")
    if textarea:
        textarea.click()
        textarea.fill("")
        time.sleep(0.3)
        textarea.fill(prompt)
    time.sleep(0.5)

    # Screenshot before
    page.screenshot(path=str(SCREENSHOTS_DIR / f"{prefix}_before.png"))

    # Click Generate via JS
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim();
            if (text.includes('Генерировать') || text.includes('Generate')) {
                btn.click();
                return true;
            }
        }
        // Try submit via Enter on textarea
        const ta = document.querySelector('textarea');
        if (ta) {
            ta.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', ctrlKey: true, bubbles: true}));
        }
        return false;
    }""")
    print(f"  Generating...")

    for i in range(30):
        time.sleep(5)
        err = page.evaluate("""() => {
            const els = document.querySelectorAll('div, span');
            for (const el of els) {
                const text = (el.textContent || '').trim();
                const rect = el.getBoundingClientRect();
                if (text === 'Что-то пошло не так.' && rect.height > 0 && rect.height < 200 && rect.width > 100) {
                    return true;
                }
            }
            return false;
        }""")
        if err:
            print(f"  ERROR after {(i+1)*5}s")
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{prefix}_error.png"))
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent.includes('Закрыть')) btn.click();
                }
            }""")
            time.sleep(1)
            return False

        loading = page.query_selector('[role="progressbar"]')
        if not loading and i > 2:
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{prefix}_success.png"))
            print(f"  SUCCESS after ~{(i+1)*5}s!")
            return True

    print("  TIMEOUT")
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

    # TEST 1: Only location ingredient
    print("=== TEST 1: 1 ingredient (location only) ===")
    page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)
    time.sleep(3)

    upload_ingredient(page, LOC_FILE)
    r1 = try_generate(page, PROMPT, "test_loc_only")
    print(f"  Result: {'OK' if r1 else 'FAIL'}\n")

    # TEST 2: 2 ingredients (char + location)
    print("=== TEST 2: 2 ingredients (char + location) ===")
    page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)
    time.sleep(3)

    upload_ingredient(page, CHAR_FILE)
    time.sleep(1)
    upload_ingredient(page, LOC_FILE)
    r2 = try_generate(page, PROMPT, "test_2ing")
    print(f"  Result: {'OK' if r2 else 'FAIL'}\n")

    # TEST 3: If test 2 failed, try a very different image as 2nd ingredient
    if not r2:
        print("=== TEST 3: 2 different ingredients ===")
        page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(3)

        upload_ingredient(page, CHAR_FILE)
        # Use a different location image
        alt_loc = PROJECT_ROOT / "локации" / "loc_garazh_outside.jpg"
        if alt_loc.exists():
            time.sleep(1)
            upload_ingredient(page, alt_loc)
            r3 = try_generate(page, PROMPT, "test_2ing_alt")
            print(f"  Result: {'OK' if r3 else 'FAIL'}")
        else:
            print(f"  Alt location not found: {alt_loc}")

    print("\nSummary:")
    print(f"  1 ingredient (location):  {'OK' if r1 else 'FAIL'}")
    print(f"  2 ingredients (char+loc): {'OK' if r2 else 'FAIL'}")

    ctx.close()
    p.stop()


if __name__ == "__main__":
    main()
