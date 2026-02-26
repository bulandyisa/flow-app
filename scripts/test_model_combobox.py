#!/usr/bin/env python3
"""
Switch model via Settings panel combobox.
The model selector is a button[role="combobox"] containing 'Модель' at y~604.
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

CHAR_FILE = PROJECT_ROOT / "персонажи" / "char_karim_full.jpeg"
LOC_FILE = PROJECT_ROOT / "локации" / "loc_garazh_inside.jpg"
PROMPT = "Extreme close-up of a homemade radio receiver on a workbench. A hand reaches for the tuning dial. Wires, exposed circuit boards, a small blinking green indicator light. Dim single-lamp lighting, deep shadows. 3D Pixar-style animation, soft volumetric lighting, cinematic."


def open_settings(page):
    """Open Settings panel."""
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim().toLowerCase();
            const rect = btn.getBoundingClientRect();
            if ((text.includes('tune') || text === 'tune') && rect.y > 600 && rect.width < 100) {
                btn.click();
                return true;
            }
        }
        return false;
    }""")
    time.sleep(1.5)


def switch_model(page, target_model):
    """Switch model in Settings panel.

    target_model: 'Imagen 4', 'Nano Banana', 'Nano Banana Pro'
    """
    print(f"\n  Switching to: {target_model}")

    # Open settings
    open_settings(page)
    time.sleep(1)

    # Find and click the model combobox (button[role="combobox"] containing 'Модель')
    clicked = page.evaluate("""() => {
        const combos = document.querySelectorAll('button[role="combobox"]');
        for (const combo of combos) {
            const text = (combo.textContent || '').trim();
            if (text.includes('Модель') || text.includes('Model')) {
                combo.click();
                return {text: text.substring(0, 50), y: Math.round(combo.getBoundingClientRect().y)};
            }
        }
        return null;
    }""")

    if not clicked:
        print("  Model combobox not found!")
        page.keyboard.press("Escape")
        return False

    print(f"  Clicked model combobox: {clicked}")
    time.sleep(1)

    page.screenshot(path=str(SCREENSHOTS_DIR / "model_combobox_open.png"))

    # Find the dropdown options
    options = page.evaluate("""() => {
        const opts = document.querySelectorAll('div[role="option"]');
        return Array.from(opts).map(o => ({
            text: (o.textContent || '').trim(),
            y: Math.round(o.getBoundingClientRect().y),
            selected: o.getAttribute('aria-selected') || ''
        }));
    }""")
    print(f"  Options: {options}")

    # Click target model
    selected = page.evaluate("""(targetModel) => {
        const opts = document.querySelectorAll('div[role="option"]');
        for (const opt of opts) {
            const text = (opt.textContent || '').trim();
            // For 'Nano Banana' need to NOT match 'Nano Banana Pro'
            if (targetModel === 'Nano Banana') {
                if (text.includes('Nano Banana') && !text.includes('Pro')) {
                    opt.click();
                    return {selected: true, text: text};
                }
            } else {
                if (text.includes(targetModel)) {
                    opt.click();
                    return {selected: true, text: text};
                }
            }
        }
        return {selected: false};
    }""", target_model)

    print(f"  Selected: {selected}")
    time.sleep(1)

    # Close settings
    page.keyboard.press("Escape")
    time.sleep(0.5)

    return selected.get('selected', False)


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
        if fi: break
        time.sleep(1)

    fi = page.query_selector('input[type="file"]')
    if not fi:
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
        print(f"    Uploaded: {file_path.name}")
    else:
        print(f"    FAILED: {file_path.name}")
        return False

    time.sleep(2)
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
            print(f"    Crop saved")
            break
        time.sleep(1)
    time.sleep(2)
    return True


def try_generate(page, prompt, prefix, with_ingredients=True):
    if with_ingredients:
        upload_ingredient(page, CHAR_FILE)
        time.sleep(1)
        upload_ingredient(page, LOC_FILE)
        page.keyboard.press("Escape")
        time.sleep(1)

    textarea = page.query_selector("textarea")
    if textarea:
        textarea.click()
        textarea.fill(prompt)
    time.sleep(0.5)

    page.screenshot(path=str(SCREENSHOTS_DIR / f"{prefix}_before.png"))

    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim();
            if (text.includes('Генерировать') || text.includes('Generate')) {
                btn.click(); return true;
            }
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
                if (text === 'Что-то пошло не так.' && rect.height > 0 && rect.height < 200 && rect.width > 100) return true;
            }
            return false;
        }""")
        if err:
            print(f"  ERROR after {(i+1)*5}s")
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{prefix}_error.png"))
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) { if (btn.textContent.includes('Закрыть')) btn.click(); }
            }""")
            return False

        loading = page.query_selector('[role="progressbar"]')
        if not loading and i > 2:
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{prefix}_success.png"))
            print(f"  SUCCESS after ~{(i+1)*5}s!")
            return True

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

    models = ["Imagen 4", "Nano Banana", "Nano Banana Pro"]
    results = {}

    for model in models:
        print(f"\n{'='*60}")
        print(f"  TESTING: {model} + S01_A ingredients")
        print(f"{'='*60}")

        page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        time.sleep(5)

        switched = switch_model(page, model)
        if not switched:
            results[model] = "switch_failed"
            continue

        time.sleep(2)

        prefix = f"gen_{model.replace(' ', '_').lower()}"
        ok = try_generate(page, PROMPT, prefix, with_ingredients=True)
        results[model] = "OK" if ok else "FAIL"

        print(f"  Waiting 45s...")
        time.sleep(45)

    print(f"\n{'='*60}")
    print(f"  RESULTS:")
    for m, r in results.items():
        print(f"    {m}: {r}")
    print(f"{'='*60}")

    ctx.close()
    p.stop()


if __name__ == "__main__":
    main()
