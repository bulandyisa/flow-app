#!/usr/bin/env python3
"""Quick test: open Flow, type a simple prompt, try to generate.
Tests whether the issue is prompt-related or platform-related.
"""
import sys, time, random
sys.path.insert(0, '.')
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def main():
    from playwright.sync_api import sync_playwright

    session_dir = PROJECT_ROOT / '.session'
    # Clean locks
    for f in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'):
        p = session_dir / f
        if p.exists():
            p.unlink()

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(session_dir),
            headless=False,
            channel='chrome',
            viewport={'width': 1440, 'height': 900},
            locale='ru-RU',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=AutomationControlled',
                '--disable-infobars',
                '--no-first-run',
                '--no-default-browser-check',
            ],
        )
        page = ctx.new_page()

        # Go to Flow main page
        print('Going to Flow...')
        page.goto('https://labs.google/fx/ru/tools/flow', timeout=60000, wait_until='domcontentloaded')
        time.sleep(5)

        # Dismiss popups
        for _ in range(3):
            page.keyboard.press('Escape')
            time.sleep(1)

        # Click "Создать проект" or any project
        for label in ['Создать проект', 'Новый проект']:
            btn = page.query_selector(f'button:has-text("{label}")')
            if btn:
                btn.click()
                print(f'Clicked: {label}')
                time.sleep(5)
                break
        else:
            # Click first project link
            link = page.query_selector('a[href*="/project/"]')
            if link:
                link.click()
                print('Clicked existing project')
                time.sleep(5)

        # Wait for prompt field
        print(f'URL: {page.url}')
        page.wait_for_selector('[role="textbox"], [contenteditable="true"]', timeout=30000)
        print('Prompt field ready.')

        # Dismiss more popups
        for _ in range(2):
            page.keyboard.press('Escape')
            time.sleep(0.5)

        # === Test 1: Very simple prompt ===
        simple_prompt = "A cute orange cat sitting on a windowsill, 3D Pixar-style animation"
        print(f'\n=== TEST 1: Simple prompt ({len(simple_prompt)} chars) ===')
        print(f'Prompt: {simple_prompt}')

        # Find and fill prompt field via JS (avoid CDP keyboard detection)
        prompt_el = page.query_selector('[role="textbox"], [contenteditable="true"]')
        if prompt_el:
            prompt_el.click()
            time.sleep(0.3)
            # Use execCommand('insertText') — mimics native paste, not CDP keyboard
            page.evaluate("""(text) => {
                const el = document.querySelector('[role="textbox"]') ||
                           document.querySelector('[contenteditable="true"]');
                if (!el) return;
                el.focus();
                const sel = window.getSelection();
                sel.selectAllChildren(el);
                sel.deleteFromDocument();
                document.execCommand('insertText', false, text);
                el.dispatchEvent(new InputEvent('input', {
                    bubbles: true, cancelable: true, inputType: 'insertText', data: text
                }));
            }""", simple_prompt)
            time.sleep(1)

            # Click Generate button
            gen_btn = page.query_selector('button:has(span.material-symbols-outlined)')
            if not gen_btn:
                gen_btn = page.query_selector('button[aria-label*="Создать"], button[aria-label*="Generate"]')
            if not gen_btn:
                # Try finding the arrow button
                buttons = page.query_selector_all('button')
                for b in buttons:
                    txt = (b.text_content() or '').strip()
                    if 'arrow_forward' in txt or 'send' in txt:
                        gen_btn = b
                        break
            if gen_btn:
                gen_btn.click()
                print('Clicked Generate. Waiting for result...')
            else:
                print('ERROR: Could not find Generate button')
                page.screenshot(path=str(PROJECT_ROOT / 'output/screenshots/test_no_gen_btn.png'))
                ctx.close()
                return

            # Wait and check result
            for i in range(60):  # up to 5 min
                time.sleep(5)
                body = (page.text_content('body') or '')[:2000]
                if 'Что-то пошло не так' in body or 'Ошибка' in body:
                    print(f'  [{i*5}s] ERROR: "Что-то пошло не так" detected')
                    page.screenshot(path=str(PROJECT_ROOT / 'output/screenshots/test_simple_error.png'))
                    break
                # Check for generated images
                imgs = page.query_selector_all('img[src*="blob:"], img[src*="lh3.google"]')
                new_imgs = [img for img in imgs if img.bounding_box() and img.bounding_box()['y'] < 600]
                if len(new_imgs) > 0:
                    print(f'  [{i*5}s] SUCCESS! Found {len(new_imgs)} generated images')
                    page.screenshot(path=str(PROJECT_ROOT / 'output/screenshots/test_simple_success.png'))
                    break
                if i % 6 == 0:
                    print(f'  [{i*5}s] Waiting...')
            else:
                print('  TIMEOUT after 5 minutes')
                page.screenshot(path=str(PROJECT_ROOT / 'output/screenshots/test_simple_timeout.png'))
        else:
            print('ERROR: No prompt field found')

        print('\nDone. Closing browser.')
        ctx.close()


if __name__ == '__main__':
    main()
