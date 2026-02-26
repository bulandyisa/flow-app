#!/usr/bin/env python3
"""
Test: generate S01_A prompt WITHOUT ingredients to see if it's the ingredients causing failures.
Uses account 2.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

ACCOUNT = {
    "session_dir": PROJECT_ROOT / ".session_2",
    "project_url": "https://labs.google/fx/ru/tools/flow/project/492b843c-217a-4c83-8c2d-4e0b0f0b1dc8",
}

S01_A_PROMPT = "Extreme close-up of a homemade radio receiver on a workbench. A hand reaches for the tuning dial. Wires, exposed circuit boards, a small blinking green indicator light. Dim single-lamp lighting, deep shadows. 3D Pixar-style animation, soft volumetric lighting, cinematic."


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

    # Ensure we're in image mode
    combo = page.query_selector('button[role="combobox"]')
    if combo:
        current = (combo.text_content() or "").replace("arrow_drop_down", "").strip()
        print(f"Current mode: {current}")
        if "изображение" not in current.lower():
            combo.click()
            time.sleep(1)
            opt = page.query_selector('div[role="option"]:has-text("Создать изображение")')
            if opt:
                opt.click()
                time.sleep(2)

    # Clear any existing prompt
    textarea = page.query_selector("textarea")
    if textarea:
        textarea.fill("")
        time.sleep(0.5)

    # Fill our prompt (NO ingredients!)
    print(f"Prompt: {S01_A_PROMPT[:80]}...")
    textarea = page.query_selector("textarea")
    textarea.click()
    textarea.fill(S01_A_PROMPT)
    time.sleep(0.5)

    # Screenshot before generation
    page.screenshot(path=str(SCREENSHOTS_DIR / "test_no_ing_before.png"))

    # Click Generate
    gen_btn = page.query_selector('button:has-text("Генерировать")')
    if not gen_btn:
        gen_btn = page.query_selector('button:has-text("Generate")')
    if gen_btn:
        gen_btn.click()
        print("Clicked Generate (no ingredients)")
    else:
        print("Generate button not found!")
        ctx.close()
        p.stop()
        return

    # Wait for result
    for i in range(24):  # 2 minutes max
        time.sleep(5)
        # Check for error
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
            print(f"ERROR after {(i+1)*5}s: {err}")
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_no_ing_error.png"))
            # Dismiss
            close_btn = page.query_selector('button:has-text("Закрыть")')
            if close_btn:
                close_btn.click()
                time.sleep(1)

            # Try again with shorter prompt
            print("\nRetrying with SHORT prompt: 'A boy looking at a radio. 3D Pixar animation.'")
            textarea = page.query_selector("textarea")
            textarea.fill("")
            time.sleep(0.3)
            textarea.fill("A boy looking at a radio. 3D Pixar animation.")
            time.sleep(0.5)
            gen_btn = page.query_selector('button:has-text("Генерировать")')
            if not gen_btn:
                gen_btn = page.query_selector('button:has-text("Generate")')
            if gen_btn:
                gen_btn.click()
                print("Clicked Generate (short prompt)")

            # Wait again
            for j in range(24):
                time.sleep(5)
                err2 = page.evaluate("""() => {
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
                if err2:
                    print(f"ERROR (short) after {(j+1)*5}s: {err2}")
                    page.screenshot(path=str(SCREENSHOTS_DIR / "test_no_ing_short_error.png"))
                    break
                # Check for new images in gallery
                loading = page.query_selector('[class*="loading"], [class*="spinner"], [role="progressbar"]')
                if not loading and j > 2:
                    page.screenshot(path=str(SCREENSHOTS_DIR / "test_no_ing_short_success.png"))
                    print(f"SHORT prompt SUCCESS after ~{(j+1)*5}s!")
                    break
            break

        # Check for completion (no loading)
        loading = page.query_selector('[class*="loading"], [class*="spinner"], [role="progressbar"]')
        if not loading and i > 2:
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_no_ing_success.png"))
            print(f"SUCCESS after ~{(i+1)*5}s!")
            break

    ctx.close()
    p.stop()
    print("Done.")


if __name__ == "__main__":
    main()
