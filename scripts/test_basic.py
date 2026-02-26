#!/usr/bin/env python3
"""Quick test: is Flow working right now? No ingredients, simple prompt."""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "screenshots"

ACCOUNT = {
    "session_dir": PROJECT_ROOT / ".session_2",
    "project_url": "https://labs.google/fx/ru/tools/flow/project/492b843c-217a-4c83-8c2d-4e0b0f0b1dc8",
}


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

    # Simple test prompt
    textarea = page.query_selector("textarea")
    if textarea:
        textarea.click()
        textarea.fill("A cute orange cat sleeping on a pillow. 3D Pixar animation style.")
        time.sleep(0.5)

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
    print("Generating...")

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
            print(f"ERROR after {(i+1)*5}s — Flow is DOWN")
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_basic_error.png"))
            break

        loading = page.query_selector('[role="progressbar"]')
        if not loading and i > 2:
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_basic_ok.png"))
            print(f"OK after ~{(i+1)*5}s — Flow is UP")
            break
    else:
        print("TIMEOUT")

    ctx.close()
    p.stop()


if __name__ == "__main__":
    main()
