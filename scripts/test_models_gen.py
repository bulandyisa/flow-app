#!/usr/bin/env python3
"""
Test different image models: Imagen 4, Nano Banana, Nano Banana Pro.
Try S01_A (garage scene) with each to see which works.
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


def switch_image_model(page, model_name):
    """Click the model button near prompt bar, then select the target model.

    model_name: 'Imagen 4', 'Nano Banana', 'Nano Banana Pro'
    """
    print(f"\n  Switching to model: {model_name}")

    # Click the model button (near prompt bar, y > 700)
    clicked = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = (btn.textContent || '').trim();
            const rect = btn.getBoundingClientRect();
            if ((text.includes('Nano Banana') || text.includes('Imagen')) &&
                rect.y > 700 && rect.y < 800 && rect.x > 600) {
                btn.click();
                return {clicked: true, text: text, y: Math.round(rect.y)};
            }
        }
        return {clicked: false};
    }""")

    if not clicked.get('clicked'):
        print(f"  Model button not found!")
        return False

    print(f"  Clicked model button: {clicked.get('text')}")
    time.sleep(1.5)

    # Take screenshot to see dropdown
    page.screenshot(path=str(SCREENSHOTS_DIR / f"model_dropdown.png"))

    # Find and click the target model option
    # The dropdown should show radio buttons with model names
    selected = page.evaluate("""(targetModel) => {
        // Look for elements containing the model name
        const allEls = document.querySelectorAll('div, span, label, button, [role="option"], [role="radio"], [role="menuitem"]');
        const candidates = [];

        for (const el of allEls) {
            const text = (el.textContent || '').trim();
            const rect = el.getBoundingClientRect();

            if (rect.width === 0 || rect.height === 0) continue;
            if (text.length > 50) continue;  // Skip containers

            if (text.includes(targetModel)) {
                candidates.push({
                    text: text,
                    tag: el.tagName,
                    role: el.getAttribute('role') || '',
                    y: Math.round(rect.y),
                    x: Math.round(rect.x),
                    w: Math.round(rect.width),
                    h: Math.round(rect.height)
                });
            }
        }

        // Click the best candidate (smallest, most specific element)
        if (candidates.length > 0) {
            // Sort by area (smallest first)
            candidates.sort((a, b) => (a.w * a.h) - (b.w * b.h));

            // Click via coordinate
            const target = candidates[0];
            const clickEl = document.elementFromPoint(target.x + target.w/2, target.y + target.h/2);
            if (clickEl) {
                clickEl.click();
                return {selected: true, target: target, candidates: candidates.length};
            }
        }

        return {selected: false, candidates: candidates};
    }""", model_name)

    print(f"  Selection result: {selected}")
    time.sleep(1.5)

    # Close any remaining dropdown
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
        if fi:
            break
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
        print(f"  Uploaded: {file_path.name}")
    else:
        print(f"  FAILED to upload {file_path.name}")
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
            print(f"  Crop saved")
            break
        time.sleep(1)

    time.sleep(2)
    return True


def try_generate(page, prompt, prefix, with_ingredients=True):
    """Upload ingredients if needed, fill prompt, generate."""
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
                btn.click();
                return true;
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

    models_to_test = ["Imagen 4", "Nano Banana"]  # Skip Pro since that's what fails

    results = {}

    for model in models_to_test:
        print(f"\n{'='*60}")
        print(f"  TESTING: {model} with S01_A (garage + ingredients)")
        print(f"{'='*60}")

        # Fresh page load
        page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        time.sleep(5)

        # Switch model
        switched = switch_image_model(page, model)
        if not switched:
            print(f"  Could not switch to {model}")
            results[model] = "switch_failed"
            continue

        time.sleep(2)

        # Try generation with ingredients
        prefix = f"test_{model.replace(' ', '_').lower()}"
        result = try_generate(page, PROMPT, prefix, with_ingredients=True)
        results[model] = "OK" if result else "FAIL"

        # Wait between tests
        print(f"  Waiting 30s before next test...")
        time.sleep(30)

    # Also retry Nano Banana Pro with S01_A after cooldown
    print(f"\n{'='*60}")
    print(f"  TESTING: Nano Banana Pro (retry) with S01_A")
    print(f"{'='*60}")

    page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(5)

    # Make sure we're on Nano Banana Pro
    switch_image_model(page, "Nano Banana Pro")
    time.sleep(2)

    result_pro = try_generate(page, PROMPT, "test_nb_pro_retry", with_ingredients=True)
    results["Nano Banana Pro"] = "OK" if result_pro else "FAIL"

    print(f"\n{'='*60}")
    print(f"  RESULTS:")
    for model, result in results.items():
        print(f"    {model}: {result}")
    print(f"{'='*60}")

    ctx.close()
    p.stop()


if __name__ == "__main__":
    main()
