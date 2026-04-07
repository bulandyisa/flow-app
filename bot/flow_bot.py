"""
Flow Bot v2 — Playwright бот для Google Flow.

Использование:
  ./scripts/run_safe.sh --review --clip S01_A --account 1
  ./scripts/run_safe.sh --review --clip S01_A --component veo --account 1
  ./scripts/run_safe.sh --select --clip S01_A --component nb_first --attempt 1 --variant 0 --batch a --scores '{"char_face":9,...}'
  ./scripts/run_safe.sh --fail --clip S01_A --component nb_first --attempt 1
  ./scripts/run_safe.sh --status
  ./scripts/run_safe.sh --extract-frames --clip S01_A --component veo --attempt 1
  ./scripts/run_safe.sh --sync-dashboard [--clip S01_A]
"""

import argparse
import base64
import hashlib
import json
import os
import random
import re
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# Ensure bot directory is in path (for bundled Python on Windows)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import r2_storage


# ── Constants ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_PATH = PROJECT_ROOT / 'output' / 'prompts' / 'all_prompts.json'
PROMPTS_PATH_LOCAL = PROJECT_ROOT / 'output' / 'prompts' / 'all_prompts_local.json'
OUTPUT_DIR   = PROJECT_ROOT / 'output'
FRAMES_DIR   = OUTPUT_DIR / 'frames'
CLIPS_DIR    = OUTPUT_DIR / 'clips'
REVIEW_DIR   = OUTPUT_DIR / 'review'
SCREENSHOTS_DIR = OUTPUT_DIR / 'screenshots'
REFS_DIR     = PROJECT_ROOT

FLOW_URL = 'https://labs.google/fx/ru/tools/flow'
COMMANDS_PATH = OUTPUT_DIR / 'commands.json'

# Sessions stored in data/sessions/ (survives app updates)
SESSIONS_BASE = Path(os.environ.get('SESSIONS_DIR', PROJECT_ROOT))

ACCOUNTS = [
    # Bot 1 — Акк 1, Chrome, сессия .session
    {'session_dir': SESSIONS_BASE / '.session', 'project_url': None},
    # Bot 2 — Акк 1, Chromium, сессия .session_1b
    {'session_dir': SESSIONS_BASE / '.session_1b', 'project_url': None},
    # Bot 3 — Акк 2, Chrome, сессия .session_2
    {'session_dir': SESSIONS_BASE / '.session_2', 'project_url': None},
    # Bot 4 — Акк 2, Chromium, сессия .session_2b
    {'session_dir': SESSIONS_BASE / '.session_2b', 'project_url': None},
    # Bot 5 — Акк 1, Chrome (2-й инстанс), сессия .session_1c
    {'session_dir': SESSIONS_BASE / '.session_1c', 'project_url': None},
    # Bot 6 — Акк 2, Chrome (2-й инстанс), сессия .session_2c
    {'session_dir': SESSIONS_BASE / '.session_2c', 'project_url': None},
]

_current_account_idx = 0
_active_context = None

GLOBAL_TIMEOUT_SEC = int(os.environ.get('FLOW_TIMEOUT', 18000))
QUALITY_THRESHOLD = 9.0
CRITICAL_MIN_SCORE = 6
MAX_ATTEMPTS = 10  # High limit; bot does exactly 1 attempt per run
GENERATION_TIMEOUT = 300
POLL_INTERVAL = 5

SCORE_CRITERIA = [
    'char_face', 'char_outfit', 'char_count',
    'anatomy_hands', 'anatomy_body', 'anatomy_face',
    'scale', 'physics', 'spatial',
    'scenario_action', 'scenario_emotion', 'scenario_objects',
    'loc_match', 'lighting',
    'artifacts', 'style_3d',
    'composition', 'continuity',
]
CRITICAL_CRITERIA = ['anatomy_hands', 'anatomy_body', 'scale', 'physics', 'spatial', 'char_count']

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
if (!window.chrome) window.chrome = {};
if (!window.chrome.runtime) window.chrome.runtime = {connect(){}, sendMessage(){}};
if (!window.chrome.app) window.chrome.app = {isInstalled: false,
    InstallState: {DISABLED:'disabled',INSTALLED:'installed',NOT_INSTALLED:'not_installed'},
    RunningState: {CANNOT_RUN:'cannot_run',READY_TO_RUN:'ready_to_run',RUNNING:'running'}};
const origQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (p) => p.name === 'notifications'
    ? Promise.resolve({state: Notification.permission}) : origQuery(p);
