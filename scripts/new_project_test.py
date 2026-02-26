#!/usr/bin/env python3
"""
Create a new project in Google Flow and test generation there.
Account 2.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "screenshots"

ACCOUNT = {
    "session_dir": PROJECT_ROOT / ".session_2",
}

FLOW_URL = "https://labs.google/fx/ru/tools/flow"
CHAR_FILE = PROJECT_ROOT / "персонажи" / "char_karim_full.jpeg"
LOC_FILE = PROJECT_ROOT / "локации" / "loc_garazh_inside.jpg"
PROMPT = "Extreme close-up of a homemade radio receiver on a workbench. A hand reaches for the tuning dial. Wires, exposed circuit boards, a small blinking green indicator light. Dim single-lamp lighting, deep shadows. 3D Pixar-style animation, soft volumetric lighting, cinematic."


def main():
    p = sync_playwright().start()
    ctx = p.chromium.launch_persistent_context(
        str(ACCOUNT["session_dir"]),
        headless=False,
        viewport={"width": 1280, "height": 900},
        locale="ru-RU",
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # Go to Flow main page (not project)
    print("Going to Flow main page...")
    page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(5)
    page.screenshot(path=str(SCREENSHOTS_DIR / "new_proj_main.png"))

    # Look for "New project" / "Новый проект" button or create project
    print("Looking for new project button...")
    new_btn = page.evaluate("""() => {
        const allEls = document.querySelectorAll('button, a, [role="button"]');
        for (const el of allEls) {
            const text = (el.textContent || '').trim().toLowerCase();
            if (text.includes('новый') || text.includes('new') || text.includes('создать') || text.includes('create')) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0) {
                    return {text: el.textContent.trim(), tag: el.tagName, y: Math.round(rect.y), x: Math.round(rect.x)};
                }
            }
        }
        return null;
    }""")
    print(f"  New button: {new_btn}")

    if new_btn:
        # Click it
        page.evaluate("""(text) => {
            const allEls = document.querySelectorAll('button, a, [role="button"]');
            for (const el of allEls) {
                if (el.textContent.trim().includes(text)) {
                    el.click();
                    return true;
                }
            }
            return false;
        }""", new_btn['text'][:20])
        time.sleep(3)
        page.screenshot(path=str(SCREENSHOTS_DIR / "new_proj_clicked.png"))

    # Alternative: look for '+' button or floating action button
    if not new_btn:
        fab = page.evaluate("""() => {
            const btns = document.querySelectorAll('button, a');
            for (const btn of btns) {
                const text = btn.textContent.trim();
                const rect = btn.getBoundingClientRect();
                if ((text === 'add' || text === '+') && rect.width > 0) {
                    btn.click();
                    return {text: text, y: Math.round(rect.y)};
                }
            }
            return null;
        }""")
        print(f"  FAB: {fab}")
        time.sleep(3)

    # Take screenshot and check URL
    time.sleep(3)
    page.screenshot(path=str(SCREENSHOTS_DIR / "new_proj_after.png"))
    current_url = page.url
    print(f"  Current URL: {current_url}")

    # If we got a new project URL, save it
    if 'project/' in current_url:
        project_id = current_url.split('project/')[-1].split('?')[0].split('/')[0]
        print(f"\n  NEW PROJECT ID: {project_id}")
        print(f"  NEW PROJECT URL: {current_url}")

        # Try generation in new project
        time.sleep(3)

        # Upload ingredients
        print("\n  Uploading ingredients in new project...")
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
        if fi:
            fi.set_input_files(str(CHAR_FILE))
            print(f"    Uploaded: {CHAR_FILE.name}")
            time.sleep(2)
            # Crop
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent.includes('Кадрировать и сохранить')) { btn.click(); return; }
                }
            }""")
            time.sleep(2)

            # Upload second
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
            fi2 = page.query_selector('input[type="file"]')
            if fi2:
                fi2.set_input_files(str(LOC_FILE))
                print(f"    Uploaded: {LOC_FILE.name}")
                time.sleep(2)
                page.evaluate("""() => {
                    const btns = document.querySelectorAll('button');
                    for (const btn of btns) {
                        if (btn.textContent.includes('Кадрировать и сохранить')) { btn.click(); return; }
                    }
                }""")
                time.sleep(2)

        # Close panel and fill prompt
        page.keyboard.press("Escape")
        time.sleep(1)

        textarea = page.query_selector("textarea")
        if textarea:
            textarea.click()
            textarea.fill(PROMPT)
        time.sleep(0.5)

        page.screenshot(path=str(SCREENSHOTS_DIR / "new_proj_before_gen.png"))

        # Generate
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                if (btn.textContent.includes('Генерировать') || btn.textContent.includes('Generate')) {
                    btn.click(); return true;
                }
            }
            return false;
        }""")
        print("  Generating in new project...")

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
                print(f"  ERROR after {(i+1)*5}s — same issue in new project")
                page.screenshot(path=str(SCREENSHOTS_DIR / "new_proj_error.png"))
                break

            loading = page.query_selector('[role="progressbar"]')
            if not loading and i > 2:
                page.screenshot(path=str(SCREENSHOTS_DIR / "new_proj_success.png"))
                print(f"  SUCCESS after ~{(i+1)*5}s in new project!")
                break
    else:
        print("  Could not create/navigate to new project")
        # Maybe we're already on a workspace — try directly
        print("  Trying to generate directly on current page...")
        textarea = page.query_selector("textarea")
        if textarea:
            textarea.click()
            textarea.fill("A red apple. 3D Pixar animation.")
            time.sleep(0.5)
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    if (btn.textContent.includes('Генерировать') || btn.textContent.includes('Generate')) {
                        btn.click(); return true;
                    }
                }
                return false;
            }""")
            time.sleep(20)
            page.screenshot(path=str(SCREENSHOTS_DIR / "new_proj_direct.png"))

    ctx.close()
    p.stop()
    print("\nDone.")


if __name__ == "__main__":
    main()
