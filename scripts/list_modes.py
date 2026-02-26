#!/usr/bin/env python3
"""Open Google Flow and list all available mode options from the dropdown."""
import traceback, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / '.session'
FLOW_PROJECT_URL = 'https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869'
OUT = PROJECT_ROOT / 'flow_modes_output.txt'

def log(msg):
    with open(OUT, 'a') as f:
        f.write(msg + '\n')

try:
    OUT.write_text('script started\n')
    log('importing playwright...')
    from playwright.sync_api import sync_playwright
    log('playwright imported OK')

    # Remove stale locks
    for lock in ['SingletonLock', 'SingletonCookie', 'SingletonSocket']:
        f = SESSION_DIR / lock
        if f.exists():
            f.unlink()
            log(f'Removed {lock}')

    log('launching browser...')
    pw = sync_playwright().start()
    ctx = pw.chromium.launch_persistent_context(
        user_data_dir=str(SESSION_DIR),
        headless=False,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--no-first-run',
        ],
        viewport={'width': 1440, 'height': 900},
    )
    log('browser launched OK')
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    log(f'navigating to {FLOW_PROJECT_URL}')
    page.goto(FLOW_PROJECT_URL, timeout=60000, wait_until='domcontentloaded')
    log('page loaded (domcontentloaded)')
    time.sleep(8)
    log('8s wait done')

    # Screenshot
    page.screenshot(path=str(PROJECT_ROOT / 'flow_modes_screenshot.png'))
    log('screenshot saved')

    # Find combobox
    combo = page.query_selector('button[role="combobox"]')
    if not combo:
        log('ERROR: combobox not found')
        buttons = page.query_selector_all('button')
        log(f'total buttons: {len(buttons)}')
        for i, b in enumerate(buttons[:20]):
            log(f'  btn {i}: {(b.text_content() or "")[:60]}')
    else:
        current = combo.text_content() or ''
        log(f'current mode: "{current.strip()}"')
        combo.click()
        time.sleep(1.5)
        options = page.query_selector_all('div[role="option"]')
        log(f'\n=== MODES ({len(options)}): ===')
        for i, opt in enumerate(options):
            text = opt.text_content() or ''
            log(f'  {i+1}. "{text.strip()}"')
        page.keyboard.press('Escape')

    log('\nDONE')
    time.sleep(3)
    ctx.close()
    pw.stop()

except Exception:
    OUT.write_text('') if not OUT.exists() else None
    with open(OUT, 'a') as f:
        f.write(f'ERROR:\n{traceback.format_exc()}\n')