Object.defineProperty(navigator, 'plugins', {get: () => {
    const p=[{name:'Chrome PDF Plugin',filename:'internal-pdf-viewer'},
             {name:'Chrome PDF Viewer',filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
             {name:'Native Client',filename:'internal-nacl-plugin'}];
    p.length=3; return p}});
Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU','ru','en-US','en']});
"""


# ── Human-like delays ────────────────────────────────────────────────────────

def human_delay(lo=0.3, hi=0.8):
    time.sleep(random.uniform(lo, hi))

def human_delay_long(lo=4.0, hi=8.0):
    time.sleep(random.uniform(lo, hi))

def human_pause_between_generations():
    """Pause between generation attempts — long enough to avoid per-minute throttling."""
    pause = random.uniform(60, 70)
    print(f'    Pausing {pause:.0f}s between generations...')
    time.sleep(pause)

def human_pause_after_error():
    """Longer pause after server_error — back off to let throttle reset."""
    pause = random.uniform(120, 180)
    print(f'    Backing off {pause:.0f}s after error...')
    time.sleep(pause)


# ── Human-like interactions ──────────────────────────────────────────────────

def human_click(page, el_or_sel, timeout=10000):
    human_delay(0.1, 0.4)
    if isinstance(el_or_sel, str):
        el = page.wait_for_selector(el_or_sel, timeout=timeout)
    else:
        el = el_or_sel
    if el:
        box = el.bounding_box()
        if box:
            x = box['x'] + box['width'] * random.uniform(0.25, 0.75)
            y = box['y'] + box['height'] * random.uniform(0.25, 0.75)
            page.mouse.move(x, y, steps=random.randint(8, 20))
            human_delay(0.03, 0.1)
            page.mouse.click(x, y)
        else:
            el.click()
    human_delay(0.08, 0.3)


def human_type(page, element, text):
    """Type text character-by-character via keyboard.type()."""
    human_click(page, element)
    base_min, base_max = (0.02, 0.05) if len(text) > 100 else (0.03, 0.08)
    for ch in text:
        delay = random.uniform(base_min, base_max)
        if ch in '.,:;!?':
            delay += random.uniform(0.1, 0.3)
        page.keyboard.type(ch, delay=0)
        time.sleep(delay)


# ── Prompt sanitization & validation ─────────────────────────────────────────

def _sanitize_common(prompt):
    p = prompt
    p = re.sub(r'\b\d{1,2}-year-old\b', 'animated', p)
    p = re.sub(r'\b\d{1,2}yo\b', 'animated', p)
    trigger_map = {
        'abandoned': 'old unused', 'dark warehouse': 'dimly lit storage building',
        'dark alley': 'dimly lit street', 'fight': 'disagreement', 'weapon': '',
        'blood': '', 'steal': 'take', 'stolen': 'hidden',
        'villain': 'rival', 'criminal': 'troublemaker',
    }
    for old, new in trigger_map.items():
        p = re.sub(re.escape(old), new, p, flags=re.IGNORECASE)
    return p


def sanitize_nb_prompt(prompt):
    p = _sanitize_common(prompt)
    if '3D Pixar' not in p and 'Pixar-style' not in p:
        p = p.rstrip('. ') + '. 3D Pixar-style, family-friendly.'
    return p


def sanitize_prompt(prompt):
    """Sanitize VEO prompt."""
    p = _sanitize_common(prompt)
    if '3D Pixar' not in p and 'Pixar-style' not in p:
        p = p.rstrip('. ') + '. 3D Pixar-style animation, family-friendly.'
    if 'no subtitle' not in p.lower():
        p = p.rstrip('. ') + '. No subtitles.'
    return p


def validate_nb_prompt(prompt, clip_id=None):
    warnings = []
    p = prompt.lower()
    for pat, lbl in [(r'\bhoodie\b','hoodie'),(r'\bshirt\b','shirt'),(r'\bjeans\b','jeans'),
                     (r'\bjacket\b','jacket'),(r'\b(?:base)?cap\b','cap'),(r'\bstriped\b','striped'),
                     (r'\bsneakers\b','sneakers'),(r'\bboots\b','boots'),(r'\bvest\b','vest'),
                     (r'\bsweater\b','sweater'),(r'\bcoat\b','coat'),(r'\bscarf\b','scarf'),
                     (r'\bshorts\b','shorts'),(r'\bdress\b','dress'),(r'\bskirt\b','skirt')]:
        if re.search(pat, p): warnings.append(f'APPEARANCE: "{lbl}"')
    for pat, lbl in [(r'\bboy\b','boy'),(r'\bgirl\b','girl'),(r'\bchild\b','child'),
                     (r'\byoung\b','young'),(r'\bshe\b','she'),(r'\bteen\b','teen'),
                     (r'\badult\b','adult'),(r'\bwoman\b','woman'),(r'\bman\b','man')]:
        if re.search(pat, p): warnings.append(f'AGE/GENDER: "{lbl}"')
    for pat in ['on the left side','on the right side','in the center','in the middle']:
        if pat in p: warnings.append(f'SPATIAL: "{pat}"')
    if '3d pixar' not in p and 'pixar-style' not in p:
        warnings.append('MISSING: Pixar style tag')
    if 'as the exact background' not in p and 'exact background location' not in p:
        warnings.append('MISSING: location reference')
    first15 = ' '.join(prompt.split()[:15]).lower()
    if 'character from image' not in first15 and 'exact character' not in first15:
        warnings.append('IDENTITY: character ref should be in first 15 words')
    if warnings:
        print(f'  {"!"*40}')
        print(f'  PROMPT WARNINGS ({clip_id or "prompt"}):')
        for w in warnings: print(f'    - {w}')
        print(f'  {"!"*40}')
    return warnings


def validate_veo_prompt(prompt, clip_id=None):
    warnings = []
    p = prompt.lower()
    cam = ['dolly','tracking','pan ','push in','pull back','static','locked-off','crane','zoom']
    if not any(c in p for c in cam):
        warnings.append('CAMERA: no camera movement')
    if '3d pixar' not in p and 'pixar-style' not in p:
        warnings.append('MISSING: Pixar style tag')
    if warnings:
        print(f'  VEO WARNINGS ({clip_id}): {warnings}')
    return warnings


# ── Browser launch ───────────────────────────────────────────────────────────

def launch_browser(pw, account=None, use_builtin_chromium=False):
    global _active_context
    acct = ACCOUNTS[account if account is not None else _current_account_idx]
    session_dir = acct['session_dir']
    if use_builtin_chromium:
        session_dir = session_dir.parent / (session_dir.name + '_chromium')
    session_dir.mkdir(parents=True, exist_ok=True)
    for f in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'):
        p = session_dir / f
        if p.exists(): p.unlink()
    vp_w = 1440 + random.randint(-20, 20)
    vp_h = 900 + random.randint(-15, 15)
    browser_label = 'Chromium (builtin)' if use_builtin_chromium else 'Chrome'
    print(f'  Account {(account if account is not None else _current_account_idx)}, session: {session_dir.name}, viewport: {vp_w}x{vp_h}, {browser_label}')
    launch_kwargs = dict(
        headless=False,
        viewport={'width': vp_w, 'height': vp_h},
        locale='ru-RU',
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-features=AutomationControlled',
            '--disable-infobars',
            '--disable-dev-shm-usage',
            '--no-first-run',
            '--no-default-browser-check',
            f'--window-size={vp_w},{vp_h + 60}',
        ],
    )
    if not use_builtin_chromium:
        launch_kwargs['channel'] = 'chrome'
    ctx = pw.chromium.launch_persistent_context(str(session_dir), **launch_kwargs)
    ctx.add_init_script(STEALTH_JS)
    _active_context = ctx

    # Dismiss any stale file chooser dialogs from previous session
    # (macOS shows a native Finder dialog if session was interrupted during upload)
    try:
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        # Press Escape to close any native dialogs
        page.keyboard.press('Escape')
        time.sleep(0.5)
        page.keyboard.press('Escape')
        time.sleep(0.5)
    except Exception:
        pass

    return ctx


# ── Navigation & Flow UI ─────────────────────────────────────────────────────

def get_project_url():
    return ACCOUNTS[_current_account_idx].get('project_url') or FLOW_URL


def dismiss_popups(page):
    dismissed = False
    for label in ['Закрыть','Close','Понятно','Got it','OK','Пропустить','Skip','Позже','Later']:
        try:
            btn = page.query_selector(f'button:has-text("{label}")')
            if btn:
                box = btn.bounding_box()
                if box and box['width'] > 0:
                    human_click(page, btn)
                    human_delay(0.5, 1.0)
                    dismissed = True
        except Exception: pass
    for sel in ['button[aria-label="Close"]', 'button[aria-label="Закрыть"]',
                'div.cdk-overlay-backdrop', 'div[class*="overlay-backdrop"]']:
        try:
            btn = page.query_selector(sel)
            if btn:
                box = btn.bounding_box()
                if box and box['width'] > 0:
                    btn.click()
                    human_delay(0.5, 1.0)
                    dismissed = True
        except Exception: pass
    return dismissed


def ensure_project(page, project_id=None):
    """Navigate to Flow and enter a project. If project_id given, navigate directly."""
    if project_id:
        project_url = f'{FLOW_URL}/project/{project_id}'
        print(f'  Opening project {project_id[:8]}...')
        page.goto(project_url, timeout=120000, wait_until='domcontentloaded')
        human_delay_long(5, 8)
        for _ in range(3):
            dismiss_popups(page)
            page.keyboard.press('Escape')
            human_delay(0.5, 1.0)
        if '/project/' in page.url:
            print(f'  In project: {page.url[-50:]}')
            return
        print(f'  WARNING: project navigation failed, falling back...')

    print(f'  Opening Flow...')
    page.goto(FLOW_URL, timeout=120000, wait_until='domcontentloaded')
    human_delay_long(5, 8)
    for _ in range(3):
        dismiss_popups(page)
        page.keyboard.press('Escape')
        human_delay(0.5, 1.0)

    # Handle "Create with Flow" landing/splash page
    try:
        cw_btn = page.query_selector('a:has-text("Create with Flow"), button:has-text("Create with Flow")')
        if cw_btn:
            box = cw_btn.bounding_box()
            if box and box['width'] > 0:
                print('  Found "Create with Flow" landing page, clicking...')
                human_click(page, cw_btn)
                human_delay_long(5, 8)
                for _ in range(3):
                    dismiss_popups(page)
                    page.keyboard.press('Escape')
                    human_delay(0.5, 1.0)
    except Exception as e:
        print(f'  Note: Create with Flow check: {e}')

    # If already in a project, done — but if in /edit/ subpage, go back to project root
    if '/project/' in page.url:
        if '/edit/' in page.url:
            # Strip /edit/... suffix to go back to main project chat view
            project_url = page.url.split('/edit/')[0]
            print(f'  In edit mode, navigating to project root...')
            page.goto(project_url, wait_until='domcontentloaded')
            human_delay_long(5, 8)
        print(f'  In project: {page.url[-50:]}')
        return

    # On main page — wait for projects to load (page shows "Загрузка..." initially)
    print(f'  On main page, entering a project...')
    for _wait in range(15):
        link = page.query_selector('a[href*="/project/"]')
        if link:
            break
        # Check if still loading
        is_loading = page.evaluate("""() => {
            for (const el of document.querySelectorAll('*')) {
                const t = (el.textContent||'').trim();
                if (t === 'Загрузка...' || t === 'Loading...') return true;
            }
            return false;
        }""")
        if is_loading:
            time.sleep(2)
        else:
            time.sleep(1)
    take_screenshot(page, 'flow_main')

    # Try clicking a project link
    link = page.query_selector('a[href*="/project/"]')
    if link:
        link.click()
        human_delay_long(5, 8)

    # If still no /project/ in URL, click first project card
    if '/project/' not in page.url:
        page.evaluate("""() => {
            for (const a of document.querySelectorAll('a')) {
                if ((a.href || '').includes('/project/')) { a.click(); return true; }
            }
            // Click first large thumbnail
            for (const img of document.querySelectorAll('img')) {
                const r = img.getBoundingClientRect();
                if (r.width > 100 && r.height > 100 && r.y > 50) {
                    const parent = img.closest('a, button, [role="button"]');
                    if (parent) { parent.click(); return true; }
                }
            }
            return false;
        }""")
        human_delay_long(5, 8)

    # Wait for URL to contain /project/
    for _ in range(10):
        if '/project/' in page.url:
            break
        human_delay(1, 2)

    if '/project/' in page.url:
        print(f'  In project: {page.url[-50:]}')
        # Wait for project to fully load (not "Загрузка...")
        human_delay_long(3, 6)
    else:
        take_screenshot(page, 'flow_no_project')
        print(f'  WARNING: not in a project. URL: {page.url[:80]}')


def wait_for_flow_ready(page):
    """Wait for prompt field to appear."""
    page.wait_for_load_state('domcontentloaded', timeout=120000)

    # Check if we landed in /edit/ mode (editing a previous generation)
    # and navigate back to project root (chat/generation view)
    if '/edit/' in page.url:
        project_url = page.url.split('/edit/')[0]
        print(f'  In edit mode, navigating back to project chat...')
        page.goto(project_url, wait_until='domcontentloaded')
        human_delay_long(5, 8)

    print(f'  Page URL: {page.url[:80]}')
    take_screenshot(page, 'flow_loaded')
    human_delay_long(2, 4)
    for _ in range(3):
        if not dismiss_popups(page): break
        human_delay(0.5, 1.0)
    sel = '[role="textbox"], [contenteditable="true"]'
    try:
        page.wait_for_selector(sel, timeout=15000)
    except Exception:
        print('  Textbox not found, trying Escape + dismiss...')
        take_screenshot(page, 'flow_no_textbox')
        for _ in range(3):
            page.keyboard.press('Escape')
            human_delay(0.5, 1.0)
        dismiss_popups(page)
        page.wait_for_selector(sel, timeout=120000)
    human_delay(1.5, 3.0)
    dismiss_popups(page)
    print('  Flow workspace ready.')


def _ensure_chat_view(page):
    """Ensure we're in the main project chat view (not /edit/, gallery overlay, etc.).

    Called between clips/components to recover from VEO download or other navigation
    that may leave the page in a non-chat state.
    """
    # 1. If on /edit/ page, navigate to project root
    if '/edit/' in page.url:
        project_url = page.url.split('/edit/')[0]
        print(f'  Returning to project chat from /edit/...')
        page.goto(project_url, wait_until='domcontentloaded')
        human_delay_long(3, 5)

    # 2. Check if textbox is visible — if not, close overlays
    has_textbox = page.evaluate("""() => {
        const tb = document.querySelector('[role="textbox"], [contenteditable="true"]');
        if (!tb) return false;
        const r = tb.getBoundingClientRect();
        return r.width > 50 && r.height > 10 && r.y > 0;
    }""")

    if not has_textbox:
        print(f'  Textbox not visible — closing overlays...')
        for _ in range(5):
            page.keyboard.press('Escape')
            human_delay(0.5, 1.0)
        dismiss_popups(page)
        human_delay(1, 2)

        # Re-check
        has_textbox = page.evaluate("""() => {
            const tb = document.querySelector('[role="textbox"], [contenteditable="true"]');
            if (!tb) return false;
            const r = tb.getBoundingClientRect();
            return r.width > 50 && r.height > 10 && r.y > 0;
        }""")

        if not has_textbox:
            # Last resort: navigate to project root
            if '/project/' in page.url:
                project_url = re.sub(r'(/project/[a-f0-9-]+).*', r'\1', page.url)
                print(f'  Force-navigating to project root...')
                page.goto(project_url, wait_until='domcontentloaded')
                human_delay_long(3, 5)
                wait_for_flow_ready(page)
            else:
                print(f'  WARNING: cannot recover chat view, URL: {page.url[:80]}')
                take_screenshot(page, 'chat_view_recovery_failed')


def take_screenshot(page, name):
    try:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENSHOTS_DIR / f'{name}.png'))
    except Exception: pass


# ── Prompt field ─────────────────────────────────────────────────────────────

def _get_prompt_field(page):
    for sel in ('[role="textbox"]', '[contenteditable="true"]'):
        el = page.query_selector(sel)
        if el:
            box = el.bounding_box()
            if box and box['width'] > 100:
                return el
    return None


def clear_prompt(page):
    field = _get_prompt_field(page)
    if field:
        human_click(page, field)
        mod = 'Meta' if sys.platform == 'darwin' else 'Control'
        page.keyboard.press(f'{mod}+a')
        human_delay(0.05, 0.15)
        page.keyboard.press('Delete')
        human_delay(0.1, 0.3)


def fill_prompt(page, text):
    """Fill prompt via keyboard.type() — safe for React."""
    for attempt in range(3):
        field = _get_prompt_field(page)
        if not field:
            raise RuntimeError('Prompt field not found')
        human_click(page, field)
        mod = 'Meta' if sys.platform == 'darwin' else 'Control'
        page.keyboard.press(f'{mod}+a')
        human_delay(0.1, 0.2)
        page.keyboard.press('Backspace')
        human_delay(0.2, 0.4)
        human_type(page, field, text)
        human_delay(0.5, 1.0)
        result = page.evaluate("""() => {
            const el = document.querySelector('[role="textbox"]') ||
                       document.querySelector('[contenteditable="true"]');
            return el ? el.textContent.trim().length : 0;
        }""")
        if result > 10:
            print(f'  Prompt filled ({result} chars).')
            return
        print(f'  Prompt fill attempt {attempt+1}/3 failed, retrying...')
        human_delay(1, 2)
    raise RuntimeError('fill_prompt FAILED after 3 attempts')


# ── Settings (model, variants) ───────────────────────────────────────────────

def _open_settings_popup(page):
    """Open settings popup by clicking the chip button left of the Generate (→) button.

    The chip shows current mode + settings:
    - Image mode: "🍌 Nano Banana Pro □ x4"
    - Video mode: "Видео □ x4"
    It's always immediately left of the "→ Создать" (Generate) button.
    """
    # Strategy: find the Generate button (arrow_forward), then find the button
    # immediately to its left — that's the settings chip
    chip_info = page.evaluate("""() => {
        // Find Generate button position
        let genBtn = null;
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            const r = btn.getBoundingClientRect();
            if (t.includes('arrow_forward') && r.y > window.innerHeight * 0.7 && r.width < 60) {
                genBtn = r;
                break;
            }
        }
        if (!genBtn) return null;

        // Find the button immediately left of Generate button (closest x, same y row)
        let best = null;
        let bestDist = 999;
        for (const btn of document.querySelectorAll('button')) {
            const r = btn.getBoundingClientRect();
            // Must be left of Generate, same row (similar y), and reasonably sized
            if (r.x < genBtn.x && Math.abs(r.y - genBtn.y) < 30 && r.width > 50 && r.height > 20) {
                const dist = genBtn.x - (r.x + r.width);
                if (dist >= -5 && dist < bestDist) {
                    best = btn;
                    bestDist = dist;
                }
            }
        }
        if (best) {
            return {x: best.getBoundingClientRect().x + best.getBoundingClientRect().width/2,
                    y: best.getBoundingClientRect().y + best.getBoundingClientRect().height/2,
                    text: best.textContent.trim().substring(0, 50)};
        }
        return null;
    }""")

    if chip_info:
        page.mouse.click(chip_info['x'], chip_info['y'])
        human_delay(0.8, 1.5)
        return True

    # Fallback: search by known text labels
    for label in ['Видео', 'Nano Banana', 'Imagen']:
        matches = page.locator(f'button:has-text("{label}")').all()
        best = None
        best_y = -1
        for m in matches:
            box = m.bounding_box()
            if box and box['width'] > 50 and box['y'] > best_y:
                best = m
                best_y = box['y']
        if best:
            best.click()
            human_delay(0.8, 1.5)
            return True
    return False


def set_image_model(page, model_name='Nano Banana Pro'):
    if not _open_settings_popup(page):
        print(f'  WARNING: Settings chip not found')
        return
    dd = page.query_selector('button:has-text("arrow_drop_down"):has-text("Nano")')
    if not dd:
        dd = page.query_selector('button:has-text("arrow_drop_down"):has-text("Imagen")')
    if not dd:
        dd = page.query_selector('button[aria-haspopup="menu"]')
    if dd:
        dd.click()
        human_delay(1.5, 2.5)
        page.evaluate("""(target) => {
            const sels = ['[role="menuitem"]','[role="option"]','[role="menuitemradio"]'];
            for (const sel of sels) {
                for (const el of document.querySelectorAll(sel)) {
                    const t = (el.textContent||'').trim();
                    if (target === 'Nano Banana Pro' && t.includes('Nano Banana') && t.includes('Pro'))
                        { el.click(); return true; }
                    if (target !== 'Nano Banana Pro' && t.includes(target))
                        { el.click(); return true; }
                }
            }
            return false;
        }""", model_name)
        human_delay(0.3, 0.8)
    page.keyboard.press('Escape')
    human_delay(0.3, 0.8)
    print(f'  Model: {model_name}')


def set_orientation(page, orientation='horizontal'):
    """Set image orientation: 'horizontal' (16:9) or 'vertical' (9:16)."""
    if not _open_settings_popup(page):
        return
    target_label = 'По горизонтали' if orientation == 'horizontal' else 'По вертикали'
    page.evaluate("""(label) => {
        for (const btn of document.querySelectorAll('button[role="tab"], button')) {
            const t = (btn.textContent||'').trim();
            if (t.includes(label)) {
                const r = btn.getBoundingClientRect();
                if (r.width > 30 && r.height > 20) { btn.click(); return true; }
            }
        }
        return false;
    }""", target_label)
    human_delay(0.3, 0.8)
    page.keyboard.press('Escape')
    human_delay(0.3, 0.8)
    print(f'  Orientation: {orientation}')


def switch_mode(page, target):
    """Switch Image / Video / Video+Frames mode via settings popup.

    target: 'Создать изображение' | 'Image' | 'Видео по кадрам' | 'video_frames' | 'Video'

    Google Flow UI popup structure (Feb 2026):
    - Row 1: [Image] [Video] — main mode pills (NOT role="tab"!)
    - Row 2 (Video only): [Frames] [Ingredients] — sub-mode pills
    - Row 3: [По горизонтали] [По вертикали] — orientation
    - Row 4: [x1] [x2] [x3] [x4] — variant count
    - Row 5: Model dropdown (Veo 3.1 - Fast, etc.)
    """
    is_video = 'идео' in target or 'video' in target.lower() or 'Video' in target
    is_frames = 'кадр' in target or 'frames' in target.lower() or 'Frames' in target
    mode = 'Video' if is_video else 'Image'

    if not _open_settings_popup(page):
        print(f'  WARNING: Could not open settings popup for mode switch')
        return

    time.sleep(1)
    take_screenshot(page, 'settings_popup_opened')

    # Click Image or Video pill — use MOUSE click (Radix UI pills need real mouse events)
    pill_pos = page.evaluate("""(isVideo) => {
        const target = isVideo ? 'Video' : 'Image';
        const targetRu = isVideo ? 'Видео' : 'Изображение';
        // First pass: exact endsWith
        for (const btn of document.querySelectorAll('button')) {
            const t = (btn.textContent || '').trim();
            const r = btn.getBoundingClientRect();
            if (r.width > 40 && r.height > 20 && r.y > 0 && r.y < window.innerHeight) {
                if (t.endsWith(target) || t.endsWith(targetRu) || t === target || t === targetRu) {
                    return {x: r.x + r.width/2, y: r.y + r.height/2, text: t.substring(0, 50)};
                }
            }
        }
        // Fallback: includes match
        for (const btn of document.querySelectorAll('button')) {
            const t = (btn.textContent || '').trim();
            const r = btn.getBoundingClientRect();
            if (r.width > 40 && r.height > 20 && r.y > 0 && r.y < window.innerHeight) {
                if (t.includes(target) || t.includes(targetRu)) {
                    return {x: r.x + r.width/2, y: r.y + r.height/2, text: t.substring(0, 50)};
                }
            }
        }
        return null;
    }""", is_video)

    if pill_pos:
        page.mouse.click(pill_pos['x'], pill_pos['y'])
        human_delay(0.5, 1.0)
    else:
        print(f'  WARNING: {"Video" if is_video else "Image"} button not found in popup')

    # If video + frames, click Frames sub-tab pill
    if is_video and is_frames:
        time.sleep(1)
        # Use mouse click for Radix pill buttons
        frames_pos = page.evaluate("""() => {
            for (const btn of document.querySelectorAll('button')) {
                const t = (btn.textContent || '').trim();
                const r = btn.getBoundingClientRect();
                if (r.width > 40 && r.height > 20 && r.y > 0 && r.y < window.innerHeight) {
                    if (t.endsWith('Frames') || t.endsWith('Кадры') ||
                        t.includes('Frames') || t.includes('Кадры') || t.includes('crop_free')) {
                        return {x: r.x + r.width/2, y: r.y + r.height/2, text: t.substring(0, 50)};
                    }
                }
            }
            return null;
        }""")
        if frames_pos:
            page.mouse.click(frames_pos['x'], frames_pos['y'])
            time.sleep(1)
            mode = 'Video+Frames'
        else:
            print('  WARNING: Frames button not found in popup')
            take_screenshot(page, 'frames_tab_missing')

    page.keyboard.press('Escape')
    human_delay(0.5, 1.0)

    # Verify frame slots appeared (for Video+Frames mode)
    if is_frames:
        time.sleep(1.5)
        if _check_frame_slots_visible(page):
            mode = 'Video+Frames'
        else:
            print('  WARNING: Frame slots (Первый/Последний кадр) not visible after mode switch')
            take_screenshot(page, 'frame_slots_missing')

    print(f'  Mode: {mode}')


def _check_frame_slots_visible(page):
    """Check if VEO frame slots (Первый кадр / Последний кадр) are visible in the UI."""
    return page.evaluate("""() => {
        for (const el of document.querySelectorAll('div, span, button')) {
            const t = (el.textContent || '').trim();
            if ((t.includes('Первый') || t.includes('First')) &&
                (t.includes('кадр') || t.includes('frame'))) {
                const r = el.getBoundingClientRect();
                if (r.width > 20 && r.height > 20 && r.y > 0) return true;
            }
        }
        return false;
    }""")


def _check_frame_slots_have_images(page):
    """Check if VEO frame slots have images loaded.

    When a frame is loaded, the slot text ('Первый кадр') is replaced by an <img>.
    So we check: if we can still find 'Первый кадр' text, the slot is EMPTY.
    If the text is gone but there's an img at that position, the slot HAS an image.
    """
    return page.evaluate("""() => {
        // If "Первый кадр" text still exists, slot is empty
        for (const el of document.querySelectorAll('div')) {
            const t = (el.textContent||'').trim();
            if (t === 'Первый кадр') {
                return false;  // text still visible = no image loaded
            }
        }
        // Text gone — check for img in the slot area (near bottom, small size ~50x50)
        const h = window.innerHeight;
        for (const img of document.querySelectorAll('img')) {
            const r = img.getBoundingClientRect();
            if (r.y > h * 0.7 && r.width > 30 && r.width < 80 && r.height > 30 && r.height < 80) {
                const alt = (img.alt||'').toLowerCase();
                if (alt.includes('медиаконтент') || alt.includes('media') || alt.includes('frame')) {
                    return true;
                }
            }
        }
        return false;
    }""")


def set_variant_count(page, count=4):
    """Set variant count (x1-x4) via settings popup."""
    if not _open_settings_popup(page):
        return
    # Try role="tab" first, then any button with "x{count}" text
    tab = page.locator(f'button[role="tab"]:has-text("x{count}")').first
    if tab.count() > 0:
        tab.click()
        human_delay(0.3, 0.8)
    else:
        # Buttons may not have role="tab" — search by text
        page.evaluate("""(target) => {
            for (const btn of document.querySelectorAll('button')) {
                const t = (btn.textContent || '').trim();
                const r = btn.getBoundingClientRect();
                if (t === target && r.width > 20 && r.height > 20) {
                    btn.click(); return true;
                }
            }
            return false;
        }""", f'x{count}')
        human_delay(0.3, 0.8)
    page.keyboard.press('Escape')
    human_delay(0.3, 0.8)
    print(f'  Variants: x{count}')


# ── Ingredients ──────────────────────────────────────────────────────────────

_last_uploaded = None


def _open_media_dialog(page):
    """Click the '+' / 'add' button to open media library dialog.

    Flow UI button locations:
    - Image mode: "add_2Создать" in bottom bar (haspopup=dialog) — PREFERRED
    - Top bar: "addДобавить медиаконтент" (haspopup=menu) — opens menu, then "Загрузить изображение"
    """
    # Strategy 1: Find "add_2Создать" in bottom bar (Image mode ingredient button)
    add_pos = page.evaluate("""() => {
        const h = window.innerHeight;
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            const r = btn.getBoundingClientRect();
            // Old-style "+" button: "add_2Создать" in bottom 40%, haspopup=dialog
            if (t.startsWith('add') && r.y > h * 0.6 && r.width > 15 && r.width < 80 &&
                (t.includes('Создать') || t.includes('add_2'))) {
                return {x: r.x + r.width/2, y: r.y + r.height/2, type: 'dialog'};
            }
        }
        // Strategy 2: "addДобавить медиаконтент" in top bar
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            const r = btn.getBoundingClientRect();
            if (t.includes('Добавить медиаконтент') && r.width > 15) {
                return {x: r.x + r.width/2, y: r.y + r.height/2, type: 'menu'};
            }
        }
        return null;
    }""")

    if not add_pos:
        take_screenshot(page, 'add_button_missing')
        print('    "+" button not found')
        return False

    # Use mouse click (Radix components need real events)
    page.mouse.click(add_pos['x'], add_pos['y'])

    if add_pos['type'] == 'menu':
        # New UI: menu opens → click "Загрузить изображение"
        try:
            page.wait_for_selector('[role="menu"]', timeout=3000)
        except Exception:
            human_delay(1, 2)
        human_delay(0.5, 1)
        # Click "Загрузить изображение" menu item
        upload_pos = page.evaluate("""() => {
            for (const el of document.querySelectorAll('[role="menuitem"]')) {
                const t = el.textContent.trim();
                if (t.includes('Загрузить')) {
                    const r = el.getBoundingClientRect();
                    return {x: r.x + r.width/2, y: r.y + r.height/2};
                }
            }
            return null;
        }""")
        if upload_pos:
            page.mouse.click(upload_pos['x'], upload_pos['y'])
            human_delay(0.5, 1)
    else:
        # Old UI: dialog opens directly
        try:
            page.wait_for_selector('[role="dialog"]', timeout=5000)
        except Exception:
            human_delay(1.5, 3)

    human_delay(0.8, 1.5)
    return True


def _find_in_library(page, filename):
    """Search for image by filename in the media library dialog.
    Returns True if found and selected.
    Uses mouse click (not JS click) because Radix dialog items need real mouse events."""
    name_no_ext = Path(filename).stem
    # Find the item coordinates (img with matching alt, or row with matching text)
    item_pos = page.evaluate("""(name) => {
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return null;
        // Look for img with matching alt text
        for (const img of dialog.querySelectorAll('img')) {
            const alt = (img.alt || '').toLowerCase();
            const r = img.getBoundingClientRect();
            if (r.width < 20 || r.height < 20) continue;
            if (alt.includes(name.toLowerCase())) {
                // Find the ROW container (wider than the thumbnail)
                let row = img.parentElement;
                while (row && row !== dialog) {
                    const rr = row.getBoundingClientRect();
                    if (rr.width > 150) break;
                    row = row.parentElement;
                }
                const rowRect = row ? row.getBoundingClientRect() : r;
                return {x: Math.round(rowRect.x + rowRect.width/2),
                        y: Math.round(rowRect.y + rowRect.height/2)};
            }
        }
        // Text-based match
        for (const el of dialog.querySelectorAll('button, [role="option"], [role="listitem"], div')) {
            const t = (el.textContent || '').toLowerCase();
            if (t.includes(name.toLowerCase()) && t.length < 60) {
                const r = el.getBoundingClientRect();
                if (r.width > 100 && r.height > 20 && r.height < 100) {
                    return {x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)};
                }
            }
        }
        return null;
    }""", name_no_ext)

    if item_pos:
        page.mouse.click(item_pos['x'], item_pos['y'])
        return True
    return False


def _upload_in_dialog(page, fpath):
    """Upload a file via the 'Загрузить изображение' button inside media dialog.
    Uses expect_file_chooser to intercept native file dialog."""
    # Find the upload button inside the dialog
    upload_btn = page.evaluate("""() => {
        const dialog = document.querySelector('[role="dialog"]');
        const root = dialog || document;
        for (const btn of root.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            if (t.includes('Загрузить') && t.includes('зображени')) {
                const r = btn.getBoundingClientRect();
                if (r.width > 0) return true;
            }
        }
        return false;
    }""")
    if not upload_btn:
        print('    "Загрузить изображение" button not found')
        return False

    # Use file chooser intercept — click "Загрузить изображение" and catch the dialog
    try:
        btn_el = page.locator('button:has-text("Загрузить изображение")').first
        with page.expect_file_chooser(timeout=8000) as fc_info:
            btn_el.click()
        fc = fc_info.value
        fc.set_files(str(fpath))
        print(f'    Uploaded: {fpath.name}')
        human_delay(5, 8)
        return True
    except Exception as e:
        print(f'    File chooser failed: {e}')
        # Fallback: use hidden input[type=file] directly
        file_input = page.query_selector('input[type="file"][accept="image/*"]')
        if file_input:
            file_input.set_input_files(str(fpath))
            print(f'    Uploaded (input): {fpath.name}')
            human_delay(5, 8)
            return True
        return False


def _close_media_dialog(page):
    """Close the media library dialog."""
    page.keyboard.press('Escape')
    human_delay(0.5, 1.0)


def _count_ingredient_thumbs(page):
    """Count ingredient thumbnails visible in the prompt area (bottom bar)."""
    return page.evaluate("""() => {
        const h = window.innerHeight;
        let count = 0;
        // Ingredient thumbnails are small images near the bottom bar, above the prompt
        for (const img of document.querySelectorAll('img')) {
            const r = img.getBoundingClientRect();
            if (r.width > 20 && r.width < 100 && r.height > 20 && r.height < 100 &&
                r.y > h * 0.7) {
                count++;
            }
        }
        return count;
    }""")


def _upload_ingredient_fresh(page, fpath):
    """Upload a single ingredient via file chooser.

    Tries multiple strategies:
    1. Direct file chooser interception on "Загрузить изображение" click
    2. Find any file input on page and set files directly
    3. Open media dialog, click upload, intercept file chooser with longer timeout

    Returns True if ingredient thumbnail appeared after upload.
    """
    thumbs_before = _count_ingredient_thumbs(page)

    # Strategy 1: Find file input BEFORE opening dialog and set files + dispatch change
    uploaded = False

    # Open media dialog first
    if not _open_media_dialog(page):
        return False

    human_delay(1, 2)

    # Strategy 2: Click "Загрузить изображение" with file chooser interception (longer timeout)
    upload_pos = page.evaluate("""() => {
        const dialog = document.querySelector('[role="dialog"]');
        const root = dialog || document;
        // Find the deepest element whose OWN text (not children) contains the upload label
        let best = null;
        for (const el of root.querySelectorAll('*')) {
            // Get only direct text content (not from children)
            let ownText = '';
            for (const node of el.childNodes) {
                if (node.nodeType === 3) ownText += node.textContent;
            }
            ownText = ownText.trim();
            if (ownText.includes('Загрузить изображение') || ownText.includes('Upload image')) {
                const r = el.getBoundingClientRect();
                if (r.width > 20 && r.height > 10) {
                    best = {x: r.x + r.width/2, y: r.y + r.height/2, text: ownText.substring(0, 60)};
                }
            }
        }
        // Fallback: look for element with exact textContent match (leaf nodes)
        if (!best) {
            for (const el of root.querySelectorAll('span, button, a, div')) {
                const t = el.textContent.trim();
                if (t === 'Загрузить изображение' || t === 'Upload image') {
                    const r = el.getBoundingClientRect();
                    if (r.width > 20 && r.height > 10) {
                        best = {x: r.x + r.width/2, y: r.y + r.height/2, text: t};
                        break;
                    }
                }
            }
        }
        return best;
    }""")

    if upload_pos:
        print(f'    Found upload button: "{upload_pos.get("text", "")[:40]}"')

        # Try file chooser with 60s timeout
        try:
            with page.expect_file_chooser(timeout=60000) as fc_info:
                page.mouse.click(upload_pos['x'], upload_pos['y'])
            fc = fc_info.value
            fc.set_files(str(fpath))
            uploaded = True
            print(f'    Uploaded via file chooser: {fpath.name}')
        except Exception as e:
            print(f'    File chooser timeout, trying input fallback...')

    # Strategy 3: Find ALL file inputs on page, set files with change event dispatch
    if not uploaded:
        file_inputs = page.query_selector_all('input[type="file"]')
        print(f'    Found {len(file_inputs)} file input(s) on page')
        for i, fi in enumerate(file_inputs):
            try:
                fi.set_input_files(str(fpath))
                # Dispatch change event to trigger React/Angular handlers
                page.evaluate("""(el) => {
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                }""", fi)
                uploaded = True
                print(f'    Uploaded via input[{i}] + change event: {fpath.name}')
                break
            except Exception as e2:
                print(f'    Input[{i}] failed: {e2}')

    if not uploaded:
        print(f'    FAILED to upload {fpath.name}')
        take_screenshot(page, 'ingredient_upload_failed')
        page.keyboard.press('Escape')
        human_delay(0.5, 1.0)
        return False

    # Wait for upload to process
    human_delay(5, 8)

    # Handle crop dialog if appeared
    for _ in range(3):
        has_crop = page.evaluate("""() => {
            for (const btn of document.querySelectorAll('button')) {
                const t = btn.textContent.trim();
                if ((t.includes('Кадрировать') || t.includes('Сохранить') || t.includes('Готово') || t.includes('Done')) &&
                    btn.getBoundingClientRect().width > 50) {
                    return {x: btn.getBoundingClientRect().x + btn.getBoundingClientRect().width/2,
                            y: btn.getBoundingClientRect().y + btn.getBoundingClientRect().height/2, text: t};
                }
            }
            return null;
        }""")
        if has_crop:
            print(f'    Crop dialog: clicking "{has_crop["text"][:30]}"')
            page.mouse.click(has_crop['x'], has_crop['y'])
            human_delay(2, 4)
        else:
            break

    # Close media library dialog if still open — try selecting the uploaded image first
    has_dialog = page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        return d && d.getBoundingClientRect().width > 100;
    }""")
    if has_dialog:
        # Try clicking the FIRST (most recent) image thumbnail in the library
        clicked_thumb = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return false;
            // Find image thumbnails in the dialog
            const imgs = dialog.querySelectorAll('img');
            for (const img of imgs) {
                const r = img.getBoundingClientRect();
                if (r.width > 40 && r.height > 40 && r.width < 300) {
                    img.click();
                    return true;
                }
            }
            return false;
        }""")
        if clicked_thumb:
            print(f'    Clicked first thumbnail in media library')
            human_delay(1, 2)

        # Now try 'Выбрать'/'Select'/'Готово' button
        selected = page.evaluate("""() => {
            const dialog = document.querySelector('[role="dialog"]');
            if (!dialog) return false;
            for (const btn of dialog.querySelectorAll('button')) {
                const t = btn.textContent.trim();
                if (t.includes('Выбрать') || t.includes('Select') || t.includes('Готово') || t.includes('Done')) {
                    btn.click(); return true;
                }
            }
            return false;
        }""")
        if selected:
            print(f'    Clicked select/done button')
            human_delay(1, 2)
        else:
            page.keyboard.press('Escape')
            human_delay(0.5, 1.0)

    # Verify ingredient was added
    human_delay(1, 2)
    thumbs_after = _count_ingredient_thumbs(page)
    if thumbs_after > thumbs_before:
        print(f'    Ingredient added! Thumbs: {thumbs_before} -> {thumbs_after}')
        return True
    else:
        print(f'    WARNING: Thumbnail count unchanged ({thumbs_before} -> {thumbs_after})')
        take_screenshot(page, 'ingredient_thumb_missing')
        return False


def _find_location_base_fallback(missing_path: Path):
    """If a location angle file is missing, try to find the base image instead.

    Handles paths like:
      .../references/locations/{locId}/angles/{angleId}.ext  → base
      .../references/locations/{locId}/{locId}_{angleId}.ext → base
    """
    parts = missing_path.parts
    # Structured: references/locations/{locId}/angles/{file}
    if 'angles' in parts:
        idx = parts.index('angles')
        loc_dir = Path(*parts[:idx])  # .../references/locations/{locId}
        loc_id = parts[idx - 1]
    # Flat: references/locations/{locId}/{locId}_{angle}.ext
    elif 'locations' in parts:
        idx = parts.index('locations')
        if idx + 1 < len(parts):
            loc_dir = Path(*parts[:idx + 2])
            loc_id = parts[idx + 1]
        else:
            return None
    else:
        return None

    # Try common base naming conventions
    for prefix in (f'{loc_id}_base', 'base'):
        for ext in ('png', 'jpg', 'jpeg', 'webp'):
            candidate = loc_dir / f'{prefix}.{ext}'
            if candidate.exists():
                return candidate
    return None


def upload_ingredients(page, ingredient_paths):
    """Upload ingredient images, reusing already-attached ones when possible.

    Optimization: if the new ingredient list shares a common prefix with the
    previous one, we only remove extras from the end and upload the missing ones.
    This saves ~10-15s per shared ingredient (54% of clips share partial ingredients).
    """
    global _last_uploaded
    if not ingredient_paths:
        return 0
    resolved = []
    for rel in ingredient_paths:
        full = REFS_DIR / rel
        if full.exists():
            resolved.append(full)
        else:
            # Try as absolute path
            p = Path(rel)
            if p.exists():
                resolved.append(p)
            else:
                # Fallback: if missing location angle → use base image
                fallback = _find_location_base_fallback(full)
                if fallback:
                    print(f'  FALLBACK: {Path(rel).name} not found, using base: {fallback.name}')
                    resolved.append(fallback)
                else:
                    print(f'  WARNING: ingredient not found: {full}')
    if not resolved:
        return 0

    keys = tuple(str(f) for f in resolved)
    prev_keys = _last_uploaded or ()

    # Exact match — verify thumbs are still visible
    if keys == prev_keys:
        cached_count = _count_ingredient_thumbs(page)
        if cached_count >= len(resolved):
            print(f'  Ingredients cached ({len(resolved)} files, {cached_count} thumbs)')
            return len(resolved)
        else:
            print(f'  Ingredient cache stale ({cached_count} thumbs, expected {len(resolved)})')
            prev_keys = ()

    # Find common prefix length between previous and new ingredients
    common_prefix = 0
    for i in range(min(len(prev_keys), len(keys))):
        if prev_keys[i] == keys[i]:
            common_prefix += 1
        else:
            break

    # Verify the common prefix thumbs are actually still visible
    if common_prefix > 0:
        current_thumbs = _count_ingredient_thumbs(page)
        if current_thumbs < common_prefix:
            print(f'  Prefix check: only {current_thumbs} thumbs visible, expected >= {common_prefix}. Full reload.')
            common_prefix = 0

    if common_prefix > 0 and common_prefix < len(prev_keys):
        # Remove extras from the end (ingredients beyond the common prefix)
        extras_to_remove = len(prev_keys) - common_prefix
        print(f'  Reusing {common_prefix} ingredients, removing {extras_to_remove} extra(s)')
        for _ in range(extras_to_remove):
            _remove_last_ingredient(page)
            human_delay(0.3, 0.6)
    elif common_prefix == 0:
        # No overlap — clear everything
        clear_ingredients(page)
        human_delay(1, 2)
    # else: common_prefix == len(prev_keys), all previous are reused, just add new ones

    if common_prefix > 0:
        print(f'  Reusing {common_prefix}/{len(resolved)} ingredients')

    # Upload only the new ingredients (after the common prefix)
    loaded = common_prefix
    for i in range(common_prefix, len(resolved)):
        fpath = resolved[i]
        print(f'  Loading ingredient {i+1}/{len(resolved)}: {fpath.name}')

        if _upload_ingredient_fresh(page, fpath):
            loaded += 1
        else:
            # Retry once
            print(f'    Retrying {fpath.name}...')
            human_delay(2, 3)
            page.keyboard.press('Escape')
            human_delay(1, 2)
            if _upload_ingredient_fresh(page, fpath):
                loaded += 1

    # Final escape to ensure no lingering dialogs
    page.keyboard.press('Escape')
    human_delay(0.5, 1.0)

    thumb_count = _count_ingredient_thumbs(page)
    print(f'  Loaded {loaded}/{len(resolved)} ingredients. Thumbs visible: {thumb_count}')

    # Take screenshot for debugging
    if loaded > common_prefix:
        take_screenshot(page, 'ingredients_loaded')

    _last_uploaded = keys if loaded == len(resolved) else None
    return loaded


def _remove_last_ingredient(page):
    """Remove the last (rightmost) ingredient thumbnail from the prompt area."""
    removed = page.evaluate("""() => {
        const h = window.innerHeight;
        // Collect all close buttons near ingredient thumbnails (bottom of page)
        const closeBtns = [];
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim().toLowerCase();
            const r = btn.getBoundingClientRect();
            if ((t === 'close' || t === '×' || t === 'cancel') &&
                r.width > 0 && r.width < 40 && r.y > h * 0.7) {
                closeBtns.push({btn, x: r.x});
            }
        }
        for (const btn of document.querySelectorAll('button[aria-label*="emov"], button[aria-label*="удал"], button[aria-label*="lose"]')) {
            const r = btn.getBoundingClientRect();
            if (r.width > 0 && r.y > h * 0.7) {
                closeBtns.push({btn, x: r.x});
            }
        }
        if (closeBtns.length === 0) return false;
        // Click the rightmost one (last ingredient)
        closeBtns.sort((a, b) => b.x - a.x);
        closeBtns[0].btn.click();
        return true;
    }""")
    if removed:
        print(f'    Removed last ingredient')
    return removed


def clear_ingredients(page):
    """Remove all ingredient thumbnails from the prompt area."""
    cleared = 0
    for _ in range(10):
        removed = page.evaluate("""() => {
            const h = window.innerHeight;
            // Look for close/remove buttons near ingredient thumbnails
            for (const btn of document.querySelectorAll('button')) {
                const t = btn.textContent.trim().toLowerCase();
                const r = btn.getBoundingClientRect();
                // Close buttons on ingredient thumbnails: small, near bottom
                if ((t === 'close' || t === '×' || t === 'cancel') &&
                    r.width > 0 && r.width < 40 && r.y > h * 0.7) {
                    btn.click(); return true;
                }
            }
            // Also try aria-label based removal
            for (const btn of document.querySelectorAll('button[aria-label*="emov"], button[aria-label*="удал"], button[aria-label*="lose"]')) {
                const r = btn.getBoundingClientRect();
                if (r.width > 0 && r.y > h * 0.7) {
                    btn.click(); return true;
                }
            }
            return false;
        }""")
        if not removed:
            break
        cleared += 1
        human_delay(0.3, 0.6)
    if cleared:
        print(f'  Cleared {cleared} ingredient(s)')


# ── VEO frame slots ─────────────────────────────────────────────────────────

def _dismiss_crop_dialog(page):
    """Dismiss crop dialog via JS click (bypasses ReactCrop overlay)."""
    dismissed = page.evaluate("""() => {
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            if ((t.includes('Кадрировать и сохранить') || t.includes('Сохранить')) &&
                btn.getBoundingClientRect().width > 50) {
                btn.click(); return true;
            }
        }
        return false;
    }""")
    if dismissed:
        print('  Crop dialog saved.')
        human_delay_long(2.5, 5.0)
    return dismissed


def clear_veo_frame_slots(page):
    """Remove pre-uploaded frames from VEO frame slots."""
    cleared = 0
    for _ in range(4):
        removed = page.evaluate("""() => {
            for (const btn of document.querySelectorAll('button')) {
                const t = btn.textContent.trim();
                const r = btn.getBoundingClientRect();
                if (t.includes('close') && r.width > 0 && r.width < 40 && r.y > 600) {
                    btn.click(); return true;
                }
            }
            return false;
        }""")
        if not removed:
            break
        cleared += 1
        human_delay(0.8, 1.8)
    if cleared:
        print(f'  Cleared {cleared} VEO frame slot(s)')


def upload_frame_for_veo(page, frame_path, slot_index):
    """Upload a frame to VEO slot (0=first, 1=last).

    Always uploads fresh via file chooser to avoid stale library copies.
    VEO frames may change (e.g. after re-selection), so library search
    is unreliable — an old wrong version could have the same filename.
    """
    slot_name = 'First' if slot_index == 0 else 'Last'
    slot_text = 'Первый' if slot_index == 0 else 'Последний'

    # Find and click the slot DIV
    slot_info = page.evaluate("""(slotText) => {
        for (const el of document.querySelectorAll('div, button')) {
            const t = (el.textContent||'').trim();
            if (t.includes(slotText) && t.includes('кадр') && t.length < 30) {
                const r = el.getBoundingClientRect();
                if (r.width > 20 && r.width < 200 && r.height > 20) {
                    return {x: r.x + r.width/2, y: r.y + r.height/2};
                }
            }
        }
        return null;
    }""", slot_text)

    if not slot_info:
        print(f'  WARNING: VEO {slot_name} slot not found')
        return False

    # Click slot to open media dialog
    page.mouse.click(slot_info['x'], slot_info['y'])
    human_delay(1.5, 3.0)
    take_screenshot(page, f'veo_slot_{slot_name}_clicked')

    # Wait for media dialog
    dialog = page.locator('[role="dialog"]')
    try:
        dialog.wait_for(timeout=5000)
    except Exception:
        print(f'  WARNING: Media dialog did not appear for {slot_name} slot')
        return False

    take_screenshot(page, f'veo_slot_{slot_name}_dialog_open')

    # Upload fresh via file chooser — click "Загрузить изображение" button
    upload_pos = page.evaluate("""() => {
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return null;
        for (const btn of dialog.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            if (t.includes('Загрузить') || t.includes('Upload')) {
                const r = btn.getBoundingClientRect();
                if (r.width > 30) return {x: r.x + r.width/2, y: r.y + r.height/2, text: t.substring(0, 60)};
            }
        }
        return null;
    }""")

    if not upload_pos:
        print(f'  WARNING: Upload button not found in dialog for {slot_name}')
        page.keyboard.press('Escape')
        return False

    try:
        with page.expect_file_chooser(timeout=5000) as fc_info:
            page.mouse.click(upload_pos['x'], upload_pos['y'])
        fc = fc_info.value
        fc.set_files(frame_path)
        print(f'  Uploaded {slot_name} frame: {Path(frame_path).name}')
    except Exception as e:
        print(f'  WARNING: File chooser failed for {slot_name}: {e}')
        # Fallback: try hidden file input
        file_input = page.query_selector('input[type="file"][accept="image/*"]')
        if file_input:
            file_input.set_input_files(frame_path)
            print(f'  Uploaded {slot_name} frame via file input fallback')
        else:
            page.keyboard.press('Escape')
            return False

    human_delay(3.0, 5.0)
    take_screenshot(page, f'veo_slot_{slot_name}_after_upload')

    # Handle crop dialog if it appeared
    has_crop = page.evaluate("""() => {
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            if (t.includes('Кадрировать') || t.includes('Сохранить')) {
                const r = btn.getBoundingClientRect();
                if (r.width > 50) return true;
            }
        }
        return false;
    }""")
    if has_crop:
        _dismiss_crop_dialog(page)
        human_delay(1.0, 2.0)

    # Close media dialog if still open (upload usually auto-closes it)
    has_dialog = page.evaluate("""() => {
        const d = document.querySelector('[role="dialog"]');
        return d && d.getBoundingClientRect().width > 100;
    }""")
    if has_dialog:
        _close_media_dialog(page)
        human_delay(0.5, 1.0)

    # Verify the slot now has an image
    human_delay(1.0, 2.0)
    take_screenshot(page, f'veo_slot_{slot_name}_final')
    has_image = _check_frame_slots_have_images(page)
    if has_image:
        print(f'  Verified: {slot_name} slot has image')
    else:
        print(f'  WARNING: {slot_name} slot may not have image attached')

    return True


# ── Generate button & polling ────────────────────────────────────────────────

def click_generate(page):
    """Click the Generate button using mouse click to avoid React visibility issues."""
    pos = page.evaluate("""() => {
        const h = window.innerHeight;
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            const r = btn.getBoundingClientRect();
            if (t.includes('arrow_forward') && r.y > h * 0.7 && r.width > 15 && r.width < 100) {
                return {x: r.x + r.width/2, y: r.y + r.height/2};
            }
        }
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            const r = btn.getBoundingClientRect();
            if ((t.includes('Генерировать') || t.includes('Generate') || t.includes('Создать')) &&
                r.y > h * 0.7 && r.width > 15) {
                return {x: r.x + r.width/2, y: r.y + r.height/2};
            }
        }
        return null;
    }""")
    if pos:
        page.mouse.click(pos['x'], pos['y'])
        print('  Clicked Generate.')
        human_delay(3.0, 6.0)
    else:
        raise RuntimeError('Generate button not found')


def _scroll_chat_bottom(page):
    page.evaluate("""() => {
        for (const el of document.querySelectorAll('*')) {
            if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                const r = el.getBoundingClientRect();
                if (r.x < 400 && r.width > 200) { el.scrollTop = el.scrollHeight; return; }
            }
        }
    }""")


def _is_generating(page):
    """Check if generation is in progress.

    For images: Generate button goes disabled.
    For video (VEO): button stays enabled, but percentage placeholders (NN%) appear.
    """
    # Check button disabled state (works for images)
    btn_disabled = page.evaluate("""() => {
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            if (t.includes('arrow_forward')) {
                return btn.disabled === true || btn.getAttribute('aria-disabled') === 'true';
            }
        }
        return false;
    }""")
    if btn_disabled:
        return True

    # Check for VEO percentage placeholders (1%, 27%, etc.)
    has_percent = page.evaluate(r"""() => {
        for (const el of document.querySelectorAll('div, span')) {
            const t = (el.textContent||'').trim();
            if (/^\d{1,3}%$/.test(t)) {
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0 && r.y > 0) return true;
            }
        }
        return false;
    }""")
    return has_percent


def _count_errors(page):
    """Count error cards currently visible in the BOTTOM HALF of viewport.

    Only counts errors near the bottom of the chat (where new messages appear)
    to avoid false positives from old error messages in chat history that
    appear due to virtual scrolling.
    """
    return page.evaluate("""(errorPatterns) => {
        let count = 0;
        const seen = new Set();
        const h = window.innerHeight;
        const minY = h * 0.4;  // Only bottom 60% of viewport
        // Standard error messages (longer text)
        for (const el of document.querySelectorAll('div, span, p')) {
            const t = (el.textContent||'').trim();
            for (const pat of errorPatterns) {
                if (t.includes(pat) && t.length < 300 && t.length > 5) {
                    if (seen.has(el)) continue;
                    seen.add(el);
                    const r = el.getBoundingClientRect();
                    if (r.width > 100 && r.height > 20 && r.y >= minY && r.y < h) {
                        count++;
                        break;
                    }
                }
            }
        }
        // VEO short error cards (just "Ошибка." text in small elements)
        for (const el of document.querySelectorAll('div, span, p')) {
            const t = (el.innerText||'').trim();
            if (t.length < 30 && t.includes(errorPatterns[3])) {
                if (seen.has(el)) continue;
                seen.add(el);
                const r = el.getBoundingClientRect();
                if (r.width > 20 && r.y >= minY && r.y < h) {
                    count++;
                }
            }
        }
        return count;
    }""", ['Что-то пошло не так', 'Не удалось сгенерировать', 'Произошла ошибка', 'Ошибка'])


def _click_retry_on_error(page):
    """Click 'Повторить' (retry) button on the last error card.

    When a generation fails, Flow shows 3 buttons below the error card:
    - 🔄 Повторить (retry with same params)
    - ↩️ Сгенерировать повторно (regenerate)
    - ❌ Удалить (delete)

    We click the first button (Повторить) — it retries the same generation
    without needing to re-upload ingredients or re-type prompt.

    Returns True if button was found and clicked, False otherwise.
    """
    # Scroll to bottom to ensure error card buttons are visible
    _scroll_chat_bottom(page)
    time.sleep(1)

    # Look for retry-related buttons near error cards
    clicked = page.evaluate("""() => {
        // Strategy 1: Find buttons by aria-label/title containing retry keywords
        const retryLabels = ['Повторить', 'Retry', 'Попробовать снова'];
        for (const label of retryLabels) {
            // aria-label match
            const btn = document.querySelector(`button[aria-label="${label}"], button[title="${label}"]`);
            if (btn && btn.getBoundingClientRect().height > 0) {
                btn.click();
                return 'label:' + label;
            }
        }

        // Strategy 2: Find the FIRST icon button in a group of 3 near an error card.
        // Error cards have text 'Ошибка' and below them are 3 small icon buttons.
        const errorCards = [];
        for (const el of document.querySelectorAll('div, span, p')) {
            const t = (el.innerText || '').trim();
            if ((t.includes('Ошибка') || t.includes('Что-то пошло не так')) && t.length < 200) {
                const r = el.getBoundingClientRect();
                if (r.width > 50 && r.height > 10 && r.y > window.innerHeight * 0.3) {
                    errorCards.push({el, y: r.y});
                }
            }
        }
        if (errorCards.length === 0) return null;

        // Take the LAST (most recent) error card
        errorCards.sort((a, b) => b.y - a.y);
        const lastError = errorCards[0];

        // Find small icon buttons below the error card (within 200px)
        const buttons = [];
        for (const btn of document.querySelectorAll('button')) {
            const r = btn.getBoundingClientRect();
            if (r.width >= 24 && r.width <= 64 && r.height >= 24 && r.height <= 64 &&
                r.y > lastError.y && r.y < lastError.y + 300) {
                buttons.push(btn);
            }
        }
        if (buttons.length >= 2) {
            // Sort left-to-right, first button is "Повторить"
            buttons.sort((a, b) => a.getBoundingClientRect().x - b.getBoundingClientRect().x);
            buttons[0].click();
            return 'positional:first-of-' + buttons.length;
        }

        // Strategy 3: Look for mat-icon or icon with 'refresh/replay/redo' in the error area
        for (const icon of document.querySelectorAll('mat-icon, span.material-icons, span.material-symbols-outlined')) {
            const t = (icon.textContent || '').trim().toLowerCase();
            if (t === 'refresh' || t === 'replay' || t === 'redo' || t === 'autorenew') {
                const r = icon.getBoundingClientRect();
                if (r.y > lastError.y && r.y < lastError.y + 300) {
                    const btn = icon.closest('button') || icon;
                    btn.click();
                    return 'icon:' + t;
                }
            }
        }

        return null;
    }""")

    if clicked:
        print(f'    Clicked retry button ({clicked})')
        return True

    # Debug: take screenshot and log available buttons near errors
    take_screenshot(page, 'retry_button_not_found')
    debug_info = page.evaluate("""() => {
        const info = [];
        // Find all buttons in the bottom half of viewport
        const h = window.innerHeight;
        for (const btn of document.querySelectorAll('button')) {
            const r = btn.getBoundingClientRect();
            if (r.y > h * 0.3 && r.y < h && r.width > 10 && r.height > 10) {
                const label = btn.getAttribute('aria-label') || btn.getAttribute('title') || '';
                const text = (btn.innerText || '').trim().substring(0, 50);
                const icon = btn.querySelector('mat-icon, span.material-icons, span.material-symbols-outlined');
                const iconText = icon ? (icon.textContent || '').trim() : '';
                info.push({
                    x: Math.round(r.x), y: Math.round(r.y),
                    w: Math.round(r.width), h: Math.round(r.height),
                    label, text, icon: iconText,
                    classes: btn.className.substring(0, 80)
                });
            }
        }
        return info;
    }""")
    if debug_info:
        print(f'    Buttons near errors:')
        for b in debug_info[:10]:
            print(f'      [{b["x"]},{b["y"]} {b["w"]}x{b["h"]}] label="{b["label"]}" text="{b["text"]}" icon="{b["icon"]}"')
    return False


def _check_new_error(page, errors_before):
    """Check if a new error appeared since errors_before count."""
    current = _count_errors(page)
    if current > errors_before:
        print(f'    New errors detected: {errors_before} -> {current}')
        # Determine error type
        error_type = page.evaluate("""() => {
            for (const el of document.querySelectorAll('*')) {
                const t = (el.textContent||'').trim();
                if (t.length > 300 || t.length < 5) continue;
                if (t.includes('дневн') && t.includes('лимит')) return 'rate_limit';
                if (t.includes('daily') && t.includes('limit')) return 'rate_limit';
                if (t.includes('Не удалось сгенерировать')) return 'content_filter';
            }
            return 'server_error';
        }""")
        print(f'    ERROR: {error_type}')
        return error_type
    return None


def _get_all_generated_image_urls(page):
    """Get set of all generated image URLs currently in DOM."""
    return set(page.evaluate("""() => {
        const urls = [];
        for (const img of document.querySelectorAll('img[alt="Сгенерированное изображение"], img[alt="Generated image"]')) {
            if (img.src && img.getBoundingClientRect().width > 50) urls.push(img.src);
        }
        return urls;
    }"""))


def _get_last_generated_image_url(page):
    """Get the src URL of the last generated image in DOM."""
    return page.evaluate("""() => {
        const imgs = document.querySelectorAll('img[alt="Сгенерированное изображение"], img[alt="Generated image"]');
        if (imgs.length === 0) return null;
        return imgs[imgs.length - 1].src || null;
    }""")


def _get_last_generated_video_url(page):
    """Get the src URL of the last generated video in DOM.

    In chat view, videos appear as <img alt="Значок видео"> (thumbnails).
    In full/dashboard view, they appear as <video> elements.
    Both use media.getMediaUrlRedirect API URLs.
    """
    # First try <video> elements (full/dashboard view)
    url = page.evaluate("""() => {
        const videos = document.querySelectorAll('video');
        let last = null;
        for (const v of videos) {
            if (v.src) last = v.src;
        }
        return last;
    }""")
    if url:
        return url

    # Fallback: <img alt="Значок видео"> in chat view
    url = page.evaluate("""() => {
        const imgs = document.querySelectorAll('img[alt="Значок видео"]');
        if (imgs.length === 0) return null;
        const last = imgs[imgs.length - 1];
        return last.src || null;
    }""")
    return url


def _open_fullview_and_get_video_url(page):
    """Click last video thumbnail, wait for <video> to appear, return its URL.
    Does NOT close fullview — caller must call _close_fullview().
    """
    # Click last video thumbnail
    thumb_count = page.evaluate("""() => {
        const imgs = document.querySelectorAll('img[alt="Значок видео"]');
        return imgs.length;
    }""")
    if thumb_count == 0:
        return None

    # Click the last thumbnail
    page.evaluate("""() => {
        const imgs = document.querySelectorAll('img[alt="Значок видео"]');
        if (imgs.length > 0) {
            const last = imgs[imgs.length - 1];
            last.click();
        }
    }""")
    time.sleep(3)

    # Wait for <video> element to appear
    for _ in range(10):
        url = page.evaluate("""() => {
            for (const v of document.querySelectorAll('video')) {
                const src = v.src || v.currentSrc || '';
                if (src) return src;
                for (const s of v.querySelectorAll('source')) {
                    if (s.src) return s.src;
                }
            }
            return null;
        }""")
        if url:
            return url
        time.sleep(1)
    return None


def _download_video_by_thumb_index(page, rel_index, dest_path, seen_urls):
    """Click a specific video thumbnail by relative index and download.
    rel_index: -1 = last, -2 = second-to-last, etc.
    Returns (path, url) tuple or None.
    """
    thumb_count = page.evaluate("""() => {
        return document.querySelectorAll('img[alt="Значок видео"]').length;
    }""")
    abs_idx = thumb_count + rel_index
    if abs_idx < 0:
        return None

    page.evaluate("""(idx) => {
        const imgs = document.querySelectorAll('img[alt="Значок видео"]');
        if (idx >= 0 && idx < imgs.length) imgs[idx].click();
    }""", abs_idx)
    time.sleep(3)

    for _ in range(10):
        url = page.evaluate("""() => {
            for (const v of document.querySelectorAll('video')) {
                const src = v.src || v.currentSrc || '';
                if (src) return src;
                for (const s of v.querySelectorAll('source')) {
                    if (s.src) return s.src;
                }
            }
            return null;
        }""")
        if url and url not in seen_urls:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if download_via_fetch(page, url, dest_path):
                _close_fullview(page)
                return (dest_path, url)
        time.sleep(1)

    _close_fullview(page)
    return None


def _open_video_fullview(page):
    """Click last video thumbnail in chat to open full view overlay.
    Returns list of video URLs found in the full view, or empty list.
    """
    # Find and click last video thumbnail (multiple selectors for different UI states)
    thumb = page.evaluate("""() => {
        const selectors = [
            'img[alt="Значок видео"]',
            'img[alt*="video" i]',
            'img[alt*="Video"]',
            'img[alt="Video icon"]',
            'img[alt="Generated video"]',
            'img[alt="Сгенерированное видео"]',
        ];
        for (const sel of selectors) {
            const imgs = document.querySelectorAll(sel);
            if (imgs.length > 0) {
                const last = imgs[imgs.length - 1];
                const r = last.getBoundingClientRect();
                if (r.width >= 20) {
                    return {x: r.x + r.width/2, y: r.y + r.height/2, sel: sel, count: imgs.length};
                }
            }
        }
        return null;
    }""")
    if not thumb:
        print('    No video thumbnail found to click')
        return []

    print(f'    Found video thumbnail via {thumb.get("sel","")} (count={thumb.get("count",0)})')
    page.mouse.click(thumb['x'], thumb['y'])
    time.sleep(3)

    # Wait for <video> elements to appear in full view
    for _wait in range(10):
        urls = page.evaluate("""() => {
            const results = [];
            for (const v of document.querySelectorAll('video')) {
                const src = v.src || v.currentSrc || '';
                if (src && !results.includes(src)) results.push(src);
                for (const s of v.querySelectorAll('source')) {
                    const ssrc = s.src || '';
                    if (ssrc && !results.includes(ssrc)) results.push(ssrc);
                }
            }
            return results;
        }""")
        if urls:
            return urls
        time.sleep(1)

    print('    No <video> elements found in full view')
    return []


def _close_fullview(page):
    """Close full view overlay by pressing Escape or clicking close button."""
    # Try close button first
    page.evaluate("""() => {
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            const r = btn.getBoundingClientRect();
            if ((t === 'close' || t === 'arrow_back' || t.includes('Закрыть') || t.includes('Назад')) &&
                r.width > 0 && r.y < 80) {
                btn.click(); return true;
            }
        }
        return false;
    }""")
    human_delay(0.5, 1.0)
    page.keyboard.press('Escape')
    human_delay(1.0, 2.0)


def _navigate_fullview_and_collect_urls(page, expected_count=4):
    """In video full view, navigate through all videos using arrow buttons.
    Returns list of unique video URLs.
    """
    all_urls = set()

    for step in range(expected_count + 2):
        # Collect current video URL
        urls = page.evaluate("""() => {
            const results = [];
            for (const v of document.querySelectorAll('video')) {
                const src = v.src || v.currentSrc || '';
                if (src) results.push(src);
                for (const s of v.querySelectorAll('source')) {
                    if (s.src) results.push(s.src);
                }
            }
            return results;
        }""")
        for u in urls:
            all_urls.add(u)

        if len(all_urls) >= expected_count:
            break

        # Try clicking "next" arrow to go to next video
        clicked = page.evaluate("""() => {
            for (const btn of document.querySelectorAll('button')) {
                const t = btn.textContent.trim();
                const aria = btn.getAttribute('aria-label') || '';
                const r = btn.getBoundingClientRect();
                if ((t === 'arrow_forward_ios' || t === 'navigate_next' || t === 'chevron_right' ||
                     aria.includes('Далее') || aria.includes('Next') || aria.includes('Следующ')) &&
                    r.width > 0 && r.height > 0) {
                    btn.click(); return true;
                }
            }
            return false;
        }""")
        if not clicked:
            break
        time.sleep(2)

    return list(all_urls)


def _count_generated_media(page, media='img'):
    """Count generated media items currently in DOM."""
    if media == 'img':
        return page.evaluate("""() => {
            return document.querySelectorAll('img[alt="Сгенерированное изображение"], img[alt="Generated image"]').length;
        }""")
    else:
        # Videos can be <video> elements or <img> thumbnails with video-related alt text
        return page.evaluate("""() => {
            let count = 0;
            // Count <video> elements
            for (const v of document.querySelectorAll('video')) {
                if (v.src || v.currentSrc) count++;
            }
            // Count video thumbnails in chat view (multiple selectors)
            const thumbSels = [
                'img[alt="Значок видео"]',
                'img[alt*="video" i]',
                'img[alt="Video icon"]',
                'img[alt="Generated video"]',
                'img[alt="Сгенерированное видео"]',
            ];
            const seen = new Set();
            for (const sel of thumbSels) {
                for (const el of document.querySelectorAll(sel)) {
                    if (!seen.has(el)) { seen.add(el); count++; }
                }
            }
            return count;
        }""")


def poll_generation(page, errors_before=0, timeout_sec=GENERATION_TIMEOUT, media='img'):
    """Wait for generation to complete.

    For images: watches Generate button disabled → enabled transition.
    For video (VEO): watches percentage placeholders (NN%) appear → disappear.
    Returns 'success'|'server_error'|'content_filter'|'timeout'.
    """
    elapsed = 0
    was_generating = False
    gen_started_at = 0
    retry_click_at = 60  # Retry clicking Generate if nothing happens after 60s
    retried = False
    count_before = _count_generated_media(page, media)
    # Minimum generation time to avoid false positives (VEO ~60-120s, images ~15-30s)
    min_gen_time = 30 if media == 'video' else 12

    while elapsed < timeout_sec:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        generating = _is_generating(page)
        if generating and not was_generating:
            print(f'    Generation started ({elapsed}s)')
            was_generating = True
            gen_started_at = elapsed

        if was_generating and not generating:
            gen_duration = elapsed - gen_started_at
            if gen_duration < min_gen_time:
                # Too fast — might be a real server error or a false positive flicker.
                # Check if a new error card appeared (using original baseline).
                err = _check_new_error(page, errors_before)
                if err:
                    # Real server error — the generation failed quickly
                    print(f'    Indicators gone after {gen_duration}s (< {min_gen_time}s min) — {err}')
                    return err
                # No new error — just a UI flicker, keep waiting
                print(f'    Indicators gone after {gen_duration}s (< {min_gen_time}s min) — waiting...')
                was_generating = False
                gen_started_at = 0
                continue

            print(f'    Generation complete ({elapsed}s, duration={gen_duration}s)')
            # Wait for new content to render (VEO needs more time)
            render_wait = 10 if media == 'video' else 3
            time.sleep(render_wait)
            # Scroll to bottom to make new content visible
            _scroll_chat_bottom(page)
            time.sleep(2)
            err = _check_new_error(page, errors_before)
            if err:
                return err
            # Verify new content appeared
            count_after = _count_generated_media(page, media)
            if count_after > count_before:
                print(f'    New media: {count_before} -> {count_after}')
            return 'success'

        # Check for NEW error (not old ones in chat history)
        # For VEO, check earlier — errors can appear within seconds
        err_check_threshold = 5 if media == 'video' else 15
        if elapsed >= err_check_threshold and not generating:
            err = _check_new_error(page, errors_before)
            if err:
                return err

        # Retry clicking Generate if nothing happened after retry_click_at seconds
        if not was_generating and not retried and elapsed >= retry_click_at:
            retried = True
            print(f'    No generation started after {elapsed}s — retrying Generate click...')
            take_screenshot(page, 'poll_retry_generate')
            try:
                click_generate(page)
                errors_before = _count_errors(page)
            except RuntimeError:
                print(f'    Generate button not found on retry')

        if elapsed % 30 == 0:
            st = ' (generating...)' if generating else ' (waiting for start...)'
            print(f'    Poll... ({elapsed}s{st})')

    print(f'    TIMEOUT after {timeout_sec}s')
    return 'timeout'


# ── Download media ───────────────────────────────────────────────────────────

def download_via_fetch(page, url, save_path, retries=2, min_size=1024):
    """Download file via browser fetch with retry and size validation.
    Args:
        retries: number of attempts (default 2)
        min_size: minimum acceptable file size in bytes (default 1KB)
    """
    for attempt in range(retries):
        if attempt > 0:
            print(f'    Retry download {attempt+1}/{retries}...')
            time.sleep(5)
        result = page.evaluate("""async (url) => {
            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 120000);
                const resp = await fetch(url, {signal: controller.signal});
                clearTimeout(timeout);
                if (!resp.ok) return {error: 'HTTP '+resp.status};
                const blob = await resp.blob();
                return {type: blob.type, size: blob.size,
                    data: await new Promise(r => {
                        const reader = new FileReader();
                        reader.onload = () => r(reader.result.split(',')[1]);
                        reader.readAsDataURL(blob);
                    })};
            } catch(e) { return {error: e.message}; }
        }""", url)
        if 'error' in result:
            print(f'    Fetch error: {result["error"]}')
            continue
        data = base64.b64decode(result['data'])
        if len(data) < min_size:
            print(f'    File too small: {len(data)} bytes (min {min_size}) — retrying')
            continue
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(data)
        print(f'  Saved: {save_path.name} ({len(data)} bytes, type={result.get("type","")})')
        _r2_sync_upload(save_path)
        return True
    print(f'    Failed to download after {retries} attempts')
    return False


def download_last_image(page, dest_path):
    """Download the last generated image from the chat."""
    _scroll_chat_bottom(page)
    human_delay(1, 2)
    url = _get_last_generated_image_url(page)
    if not url:
        print('    No generated image found in DOM')
        return None
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if download_via_fetch(page, url, dest_path):
        return dest_path
    return None


def download_last_video(page, dest_path):
    """Download the last generated video from the chat.
    Opens full view to access <video> elements."""
    _scroll_chat_bottom(page)
    human_delay(1, 2)

    # Try direct <video> first (works if already in full view)
    url = _get_last_generated_video_url(page)
    if url and 'media' in url.lower():
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if download_via_fetch(page, url, dest_path):
            return dest_path

    # Open full view to get real video URL
    urls = _open_video_fullview(page)
    if urls:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if download_via_fetch(page, urls[0], dest_path):
            _close_fullview(page)
            return dest_path
    _close_fullview(page)
    print('    No generated video found')
    return None


def _download_videos_individually(page, dest_dir, expected_count=4):
    """Fallback: click each video thumbnail one by one to download.
    Returns list of saved file paths.
    """
    _scroll_chat_bottom(page)
    human_delay(1, 2)

    # Find all video thumbnails
    thumb_count = page.evaluate("""() => {
        const selectors = [
            'img[alt="Значок видео"]', 'img[alt*="video" i]',
            'img[alt="Video icon"]', 'img[alt="Generated video"]',
            'img[alt="Сгенерированное видео"]',
        ];
        const seen = new Set();
        for (const sel of selectors) {
            for (const el of document.querySelectorAll(sel)) seen.add(el);
        }
        return seen.size;
    }""")

    if thumb_count == 0:
        print('    No video thumbnails found for individual download')
        return []

    print(f'    Found {thumb_count} video thumbnails, downloading individually...')
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    for idx in range(min(thumb_count, expected_count)):
        # Click thumbnail by index (re-query each time since DOM may change)
        clicked = page.evaluate("""(idx) => {
            const selectors = [
                'img[alt="Значок видео"]', 'img[alt*="video" i]',
                'img[alt="Video icon"]', 'img[alt="Generated video"]',
                'img[alt="Сгенерированное видео"]',
            ];
            const all = [];
            const seen = new Set();
            for (const sel of selectors) {
                for (const el of document.querySelectorAll(sel)) {
                    if (!seen.has(el)) { seen.add(el); all.push(el); }
                }
            }
            if (idx >= all.length) return false;
            const r = all[idx].getBoundingClientRect();
            if (r.width < 20) return false;
            all[idx].click();
            return true;
        }""", idx)

        if not clicked:
            continue

        time.sleep(3)

        # Collect video URL from full view
        url = None
        for _wait in range(8):
            url = page.evaluate("""() => {
                for (const v of document.querySelectorAll('video')) {
                    const src = v.src || v.currentSrc || '';
                    if (src) return src;
                    for (const s of v.querySelectorAll('source')) {
                        if (s.src) return s.src;
                    }
                }
                return null;
            }""")
            if url:
                break
            time.sleep(1)

        if url:
            dest_path = dest_dir / f'variant_{idx+1}.mp4'
            if download_via_fetch(page, url, dest_path):
                saved.append(dest_path)

        _close_fullview(page)
        human_delay(1, 2)

    return saved


def _scan_dom_video_urls(page):
    """Scan DOM for all <video> src URLs as last resort fallback."""
    return page.evaluate("""() => {
        const urls = new Set();
        for (const v of document.querySelectorAll('video')) {
            if (v.src) urls.add(v.src);
            if (v.currentSrc) urls.add(v.currentSrc);
            for (const s of v.querySelectorAll('source')) {
                if (s.src) urls.add(s.src);
            }
        }
        return [...urls];
    }""")


def download_all_videos(page, dest_dir, expected_count=4):
    """Download all generated videos using 3-level strategy:
    1. Full view + arrow navigation
    2. Click each thumbnail individually
    3. Direct DOM scan for <video> elements
    Returns list of saved file paths.
    """
    _scroll_chat_bottom(page)
    human_delay(1, 2)

    # Strategy 1: Full view + navigation
    print('    Strategy 1: Full view + arrow navigation')
    urls = _open_video_fullview(page)
    all_urls = []
    if urls:
        if len(urls) < expected_count:
            all_urls = _navigate_fullview_and_collect_urls(page, expected_count)
        else:
            all_urls = urls
        _close_fullview(page)

        if all_urls:
            dest_dir.mkdir(parents=True, exist_ok=True)
            saved = []
            for i, url in enumerate(all_urls):
                dest_path = dest_dir / f'variant_{i+1}.mp4'
                if download_via_fetch(page, url, dest_path):
                    saved.append(dest_path)
            if saved:
                print(f'  Strategy 1: Downloaded {len(saved)}/{len(all_urls)} videos')
                return saved
    else:
        _close_fullview(page)

    # Strategy 2: Click each thumbnail individually
    print('    Strategy 2: Click thumbnails individually')
    saved = _download_videos_individually(page, dest_dir, expected_count)
    if saved:
        print(f'  Strategy 2: Downloaded {len(saved)} videos')
        return saved

    # Strategy 3: Direct DOM scan for <video> elements
    print('    Strategy 3: Direct DOM scan for <video> elements')
    dom_urls = _scan_dom_video_urls(page)
    if dom_urls:
        dest_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for i, url in enumerate(dom_urls[:expected_count]):
            dest_path = dest_dir / f'variant_{i+1}.mp4'
            if download_via_fetch(page, url, dest_path):
                saved.append(dest_path)
        if saved:
            print(f'  Strategy 3: Downloaded {len(saved)}/{len(dom_urls)} videos')
            return saved

    print('    All download strategies failed — no videos downloaded')
    return []


# ── Manifest (review state) ─────────────────────────────────────────────────

def _r2_key(local_path):
    """Convert local path to R2 key relative to PROJECT_ROOT."""
    try:
        return str(Path(local_path).relative_to(PROJECT_ROOT))
    except ValueError:
        return str(local_path)


def _r2_sync_upload(local_path):
    """Upload a local file to R2 (non-blocking, best-effort)."""
    if r2_storage.is_configured():
        r2_storage.upload_file(local_path, _r2_key(local_path))


def load_manifest(clip_id):
    default = {
        'clip_id': clip_id,
        'components': {
            c: {'attempts':[], 'selected_variant_a':None, 'selected_variant_b':None, 'status':'pending'}
            for c in ('nb_first','nb_mid','nb_last','veo')
        }
    }
    # Try local first (dashboard may update locally), then R2 fallback
    m = None
    path = REVIEW_DIR / clip_id / 'manifest.json'
    if path.exists():
        with open(path) as f:
            m = json.load(f)
    if m is None and r2_storage.is_configured():
        r2_key = _r2_key(REVIEW_DIR / clip_id / 'manifest.json')
        m = r2_storage.read_json(r2_key)
    if m is None:
        return default
    for c in ('nb_first','nb_mid','nb_last','veo'):
        comp = m['components'].get(c, {})
        # Migration: selected_variant → selected_variant_a
        if 'selected_variant' in comp and comp['selected_variant'] is not None:
            if not comp.get('selected_variant_a'):
                comp['selected_variant_a'] = comp['selected_variant']
            del comp['selected_variant']
        comp.setdefault('selected_variant_a', None)
        comp.setdefault('selected_variant_b', None)
        m['components'][c] = comp
    if 'nb_mid' not in m['components']:
        m['components']['nb_mid'] = {'attempts':[], 'selected_variant_a':None, 'selected_variant_b':None, 'status':'pending'}
    return m


def save_manifest(clip_id, manifest):
    path = REVIEW_DIR / clip_id / 'manifest.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    # Sync to R2
    if r2_storage.is_configured():
        r2_storage.write_json(_r2_key(path), manifest)


def get_next_attempt(manifest, component):
    n = len(manifest['components'].get(component, {}).get('attempts', []))
    return n + 1 if n < MAX_ATTEMPTS else 0


def record_attempt(manifest, component, attempt, prompt, paths, prompt_b=None, batch_a_count=None, batch_b_count=None):
    comp = manifest['components'][component]
    entry = {
        'attempt': attempt, 'prompt': prompt,
        'variants': [{'file': str(p.relative_to(p.parent.parent)) if 'prompt_' in str(p.parent.name) else p.name,
                       'scores': None, 'avg': None} for p in paths],
        'best_variant': None, 'best_avg': None,
    }
    if prompt_b: entry['prompt_b'] = prompt_b
    if batch_a_count is not None: entry['batch_a_count'] = batch_a_count
    if batch_b_count is not None: entry['batch_b_count'] = batch_b_count
    comp['attempts'].append(entry)


def mark_selected(manifest, component, attempt, variant_idx, scores, avg, batch='a'):
    comp = manifest['components'][component]
    entry = comp['attempts'][attempt - 1]
    entry['variants'][variant_idx]['scores'] = scores
    entry['variants'][variant_idx]['avg'] = avg
    entry['best_variant'] = variant_idx
    entry['best_avg'] = avg
    comp[f'selected_variant_{batch}'] = {'attempt': attempt, 'variant': variant_idx}
    if comp.get('selected_variant_a') is not None:
        comp['status'] = 'accepted'


def mark_failed(manifest, component, attempt, scores_per_variant=None):
    comp = manifest['components'][component]
    if scores_per_variant:
        entry = comp['attempts'][attempt - 1]
        for i, sc in enumerate(scores_per_variant):
            if i < len(entry['variants']):
                entry['variants'][i]['scores'] = sc
                if sc:
                    nz = [v for v in sc.values() if v > 0]
                    entry['variants'][i]['avg'] = sum(nz)/len(nz) if nz else 0
    if len(comp['attempts']) >= MAX_ATTEMPTS:
        comp['status'] = 'needs_manual_work'


def copy_selected_to_output(clip_id, manifest, trim_start=None, trim_end=None):
    suffixes = {'nb_first':'first', 'nb_mid':'mid', 'nb_last':'last'}
    for comp_name in ('nb_first','nb_mid','nb_last','veo'):
        comp = manifest['components'][comp_name]
        if comp_name in suffixes:
            suffix = suffixes[comp_name]
            for slot, ext in [('selected_variant_a', '')]:
                sel = comp.get(slot)
                if not sel: continue
                entry = comp['attempts'][sel['attempt']-1]
                vfile = entry['variants'][sel['variant']]['file']
                src = REVIEW_DIR / clip_id / comp_name / f'attempt_{sel["attempt"]}' / vfile
                if src.exists():
                    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
                    dest = FRAMES_DIR / f'{clip_id}_{suffix}{ext}.png'
                    shutil.copy2(src, dest)
                    _r2_sync_upload(dest)
                    print(f'  Copied -> {dest.name}')
        elif comp_name == 'veo':
            sel = comp.get('selected_variant_a')
            if not sel: continue
            entry = comp['attempts'][sel['attempt']-1]
            vfile = entry['variants'][sel['variant']]['file']
            src = REVIEW_DIR / clip_id / 'veo' / f'attempt_{sel["attempt"]}' / vfile
            if src.exists():
                CLIPS_DIR.mkdir(parents=True, exist_ok=True)
                dest = CLIPS_DIR / f'{clip_id}_clip.mp4'
                if trim_start is not None and trim_end is not None:
                    subprocess.run(['ffmpeg','-y','-i',str(src),'-ss',str(trim_start),
                                    '-t',str(trim_end-trim_start),'-c','copy',str(dest)],
                                   capture_output=True)
                else:
                    shutil.copy2(src, dest)
                _r2_sync_upload(dest)
                print(f'  Copied -> {dest.name}')


def mark_selected_simple(manifest, component, attempt, variant_idx):
    """Mark variant as selected (user-driven, no score validation)."""
    comp = manifest['components'][component]
    comp['selected_variant_a'] = {'attempt': attempt, 'variant': variant_idx}
    comp['status'] = 'accepted'


def _all_done(manifest):
    for c in ('nb_first','nb_mid','nb_last','veo'):
        comp = manifest['components'].get(c, {})
        st = comp.get('status', 'pending')
        if c == 'nb_mid' and st == 'pending' and len(comp.get('attempts',[])) == 0:
            continue
        if st not in ('accepted', 'needs_manual_work'):
            return False
    return True


# ── Generation core ──────────────────────────────────────────────────────────

# Track downloaded URLs within a batch to detect duplicates
_downloaded_urls = set()


def generate_nb_batch(page, clip_id, component, prompt, attempt, ingredients, dest_dir, num_variants=4):
    """Generate NB variants using x4 mode (single generation produces num_variants images).

    NB API: flowMedia:batchGenerateImages returns media[].name (UUID) and fifeUrl (storage URL).
    With x4 selected, one Generate click produces 4 images in a single API response.
    """
    validate_nb_prompt(prompt, f'{clip_id}/{component}')
    prompt = sanitize_nb_prompt(prompt)
    print(f'\n  --- {component} for {clip_id} (attempt {attempt}) ---')
    print(f'  Prompt: {prompt[:80]}...')
    print(f'  Generating {num_variants} variants (x{num_variants} single run)...')

    dest_dir.mkdir(parents=True, exist_ok=True)
    all_saved = []

    # Set x4 in settings popup
    set_variant_count(page, num_variants)

    # Set up network capture
    capture = NbNetworkCapture()
    capture.start(page)

    clear_prompt(page)
    fill_prompt(page, prompt)
    take_screenshot(page, f'{clip_id}_{component}_a{attempt}_before')

    # Scroll to bottom so existing errors are visible and counted
    _scroll_chat_bottom(page)
    time.sleep(1)
    errors_before = _count_errors(page)
    click_generate(page)
    result = poll_generation(page, errors_before=errors_before)

    # On server_error: try clicking "Повторить" button once
    if result == 'server_error':
        print(f'    FAILED ({result}) — trying retry button...')
        time.sleep(2)
        if _click_retry_on_error(page):
            time.sleep(3)
            errors_before = _count_errors(page)
            result = poll_generation(page, errors_before=errors_before)
            if result != 'success':
                print(f'    Retry also failed ({result})')
        else:
            print(f'    Retry button not found')

    # Rate limit on NB Pro → fallback to Nano Banana 2, retry
    if result == 'rate_limit':
        print(f'    Rate limit on NB Pro — switching to Nano Banana 2...')
        time.sleep(2)
        set_image_model(page, 'Nano Banana 2')
        human_delay(1, 2)
        capture.stop(page)
        capture = NbNetworkCapture()
        capture.start(page)
        clear_prompt(page)
        fill_prompt(page, prompt_full)
        _scroll_chat_bottom(page)
        time.sleep(1)
        errors_before = _count_errors(page)
        click_generate(page)
        result = poll_generation(page, errors_before=errors_before)

    if result != 'success':
        # Back off after failed generation to avoid throttling
        human_pause_after_error()

    if result == 'success':
        # Wait for API response to be fully captured
        time.sleep(3)

        # Download all captured images
        if capture.images:
            print(f'    Network captured {len(capture.images)} images')
            for idx, img in enumerate(capture.images):
                media_id = img['id']
                fife_url = img['url']
                dest_path = dest_dir / f'variant_{idx+1}.png'
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                print(f'    Network: media {media_id[:8]}...')
                saved = False
                if fife_url and download_via_fetch(page, fife_url, dest_path):
                    all_saved.append(dest_path)
                    print(f'  Saved: variant_{idx+1}.png ({dest_path.stat().st_size} bytes, type=image/jpeg)')
                    print(f'    Saved variant_{idx+1}.png (network)')
                    saved = True

                if not saved:
                    # Fallback: use media.getMediaUrlRedirect API
                    redirect_url = f'/fx/api/trpc/media.getMediaUrlRedirect?name={media_id}'
                    if download_via_fetch(page, redirect_url, dest_path):
                        all_saved.append(dest_path)
                        print(f'    Saved variant_{idx+1}.png (redirect)')
                        saved = True

                if not saved:
                    print(f'    Failed to download variant_{idx+1}')
        else:
            print(f'    No network capture — trying DOM fallback...')
            _scroll_chat_bottom(page)
            time.sleep(2)
            new_url = _get_last_generated_image_url(page)
            if new_url:
                dest_path = dest_dir / 'variant_1.png'
                if download_via_fetch(page, new_url, dest_path, min_size=200000):
                    all_saved.append(dest_path)
                    print(f'    Saved variant_1.png (DOM fallback)')

    elif result == 'content_filter':
        print('    Content filter — generation blocked')
    else:
        print(f'    FAILED ({result})')

    capture.stop(page)
    print(f'  Downloaded {len(all_saved)}/{num_variants} variants')
    return all_saved


# ── Review mode ──────────────────────────────────────────────────────────────

def review_nano_banana(page, clip, manifest, component, attempt, prompt_override=None, first_frame_ref=None):
    clip_id = clip['clip_id']
    prompt_key = {'nb_first':'nano_banana_prompt_first', 'nb_mid':'nano_banana_prompt_mid',
                  'nb_last':'nano_banana_prompt_last'}[component]
    prompt_a = prompt_override or clip[prompt_key]
    ingredients = list(clip.get('nano_banana_ingredients', []))

    print(f'\n{"="*60}')
    print(f'  REVIEW — {component} — {clip_id} — attempt {attempt}')
    print(f'{"="*60}')

    # Ensure we're in chat view (not /edit/ or gallery overlay)
    _ensure_chat_view(page)
    dismiss_popups(page)
    switch_mode(page, 'Создать изображение')
    set_image_model(page, clip.get('nano_banana_model_name', 'Nano Banana Pro'))
    set_orientation(page, clip.get('orientation', 'horizontal'))

    ref_suffix = ''
    if first_frame_ref and first_frame_ref.exists():
        ref_num = len(ingredients) + 1
        ingredients.append(str(first_frame_ref))
        if component == 'nb_first':
            ref_suffix = f' Use Image {ref_num} as reference for the exact room layout, furniture placement, and all visible objects.'
        else:
            ref_suffix = (f' Use Image {ref_num} ONLY as reference for visual style, lighting, and background.'
                          f' The character poses, positions, and actions MUST be clearly different from Image {ref_num}'
                          f' — show the END state of the motion, not the beginning.')

    prompt_full = prompt_a + ref_suffix

    uploaded = upload_ingredients(page, ingredients)
    if uploaded == 0 and any('персонаж' in str(p).lower() for p in ingredients):
        print('  FAILED: no character refs uploaded')
        return []

    attempt_dir = REVIEW_DIR / clip_id / component / f'attempt_{attempt}'
    variants = generate_nb_batch(page, clip_id, component, prompt_full, attempt, ingredients, attempt_dir)

    record_attempt(manifest, component, attempt, prompt_full, variants)
    save_manifest(clip_id, manifest)
    return variants


def _collect_edit_uuids(page):
    """Collect all edit-link UUIDs currently visible in the chat DOM."""
    return set(page.evaluate("""() => {
        return Array.from(document.querySelectorAll('a[href*="/edit/"]'))
            .map(a => {
                const m = a.href.match(/\\/edit\\/([a-f0-9-]+)/);
                return m ? m[1] : null;
            })
            .filter(Boolean);
    }"""))


# ── VEO Network Interception Download ────────────────────────────────────────

class NbNetworkCapture:
    """Captures NB (Nano Banana) API responses to extract generated image media IDs and URLs.

    Flow API endpoint:
    - flowMedia:batchGenerateImages: returns media[].name (UUID) and fifeUrl (direct storage URL)
    - May fail with 403 reCAPTCHA and auto-retry (3-4 attempts)

    Usage:
        capture = NbNetworkCapture()
        capture.start(page)
        # ... generate image ...
        capture.stop(page)
        media_id, fife_url = capture.get_last_image()
    """

    def __init__(self):
        self.images = []  # list of {id, url} dicts
        self._listener = None

    def start(self, page):
        """Start capturing network responses."""
        self.images = []

        def on_response(response):
            url = response.url
            try:
                if 'batchGenerateImages' in url and response.status == 200:
                    body = response.text()
                    data = json.loads(body)
                    for media in data.get('media', []):
                        mid = media.get('name', '')
                        fife_url = media.get('image', {}).get('generatedImage', {}).get('fifeUrl', '')
                        if mid:
                            self.images.append({'id': mid, 'url': fife_url})
            except Exception:
                pass

        self._listener = on_response
        page.on('response', on_response)

    def stop(self, page):
        """Stop capturing."""
        if self._listener:
            page.remove_listener('response', self._listener)
            self._listener = None

    def get_last_image(self):
        """Return (media_id, fife_url) of the last generated image, or (None, None)."""
        if self.images:
            last = self.images[-1]
            return last['id'], last['url']
        return None, None

    def clear(self):
        """Clear captured images (between variants)."""
        self.images = []


class VeoNetworkCapture:
    """Captures VEO API responses to extract generated video media IDs.

    Flow uses these API endpoints:
    - batchAsyncGenerateVideoStartAndEndImage: returns media IDs at generation start
    - batchCheckAsyncVideoGenerationStatus: polling with PENDING→SUCCESSFUL status
    - media.getMediaUrlRedirect?name={UUID}: 307 redirect to actual video storage URL

    By intercepting these responses, we get video UUIDs directly from the API,
    completely bypassing the unreliable DOM/virtual-scrolling approach.
    """

    def __init__(self):
        self.media_ids = []       # UUIDs of generated videos
        self.status_history = []  # status transitions
        self._listener = None

    def start(self, page):
        """Start capturing network responses."""
        self.media_ids = []
        self.status_history = []

        def on_response(response):
            url = response.url
            try:
                if 'batchAsyncGenerateVideo' in url and response.status == 200:
                    body = response.text()
                    data = json.loads(body)
                    # Extract media IDs from generation start response
                    for media in data.get('media', []):
                        mid = media.get('name', '')
                        if mid and mid not in self.media_ids:
                            self.media_ids.append(mid)
                    # Also check workflows for media IDs
                    for wf in data.get('workflows', []):
                        meta = wf.get('metadata', {})
                        mid = meta.get('primaryMediaId', '')
                        if mid and mid not in self.media_ids:
                            self.media_ids.append(mid)

                elif 'batchCheckAsyncVideoGenerationStatus' in url and response.status == 200:
                    body = response.text()
                    data = json.loads(body)
                    for media in data.get('media', []):
                        mid = media.get('name', '')
                        status = media.get('mediaMetadata', {}).get('mediaStatus', {}).get('mediaGenerationStatus', '')
                        if mid and mid not in self.media_ids:
                            self.media_ids.append(mid)
                        if mid and status:
                            self.status_history.append((mid[:8], status.split('_')[-1]))
            except Exception:
                pass  # Don't crash on parse errors

        self._listener = on_response
        page.on('response', on_response)

    def stop(self, page):
        """Stop capturing."""
        if self._listener:
            page.remove_listener('response', self._listener)
            self._listener = None

    def get_successful_ids(self):
        """Return media IDs that reached SUCCESSFUL status."""
        successful = set()
        for mid_short, status in self.status_history:
            if status == 'SUCCESSFUL':
                # Find full ID matching this short prefix
                for full_id in self.media_ids:
                    if full_id.startswith(mid_short):
                        successful.add(full_id)
        # If no status tracking but we have IDs, return all (generation may have completed)
        if not successful and self.media_ids:
            return list(self.media_ids)
        return list(successful)


def _download_video_by_media_id(page, media_id, dest_path):
    """Download a video using Flow's media.getMediaUrlRedirect API.

    This API returns a 307 redirect to the actual video storage URL.
    We fetch the video URL first, then download the video data.
    """
    # Build the redirect URL (no mediaUrlType = full video, not thumbnail)
    redirect_url = f'/fx/api/trpc/media.getMediaUrlRedirect?name={media_id}'

    # Use fetch to follow the redirect and get the final video URL, then download
    result = page.evaluate("""async (redirectUrl) => {
        try {
            // First, get the redirect URL
            const resp = await fetch(redirectUrl, {redirect: 'follow'});
            if (!resp.ok) return {error: 'HTTP ' + resp.status};
            const contentType = resp.headers.get('content-type') || '';
            // If we got the video directly (redirect was followed)
            if (contentType.includes('video') || contentType.includes('octet-stream')) {
                const blob = await resp.blob();
                return {
                    type: blob.type, size: blob.size,
                    data: await new Promise(r => {
                        const reader = new FileReader();
                        reader.onload = () => r(reader.result.split(',')[1]);
                        reader.readAsDataURL(blob);
                    })
                };
            }
            // If content-type is not video, the URL itself might be the video URL
            // Try to get the final URL from the response
            const finalUrl = resp.url;
            if (finalUrl.includes('storage.googleapis.com')) {
                const vidResp = await fetch(finalUrl);
                if (!vidResp.ok) return {error: 'Video fetch HTTP ' + vidResp.status};
                const blob = await vidResp.blob();
                return {
                    type: blob.type, size: blob.size,
                    data: await new Promise(r => {
                        const reader = new FileReader();
                        reader.onload = () => r(reader.result.split(',')[1]);
                        reader.readAsDataURL(blob);
                    })
                };
            }
            return {error: 'Unexpected content type: ' + contentType, url: finalUrl};
        } catch(e) { return {error: e.message}; }
    }""", redirect_url)

    if 'error' in result:
        # Fallback: try with absolute URL
        abs_url = f'https://labs.google{redirect_url}'
        result = page.evaluate("""async (url) => {
            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 120000);
                const resp = await fetch(url, {signal: controller.signal, redirect: 'follow'});
                clearTimeout(timeout);
                if (!resp.ok) return {error: 'HTTP ' + resp.status};
                const blob = await resp.blob();
                return {
                    type: blob.type, size: blob.size,
                    data: await new Promise(r => {
                        const reader = new FileReader();
                        reader.onload = () => r(reader.result.split(',')[1]);
                        reader.readAsDataURL(blob);
                    })
                };
            } catch(e) { return {error: e.message}; }
        }""", abs_url)

    if 'error' in result:
        print(f'    Download failed for {media_id[:8]}: {result["error"]}')
        return False

    data = base64.b64decode(result['data'])
    if len(data) < 1024:
        print(f'    File too small ({len(data)} bytes) for {media_id[:8]}')
        return False

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(data)
    md5 = hashlib.md5(data).hexdigest()[:8]
    print(f'  Saved: {dest_path.name} ({len(data)} bytes, md5={md5}, type={result.get("type","")})')
    _r2_sync_upload(dest_path)
    return True


def _download_veo_videos(page, dest_dir, num_expected, captured_media_ids, project_url):
    """Download VEO videos using media IDs captured from network interception.

    Primary strategy: use media.getMediaUrlRedirect API with captured UUIDs.
    Fallback: navigate to /edit/{UUID} and extract <video> src.

    Args:
        captured_media_ids: list of video UUIDs from VeoNetworkCapture
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    seen_md5 = set()

    print(f'    Captured {len(captured_media_ids)} media IDs from API')

    # --- If on /edit/ page after generation, download current video first ---
    if '/edit/' in page.url:
        m = re.search(r'/edit/([a-f0-9-]+)', page.url)
        if m:
            current_uuid = m.group(1)
            print(f'    On /edit/{current_uuid[:8]}... downloading current video')
            dest_path = dest_dir / f'variant_{len(saved)+1}.mp4'
            if _download_video_by_media_id(page, current_uuid, dest_path):
                md5 = hashlib.md5(dest_path.read_bytes()).hexdigest()[:8]
                seen_md5.add(md5)
                saved.append(dest_path)
                # Remove from captured list to avoid re-downloading
                if current_uuid in captured_media_ids:
                    captured_media_ids.remove(current_uuid)

        # Return to project chat
        page.go_back(wait_until='domcontentloaded')
        time.sleep(3)
        if '/edit/' in page.url:
            page.goto(project_url, wait_until='domcontentloaded')
            time.sleep(3)

    # --- Primary strategy: download via API using captured media IDs ---
    for mid in captured_media_ids:
        if len(saved) >= num_expected:
            break
        print(f'    [{len(saved)+1}/{num_expected}] Downloading media {mid[:8]}...')
        dest_path = dest_dir / f'variant_{len(saved)+1}.mp4'
        if _download_video_by_media_id(page, mid, dest_path):
            md5 = hashlib.md5(dest_path.read_bytes()).hexdigest()[:8]
            if md5 not in seen_md5:
                seen_md5.add(md5)
                saved.append(dest_path)
            else:
                print(f'    DUPLICATE md5={md5}, removing')
                dest_path.unlink()
        else:
            # Fallback: try navigating to /edit/{UUID} page via SPA
            print(f'    Trying SPA navigation to /edit/{mid[:8]}...')
            navigated = page.evaluate("""(uuid) => {
                const a = document.querySelector('a[href*="/edit/' + uuid + '"]');
                if (a) { a.click(); return true; }
                return false;
            }""", mid)

            if not navigated:
                # Create a temporary <a> and click it for SPA navigation
                navigated = page.evaluate("""(uuid) => {
                    const a = document.createElement('a');
                    a.href = '/fx/ru/tools/flow/project/' + document.location.pathname.split('/project/')[1].split('/')[0] + '/edit/' + uuid;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    return true;
                }""", mid)

            if navigated:
                time.sleep(5)
                # Wait for <video> to appear
                video_url = None
                for _wait in range(15):
                    video_url = page.evaluate("""() => {
                        for (const v of document.querySelectorAll('video')) {
                            const src = v.src || v.currentSrc || '';
                            if (src) return src;
                            for (const s of v.querySelectorAll('source')) {
                                if (s.src) return s.src;
                            }
                        }
                        return null;
                    }""")
                    if video_url:
                        break
                    time.sleep(1)

                if video_url:
                    dest_path2 = dest_dir / f'variant_{len(saved)+1}.mp4'
                    if download_via_fetch(page, video_url, dest_path2):
                        md5 = hashlib.md5(dest_path2.read_bytes()).hexdigest()[:8]
                        if md5 not in seen_md5:
                            seen_md5.add(md5)
                            saved.append(dest_path2)
                            print(f'    {dest_path2.name}: {dest_path2.stat().st_size} bytes (md5={md5})')
                        else:
                            print(f'    DUPLICATE md5={md5}')
                            dest_path2.unlink()

                # Return to chat
                if '/edit/' in page.url:
                    page.go_back(wait_until='domcontentloaded')
                    time.sleep(3)

    # Ensure we're back in chat for next operations
    if '/edit/' in page.url:
        page.goto(project_url, wait_until='domcontentloaded')
        time.sleep(3)

    print(f'  Downloaded {len(saved)}/{num_expected} videos total')
    return saved


