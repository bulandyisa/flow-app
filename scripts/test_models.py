#!/usr/bin/env python3
"""
Quick test: list available models and try generation with a different model.
Uses account 2 by default.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACCOUNTS = [
    {
        "session_dir": PROJECT_ROOT / ".session",
        "project_url": "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869",
    },
    {
        "session_dir": PROJECT_ROOT / ".session_2",
        "project_url": "https://labs.google/fx/ru/tools/flow/project/492b843c-217a-4c83-8c2d-4e0b0f0b1dc8",
    },
]
SCREENSHOTS_DIR = PROJECT_ROOT / "output" / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def launch_browser(account_idx=1):
    """Launch browser with persistent context for given account."""
    acct = ACCOUNTS[account_idx]
    p = sync_playwright().start()
    ctx = p.chromium.launch_persistent_context(
        str(acct["session_dir"]),
        headless=False,
        viewport={"width": 1280, "height": 900},
        locale="ru-RU",
    )
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(acct["project_url"], wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle", timeout=30000)
    time.sleep(3)
    print(f"Opened Flow on account {account_idx + 1}")
    return p, ctx, page


def list_all_models(page):
    """Click the combobox and list ALL available model options."""
    # First, read the current model
    combo = page.query_selector('button[role="combobox"]')
    if combo:
        current = (combo.text_content() or "").replace("arrow_drop_down", "").strip()
        print(f"\nТекущий режим: {current}")

    # Click combobox to open dropdown
    if combo:
        combo.click()
        time.sleep(1)

    # List all options
    options = page.query_selector_all('div[role="option"]')
    print(f"\nДоступные режимы ({len(options)}):")
    for i, opt in enumerate(options):
        text = (opt.text_content() or "").strip()
        print(f"  [{i}] {text}")

    # Close dropdown
    page.keyboard.press("Escape")
    time.sleep(0.5)
    return options


def list_model_variants(page):
    """Look for a model selector WITHIN the current mode (e.g. model chip/button near prompt bar)."""
    # Take a screenshot to see the UI
    page.screenshot(path=str(SCREENSHOTS_DIR / "test_models_ui.png"))
    print(f"\nСкриншот сохранен: test_models_ui.png")

    # Look for model chips/buttons that might show "Nano Banana Pro", etc.
    result = page.evaluate("""() => {
        const items = [];

        // Look for any element containing model names
        const modelKeywords = ['nano banana', 'gemini', 'veo', 'imagen', 'fast', 'pro', 'lower priority'];
        const allEls = document.querySelectorAll('button, [role="button"], [role="chip"], span, div');

        for (const el of allEls) {
            const text = (el.textContent || '').trim().toLowerCase();
            const rect = el.getBoundingClientRect();

            // Skip invisible elements
            if (rect.width === 0 || rect.height === 0) continue;
            // Skip very large elements (containers)
            if (rect.width > 400) continue;

            for (const kw of modelKeywords) {
                if (text.includes(kw) && text.length < 100) {
                    items.push({
                        text: el.textContent.trim(),
                        tag: el.tagName,
                        role: el.getAttribute('role') || '',
                        y: Math.round(rect.y),
                        x: Math.round(rect.x),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height),
                        clickable: el.tagName === 'BUTTON' || el.getAttribute('role') === 'button' || el.getAttribute('role') === 'chip'
                    });
                    break;
                }
            }
        }

        // Deduplicate by text
        const seen = new Set();
        return items.filter(i => {
            const key = i.text + '_' + i.y;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }""")

    print(f"\nНайдены элементы с названиями моделей ({len(result)}):")
    for item in result:
        print(f"  {item['text']} (tag={item['tag']}, role={item['role']}, y={item['y']}, clickable={item['clickable']})")

    return result


def switch_to_mode(page, mode_text):
    """Switch mode via combobox dropdown."""
    combo = page.query_selector('button[role="combobox"]')
    if not combo:
        print("Combobox не найден!")
        return False

    current = (combo.text_content() or "").replace("arrow_drop_down", "").strip()
    if mode_text.lower() in current.lower():
        print(f"Уже в режиме: {current}")
        return True

    combo.click()
    time.sleep(1)

    # Find and click the option
    options = page.query_selector_all('div[role="option"]')
    for opt in options:
        text = (opt.text_content() or "").strip()
        if mode_text.lower() in text.lower():
            print(f"Переключаюсь на: {text}")
            opt.click()
            time.sleep(2)
            return True

    page.keyboard.press("Escape")
    print(f"Режим '{mode_text}' не найден!")
    return False


def try_generate(page, prompt, screenshot_prefix="test"):
    """Try to generate with current model and see if it works."""
    # Fill prompt
    textarea = page.query_selector("textarea")
    if not textarea:
        print("Textarea не найден!")
        return False

    textarea.click()
    textarea.fill(prompt)
    time.sleep(0.5)

    # Click Generate button
    gen_btn = page.query_selector('button:has-text("Генерировать")')
    if not gen_btn:
        gen_btn = page.query_selector('button:has-text("Generate")')
    if not gen_btn:
        # Try finding by the play/send icon
        gen_btn = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                if (rect.y > 700 && rect.x > 800) {
                    return {found: true, text: btn.textContent.trim(), y: Math.round(rect.y), x: Math.round(rect.x)};
                }
            }
            return {found: false};
        }""")
        if gen_btn and gen_btn.get("found"):
            print(f"Нажимаю кнопку генерации: {gen_btn['text']} (y={gen_btn['y']})")
            page.click(f'button >> nth=-1')  # last button on page

    if gen_btn and not isinstance(gen_btn, dict):
        gen_btn.click()
        print("Нажал Генерировать")

    # Wait and check for errors
    time.sleep(5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"{screenshot_prefix}_after_gen.png"))

    # Check for error
    error_el = page.query_selector('div:has-text("Что-то пошло не так")')
    if error_el:
        box = error_el.bounding_box()
        if box and box['height'] < 200:
            print("ОШИБКА: 'Что-то пошло не так'")
            # Dismiss
            close_btn = page.query_selector('button:has-text("Закрыть")')
            if close_btn:
                close_btn.click()
                time.sleep(1)
            return False

    # Wait for generation (up to 60s)
    print("Жду генерации (до 60с)...")
    for i in range(12):
        time.sleep(5)
        # Check for new images
        error_el = page.query_selector('div:has-text("Что-то пошло не так")')
        if error_el:
            box = error_el.bounding_box()
            if box and box['height'] < 200:
                print(f"ОШИБКА после {(i+1)*5}с: 'Что-то пошло не так'")
                close_btn = page.query_selector('button:has-text("Закрыть")')
                if close_btn:
                    close_btn.click()
                    time.sleep(1)
                return False

        # Check for spinner/loading indicator disappearing
        loading = page.query_selector('[class*="loading"], [class*="spinner"], [role="progressbar"]')
        if not loading and i > 2:
            page.screenshot(path=str(SCREENSHOTS_DIR / f"{screenshot_prefix}_result.png"))
            print(f"Генерация завершена за ~{(i+1)*5}с")
            return True

    page.screenshot(path=str(SCREENSHOTS_DIR / f"{screenshot_prefix}_timeout.png"))
    print("Таймаут генерации (60с)")
    return False


