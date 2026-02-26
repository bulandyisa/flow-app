#!/usr/bin/env python3
"""Wait 60s, then try 1 ingredient (char). If fails, try fresh page."""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "screenshots"

ACCOUNT = {
    "session_dir": PROJECT_ROOT / ".session_2",
    "project_url": "https://labs.google/fx/ru/tools/flow/project/492b843c-217a-4c83-8c2d-4e0b0f0b1dc8",
}

CHAR_FILE = PROJECT_ROOT / "персонажи" / "char_karim_full.jpeg"
PROMPT = "A boy sitting at a workbench with a radio. 3D Pixar-style animation, cinematic."


def upload_and_generate(page, ingredient_path, prompt, prefix):
    """Upload ingredient, fill prompt, generate, return True/False."""
    # Upload ingredient
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

    # Wait for file input
    for _ in range(5):
        fi = page.query_selector('input[type="file"]')
        if fi:
            break
        time.sleep(1)

    fi = page.query_selector('input[type="file"]')
    if fi:
        fi.set_input_files(str(ingredient_path))
        print(f"  Uploaded: {ingredient_path.name}")
    else:
        print("  File input not found!")
        return False

    time.sleep(2)

    # Crop save
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
            print("  Crop saved")
            break
        time.sleep(1)

    time.sleep(2)
    page.keyboard.press("Escape")
    time.sleep(1)

    # Fill prompt
    textarea = page.query_selector("textarea")
    if textarea:
        textarea.click()
        textarea.fill(prompt)
    time.sleep(0.5)

    # Screenshot
    page.screenshot(path=str(SCREENSHOTS_DIR / f"{prefix}_before.png"))

    # Generate via JS
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
    print("  Generating...")

    for i in range(24):
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
            return False

        loading = page.query_selector('[role="progressbar"]')
        if not loading and i > 2:
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{prefix}_success.png"))
            print(f"  SUCCESS after ~{(i+1)*5}s!")
            return True

    return False


def main():
    print("Waiting 60s before test (cooldown)...")
    time.sleep(60)

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
    print("Flow ready\n")

    print("=== Test: 1 ingredient (char_karim) ===")
    r1 = upload_and_generate(page, CHAR_FILE, PROMPT, "test_1ing_wait")

    if not r1:
        # Try with account 1 instead
        print("\n=== Retrying on account 1 ===")
        ctx.close()
        time.sleep(5)

        acct1 = {
            "session_dir": PROJECT_ROOT / ".session",
            "project_url": "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869",
        }
        ctx = p.chromium.launch_persistent_context(
            str(acct1["session_dir"]),
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="ru-RU",
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(acct1["project_url"], wait_until="domcontentloaded", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(3)
        print("Flow ready (account 1)\n")

        r2 = upload_and_generate(page, CHAR_FILE, PROMPT, "test_1ing_acct1")
        print(f"Account 1 result: {'OK' if r2 else 'FAIL'}")

    ctx.close()
    p.stop()
    print(f"\nFinal: {'OK' if r1 else 'FAIL'}")


if __name__ == "__main__":
    main()