def _veo_setup_and_generate(page, prompt, first_frame, last_frame, num_variants, batch_label):
    """Setup VEO mode, upload frames, fill prompt, click Generate.
    Returns (project_url, capture, errors_before) tuple.
    """
    switch_mode(page, 'Видео по кадрам')
    human_delay_long(2, 4)
    set_variant_count(page, num_variants)

    # Upload first/last frames to VEO slots
    if first_frame and Path(first_frame).exists() and last_frame and Path(last_frame).exists():
        clear_veo_frame_slots(page)
        upload_frame_for_veo(page, first_frame, 0)
        upload_frame_for_veo(page, last_frame, 1)
    elif first_frame and Path(first_frame).exists():
        clear_veo_frame_slots(page)
        upload_frame_for_veo(page, first_frame, 0)

    take_screenshot(page, f'veo_{batch_label}_frames_loaded')

    if not _check_frame_slots_have_images(page):
        print(f'  WARNING: Frame slots do not have images!')
        take_screenshot(page, f'veo_{batch_label}_no_frames_warning')

    project_url = page.url.split('/edit/')[0].split('?')[0]

    # Start network capture BEFORE generation
    capture = VeoNetworkCapture()
    capture.start(page)

    clear_prompt(page)
    fill_prompt(page, prompt)
    take_screenshot(page, f'veo_{batch_label}_before_generate')
    errors_before = _count_errors(page)
    click_generate(page)

    return project_url, capture, errors_before


