#!/usr/bin/env python3
"""
Quick test: try VEO3 video generation (text-to-video mode) on account 2.
Also try NB with ingredients in new project.
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

VEO_PROMPT = "A boy sitting at a workbench slowly turns a dial on a radio receiver. Static and crackling fill the air. A small green indicator light pulses. Smooth cinematic motion, 3D Pixar-style animation."


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
    print("Flow ready (account 2)\n")

    # Switch to "Видео по описанию" (text-to-video VEO)
    print("=== TEST: VEO text-to-video ===")
    combo = page.query_selector('button[role="combobox"]')
    if combo:
        combo.click()
        time.sleep(1)
        option = page.query_selector('div[role="option"]:has-text("Видео по описанию")')
        if option:
            option.click()
            print("  Switched to: Видео по описанию")
            time.sleep(2)
        else:
            page.keyboard.press("Escape")
            print("  Mode 'Видео по описанию' not found!")

    # Check which VEO model is active
    model_info = page.evaluate("""() => {
        const btns = document.querySelectorAll('button, div');
        for (const btn of btns) {
            const text = (btn.textContent || '').trim();
            const rect = btn.getBoundingClientRect();
            if (text.toLowerCase().includes('veo') && rect.y > 700 && rect.y < 800 && rect.width < 200) {
                return {text: text, y: Math.round(rect.y), x: Math.round(rect.x)};
            }
        }
        return null;
    }""")
    print(f"  Current VEO model: {model_info}")

    # Fill VEO prompt
    textarea = page.query_selector("textarea")
    if textarea:
        textarea.click()
        textarea.fill(VEO_PROMPT)
    time.sleep(0.5)

    page.screenshot(path=str(SCREENSHOTS_DIR / "test_veo_before.png"))

    # Generate
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim();
            if (text.includes('Генерировать') || text.includes('Generate') || text.includes('arrow_forward')) {
                btn.click(); return true;
            }
        }
        return false;
    }""")
    print("  Generating VEO video...")

    # VEO takes longer — wait up to 5 minutes
    for i in range(60):
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
            print(f"  VEO ERROR after {(i+1)*5}s")
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_veo_error.png"))
            # Dismiss
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) { if (btn.textContent.includes('Закрыть')) btn.click(); }
            }""")
            break

        # Check for video
        video_el = page.evaluate("""() => {
            const videos = document.querySelectorAll('video');
            return videos.length;
        }""")

        loading = page.query_selector('[role="progressbar"]')
        if i > 5 and i % 6 == 0:
            print(f"    ...{(i+1)*5}s, videos={video_el}, loading={loading is not None}")

        if not loading and i > 5:
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_veo_success.png"))
            print(f"  VEO SUCCESS after ~{(i+1)*5}s! Videos on page: {video_el}")
            break

    # Also test NB with ingredients again (maybe VEO worked and NB is the issue)
    print("\n=== TEST: NB with ingredients (after VEO cooldown) ===")
    time.sleep(10)

    # Switch to image mode
    combo = page.query_selector('button[role="combobox"]')
    if combo:
        combo.click()
        time.sleep(1)
        option = page.query_selector('div[role="option"]:has-text("Создать изображение")')
        if option:
            option.click()
            time.sleep(2)
        else:
            page.keyboard.press("Escape")

    # Upload 1 ingredient only
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
        fi.set_input_files(str(PROJECT_ROOT / "персонажи" / "char_karim_full.jpeg"))
        print("  Uploaded char_karim")
    time.sleep(2)
    page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            if (btn.textContent.includes('Кадрировать и сохранить')) { btn.click(); return; }
        }
    }""")
    time.sleep(2)
    page.keyboard.press("Escape")
    time.sleep(1)

    textarea = page.query_selector("textarea")
    if textarea:
        textarea.click()
        textarea.fill("A boy at a workbench with a radio. 3D Pixar animation.")
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
    print("  Generating NB image with 1 ingredient...")

    for i in range(24):
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
            print(f"  NB ERROR after {(i+1)*5}s")
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_nb_after_veo_error.png"))
            break

        loading = page.query_selector('[role="progressbar"]')
        if not loading and i > 2:
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_nb_after_veo_ok.png"))
            print(f"  NB SUCCESS after ~{(i+1)*5}s!")
            break

    ctx.close()
    p.stop()
    print("\nDone.")


if __name__ == "__main__":
    main()
