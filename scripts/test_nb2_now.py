#!/usr/bin/env python3
"""Quick test: NB with 2 ingredients right now. Account 2."""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "screenshots"

ACCOUNT = {
    "session_dir": PROJECT_ROOT / ".session_2",
    "project_url": "https://labs.google/fx/ru/tools/flow/project/492b843c-217a-4c83-8c2d-4e0b0f0b1dc8",
}

CHAR = PROJECT_ROOT / "персонажи" / "char_karim_full.jpeg"
LOC = PROJECT_ROOT / "локации" / "loc_garazh_inside.jpg"
PROMPT = "Extreme close-up of a homemade radio receiver on a workbench. A hand reaches for the tuning dial. 3D Pixar-style animation, soft volumetric lighting, cinematic."


def upload(page, path):
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const t = btn.textContent.trim();
            const r = btn.getBoundingClientRect();
            if (t === 'add' && r.y > 750 && r.width > 40 && r.width < 100) { btn.click(); return; }
        }
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
                const t = btn.textContent.trim();
                const r = btn.getBoundingClientRect();
                if (t === 'add' && r.y > 750 && r.width > 40 && r.width < 100) { btn.click(); return; }
            }
        }""")
        time.sleep(2)
        fi = page.query_selector('input[type="file"]')
    if fi:
        fi.set_input_files(str(path))
        print(f"  Uploaded: {path.name}")
    time.sleep(2)
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            if (btn.textContent.includes('Кадрировать и сохранить')) { btn.click(); return; }
        }
    }""")
    time.sleep(2)


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
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(5)
    print("Flow ready\n")

    # Upload 2 ingredients
    upload(page, CHAR)
    time.sleep(1)
    upload(page, LOC)
    page.keyboard.press("Escape")
    time.sleep(1)

    # Fill prompt
    ta = page.query_selector("textarea")
    if ta:
        ta.click()
        ta.fill(PROMPT)
    time.sleep(0.5)

    # Generate
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            if (btn.textContent.includes('Генерировать') || btn.textContent.includes('Generate')) {
                btn.click(); return;
            }
        }
    }""")
    print("Generating NB with 2 ingredients...")

    for i in range(30):
        time.sleep(5)
        err = page.evaluate("""() => {
            const els = document.querySelectorAll('div, span');
            for (const el of els) {
                const t = (el.textContent || '').trim();
                const r = el.getBoundingClientRect();
                if (t === 'Что-то пошло не так.' && r.height > 0 && r.height < 200 && r.width > 100) return true;
            }
            return false;
        }""")
        if err:
            print(f"ERROR after {(i+1)*5}s — 2 ingredients still failing")
            page.screenshot(path=str(SCREENSHOTS_DIR / "nb2_now_error.png"))
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) { if (btn.textContent.includes('Закрыть')) btn.click(); }
            }""")
            break

        loading = page.query_selector('[role="progressbar"]')
        if not loading and i > 2:
            page.screenshot(path=str(SCREENSHOTS_DIR / "nb2_now_ok.png"))
            print(f"SUCCESS after ~{(i+1)*5}s — 2 ingredients WORK!")
            break

    ctx.close()
    p.stop()


if __name__ == "__main__":
    main()