def review_veo_batch(page, clip, clip_id, prompt, first_frame, last_frame, attempt, batch_label, dest_dir, veo_mode='frames', num_variants=4):
    """Generate VEO videos with x4 (single generation produces num_variants videos).

    Uses network interception to capture video media IDs from Flow API responses,
    then downloads directly via media.getMediaUrlRedirect API.
    Retries on server_error up to 3 times with increasing pauses (45s, 60s, 90s).
    """
    print(f'\n  --- VEO {batch_label} for {clip_id} (x{num_variants}) ---')
    validate_veo_prompt(prompt, f'{clip_id}/veo_{batch_label}')

    project_url, capture, errors_before = _veo_setup_and_generate(
        page, prompt, first_frame, last_frame, num_variants, batch_label)

    result = poll_generation(page, errors_before=errors_before,
                             timeout_sec=GENERATION_TIMEOUT, media='video')

    # On server_error: try clicking "Повторить" button once
    if result == 'server_error':
        print(f'  VEO {batch_label} server error — trying retry button...')
        time.sleep(2)
        if _click_retry_on_error(page):
            time.sleep(3)
            errors_before = _count_errors(page)
            result = poll_generation(page, errors_before=errors_before,
                                     timeout_sec=GENERATION_TIMEOUT, media='video')
            if result != 'success':
                print(f'  VEO {batch_label} retry also failed ({result})')
        else:
            print(f'  VEO {batch_label} retry button not found')

    if result != 'success':
        # Back off after failed generation to avoid throttling
        human_pause_after_error()

    capture.stop(page)

    if result == 'content_filter':
        print(f'  VEO {batch_label} BLOCKED by content filter')
        return []

    if result != 'success':
        print(f'  VEO {batch_label} FAILED ({result})')
        return []

    # Wait for post-generation API calls (thumbnails, etc.)
    time.sleep(5)
    take_screenshot(page, f'veo_{batch_label}_after_generate')
    print(f'    URL after generation: {page.url[:80]}')

    media_ids = capture.get_successful_ids()
    print(f'    Network capture: {len(media_ids)} media IDs, {len(capture.status_history)} status updates')
    for mid in media_ids:
        print(f'      - {mid[:8]}...')

    all_saved = _download_veo_videos(page, dest_dir, num_variants, media_ids, project_url)
    print(f'  Downloaded {len(all_saved)}/{num_variants} variants for {batch_label}')
    return all_saved