def main():
    account_idx = 1  # Account 2 by default
    if "--account" in sys.argv:
        idx = sys.argv.index("--account")
        account_idx = int(sys.argv[idx + 1]) - 1

    print("=" * 60)
    print("  ТЕСТ МОДЕЛЕЙ GOOGLE FLOW")
    print("=" * 60)

    p, ctx, page = launch_browser(account_idx)

    try:
        # Step 1: List all modes from combobox
        print("\n--- Шаг 1: Список режимов (combobox) ---")
        list_all_models(page)

        # Step 2: Look for model selectors in the UI
        print("\n--- Шаг 2: Поиск элементов модели в UI ---")
        model_elements = list_model_variants(page)

        # Step 3: Try each image mode
        print("\n--- Шаг 3: Пробуем генерацию ---")

        # First, try image mode (Создать изображение) with different model if available
        switch_to_mode(page, "Создать изображение")
        time.sleep(2)

        # Take screenshot to see what model is selected
        page.screenshot(path=str(SCREENSHOTS_DIR / "test_models_image_mode.png"))

        # Look for model selector chip/button and click it
        model_chip = page.evaluate("""() => {
            const btns = document.querySelectorAll('button, [role="button"], [role="chip"], [role="tab"]');
            const results = [];
            for (const btn of btns) {
                const text = (btn.textContent || '').trim();
                const rect = btn.getBoundingClientRect();
                if (rect.width === 0) continue;
                // Model selectors are typically near the top of the tool area or near prompt bar
                if (text.match(/nano banana|gemini|imagen|fast|pro/i) && text.length < 60) {
                    results.push({
                        text: text.replace(/\\n/g, ' ').replace(/\\s+/g, ' '),
                        tag: btn.tagName,
                        role: btn.getAttribute('role') || '',
                        y: Math.round(rect.y),
                        x: Math.round(rect.x),
                        w: Math.round(rect.width)
                    });
                }
            }
            return results;
        }""")

        print(f"\nМодели-кнопки: {model_chip}")

        # Try simple generation with current model
        print("\n--- Попытка генерации: текущая модель ---")
        result = try_generate(page, "A red apple on a white table. Photorealistic.", "test_current_model")

        if not result:
            # Try switching to VEO mode and try VEO2 Fast
            print("\n--- Попытка: переключение на видео ---")
            switch_to_mode(page, "Видео")
            time.sleep(2)

            # Screenshot of video mode
            page.screenshot(path=str(SCREENSHOTS_DIR / "test_models_video_mode.png"))

            # List models again in video mode
            model_elements = list_model_variants(page)

        # Final screenshot
        page.screenshot(path=str(SCREENSHOTS_DIR / "test_models_final.png"))

    finally:
        print("\nЗавершаю...")
        ctx.close()
        p.stop()


if __name__ == "__main__":
    main()
