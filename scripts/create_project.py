"""Create a new project in Flow for account 2."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time

SESSION_DIR = Path(__file__).resolve().parent.parent / ".session_2"
SCREENSHOTS = Path(__file__).resolve().parent.parent / "output" / "screenshots"

with sync_playwright() as pw:
    ctx = pw.chromium.launch_persistent_context(
        user_data_dir=str(SESSION_DIR),
        headless=False,
        viewport={"width": 1440, "height": 900},
        locale="en-US",
        args=["--disable-blink-features=AutomationControlled"],
    )
    page = ctx.new_page()

    page.goto("https://labs.google/fx/ru/tools/flow", timeout=60000,
              wait_until="domcontentloaded")
    time.sleep(5)
    print(f"URL: {page.url}")

    # Click 'Создать проект'
    create_js = """() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            if (btn.textContent.includes('Создать проект')) {
                btn.click();
                return true;
            }
        }
        return false;
    }"""
    clicked = page.evaluate(create_js)
    print(f"Clicked 'Создать проект': {clicked}")
    time.sleep(3)

    page.screenshot(path=str(SCREENSHOTS / "account2_create_dialog.png"))

    # Fill project name
    inp = page.query_selector('input[type="text"], input:not([type])')
    if inp:
        inp.fill("автоматизация 1")
        print("Filled project name: автоматизация 1")
    else:
        print("ERROR: No input field found")

    time.sleep(1)

    # Click confirm button (Создать / Сохранить / Готово)
    confirm_js = """() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = btn.textContent.trim();
            const rect = btn.getBoundingClientRect();
            if (rect.width > 50 && rect.height > 20) {
                if (text === 'Создать' || text.includes('Сохранить') ||
                    text === 'OK' || text === 'Готово' ||
                    (text.includes('Создать') && !text.includes('проект') && rect.y > 300)) {
                    btn.click();
                    return 'clicked: ' + text;
                }
            }
        }
        // List all visible buttons for debug
        const debug = [];
        for (const btn of btns) {
            const text = btn.textContent.trim();
            const rect = btn.getBoundingClientRect();
            if (rect.width > 30 && rect.height > 15 && rect.y > 300) {
                debug.push(text.substring(0, 40) + ' y=' + Math.round(rect.y));
            }
        }
        return 'no confirm found. Buttons: ' + debug.join(' | ');
    }"""
    result = page.evaluate(confirm_js)
    print(f"Confirm: {result}")
    time.sleep(8)

    final_url = page.url
    print(f"\nFinal URL: {final_url}")

    page.screenshot(path=str(SCREENSHOTS / "account2_project_created.png"))

    # If we're in a project, extract the project UUID
    if "/project/" in final_url:
        project_id = final_url.split("/project/")[-1].split("?")[0].split("/")[0]
        full_url = f"https://labs.google/fx/ru/tools/flow/project/{project_id}"
        print(f"\nPROJECT URL: {full_url}")
    else:
        print("\nWARNING: Not redirected to project page. Check screenshot.")

    ctx.close()