def review_veo(page, clip, manifest, attempt, first_frame, last_frame, prompt_override=None,
               veo_mode='frames'):
    clip_id = clip['clip_id']
    prompt = sanitize_prompt(prompt_override or clip['veo_prompt'])
    dest_dir = REVIEW_DIR / clip_id / 'veo' / f'attempt_{attempt}'

    saved = review_veo_batch(page, clip, clip_id, prompt, first_frame, last_frame,
                             attempt, 'variants', dest_dir, veo_mode)

    record_attempt(manifest, 'veo', attempt, prompt, saved)
    save_manifest(clip_id, manifest)
    print(f'  VEO TOTAL: {len(saved)} videos')

    # Return to project chat view after VEO (download may leave us on /edit/ page)
    _ensure_chat_view(page)

    return saved


# ── CLI Commands ─────────────────────────────────────────────────────────────

def _prompts_path():
    """Return the best available prompts path (fallback if iCloud blocks main file)."""
    import signal
    def _timeout_handler(signum, frame):
        raise TimeoutError("File read timed out")
    old = signal.signal(signal.SIGALRM, _timeout_handler)
    try:
        signal.alarm(5)
        with open(PROMPTS_PATH) as f:
            f.read(100)
        signal.alarm(0)
        return PROMPTS_PATH
    except (TimeoutError, OSError):
        signal.alarm(0)
        if PROMPTS_PATH_LOCAL.exists():
            print(f'  Using local prompts fallback: {PROMPTS_PATH_LOCAL.name}')
            return PROMPTS_PATH_LOCAL
        return PROMPTS_PATH
    finally:
        signal.signal(signal.SIGALRM, old)


def load_clips(clip_filter=None):
    with open(_prompts_path()) as f:
        clips = json.load(f)
    if clip_filter:
        # Support comma-separated list: "S02_B,S02_C,S02_D"
        filter_ids = [s.strip() for s in clip_filter.split(',')]
        clips = [c for c in clips if c['clip_id'] in filter_ids]
        if not clips:
            print(f'Error: clip(s) "{clip_filter}" not found')
            sys.exit(1)
    return clips


