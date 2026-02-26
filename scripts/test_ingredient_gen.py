#!/usr/bin/env python3
"""
Minimal test: upload 1 ingredient, generate, check result.
Uses JS clicks for crop dialog (same as flow_bot.py).
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
INGREDIENT = PROJECT_ROOT / "персонажи" / "char_karim_full.jpeg"


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
    print("Flow ready")

    # Ensure image mode
    combo = page.query_selector('button[role="combobox"]')
    if combo:
        current = (combo.text_content() or "").replace("arrow_drop_down", "").strip()
        print(f"Mode: {current}")

    # Upload 1 ingredient
    print(f"\nUploading ingredient: {INGREDIENT.name}")

    # Click '+' button for ingredients
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
        has_upload = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                if (btn.textContent.includes('Загрузить')) return true;
            }
            return false;
        }""")
        if has_upload:
            break
        time.sleep(1)

    # Upload via file input
    file_input = page.query_selector('input[type="file"]')
    if file_input:
        file_input.set_input_files(str(INGREDIENT))
        print("  Set input files")
    else:
        print("  ERROR: file input not found!")
        ctx.close()
        p.stop()
        return

    time.sleep(2)

    # Handle crop dialog via JS (same approach as flow_bot.py)
    for attempt in range(10):
        saved = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = btn.textContent.trim();
                if (text.includes('Кадрировать и сохранить') || text.includes('Crop and save') ||
                    (text.includes('Сохранить') && !text.includes('Настройки'))) {
                    btn.click();
                    return text;
                }
            }
            return null;
        }""")
        if saved:
            print(f"  Crop saved: {saved}")
            break
        time.sleep(1)
    else:
        print("  Crop dialog not found after 10s, pressing Escape")
        page.keyboard.press("Escape")

    time.sleep(2)

    # Close ingredient panel (press Escape)
    page.keyboard.press("Escape")
    time.sleep(1)

    # Screenshot to see state
    page.screenshot(path=str(SCREENSHOTS_DIR / "test_ing_before_gen.png"))

    # Fill prompt
    textarea = page.query_selector("textarea")
    if textarea:
        textarea.click()
        textarea.fill(PROMPT)
        print(f"  Prompt filled")
    time.sleep(0.5)

    # Click Generate via JS (avoid crop dialog blocking)
    gen_clicked = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim();
            if (text.includes('Генерировать') || text.includes('Generate')) {
                const rect = btn.getBoundingClientRect();
                if (rect.y > 700) {
                    btn.click();
                    return {text: text, y: Math.round(rect.y)};
                }
            }
        }
        return null;
    }""")
    print(f"  Generate: {gen_clicked}")

    # Wait for result
    print("  Waiting for generation...")
    for i in range(30):
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
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_ing_error.png"))
            # Dismiss
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent.includes('Закрыть')) { btn.click(); return; }
                }
            }""")
            break

        # Check gallery for new images
        new_imgs = page.evaluate("""() => {
            const imgs = document.querySelectorAll('img[src*="blob:"], img[src*="lh3.googleusercontent"]');
            return imgs.length;
        }""")

        if i > 2 and i % 4 == 0:
            print(f"    ...{(i+1)*5}s elapsed, gallery images: {new_imgs}")

        loading = page.query_selector('[role="progressbar"]')
        if not loading and i > 3:
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_ing_success.png"))
            print(f"  SUCCESS after ~{(i+1)*5}s! Gallery images: {new_imgs}")
            break

    page.screenshot(path=str(SCREENSHOTS_DIR / "test_ing_final.png"))
    ctx.close()
    p.stop()
    print("Done.")


if __name__ == "__main__":
    main()
