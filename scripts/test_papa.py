#!/usr/bin/env python3
"""
Test: generate S03_B (papa in office) on account 2.
Different scene, different ingredients.
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

PROMPT = "Medium shot of a home office, evening. A man sits at a desk, writing with a pen. Focused expression. Warm desk lamp lighting. 3D Pixar-style animation, soft volumetric lighting, cinematic."
CHAR_FILE = PROJECT_ROOT / "персонажи" / "char_papa_full.jpeg"
LOC_FILE = PROJECT_ROOT / "локации" / "loc_kabinet_full.jpg"


def upload_ingredient(page, file_path):
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

    for _ in range(5):
        fi = page.query_selector('input[type="file"]')
        if fi:
            break
        time.sleep(1)

    fi = page.query_selector('input[type="file"]')
    if not fi:
        print(f"  No file input for {file_path.name}, retrying...")
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
        fi = page.query_selector('input[type="file"]')

    if fi:
        fi.set_input_files(str(file_path))
        print(f"  Uploaded: {file_path.name}")
    else:
        print(f"  FAILED to upload {file_path.name}")
        return False

    time.sleep(2)

    # Crop
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


def main():
    # Check files exist
    for f in [CHAR_FILE, LOC_FILE]:
        if not f.exists():
            print(f"File not found: {f}")
            return

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
    print("Flow ready (account 2)\n")

    # Upload 2 ingredients
    print("Uploading papa character...")
    upload_ingredient(page, CHAR_FILE)
    time.sleep(1)
    print("Uploading office location...")
    upload_ingredient(page, LOC_FILE)

    # Close panel
    page.keyboard.press("Escape")
    time.sleep(1)

    # Fill prompt
    textarea = page.query_selector("textarea")
    if textarea:
        textarea.click()
        textarea.fill(PROMPT)
    time.sleep(0.5)

    page.screenshot(path=str(SCREENSHOTS_DIR / "test_papa_before.png"))

    # Generate
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim();
            if (text.includes('Генерировать') || text.includes('Generate')) {
                btn.click();
                return true;
            }
        }
        return false;
    }""")
    print("Generating S03_B (papa in office)...")

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
            print(f"ERROR after {(i+1)*5}s")
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_papa_error.png"))
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent.includes('Закрыть')) btn.click();
                }
            }""")
            time.sleep(1)

            # Try WITHOUT ingredients
            print("\nRetrying WITHOUT ingredients...")
            page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            time.sleep(5)

            textarea = page.query_selector("textarea")
            if textarea:
                textarea.click()
                textarea.fill(PROMPT)
            time.sleep(0.5)

            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent.includes('Генерировать') || btn.textContent.includes('Generate')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }""")

            for j in range(24):
                time.sleep(5)
                err2 = page.evaluate("""() => {
                    const els = document.querySelectorAll('div, span');
                    for (const el of els) {
                        const text = (el.textContent || '').trim();
                        const rect = el.getBoundingClientRect();
                        if (text === 'Что-то пошло не так.' && rect.height > 0 && rect.height < 200 && rect.width > 100) {
                            return true;
                        }
                    }
                    return null;
                }""")
                if err2:
                    print(f"ERROR (no ingredients) after {(j+1)*5}s — Flow is down again")
                    break
                loading = page.query_selector('[role="progressbar"]')
                if not loading and j > 2:
                    page.screenshot(path=str(SCREENSHOTS_DIR / "test_papa_no_ing_ok.png"))
                    print(f"OK (no ingredients) after ~{(j+1)*5}s!")
                    break
            break

        loading = page.query_selector('[role="progressbar"]')
        if not loading and i > 2:
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_papa_success.png"))
            print(f"SUCCESS after ~{(i+1)*5}s!")
            break

    ctx.close()
    p.stop()
    print("Done.")


if __name__ == "__main__":
    main()