def find_scene_ref(current_clip_id):
    """Find accepted last frame from the immediately preceding clip in same scene.

    This creates a continuity chain: S01_A_last → S01_B_first → S01_B_last → S01_C_first ...
    """
    with open(_prompts_path()) as f:
        all_clips = json.load(f)
    scene = next((c['scene_id'] for c in all_clips if c['clip_id'] == current_clip_id), None)
    if not scene: return None
    prev_clip_id = None
    for c in all_clips:
        if c['scene_id'] != scene: continue
        if c['clip_id'] == current_clip_id: break
        prev_clip_id = c['clip_id']
    if not prev_clip_id: return None
    frame = FRAMES_DIR / f'{prev_clip_id}_last.png'
    if frame.exists(): return frame
    # Try downloading from R2 (dashboard may have accepted it)
    if r2_storage.is_configured():
        r2_key = _r2_key(frame)
        if r2_storage.download_file(r2_key, frame):
            print(f'    Downloaded ref from R2: {frame.name}')
            return frame
    return None


def _resolve_ref_frame(manifest, clip_id, component):
    """Resolve reference frame for nb_mid/nb_last from selected previous frames."""
    if component == 'nb_first':
        return find_scene_ref(clip_id)

    # nb_last prefers mid, falls back to first
    if component == 'nb_last':
        mid_sel = manifest['components']['nb_mid'].get('selected_variant_a')
        if mid_sel:
            entry = manifest['components']['nb_mid']['attempts'][mid_sel['attempt']-1]
            ref = REVIEW_DIR / clip_id / 'nb_mid' / f'attempt_{mid_sel["attempt"]}' / entry['variants'][mid_sel['variant']]['file']
            if ref.exists(): return ref

    # nb_mid and nb_last fallback: use first frame
    first_sel = manifest['components']['nb_first'].get('selected_variant_a')
    if first_sel:
        entry = manifest['components']['nb_first']['attempts'][first_sel['attempt']-1]
        ref = REVIEW_DIR / clip_id / 'nb_first' / f'attempt_{first_sel["attempt"]}' / entry['variants'][first_sel['variant']]['file']
        if ref.exists(): return ref
    return None


def do_review(pw, clip_filter=None, component_filter=None, project_id=None, use_builtin_chromium=False):
    clips = load_clips(clip_filter)
    print(f'Review mode: {len(clips)} clips.')
    if component_filter:
        print(f'  Component filter: {component_filter}')
    print()

    ctx = launch_browser(pw, use_builtin_chromium=use_builtin_chromium)
    print('  Launched browser.')
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # Console log capture for debugging
    def _on_console(msg):
        if msg.type in ('error', 'warning'):
            text = msg.text[:300]
            print(f'  [CONSOLE {msg.type.upper()}] {text}')
    page.on('console', _on_console)

    print(f'  Page ready, navigating to project...')
    ensure_project(page, project_id=project_id)
    wait_for_flow_ready(page)

    summary = {'generated': [], 'skipped': [], 'failed': []}

    for i, clip in enumerate(clips):
        clip_id = clip['clip_id']
        print(f'\n[{i+1}/{len(clips)}] Review: {clip_id}')

        # Ensure we're in chat view before processing each clip
        _ensure_chat_view(page)

        manifest = load_manifest(clip_id)

        for component in ('nb_first', 'nb_mid', 'nb_last'):
            if component_filter and component != component_filter:
                continue
            if component == 'nb_mid' and not clip.get('nano_banana_prompt_mid'):
                continue
            if component == 'nb_last' and manifest.get('skip_last', False):
                summary['skipped'].append(f'{clip_id}/{component} (skip_last)')
                continue
            status = manifest['components'][component].get('status', 'pending')
            if status in ('accepted', 'needs_manual_work', 'skipped'):
                summary['skipped'].append(f'{clip_id}/{component}')
                continue
            attempt = get_next_attempt(manifest, component)
            if attempt == 0:
                manifest['components'][component]['status'] = 'needs_manual_work'
                save_manifest(clip_id, manifest)
                summary['failed'].append(f'{clip_id}/{component}')
                continue

            # Check dependency: nb_mid/nb_last need selected previous frame
            if component in ('nb_mid', 'nb_last'):
                ref = _resolve_ref_frame(manifest, clip_id, component)
                if not ref:
                    print(f'  {component}: waiting for previous frame — skipping')
                    summary['skipped'].append(f'{clip_id}/{component}')
                    continue
                first_frame_ref = ref
            else:
                first_frame_ref = _resolve_ref_frame(manifest, clip_id, component)

            variants = review_nano_banana(page, clip, manifest, component, attempt,
                                          first_frame_ref=first_frame_ref)
            if variants:
                summary['generated'].append(f'{clip_id}/{component}/a{attempt} ({len(variants)}v)')
            else:
                summary['failed'].append(f'{clip_id}/{component}/a{attempt}')

            if component in ('nb_first', 'nb_mid'):
                human_pause_between_generations()

        # VEO
        is_skip_last = manifest.get('skip_last', False)
        if component_filter and component_filter != 'veo':
            pass  # skip VEO when filtering for NB components
        elif (veo_status := manifest['components']['veo'].get('status', 'pending')) in ('accepted', 'needs_manual_work'):
            summary['skipped'].append(f'{clip_id}/veo')
        else:
            first_sel = manifest['components']['nb_first'].get('selected_variant_a')
            last_sel = manifest['components']['nb_last'].get('selected_variant_a')

            if is_skip_last and first_sel:
                # Only first frame needed — skip last
                fp = FRAMES_DIR / f'{clip_id}_first.png'
                if not fp.exists():
                    fe = manifest['components']['nb_first']['attempts'][first_sel['attempt']-1]
                    fp = REVIEW_DIR / clip_id / 'nb_first' / f'attempt_{first_sel["attempt"]}' / fe['variants'][first_sel['variant']]['file']
                if fp.exists():
                    attempt = get_next_attempt(manifest, 'veo')
                    if attempt > 0:
                        human_pause_between_generations()
                        variants = review_veo(page, clip, manifest, attempt, fp, None,
                                              veo_mode=clip.get('veo_mode','frames'))
                        if variants:
                            summary['generated'].append(f'{clip_id}/veo/a{attempt} ({len(variants)}v)')
                        else:
                            summary['failed'].append(f'{clip_id}/veo/a{attempt}')
                else:
                    summary['skipped'].append(f'{clip_id}/veo (waiting for first frame)')
            elif first_sel and last_sel:
                # Use uniquely-named files from output/frames/ (not generic variant_N.png from review/)
                fp = FRAMES_DIR / f'{clip_id}_first.png'
                lp = FRAMES_DIR / f'{clip_id}_last.png'
                if not fp.exists() or not lp.exists():
                    # Fallback to review dir paths
                    fe = manifest['components']['nb_first']['attempts'][first_sel['attempt']-1]
                    le = manifest['components']['nb_last']['attempts'][last_sel['attempt']-1]
                    fp = REVIEW_DIR / clip_id / 'nb_first' / f'attempt_{first_sel["attempt"]}' / fe['variants'][first_sel['variant']]['file']
                    lp = REVIEW_DIR / clip_id / 'nb_last' / f'attempt_{last_sel["attempt"]}' / le['variants'][last_sel['variant']]['file']
                if fp.exists() and lp.exists():
                    attempt = get_next_attempt(manifest, 'veo')
                    if attempt > 0:
                        human_pause_between_generations()
                        variants = review_veo(page, clip, manifest, attempt, fp, lp,
                                              veo_mode=clip.get('veo_mode','frames'))
                        if variants:
                            summary['generated'].append(f'{clip_id}/veo/a{attempt} ({len(variants)}v)')
                        else:
                            summary['failed'].append(f'{clip_id}/veo/a{attempt}')
            else:
                summary['skipped'].append(f'{clip_id}/veo (waiting for frames)')

        if i < len(clips) - 1:
            human_pause_between_generations()

    print(f'\n{"="*60}')
    print(f'  Generated: {len(summary["generated"])}')
    for g in summary['generated']: print(f'    {g}')
    print(f'  Skipped: {len(summary["skipped"])}')
    print(f'  Failed: {len(summary["failed"])}')
    for f in summary['failed']: print(f'    {f}')
    print(f'{"="*60}')
    ctx.close()

    # Auto-sync to dashboard after review
    if summary['generated']:
        try:
            do_sync_dashboard(clip_filter)
            print(f'  Dashboard synced.')
        except Exception as e:
            print(f'  Dashboard sync error: {e}')


def do_select(clip_id, component, attempt, variant, scores_json, trim_start=None, trim_end=None, batch='a'):
    scores = json.loads(scores_json)
    manifest = load_manifest(clip_id)
    comp = manifest['components'].get(component)
    if not comp or attempt > len(comp['attempts']):
        print('Error: invalid component/attempt'); sys.exit(1)
    entry = comp['attempts'][attempt-1]
    if variant >= len(entry['variants']):
        print(f'Error: variant {variant} not found'); sys.exit(1)

    non_zero = [v for v in scores.values() if v > 0]
    avg = sum(non_zero) / len(non_zero) if non_zero else 0
    print(f'  {clip_id}/{component} a{attempt} v{variant} batch={batch} avg={avg:.2f}')

    fails = [f'{c}={scores[c]}' for c in CRITICAL_CRITERIA if c in scores and scores[c] < CRITICAL_MIN_SCORE]
    if fails:
        print(f'  REJECTED — critical: {", ".join(fails)}')
        save_manifest(clip_id, manifest)
        return

    if avg >= QUALITY_THRESHOLD:
        mark_selected(manifest, component, attempt, variant, scores, avg, batch)
        if trim_start is not None: entry['variants'][variant]['trim_start'] = trim_start
        if trim_end is not None: entry['variants'][variant]['trim_end'] = trim_end
        save_manifest(clip_id, manifest)
        copy_selected_to_output(clip_id, manifest, trim_start, trim_end)
        print(f'  ACCEPTED (batch {batch.upper()})')
        # Auto-sync to dashboard
        try:
            do_sync_dashboard(clip_id)
            print(f'  Dashboard synced for {clip_id}')
        except Exception as e:
            print(f'  Dashboard sync error: {e}')
    else:
        save_manifest(clip_id, manifest)
        print(f'  BELOW THRESHOLD ({avg:.2f} < {QUALITY_THRESHOLD})')


def do_fail(clip_id, component, attempt, scores_json=None):
    manifest = load_manifest(clip_id)
    scores = json.loads(scores_json) if scores_json else None
    mark_failed(manifest, component, attempt, scores)
    save_manifest(clip_id, manifest)
    print(f'  {clip_id}/{component} attempt {attempt} marked failed')
    # Auto-sync to dashboard
    try:
        do_sync_dashboard(clip_id)
    except Exception:
        pass


def do_extract_frames(clip_id, component, attempt):
    manifest = load_manifest(clip_id)
    comp = manifest['components'].get(component)
    if not comp or attempt > len(comp['attempts']):
        print('Error: invalid component/attempt'); sys.exit(1)
    entry = comp['attempts'][attempt-1]
    attempt_dir = REVIEW_DIR / clip_id / component / f'attempt_{attempt}'
    for i, var in enumerate(entry['variants']):
        vpath = attempt_dir / var['file']
        if not vpath.exists(): continue
        frames_dir = attempt_dir / f'variant_{i+1}_frames'
        frames_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg','-y','-i',str(vpath),'-vf','fps=1',
                         str(frames_dir/'frame_%03d.png')], capture_output=True)
        dur_result = subprocess.run(['ffprobe','-v','quiet','-print_format','json',
                                     '-show_format',str(vpath)], capture_output=True, text=True)
        dur = 0
        if dur_result.returncode == 0:
            dur = float(json.loads(dur_result.stdout).get('format',{}).get('duration',0))
        var['duration'] = dur
        var['frames_dir'] = frames_dir.name
        print(f'  variant_{i+1}: {dur:.1f}s -> {frames_dir.name}')
    save_manifest(clip_id, manifest)


def do_status(clip_filter=None):
    clips = load_clips(clip_filter)
    print(f'\n{"="*90}')
    print(f'  {"CLIP":<10} {"NB_FIRST":<20} {"NB_MID":<20} {"NB_LAST":<20} {"VEO":<20}')
    print(f'  {"-"*10} {"-"*20} {"-"*20} {"-"*20} {"-"*20}')
    for clip in clips:
        cid = clip['clip_id']
        m = load_manifest(cid)
        cells = []
        for c in ('nb_first','nb_mid','nb_last','veo'):
            comp = m['components'].get(c, {})
            st = comp.get('status','pending')
            na = len(comp.get('attempts',[]))
            if c == 'nb_mid' and na == 0 and st == 'pending' and not clip.get('nano_banana_prompt_mid'):
                cells.append('—'); continue
            if st == 'accepted': cells.append('ACCEPTED'); continue
            if st == 'needs_manual_work': cells.append('MANUAL'); continue
            if na > 0:
                sel_a = 'A' if comp.get('selected_variant_a') else ''
                sel_b = 'B' if comp.get('selected_variant_b') else ''
                sel = f' sel={sel_a}+{sel_b}'.rstrip('+') if (sel_a or sel_b) else ' awaiting'
                cells.append(f'a{na}{sel}')
            else:
                cells.append('pending')
        print(f'  {cid:<10} {cells[0]:<20} {cells[1]:<20} {cells[2]:<20} {cells[3]:<20}')
    print(f'{"="*90}')


def do_sync_dashboard(clip_filter=None):
    """Sync review/, frames/, clips/ and prompts.json to signal-dashboard repo.
    Incremental by mtime — only copies newer files.
    Works without Playwright (pure file operations).
    """
    DASHBOARD_ROOT = Path('/tmp/signal-dashboard/series/signal-part1')
    DASHBOARD_ROOT.mkdir(parents=True, exist_ok=True)

    synced = 0
    skipped = 0
    errors = 0

    def _sync_file(src, dest):
        nonlocal synced, skipped, errors
        try:
            if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
                skipped += 1
                return
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            synced += 1
        except Exception as e:
            print(f'    Error copying {src.name}: {e}')
            errors += 1

    def _sync_dir(src_dir, dest_dir, pattern='**/*', clip_id=None):
        if not src_dir.exists():
            return
        for src in src_dir.glob(pattern):
            if src.is_dir():
                continue
            if src.name == '.DS_Store':
                continue
            # Filter by clip if specified
            if clip_id:
                rel = str(src.relative_to(src_dir))
                if not rel.startswith(clip_id):
                    continue
            dest = dest_dir / src.relative_to(src_dir)
            _sync_file(src, dest)

    print(f'Syncing to {DASHBOARD_ROOT}...')

    # 1. review/ — generated variants (PNG/MP4)
    print('  Syncing review/...')
    _sync_dir(REVIEW_DIR, DASHBOARD_ROOT / 'review', clip_id=clip_filter)

    # 2. frames/ — accepted keyframes
    print('  Syncing frames/...')
    _sync_dir(FRAMES_DIR, DASHBOARD_ROOT / 'frames', clip_id=clip_filter)

    # 3. clips/ — accepted video clips
    print('  Syncing clips/...')
    _sync_dir(CLIPS_DIR, DASHBOARD_ROOT / 'clips', clip_id=clip_filter)

    # 4. prompts.json — always sync
    print('  Syncing prompts.json...')
    if PROMPTS_PATH.exists():
        _sync_file(PROMPTS_PATH, DASHBOARD_ROOT / 'prompts' / 'all_prompts.json')

    print(f'\nSync complete: {synced} copied, {skipped} up-to-date, {errors} errors')
    print(f'Dashboard: {DASHBOARD_ROOT}')

    # Auto-push to git repo for Streamlit Cloud
    if synced > 0:
        _auto_push_to_git(clip_filter)


