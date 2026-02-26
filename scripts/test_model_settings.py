#!/usr/bin/env python3
"""
Switch model via Settings panel: click tune button → find 'Модель' dropdown → select target.
Then test generation with each model.
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
    """Open Settings panel via tune button."""
    result = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim().toLowerCase();
            const rect = btn.getBoundingClientRect();
            if ((text.includes('tune') || text === 'tune' ||
                 text.includes('settings') || text.includes('настройки')) &&
                rect.y > 600 && rect.width < 100) {
                btn.click();
                return {clicked: true, text: text, y: Math.round(rect.y), x: Math.round(rect.x)};
            }
        }
        // Fallback: icon
        const icons = document.querySelectorAll('[class*="icon"], .material-icons, .material-symbols');
        for (const icon of icons) {
            const text = icon.textContent.trim().toLowerCase();
            const rect = icon.getBoundingClientRect();
            if ((text === 'tune' || text === 'settings') && rect.y > 600) {
                icon.click();
                return {clicked: true, text: text, y: Math.round(rect.y), via: 'icon'};
            }
        }
        return {clicked: false};
    }""")
    time.sleep(1.5)
    return result.get('clicked', False)


def switch_model(page, model_name):
    """In the Settings panel, click the 'Модель' dropdown and select model_name."""
    print(f"  Switching model to: {model_name}")

    # Open settings
    if not open_settings(page):
        print("  ERROR: Settings button not found")
        return False

    time.sleep(1)
    page.screenshot(path=str(SCREENSHOTS_DIR / "settings_opened.png"))

    # Click the 'Модель' dropdown
    clicked_dropdown = page.evaluate("""() => {
        // Find the 'Модель' label and the dropdown near it
        const allEls = document.querySelectorAll('*');
        let modelLabel = null;
        for (const el of allEls) {
            const text = (el.textContent || '').trim();
            if (text === 'Модель' || text === 'Model') {
                const rect = el.getBoundingClientRect();
                if (rect.height > 0 && rect.height < 50 && rect.width < 200) {
                    modelLabel = {y: rect.y, x: rect.x, text: text};
                    break;
                }
            }
        }

        if (!modelLabel) {
            return {error: 'Model label not found'};
        }

        // Find a clickable element near the model label (dropdown/select)
        for (const el of allEls) {
            const rect = el.getBoundingClientRect();
            if (Math.abs(rect.y - modelLabel.y) < 80 &&
                rect.width > 150 && rect.height > 20 && rect.height < 80 &&
                (el.tagName === 'BUTTON' || el.tagName === 'SELECT' ||
                 el.getAttribute('role') === 'combobox' || el.getAttribute('role') === 'listbox' ||
                 el.getAttribute('role') === 'button')) {
                el.click();
                return {clicked: true, tag: el.tagName, role: el.getAttribute('role') || '',
                        text: (el.textContent || '').trim().substring(0, 50),
                        y: Math.round(rect.y)};
            }
        }

        // Fallback: click the container div that contains the model name
        for (const el of allEls) {
            const text = (el.textContent || '').trim();
            const rect = el.getBoundingClientRect();
            if ((text.includes('Nano Banana') || text.includes('Imagen')) &&
                Math.abs(rect.y - modelLabel.y) < 80 &&
                rect.height > 20 && rect.height < 80 && rect.width > 150) {
                el.click();
                return {clicked: true, tag: el.tagName, text: text.substring(0, 50),
                        y: Math.round(rect.y), via: 'text_match'};
            }
        }

        return {error: 'Model dropdown not found', label: modelLabel};
    }""")

    print(f"  Dropdown click: {clicked_dropdown}")

    if clicked_dropdown.get('error'):
        page.keyboard.press("Escape")
        return False

    time.sleep(1.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / "model_dropdown_open.png"))

    # Now select the target model from the dropdown options
    selected = page.evaluate("""(targetModel) => {
        // Look for options/items containing the target model name
        const allEls = document.querySelectorAll('div[role="option"], li[role="option"], [role="menuitem"], [role="radio"], option, li, div');
        const candidates = [];

        for (const el of allEls) {
            const text = (el.textContent || '').trim();
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            if (text.length > 50) continue;

            // Exact match: target model name should be in the text
            if (text.includes(targetModel)) {
                // For "Nano Banana" vs "Nano Banana Pro" — need exact match
                if (targetModel === 'Nano Banana' && text.includes('Pro')) continue;

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

        if (candidates.length > 0) {
            // Sort by specificity (smallest element first)
            candidates.sort((a, b) => (a.w * a.h) - (b.w * b.h));
            const target = candidates[0];

            // Click via coordinates
            const clickX = target.x + target.w / 2;
            const clickY = target.y + target.h / 2;
            const clickEl = document.elementFromPoint(clickX, clickY);
            if (clickEl) {
                clickEl.click();
                return {selected: true, target: target};
            }
        }

        return {selected: false, candidates: candidates};
    }""", model_name)

    print(f"  Selection: {selected}")
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
                if (text === 'Что-то пошло не так.' && rect.height > 0 && rect.height < 200 && rect.width > 100)
                    return true;
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
        print(f"  TESTING: {model}")
        print(f"{'='*60}")

        # Fresh page
        page.goto(ACCOUNT["project_url"], wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        time.sleep(5)

        # Switch model via settings
        switched = switch_model(page, model)
        if not switched:
            print(f"  Could not switch to {model}")
            results[model] = "switch_failed"
            continue

        time.sleep(2)

        # Generate with S01_A prompt + ingredients
        prefix = f"test_{model.replace(' ', '_').lower()}"
        ok = try_generate(page, PROMPT, prefix, with_ingredients=True)
        results[model] = "OK" if ok else "FAIL"

        if ok:
            print(f"  Waiting 45s before next test...")
            time.sleep(45)
        else:
            print(f"  Waiting 30s...")
            time.sleep(30)

    print(f"\n{'='*60}")
    print(f"  RESULTS:")
    for m, r in results.items():
        print(f"    {m}: {r}")
    print(f"{'='*60}")

    ctx.close()
    p.stop()


if __name__ == "__main__":
    main()