def _auto_push_to_git(clip_filter=None):
    """Auto-commit and push generated files from the main project repo."""
    import subprocess
    PROJECT_ROOT = Path(__file__).parent.parent
    if not (PROJECT_ROOT / '.git').exists():
        print(f'  No git repo at {PROJECT_ROOT}, skipping auto-push.')
        return
    try:
        # Add generated output files
        add_paths = ['output/review/', 'output/frames/', 'output/clips/',
                     'output/prompts/', 'output/status.json']
        for p in add_paths:
            full = PROJECT_ROOT / p
            if full.exists():
                subprocess.run(['git', 'add', p], cwd=PROJECT_ROOT,
                               capture_output=True, timeout=30)

        # Commit
        msg = f'Auto-sync: {clip_filter or "all"}'
        result = subprocess.run(
            ['git', 'commit', '-m', msg],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            # Push (with pull --rebase to handle concurrent pushes)
            subprocess.run(
                ['git', 'pull', '--rebase', 'origin', 'master'],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60
            )
            push_result = subprocess.run(
                ['git', 'push', 'origin', 'master'],
                cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120
            )
            if push_result.returncode == 0:
                print(f'  Dashboard pushed to git.')
            else:
                print(f'  Dashboard push failed: {push_result.stderr[:200]}')
        else:
            print(f'  No new changes to push.')
    except Exception as e:
        print(f'  Dashboard auto-push error: {e}')


# ── Phase workflow ────────────────────────────────────────────────────────────

def _load_commands():
    """Load commands.json for phase-based workflow."""
    if not COMMANDS_PATH.exists():
        return None
    with open(COMMANDS_PATH) as f:
        return json.load(f)


def _save_commands(cmd):
    """Save commands.json."""
    with open(COMMANDS_PATH, 'w') as f:
        json.dump(cmd, f, indent=2, ensure_ascii=False)


def do_phase_select(phase, clip_commands):
    """Copy selected variants to output/frames or output/clips. No browser needed."""
    suffixes = {'nb_first': 'first', 'nb_mid': 'mid', 'nb_last': 'last'}
    selected_count = 0

    for cid, cmd_info in clip_commands.items():
        if cmd_info.get('status') != 'selected':
            continue

        variant_idx = cmd_info['variant']  # 0-based
        attempt = cmd_info.get('attempt', 1)
        manifest = load_manifest(cid)

        attempt_dir = REVIEW_DIR / cid / phase / f'attempt_{attempt}'

        if phase in suffixes:
            # Try flat format first, then prompt_a subdirectory
            variant_file = attempt_dir / f'variant_{variant_idx + 1}.png'
            if not variant_file.exists():
                variant_file = attempt_dir / 'prompt_a' / f'variant_{variant_idx + 1}.png'

            if variant_file.exists():
                FRAMES_DIR.mkdir(parents=True, exist_ok=True)
                dest = FRAMES_DIR / f'{cid}_{suffixes[phase]}.png'
                shutil.copy2(variant_file, dest)
                print(f'  {cid}: variant_{variant_idx + 1} -> {dest.name}')

                mark_selected_simple(manifest, phase, attempt, variant_idx)
                save_manifest(cid, manifest)
                cmd_info['status'] = 'accepted'
                selected_count += 1
            else:
                print(f'  {cid}: variant file not found: {variant_file}')

        elif phase == 'veo':
            variant_file = attempt_dir / f'variant_{variant_idx + 1}.mp4'
            if not variant_file.exists():
                variant_file = attempt_dir / 'prompt_a' / f'variant_{variant_idx + 1}.mp4'

            if variant_file.exists():
                CLIPS_DIR.mkdir(parents=True, exist_ok=True)
                dest = CLIPS_DIR / f'{cid}_clip.mp4'
                shutil.copy2(variant_file, dest)
                print(f'  {cid}: variant_{variant_idx + 1} -> {dest.name}')

                mark_selected_simple(manifest, phase, attempt, variant_idx)
                save_manifest(cid, manifest)
                cmd_info['status'] = 'accepted'
                selected_count += 1
            else:
                print(f'  {cid}: variant file not found: {variant_file}')

    print(f'\n  Selected: {selected_count} clips')
    return selected_count


def do_chain(pw, scenes_filter=None, clip_filter=None, use_builtin_chromium=False):
    """Chain workflow: process clips sequentially within each scene (first→last→first→last).

    For each scene, processes clips in order:
      S01_A nb_first → S01_A nb_last → S01_B nb_first → S01_B nb_last → ...
    Skips clips whose dependencies aren't met (previous clip's last frame not accepted).
    All scenes are interleaved in one pass — ready clips from any scene get processed.

    scenes_filter: 'odd', 'even', or comma-separated scene IDs like 'S01,S03,S05'
    clip_filter: comma-separated clip IDs like 'S01_A,S02_B'
    """
    all_clips = load_clips(clip_filter)

    # Filter scenes
    if scenes_filter:
        all_scene_ids = list(dict.fromkeys(c['scene_id'] for c in all_clips))
        if scenes_filter == 'odd':
            allowed = {sid for i, sid in enumerate(all_scene_ids) if i % 2 == 0}
        elif scenes_filter == 'even':
            allowed = {sid for i, sid in enumerate(all_scene_ids) if i % 2 == 1}
        elif scenes_filter in ('q1', 'q2', 'q3', 'q4'):
            n = len(all_scene_ids)
            q = int(scenes_filter[1]) - 1  # 0-based quarter index
            chunk = n // 4
            remainder = n % 4
            start = sum(chunk + (1 if i < remainder else 0) for i in range(q))
            end = start + chunk + (1 if q < remainder else 0)
            allowed = set(all_scene_ids[start:end])
        else:
            allowed = set(scenes_filter.split(','))
        all_clips = [c for c in all_clips if c['scene_id'] in allowed]

    if not all_clips:
        print('  No clips to process.')
        return

    # Group by scene, preserving order
    from collections import OrderedDict
    scenes = OrderedDict()
    for clip in all_clips:
        sid = clip['scene_id']
        scenes.setdefault(sid, []).append(clip)

    print(f'\n  Chain mode: {len(all_clips)} clips across {len(scenes)} scenes')
    print(f'  Scenes: {", ".join(scenes.keys())}')

    # Launch browser
    ctx = launch_browser(pw, use_builtin_chromium=use_builtin_chromium)
    print('  Launched browser.')
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    def _on_console(msg):
        if msg.type in ('error', 'warning'):
            print(f'  [CONSOLE {msg.type.upper()}] {msg.text[:300]}')
    page.on('console', _on_console)

    ensure_project(page)
    wait_for_flow_ready(page)

    summary = {'generated': [], 'skipped': [], 'blocked': []}
    total_generated = 0
    consecutive_failures = 0  # track consecutive generation failures for retry logic
    MAX_CONSECUTIVE_FAILURES = 3  # after this many, pause 30 min
    MAX_RETRY_PAUSES = 2  # max number of 30-min pauses before giving up
    retry_pauses_done = 0

    # Distribute scenes across bots — only scenes that still have work
    num_bots = len(ACCOUNTS)
    bot_idx = _current_account_idx  # 0-based

    def _scenes_with_work():
        """Return set of scene IDs that still have pending clips."""
        pending = []
        for sid, sclips in scenes.items():
            for clip in sclips:
                m = load_manifest(clip['clip_id'])
                for comp in ('nb_first', 'nb_last', 'veo'):
                    st = m['components'].get(comp, {}).get('status', 'pending')
                    if st not in ('accepted', 'generated', 'needs_manual_work'):
                        pending.append(sid)
                        break
                else:
                    continue
                break
        return pending

    work_scenes = _scenes_with_work()
    my_scenes = {sid for i, sid in enumerate(work_scenes) if i % num_bots == bot_idx}
    print(f'  Bot {bot_idx + 1}/{num_bots}: assigned {len(my_scenes)}/{len(work_scenes)} scenes with work (total {len(scenes)})')

    # Keep looping until no more progress can be made
    max_passes = 50  # safety limit
    for pass_num in range(1, max_passes + 1):
        progress_this_pass = 0
        failures_this_pass = 0
        print(f'\n{"="*60}')
        print(f'  Pass {pass_num}')
        print(f'{"="*60}')

        # Re-distribute on each pass in case other bots finished
        if pass_num > 1:
            work_scenes = _scenes_with_work()
            my_scenes = {sid for i, sid in enumerate(work_scenes) if i % num_bots == bot_idx}
            print(f'  Bot {bot_idx + 1}: {len(my_scenes)}/{len(work_scenes)} scenes with work')

        for sid, scene_clips in scenes.items():
            if sid not in my_scenes:
                continue
            for clip_idx, clip in enumerate(scene_clips):
                cid = clip['clip_id']
                is_first_in_scene = (clip_idx == 0)

                _ensure_chat_view(page)
                manifest = load_manifest(cid)

                is_skip_last = manifest.get('skip_last', False)

                for component in ('nb_first', 'nb_last', 'veo'):
                    # Skip mid for now (most clips don't use it)
                    if component == 'nb_last' and (not clip.get('nano_banana_prompt_last') or is_skip_last):
                        continue
                    if component == 'veo' and not clip.get('veo_prompt'):
                        continue

                    status = manifest['components'][component].get('status', 'pending')
                    if status in ('accepted', 'needs_manual_work', 'skipped'):
                        continue

                    # Check if already generated (waiting for selection)
                    attempts = manifest['components'][component].get('attempts', [])
                    if attempts and status == 'generated':
                        continue

                    # Dependency check
                    if component == 'nb_first' and not is_first_in_scene:
                        # Need previous clip's last (or first if skip_last) frame to be ACCEPTED
                        ref = find_scene_ref(cid)
                        if not ref:
                            prev_cid = scene_clips[clip_idx - 1]['clip_id']
                            prev_manifest = load_manifest(prev_cid)
                            prev_skip = prev_manifest.get('skip_last', False)
                            if prev_skip:
                                prev_dep_status = prev_manifest['components']['nb_first'].get('status', 'pending')
                            else:
                                prev_dep_status = prev_manifest['components']['nb_last'].get('status', 'pending')
                            if prev_dep_status != 'accepted':
                                continue
                    elif component == 'nb_last':
                        # Need this clip's first frame to be accepted
                        ref = _resolve_ref_frame(manifest, cid, component)
                        if not ref:
                            continue
                    elif component == 'veo':
                        # Need first frame accepted; last frame only if not skip_last
                        first_st = manifest['components']['nb_first'].get('status', 'pending')
                        if first_st != 'accepted':
                            continue
                        if not is_skip_last:
                            last_st = manifest['components']['nb_last'].get('status', 'pending')
                            if last_st != 'accepted':
                                continue

                    # Ready to generate
                    attempt = get_next_attempt(manifest, component)
                    if attempt == 0:
                        manifest['components'][component]['status'] = 'needs_manual_work'
                        save_manifest(cid, manifest)
                        continue

                    if component == 'veo':
                        # VEO: use accepted first + last frames (last is optional if skip_last)
                        first_frame = FRAMES_DIR / f'{cid}_first.png'
                        last_frame = None if is_skip_last else FRAMES_DIR / f'{cid}_last.png'
                        if not first_frame.exists():
                            r2_key = _r2_key(first_frame)
                            if r2_storage.is_configured():
                                r2_storage.download_file(r2_key, first_frame)
                        if last_frame and not last_frame.exists():
                            r2_key = _r2_key(last_frame)
                            if r2_storage.is_configured():
                                r2_storage.download_file(r2_key, last_frame)
                        if not first_frame.exists():
                            summary['blocked'].append(f'{cid}/veo (missing first frame)')
                            continue
                        if last_frame and not last_frame.exists():
                            summary['blocked'].append(f'{cid}/veo (missing last frame)')
                            continue

                        print(f'\n  [{sid}] {cid} / veo / attempt_{attempt}')
                        variants = review_veo(page, clip, manifest, attempt,
                                              first_frame, last_frame)
                        if variants:
                            manifest['components']['veo']['status'] = 'generated'
                            save_manifest(cid, manifest)
                            summary['generated'].append(f'{cid}/veo/a{attempt}')
                            total_generated += 1
                            progress_this_pass += 1
                            consecutive_failures = 0
                        else:
                            summary['blocked'].append(f'{cid}/veo/a{attempt}')
                            consecutive_failures += 1
                            failures_this_pass += 1
                    else:
                        first_frame_ref = None
                        if component == 'nb_first':
                            first_frame_ref = find_scene_ref(cid)  # may be None for first clip
                        else:
                            first_frame_ref = _resolve_ref_frame(manifest, cid, component)

                        print(f'\n  [{sid}] {cid} / {component} / attempt_{attempt}')
                        if first_frame_ref:
                            print(f'    ref: {first_frame_ref.name}')

                        variants = review_nano_banana(page, clip, manifest, component, attempt,
                                                      first_frame_ref=first_frame_ref)
                        if variants:
                            manifest['components'][component]['status'] = 'generated'
                            save_manifest(cid, manifest)
                            summary['generated'].append(f'{cid}/{component}/a{attempt}')
                            total_generated += 1
                            progress_this_pass += 1
                            consecutive_failures = 0
                        else:
                            summary['blocked'].append(f'{cid}/{component}/a{attempt}')
                            consecutive_failures += 1
                            failures_this_pass += 1

                    # If too many consecutive failures, pause 30 min before continuing
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES and retry_pauses_done < MAX_RETRY_PAUSES:
                        retry_pauses_done += 1
                        wait_min = 30
                        print(f'\n  {"!"*60}')
                        print(f'  {consecutive_failures} consecutive failures — pausing {wait_min} min (pause {retry_pauses_done}/{MAX_RETRY_PAUSES})')
                        print(f'  {"!"*60}')
                        import time as _time
                        _time.sleep(wait_min * 60)
                        consecutive_failures = 0
                        print(f'  Resuming after {wait_min} min pause...')

                    human_pause_between_generations()

        if progress_this_pass == 0:
            if failures_this_pass > 0 and retry_pauses_done < MAX_RETRY_PAUSES:
                retry_pauses_done += 1
                wait_min = 30
                print(f'\n  No progress but {failures_this_pass} failures — pausing {wait_min} min (pause {retry_pauses_done}/{MAX_RETRY_PAUSES})')
                import time as _time
                _time.sleep(wait_min * 60)
                consecutive_failures = 0
                print(f'  Resuming after {wait_min} min pause...')
                continue
            print(f'\n  No progress in pass {pass_num} — stopping.')
            break

        print(f'\n  Pass {pass_num} done: {progress_this_pass} generations')

    # Summary
    print(f'\n{"="*60}')
    print(f'  CHAIN COMPLETE')
    print(f'  Total generated: {total_generated}')
    if summary["generated"]:
        print(f'  Generated:')
        for g in summary['generated']:
            print(f'    {g}')
    if summary["blocked"]:
        print(f'  Blocked/failed:')
        for b in summary['blocked']:
            print(f'    {b}')
    print(f'{"="*60}')

    ctx.close()


def do_phase(pw, use_builtin_chromium=False):
    """Execute phase-based workflow from commands.json."""
    cmd = _load_commands()
    if not cmd:
        print('Error: output/commands.json not found. Use the dashboard to start a phase.')
        sys.exit(1)

    phase = cmd['phase']
    action = cmd.get('action', 'generate')
    clip_commands = cmd.get('clips', {})

    print(f'\n  Phase: {phase}')
    print(f'  Action: {action}')

    # Select action: copy selected variants without browser
    if action == 'select':
        do_phase_select(phase, clip_commands)
        _save_commands(cmd)
        _auto_push_to_git()
        return

    # Determine which clips need generation
    all_clips = load_clips()
    clips_to_generate = []
    for clip in all_clips:
        cid = clip['clip_id']
        clip_cmd = clip_commands.get(cid, {})
        status = clip_cmd.get('status', 'pending')
        if status in ('pending', 'rejected'):
            clips_to_generate.append(clip)

    if not clips_to_generate:
        print('  No clips need generation.')
        return

    print(f'  Clips to generate: {len(clips_to_generate)}')

    # Mark bot as running
    cmd['bot_running'] = True
    _save_commands(cmd)

    # Launch browser
    ctx = launch_browser(pw, use_builtin_chromium=use_builtin_chromium)
    print('  Launched browser.')
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    def _on_console(msg):
        if msg.type in ('error', 'warning'):
            print(f'  [CONSOLE {msg.type.upper()}] {msg.text[:300]}')
    page.on('console', _on_console)

    ensure_project(page)
    wait_for_flow_ready(page)

    summary = {'generated': [], 'failed': []}

    for i, clip in enumerate(clips_to_generate):
        cid = clip['clip_id']
        clip_cmd = clip_commands.get(cid, {})
        print(f'\n[{i+1}/{len(clips_to_generate)}] Phase {phase}: {cid}')

        _ensure_chat_view(page)
        manifest = load_manifest(cid)

        if phase in ('nb_first', 'nb_mid', 'nb_last'):
            # Determine attempt number
            attempt = get_next_attempt(manifest, phase)
            if attempt == 0:
                print(f'  {cid}: max attempts reached, skip')
                summary['failed'].append(f'{cid}/{phase}')
                continue

            # Check dependency
            first_frame_ref = None
            if phase in ('nb_mid', 'nb_last'):
                ref = _resolve_ref_frame(manifest, cid, phase)
                if not ref:
                    print(f'  {cid}: waiting for previous frame — skip')
                    summary['failed'].append(f'{cid}/{phase} (no ref)')
                    continue
                first_frame_ref = ref
            else:
                first_frame_ref = _resolve_ref_frame(manifest, cid, phase)

            variants = review_nano_banana(page, clip, manifest, phase, attempt,
                                          first_frame_ref=first_frame_ref)
            if variants:
                summary['generated'].append(f'{cid}/{phase}/a{attempt} ({len(variants)}v)')
                clip_commands.setdefault(cid, {})['status'] = 'generated'
                clip_commands[cid]['attempt'] = attempt
            else:
                summary['failed'].append(f'{cid}/{phase}/a{attempt}')
                clip_commands.setdefault(cid, {})['status'] = 'failed'

        elif phase == 'veo':
            fp = FRAMES_DIR / f'{cid}_first.png'
            lp = FRAMES_DIR / f'{cid}_last.png'
            if not fp.exists() or not lp.exists():
                print(f'  {cid}: frames not ready, skip')
                summary['failed'].append(f'{cid}/veo (no frames)')
                continue

            attempt = get_next_attempt(manifest, 'veo')
            if attempt == 0:
                print(f'  {cid}: max attempts reached, skip')
                summary['failed'].append(f'{cid}/veo')
                continue

            variants = review_veo(page, clip, manifest, attempt, fp, lp,
                                  veo_mode=clip.get('veo_mode', 'frames'))
            if variants:
                summary['generated'].append(f'{cid}/veo/a{attempt} ({len(variants)}v)')
                clip_commands.setdefault(cid, {})['status'] = 'generated'
                clip_commands[cid]['attempt'] = attempt
            else:
                summary['failed'].append(f'{cid}/veo/a{attempt}')
                clip_commands.setdefault(cid, {})['status'] = 'failed'

        # Save progress after each clip
        _save_commands(cmd)

        if i < len(clips_to_generate) - 1:
            human_pause_between_generations()

    # Summary
    print(f'\n{"="*60}')
    print(f'  Generated: {len(summary["generated"])}')
    for g in summary['generated']:
        print(f'    {g}')
    print(f'  Failed: {len(summary["failed"])}')
    for f in summary['failed']:
        print(f'    {f}')
    print(f'{"="*60}')

    # Mark bot as done
    cmd['bot_running'] = False
    _save_commands(cmd)

    ctx.close()

    # Auto-push results
    if summary['generated']:
        try:
            _auto_push_to_git()
            print('  Results pushed to git.')
        except Exception as e:
            print(f'  Git push error: {e}')


# ── Main ─────────────────────────────────────────────────────────────────────

def _timeout_handler(signum, frame):
    print(f'\n  GLOBAL TIMEOUT ({GLOBAL_TIMEOUT_SEC}s) — exiting!')
    if _active_context:
        try: _active_context.close()
        except Exception: pass
    sys.exit(42)


def do_generate_location(pw, prompt, output_path, num_variants=4, project_id=None, use_builtin_chromium=False):
    """Generate a location image from a text prompt (no ingredients).

    Generates num_variants variants into a temp directory, then the user
    can pick the best one. All variants are saved to output_path parent dir.
    """
    global _active_context
    output_path = Path(output_path)
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = output_path.stem  # e.g. loc_underground_corridor
    variants_dir = output_dir / f'.{stem}_variants'
    variants_dir.mkdir(parents=True, exist_ok=True)

    print(f'\n{"="*60}')
    print(f'  GENERATE LOCATION')
    print(f'  Output: {output_path}')
    print(f'  Variants dir: {variants_dir}')
    print(f'  Prompt: {prompt[:100]}...')
    print(f'{"="*60}')

    ctx = launch_browser(pw, use_builtin_chromium=use_builtin_chromium)
    _active_context = ctx
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.add_init_script(STEALTH_JS)
    page.goto(FLOW_URL, timeout=60000, wait_until='domcontentloaded')
    human_delay_long(3, 5)
    dismiss_popups(page)
    ensure_project(page, project_id)
    human_delay(1, 2)

    _ensure_chat_view(page)
    dismiss_popups(page)
    switch_mode(page, 'Создать изображение')
    set_image_model(page, 'Nano Banana Pro')
    set_orientation(page, 'horizontal')

    # Sanitize prompt (add Pixar style if missing) but skip character validation
    clean_prompt = sanitize_nb_prompt(prompt)

    # Set x4 variant count
    set_variant_count(page, num_variants)

    # Set up network capture
    capture = NbNetworkCapture()
    capture.start(page)

    clear_prompt(page)
    fill_prompt(page, clean_prompt)
    take_screenshot(page, f'loc_{stem}_before')

    # Generate
    _scroll_chat_bottom(page)
    time.sleep(1)
    errors_before = _count_errors(page)
    click_generate(page)
    result = poll_generation(page, errors_before=errors_before)

    if result == 'server_error':
        print(f'    FAILED ({result}) — trying retry...')
        time.sleep(2)
        if _click_retry_on_error(page):
            time.sleep(3)
            errors_before = _count_errors(page)
            result = poll_generation(page, errors_before=errors_before)

    # Rate limit on NB Pro → fallback to Nano Banana 2
    if result == 'rate_limit':
        print(f'    Rate limit on NB Pro — switching to Nano Banana 2...')
        time.sleep(2)
        set_image_model(page, 'Nano Banana 2')
        human_delay(1, 2)
        capture.stop(page)
        capture = NbNetworkCapture()
        capture.start(page)
        clear_prompt(page)
        fill_prompt(page, clean_prompt)
        _scroll_chat_bottom(page)
        time.sleep(1)
        errors_before = _count_errors(page)
        click_generate(page)
        result = poll_generation(page, errors_before=errors_before)

    saved = []
    if result == 'success':
        time.sleep(3)
        if capture.images:
            print(f'    Network captured {len(capture.images)} images')
            for idx, img in enumerate(capture.images):
                media_id = img['id']
                fife_url = img['url']
                dest_path = variants_dir / f'variant_{idx+1}.png'
                ok = False
                if fife_url and download_via_fetch(page, fife_url, dest_path):
                    saved.append(dest_path)
                    print(f'    Saved variant_{idx+1}.png ({dest_path.stat().st_size} bytes)')
                    ok = True
                if not ok:
                    redirect_url = f'/fx/api/trpc/media.getMediaUrlRedirect?name={media_id}'
                    if download_via_fetch(page, redirect_url, dest_path):
                        saved.append(dest_path)
                        print(f'    Saved variant_{idx+1}.png (redirect)')
                        ok = True
                if not ok:
                    print(f'    Failed to download variant_{idx+1}')
        else:
            print(f'    No network capture — trying DOM fallback...')
            _scroll_chat_bottom(page)
            time.sleep(2)
            new_url = _get_last_generated_image_url(page)
            if new_url:
                dest_path = variants_dir / 'variant_1.png'
                if download_via_fetch(page, new_url, dest_path, min_size=200000):
                    saved.append(dest_path)
                    print(f'    Saved variant_1.png (DOM fallback)')
    else:
        print(f'    Generation FAILED: {result}')

    capture.stop(page)
    take_screenshot(page, f'loc_{stem}_after')

    print(f'\n  Results: {len(saved)}/{num_variants} variants saved to {variants_dir}')
    if saved:
        # Copy first variant as the main output (user can replace later)
        import shutil
        shutil.copy2(saved[0], output_path)
        print(f'  Copied variant_1 -> {output_path}')
        print(f'  All variants in: {variants_dir}/')
        print(f'  To pick a different variant, copy it manually:')
        for s in saved:
            print(f'    cp "{s}" "{output_path}"')

    try:
        ctx.close()
    except Exception:
        pass
    _active_context = None

    return saved


def do_generate_locations_batch(pw, batch_file, use_builtin_chromium=False):
    """Generate multiple location images in a SINGLE browser session.

    batch_file is a JSON file with a list of objects:
    [
      {"name": "loc_xxx", "prompt": "...", "output": "path/to/result.png"},
      ...
    ]
    """
    import json as _json
    global _active_context

    batch_path = Path(batch_file)
    if not batch_path.is_absolute():
        batch_path = PROJECT_ROOT / batch_path
    with open(batch_path) as f:
        tasks = _json.load(f)

    print(f'\n{"="*60}')
    print(f'  BATCH LOCATION GENERATION')
    print(f'  Tasks: {len(tasks)}')
    print(f'{"="*60}')

    ctx = launch_browser(pw, use_builtin_chromium=use_builtin_chromium)
    _active_context = ctx
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.add_init_script(STEALTH_JS)

    def _on_console(msg):
        if msg.type in ('error', 'warning'):
            print(f'  [CONSOLE {msg.type.upper()}] {msg.text[:300]}')
    page.on('console', _on_console)

    page.goto(FLOW_URL, timeout=60000, wait_until='domcontentloaded')
    human_delay_long(3, 5)
    dismiss_popups(page)
    ensure_project(page)
    wait_for_flow_ready(page)

    total_ok = 0
    total_fail = 0
    _batch_current_model = 'Nano Banana Pro'  # Track current model for rate limit fallback

    for idx, task in enumerate(tasks):
        name = task['name']
        prompt = task['prompt']
        output_path = Path(task['output'])
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

        output_dir = output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = output_path.stem
        variants_dir = output_dir / f'.{stem}_variants'
        variants_dir.mkdir(parents=True, exist_ok=True)

        print(f'\n{"="*60}')
        print(f'  [{idx+1}/{len(tasks)}] {name}')
        print(f'  Output: {output_path}')
        print(f'  Prompt: {prompt[:80]}...')
        print(f'{"="*60}')

        try:
            # Ensure we're in chat view and ready
            _ensure_chat_view(page)
            dismiss_popups(page)

            # Set up mode/model — try NB Pro first, stay on NB2 if rate limited
            switch_mode(page, 'Создать изображение')
            set_image_model(page, _batch_current_model)
            set_orientation(page, 'horizontal')
            set_variant_count(page, 4)

            # Upload reference image as ingredient if provided
            ref_image = task.get('ref_image')
            if ref_image:
                print(f'  Uploading reference: {ref_image}')
                clear_ingredients(page)
                upload_ingredients(page, [ref_image])
            elif idx == 0 or tasks[idx - 1].get('ref_image'):
                # Clear ingredients from previous task if it had a ref
                clear_ingredients(page)

            # Sanitize and fill prompt
            clean_prompt = sanitize_nb_prompt(prompt)

            # Set up network capture
            capture = NbNetworkCapture()
            capture.start(page)

            clear_prompt(page)
            fill_prompt(page, clean_prompt)

            # Generate
            _scroll_chat_bottom(page)
            time.sleep(1)
            errors_before = _count_errors(page)
            click_generate(page)
            result = poll_generation(page, errors_before=errors_before)

            if result == 'server_error':
                print(f'    Server error — retrying...')
                time.sleep(2)
                if _click_retry_on_error(page):
                    time.sleep(3)
                    errors_before = _count_errors(page)
                    result = poll_generation(page, errors_before=errors_before)

            # Rate limit on NB Pro → fallback to Nano Banana 2, retry
            if result == 'rate_limit':
                print(f'    Rate limit on NB Pro — switching to Nano Banana 2...')
                time.sleep(2)
                set_image_model(page, 'Nano Banana 2')
                human_delay(1, 2)
                # Re-do capture
                capture.stop(page)
                capture = NbNetworkCapture()
                capture.start(page)
                clear_prompt(page)
                fill_prompt(page, clean_prompt)
                _scroll_chat_bottom(page)
                time.sleep(1)
                errors_before = _count_errors(page)
                click_generate(page)
                result = poll_generation(page, errors_before=errors_before)
                # Stay on NB2 for remaining tasks (NB Pro daily limit hit)
                _batch_current_model = 'Nano Banana 2'  # noqa: F841 — used in outer loop

            saved = []
            if result == 'success':
                time.sleep(3)
                if capture.images:
                    print(f'    Network captured {len(capture.images)} images')
                    for vi, img in enumerate(capture.images):
                        media_id = img['id']
                        fife_url = img['url']
                        dest_path = variants_dir / f'variant_{vi+1}.png'
                        ok = False
                        if fife_url and download_via_fetch(page, fife_url, dest_path):
                            saved.append(dest_path)
                            print(f'    Saved variant_{vi+1}.png ({dest_path.stat().st_size} bytes)')
                            ok = True
                        if not ok:
                            redirect_url = f'/fx/api/trpc/media.getMediaUrlRedirect?name={media_id}'
                            if download_via_fetch(page, redirect_url, dest_path):
                                saved.append(dest_path)
                                print(f'    Saved variant_{vi+1}.png (redirect)')
                                ok = True
                        if not ok:
                            print(f'    Failed to download variant_{vi+1}')
                else:
                    print(f'    No network capture — DOM fallback...')
                    _scroll_chat_bottom(page)
                    time.sleep(2)
                    new_url = _get_last_generated_image_url(page)
                    if new_url:
                        dest_path = variants_dir / 'variant_1.png'
                        if download_via_fetch(page, new_url, dest_path, min_size=200000):
                            saved.append(dest_path)
            else:
                print(f'    Generation FAILED: {result}')

            capture.stop(page)

            if saved:
                import shutil
                shutil.copy2(saved[0], output_path)
                # If parent dir has existing variant_*.png (redo scenario),
                # back up old ones and replace with new redo variants
                parent_dir = output_path.parent
                existing_variants = sorted(parent_dir.glob('variant_*.png'))
                if existing_variants and variants_dir != parent_dir:
                    old_dir = parent_dir / '.old_variants'
                    old_dir.mkdir(exist_ok=True)
                    for ev in existing_variants:
                        shutil.move(str(ev), str(old_dir / ev.name))
                    for vi, sv in enumerate(saved):
                        shutil.copy2(str(sv), str(parent_dir / f'variant_{vi+1}.png'))
                    print(f'    Replaced {len(existing_variants)} old variants with {len(saved)} new ones')
                    # Update manifest if exists
                    manifest_path = parent_dir.parent / 'manifest.json'
                    if manifest_path.exists():
                        try:
                            mdata = json.load(open(manifest_path))
                            if mdata.get('status') == 'rejected':
                                mdata['status'] = 'pending'
                                mdata['feedback'] = ''
                                ref_img = task.get('ref_image')
                                if ref_img:
                                    mdata['ref_image'] = ref_img
                                prompt_field = name.split('/')[-1] if '/' in name else 'prompt_a'
                                mdata[prompt_field] = prompt
                                json.dump(mdata, open(manifest_path, 'w'), indent=2, ensure_ascii=False)
                                print(f'    Updated manifest: status -> pending')
                        except Exception as me:
                            print(f'    Manifest update failed: {me}')
                print(f'  [{idx+1}/{len(tasks)}] OK — {len(saved)} variants saved')
                total_ok += 1
            else:
                print(f'  [{idx+1}/{len(tasks)}] FAIL — no variants saved')
                total_fail += 1

            # Ready for next generation — just clear prompt
            human_delay(1, 2)

        except Exception as e:
            print(f'  [{idx+1}/{len(tasks)}] ERROR: {e}')
            total_fail += 1
            # Try to recover
            try:
                _ensure_chat_view(page)
            except Exception:
                pass

    print(f'\n{"="*60}')
    print(f'  BATCH DONE. Success: {total_ok}/{total_ok + total_fail}')
    print(f'{"="*60}')

    try:
        ctx.close()
    except Exception:
        pass
    _active_context = None

    return total_ok


def do_generate_refs(pw, project_dir, use_builtin_chromium=False, bot_index=0, bot_count=1, ref_filter=None):
    """Generate reference images (base and angles) from project manifests.

    Reads manifests from <project_dir>/references/ and generates images
    for each manifest with status 'generating'.

    Outputs progress as [REF] lines for BotManager parsing.
    """
    global _active_context

    project_dir = Path(project_dir)
    refs_dir = project_dir / 'references'
    project_json_path = project_dir / 'project.json'

    if not project_json_path.exists():
        print(f'[REF] ERROR: project.json not found at {project_json_path}')
        return 0

    with open(project_json_path) as f:
        project = json.load(f)

    # Collect all manifests with status 'generating'
    tasks = []

    for entity_type in ('characters', 'locations'):
        items = project.get(entity_type, [])
        for item in items:
            item_id = item['id']
            item_name = item.get('nameRu') or item.get('name') or item_id

            # Check base manifest
            base_manifest_path = refs_dir / entity_type / item_id / 'review' / 'base' / 'manifest.json'
            if base_manifest_path.exists():
                with open(base_manifest_path) as f:
                    manifest = json.load(f)
                if manifest.get('status') in ('generating', 'pending') and manifest.get('attempts'):
                    last_attempt = manifest['attempts'][-1]
                    prompt = last_attempt.get('prompt', '')
                    if prompt:
                        tasks.append({
                            'type': entity_type,
                            'item_id': item_id,
                            'item_name': item_name,
                            'target': 'base',
                            'angle_id': None,
                            'prompt': prompt,
                            'ingredients': [],
                            'manifest_path': str(base_manifest_path),
                            'attempt_num': last_attempt['attempt'],
                            'review_dir': str(base_manifest_path.parent / f'attempt_{last_attempt["attempt"]}'),
                        })

            # Check angle manifests
            angles_dir = refs_dir / entity_type / item_id / 'review' / 'angles'
            if angles_dir.exists():
                for angle_dir in sorted(angles_dir.iterdir()):
                    if not angle_dir.is_dir():
                        continue
                    angle_id = angle_dir.name
                    angle_manifest_path = angle_dir / 'manifest.json'
                    if not angle_manifest_path.exists():
                        continue
                    with open(angle_manifest_path) as f:
                        manifest = json.load(f)
                    if manifest.get('status') in ('generating', 'pending') and manifest.get('attempts'):
                        last_attempt = manifest['attempts'][-1]
                        prompt = last_attempt.get('prompt', '')
                        if not prompt:
                            continue
                        # Base image is the ingredient for angles — use path from project.json
                        ingredients = []
                        base_image_rel = item.get('baseImage')
                        if base_image_rel:
                            base_image_abs = project_dir / base_image_rel
                            if base_image_abs.exists():
                                ingredients = [str(base_image_abs)]
                                print(f'  [REF] Base ingredient from project.json: {base_image_rel}')
                            else:
                                print(f'  [REF] WARNING: baseImage path not found: {base_image_abs}')
                        # Fallback: scan for base.* files
                        if not ingredients:
                            base_dir = refs_dir / entity_type / item_id
                            # Try {id}_base.* first (new format), then base.* (legacy)
                            for prefix in (f'{item_id}_base', 'base'):
                                for ext in ('png', 'jpg', 'jpeg', 'webp'):
                                    candidate = base_dir / f'{prefix}.{ext}'
                                    if candidate.exists():
                                        ingredients = [str(candidate)]
                                        print(f'  [REF] Base ingredient from scan: {candidate.name}')
                                        break
                                if ingredients:
                                    break
                        if not ingredients:
                            print(f'  [REF] SKIP {entity_type}/{item_id}/{angle_id}: no base image found')
                            continue
                        tasks.append({
                            'type': entity_type,
                            'item_id': item_id,
                            'item_name': item_name,
                            'target': 'angle',
                            'angle_id': angle_id,
                            'prompt': prompt,
                            'ingredients': ingredients,
                            'manifest_path': str(angle_manifest_path),
                            'attempt_num': last_attempt['attempt'],
                            'review_dir': str(angle_manifest_path.parent / f'attempt_{last_attempt["attempt"]}'),
                        })

    # Apply filter if provided
    if ref_filter:
        filtered_chars = set(ref_filter.get('characters', []))
        filtered_locs = set(ref_filter.get('locations', []))
        filtered_angles = set(ref_filter.get('angles', []))  # keys like "characters:charId:angleId"

        def task_matches_filter(task):
            entity_type = task['type']
            item_id = task['item_id']

            # Check if the character/location itself is selected
            if entity_type == 'characters' and filtered_chars and item_id not in filtered_chars:
                return False
            if entity_type == 'locations' and filtered_locs and item_id not in filtered_locs:
                return False

            # For angle tasks, check if the specific angle is selected
            if task['target'] == 'angle' and task['angle_id'] and filtered_angles:
                angle_key = f"{entity_type}:{item_id}:{task['angle_id']}"
                if angle_key not in filtered_angles:
                    return False

            return True

        before_count = len(tasks)
        tasks = [t for t in tasks if task_matches_filter(t)]
        if before_count != len(tasks):
            print(f'[REF] Filter applied: {len(tasks)}/{before_count} tasks match selection')

    if not tasks:
        print(f'[REF] No pending tasks found. Done.')
        return 0

    # Multi-bot distribution: each bot takes only its share of tasks
    if bot_count > 1:
        all_count = len(tasks)
        tasks = [t for i, t in enumerate(tasks) if i % bot_count == bot_index]
        print(f'[REF] Multi-bot: bot {bot_index}/{bot_count}, taking {len(tasks)}/{all_count} tasks')

    if not tasks:
        print(f'[REF] No tasks assigned to this bot. Done.')
        return 0

    print(f'\n{"="*60}')
    print(f'[REF] REFERENCE GENERATION')
    print(f'[REF] Project: {project_dir}')
    print(f'[REF] Tasks: {len(tasks)}')
    if bot_count > 1:
        print(f'[REF] Bot: {bot_index}/{bot_count}')
    print(f'{"="*60}')

    ctx = launch_browser(pw, use_builtin_chromium=use_builtin_chromium)
    _active_context = ctx
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.add_init_script(STEALTH_JS)
    page.goto(FLOW_URL, timeout=60000, wait_until='domcontentloaded')
    human_delay_long(3, 5)
    dismiss_popups(page)
    ensure_project(page)
    wait_for_flow_ready(page)

    total_ok = 0
    total_fail = 0
    _ref_current_model = 'Nano Banana Pro'

    for idx, task in enumerate(tasks):
        target_label = task['target']
        if task['angle_id']:
            target_label = f"angle:{task['angle_id']}"
        label = f"{task['type']}/{task['item_name']}/{target_label}"

        print(f'\n{"="*60}')
        print(f'[REF] [{idx+1}/{len(tasks)}] Generating {label}')
        print(f'[REF] Prompt: {task["prompt"][:80]}...')
        if task['ingredients']:
            print(f'[REF] Ingredients: {len(task["ingredients"])} files')
        print(f'{"="*60}')

        review_dir = Path(task['review_dir'])
        review_dir.mkdir(parents=True, exist_ok=True)

        try:
            _ensure_chat_view(page)
            dismiss_popups(page)

            switch_mode(page, 'Создать изображение')
            set_image_model(page, _ref_current_model)
            set_orientation(page, 'horizontal')
            set_variant_count(page, 4)

            # Upload ingredients (base image for angles)
            if task['ingredients']:
                print(f'  [REF] Ingredients: {task["ingredients"]}')
                clear_ingredients(page)
                count = upload_ingredients(page, task['ingredients'])
                thumbs = _count_ingredient_thumbs(page)
                print(f'  [REF] Uploaded {count} ingredient(s), thumbs: {thumbs}')
                if thumbs == 0 and task['target'] == 'angle':
                    print(f'  [REF] SKIP: angle generation without ingredient — skipping')
                    total_fail += 1
                    continue
            elif idx == 0 or tasks[idx - 1].get('ingredients'):
                clear_ingredients(page)

            clean_prompt = sanitize_nb_prompt(task['prompt'])

            capture = NbNetworkCapture()
            capture.start(page)

            clear_prompt(page)
            fill_prompt(page, clean_prompt)

            _scroll_chat_bottom(page)
            time.sleep(1)
            errors_before = _count_errors(page)
            click_generate(page)
            result = poll_generation(page, errors_before=errors_before)

            if result == 'server_error':
                print(f'[REF]   Server error -- retrying...')
                time.sleep(2)
                if _click_retry_on_error(page):
                    time.sleep(3)
                    errors_before = _count_errors(page)
                    result = poll_generation(page, errors_before=errors_before)

            if result == 'rate_limit':
                print(f'[REF]   Rate limit on NB Pro -- switching to Nano Banana 2...')
                time.sleep(2)
                set_image_model(page, 'Nano Banana 2')
                human_delay(1, 2)
                capture.stop(page)
                capture = NbNetworkCapture()
                capture.start(page)
                clear_prompt(page)
                fill_prompt(page, clean_prompt)
                _scroll_chat_bottom(page)
                time.sleep(1)
                errors_before = _count_errors(page)
                click_generate(page)
                result = poll_generation(page, errors_before=errors_before)
                _ref_current_model = 'Nano Banana 2'

            saved = []
            if result == 'success':
                time.sleep(3)
                if capture.images:
                    print(f'[REF]   Network captured {len(capture.images)} images')
                    for vi, img in enumerate(capture.images):
                        media_id = img['id']
                        fife_url = img['url']
                        dest_path = review_dir / f'variant_{vi}.png'
                        ok = False
                        if fife_url and download_via_fetch(page, fife_url, dest_path):
                            saved.append(dest_path)
                            print(f'[REF]   Saved variant_{vi}.png ({dest_path.stat().st_size} bytes)')
                            ok = True
                        if not ok:
                            redirect_url = f'/fx/api/trpc/media.getMediaUrlRedirect?name={media_id}'
                            if download_via_fetch(page, redirect_url, dest_path):
                                saved.append(dest_path)
                                print(f'[REF]   Saved variant_{vi}.png (redirect)')
                                ok = True
                        if not ok:
                            print(f'[REF]   Failed to download variant_{vi}')
                else:
                    print(f'[REF]   No network capture -- DOM fallback...')
                    _scroll_chat_bottom(page)
                    time.sleep(2)
                    new_url = _get_last_generated_image_url(page)
                    if new_url:
                        dest_path = review_dir / 'variant_0.png'
                        if download_via_fetch(page, new_url, dest_path, min_size=200000):
                            saved.append(dest_path)
            else:
                print(f'[REF]   Generation FAILED: {result}')

            capture.stop(page)

            # Update manifest with results
            manifest_path = Path(task['manifest_path'])
            with open(manifest_path) as f:
                manifest = json.load(f)

            if saved:
                # Update last attempt variants
                last_attempt = manifest['attempts'][-1]
                last_attempt['variants'] = [
                    {'file': f'variant_{vi}.png', 'scores': None, 'avg': None}
                    for vi in range(len(saved))
                ]
                manifest['status'] = 'generated'
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)
                print(f'[REF] [{idx+1}/{len(tasks)}] OK -- {len(saved)} variants saved')
                total_ok += 1
            else:
                manifest['status'] = 'pending'
                with open(manifest_path, 'w') as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)
                print(f'[REF] [{idx+1}/{len(tasks)}] FAIL -- no variants saved')
                total_fail += 1

            human_delay(1, 2)

        except Exception as e:
            print(f'[REF] [{idx+1}/{len(tasks)}] ERROR: {e}')
            total_fail += 1
            try:
                _ensure_chat_view(page)
            except Exception:
                pass

    print(f'\n{"="*60}')
    print(f'[REF] Done. Generated {total_ok}/{total_ok + total_fail} items.')
    print(f'{"="*60}')

    try:
        ctx.close()
    except Exception:
        pass
    _active_context = None

    return total_ok


def main():
    global _current_account_idx

    parser = argparse.ArgumentParser(description='Flow Bot v2')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--review', action='store_true', help='Generate variants for review')
    group.add_argument('--select', action='store_true', help='Accept a variant')
    group.add_argument('--fail', action='store_true', help='Mark attempt as failed')
    group.add_argument('--status', action='store_true', help='Show status')
    group.add_argument('--extract-frames', action='store_true', help='Extract video frames')
    group.add_argument('--login', action='store_true', help='Open browser for manual login')
    group.add_argument('--sync-dashboard', action='store_true', help='Sync files to signal-dashboard')
    group.add_argument('--phase', action='store_true', help='Phase workflow: reads output/commands.json')
    group.add_argument('--chain', action='store_true', help='Chain workflow: sequential first→last per scene')
    group.add_argument('--generate-location', action='store_true', help='Generate location image from prompt (no ingredients)')
    group.add_argument('--generate-locations-batch', action='store_true', help='Generate multiple locations from a JSON batch file (single browser session)')
    group.add_argument('--generate-refs', action='store_true', help='Generate reference images from project manifests')

    parser.add_argument('--clip', type=str, default=None, help='Clip ID or comma-separated list: S02_B,S02_C,S02_D')
    parser.add_argument('--scenes', type=str, default=None, help='Scene filter: odd, even, or comma-separated list: S01,S03,S05')
    parser.add_argument('--component', type=str, default=None, choices=['nb_first','nb_mid','nb_last','veo'])
    parser.add_argument('--attempt', type=int, default=None)
    parser.add_argument('--variant', type=int, default=None)
    parser.add_argument('--scores', type=str, default=None)
    parser.add_argument('--trim-start', type=float, default=None)
    parser.add_argument('--trim-end', type=float, default=None)
    parser.add_argument('--batch', type=str, default='a', choices=['a','b'])
    parser.add_argument('--account', type=int, default=1, choices=range(1, len(ACCOUNTS)+1))
    parser.add_argument('--project', type=str, default=None, help='Project UUID to use (overrides auto-detect)')
    parser.add_argument('--chromium', action='store_true', help='Use built-in Chromium instead of system Chrome (for parallel bots)')
    parser.add_argument('--prompts', type=str, default=None, help='Path to prompts JSON file (overrides default)')
    parser.add_argument('--output-dir', type=str, default=None, help='Output directory (overrides default output/)')
    parser.add_argument('--loc-prompt', type=str, default=None, help='Prompt text for --generate-location')
    parser.add_argument('--loc-output', type=str, default=None, help='Output file path for --generate-location (e.g. sosed_локации_hq/loc_name.png)')
    parser.add_argument('--loc-variants', type=int, default=4, help='Number of variants to generate (default 4)')
    parser.add_argument('--loc-batch', type=str, default=None, help='JSON batch file for --generate-locations-batch')
    parser.add_argument('--project-dir', type=str, default=None, help='Project directory for --generate-refs mode')
    parser.add_argument('--bot-index', type=int, default=0, help='Bot index for multi-bot distribution (0-based)')
    parser.add_argument('--bot-count', type=int, default=1, help='Total number of bots for task distribution')
    parser.add_argument('--filter', type=str, default=None, help='JSON filter for selected characters/locations/angles')

    args = parser.parse_args()
    _current_account_idx = args.account - 1

    # Override paths if --prompts or --output-dir provided
    global PROMPTS_PATH, OUTPUT_DIR, FRAMES_DIR, CLIPS_DIR, REVIEW_DIR, SCREENSHOTS_DIR
    if args.prompts:
        PROMPTS_PATH = Path(args.prompts).resolve()
    if args.output_dir:
        OUTPUT_DIR = Path(args.output_dir).resolve()
        FRAMES_DIR = OUTPUT_DIR / 'frames'
        CLIPS_DIR = OUTPUT_DIR / 'clips'
        REVIEW_DIR = OUTPUT_DIR / 'review'
        SCREENSHOTS_DIR = OUTPUT_DIR / 'screenshots'

    for d in (FRAMES_DIR, CLIPS_DIR, REVIEW_DIR, SCREENSHOTS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    if args.select:
        if not all([args.clip, args.component, args.attempt, args.variant is not None, args.scores]):
            parser.error('--select requires --clip, --component, --attempt, --variant, --scores')
        do_select(args.clip, args.component, args.attempt, args.variant, args.scores,
                  args.trim_start, args.trim_end, args.batch)
    elif args.fail:
        if not all([args.clip, args.component, args.attempt]):
            parser.error('--fail requires --clip, --component, --attempt')
        do_fail(args.clip, args.component, args.attempt, args.scores)
    elif args.extract_frames:
        if not all([args.clip, args.component, args.attempt]):
            parser.error('--extract-frames requires --clip, --component, --attempt')
        do_extract_frames(args.clip, args.component, args.attempt)
    elif args.status:
        do_status(args.clip)
    elif args.login:
        print('  Opening browser for manual login...')
        print('  1. Log in to Google with your account')
        print('  2. Go to https://labs.google/fx/ru/tools/flow')
        print('  3. Make sure Flow works (try a test generation)')
        print('  4. Close the browser window when done')
        print()
        with sync_playwright() as pw:
            ctx = launch_browser(pw, use_builtin_chromium=args.chromium)
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto('https://accounts.google.com', timeout=60000, wait_until='domcontentloaded')
            print('  Browser open. Log in and close the window when ready.')
            print(f'  URL: {page.url}')
            try:
                # Wait indefinitely until user closes the page
                page.wait_for_timeout(600000)
            except Exception:
                pass
            try:
                ctx.close()
            except Exception:
                pass
        print('  Session saved!')
        sys.exit(0)
    elif args.sync_dashboard:
        do_sync_dashboard(args.clip)
    elif args.chain:
        timeout = GLOBAL_TIMEOUT_SEC
        if timeout > 0:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
            print(f'  Timeout: {timeout}s')
        with sync_playwright() as pw:
            try:
                do_chain(pw, scenes_filter=args.scenes, clip_filter=args.clip, use_builtin_chromium=args.chromium)
            finally:
                signal.alarm(0)
                if _active_context:
                    try: _active_context.close()
                    except Exception: pass
    elif args.phase:
        timeout = GLOBAL_TIMEOUT_SEC
        if timeout > 0:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
            print(f'  Timeout: {timeout}s')
        with sync_playwright() as pw:
            try:
                do_phase(pw, use_builtin_chromium=args.chromium)
            finally:
                signal.alarm(0)
                if _active_context:
                    try: _active_context.close()
                    except Exception: pass
    elif args.generate_location:
        if not args.loc_prompt:
            parser.error('--generate-location requires --loc-prompt')
        if not args.loc_output:
            parser.error('--generate-location requires --loc-output')
        timeout = GLOBAL_TIMEOUT_SEC
        if timeout > 0:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
            print(f'  Timeout: {timeout}s')
        with sync_playwright() as pw:
            try:
                do_generate_location(pw, args.loc_prompt, args.loc_output,
                                     num_variants=args.loc_variants,
                                     project_id=args.project,
                                     use_builtin_chromium=args.chromium)
            finally:
                signal.alarm(0)
                if _active_context:
                    try: _active_context.close()
                    except Exception: pass
    elif args.generate_locations_batch:
        if not args.loc_batch:
            parser.error('--generate-locations-batch requires --loc-batch')
        timeout = GLOBAL_TIMEOUT_SEC
        if timeout > 0:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
            print(f'  Timeout: {timeout}s')
        with sync_playwright() as pw:
            try:
                do_generate_locations_batch(pw, args.loc_batch,
                                            use_builtin_chromium=args.chromium)
            finally:
                signal.alarm(0)
                if _active_context:
                    try: _active_context.close()
                    except Exception: pass
    elif args.generate_refs:
        if not args.project_dir:
            parser.error('--generate-refs requires --project-dir')
        timeout = GLOBAL_TIMEOUT_SEC
        if timeout > 0 and hasattr(signal, 'SIGALRM'):
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
            print(f'  Timeout: {timeout}s')
        else:
            print(f'  Timeout: {timeout}s (no SIGALRM on Windows, using soft timeout)')
        with sync_playwright() as pw:
            try:
                ref_filter_parsed = None
                if args.filter:
                    try:
                        ref_filter_parsed = json.loads(args.filter)
                    except json.JSONDecodeError:
                        print(f'[REF] WARNING: Could not parse --filter JSON, ignoring filter')
                do_generate_refs(pw, args.project_dir,
                                 use_builtin_chromium=args.chromium,
                                 bot_index=args.bot_index,
                                 bot_count=args.bot_count,
                                 ref_filter=ref_filter_parsed)
            finally:
                if hasattr(signal, 'alarm'):
                    signal.alarm(0)
                if _active_context:
                    try: _active_context.close()
                    except Exception: pass
    elif args.review:
        timeout = GLOBAL_TIMEOUT_SEC
        if timeout > 0:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
            print(f'  Timeout: {timeout}s')
        with sync_playwright() as pw:
            try:
                do_review(pw, args.clip, component_filter=args.component, project_id=args.project,
                         use_builtin_chromium=args.chromium)
            finally:
                signal.alarm(0)
                if _active_context:
                    try: _active_context.close()
                    except Exception: pass


if __name__ == '__main__':
    main()
