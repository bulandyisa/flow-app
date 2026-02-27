"""
Flow Bot v2 — Чистая переписка Playwright бота для Google Flow.

Только launch_persistent_context (без CDP).
keyboard.type() для промптов (без execCommand).
~800 строк вместо 4000+.

Использование:
  ./scripts/run_safe.sh --review --clip S01_A --account 1
  ./scripts/run_safe.sh --select --clip S01_A --component nb_first --attempt 1 --variant 0 --batch a --scores '{"char_face":9,...}'
  ./scripts/run_safe.sh --fail --clip S01_A --component nb_first --attempt 1
  ./scripts/run_safe.sh --status
  ./scripts/run_safe.sh --extract-frames --clip S01_A --component veo --attempt 1
"""

import argparse
import base64
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


# ── Constants ────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_PATH = PROJECT_ROOT / 'output' / 'prompts' / 'all_prompts.json'
OUTPUT_DIR   = PROJECT_ROOT / 'output'
FRAMES_DIR   = OUTPUT_DIR / 'frames'
CLIPS_DIR    = OUTPUT_DIR / 'clips'
REVIEW_DIR   = OUTPUT_DIR / 'review'
SCREENSHOTS_DIR = OUTPUT_DIR / 'screenshots'
REFS_DIR     = PROJECT_ROOT

FLOW_URL = 'https://labs.google/fx/ru/tools/flow'

ACCOUNTS = [
    # Bot 1 — EduBoom profile + 2026genvid Flow account
    {'session_dir': PROJECT_ROOT / '.session', 'project_url': None},
    # Bot 2-4 — будут добавлены позже
]

_current_account_idx = 0
_active_context = None

GLOBAL_TIMEOUT_SEC = int(os.environ.get('FLOW_TIMEOUT', 1200))
QUALITY_THRESHOLD = 9.0
CRITICAL_MIN_SCORE = 6
MAX_ATTEMPTS = 5
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
    time.sleep(random.uniform(15, 25))


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

def launch_browser(pw, account=None):
    global _active_context
    acct = ACCOUNTS[account if account is not None else _current_account_idx]
    session_dir = acct['session_dir']
    session_dir.mkdir(parents=True, exist_ok=True)
    for f in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'):
        p = session_dir / f
        if p.exists(): p.unlink()
    vp_w = 1440 + random.randint(-20, 20)
    vp_h = 900 + random.randint(-15, 15)
    print(f'  Account {(account if account is not None else _current_account_idx)}, session: {session_dir.name}, viewport: {vp_w}x{vp_h}')
    ctx = pw.chromium.launch_persistent_context(
        str(session_dir),
        headless=False,
        channel='chrome',
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
    ctx.add_init_script(STEALTH_JS)
    _active_context = ctx
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


def ensure_project(page):
    """Navigate to Flow and enter a project."""
    print(f'  Opening Flow...')
    page.goto(FLOW_URL, timeout=120000, wait_until='domcontentloaded')
    human_delay_long(5, 8)
    for _ in range(3):
        dismiss_popups(page)
        page.keyboard.press('Escape')
        human_delay(0.5, 1.0)

    # If already in a project, done
    if '/project/' in page.url:
        print(f'  In project: {page.url[-50:]}')
        return

    # On main page — click first project to enter it
    print(f'  On main page, entering a project...')
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
    """Open settings popup via Playwright click (NOT JS click — React needs real events)."""
    # Try chip in bottom bar (last match = bottom bar, not inside popup)
    for label in ['Nano Banana', 'Imagen', 'Veo', 'Видео']:
        matches = page.locator(f'button:has-text("{label}")').all()
        # Pick the one in bottom bar (highest y coordinate)
        best = None
        best_y = -1
        for m in matches:
            box = m.bounding_box()
            if box and box['width'] > 30 and box['y'] > best_y:
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
        for (const tab of document.querySelectorAll('button[role="tab"]')) {
            const t = (tab.textContent||'').trim();
            if (t.includes(label)) { tab.click(); return true; }
        }
        return false;
    }""", target_label)
    human_delay(0.3, 0.8)
    page.keyboard.press('Escape')
    human_delay(0.3, 0.8)
    print(f'  Orientation: {orientation}')


def switch_mode(page, target):
    """Switch Image / Video / Video+Frames mode via settings popup tabs.

    target: 'Создать изображение' | 'Image' | 'Видео по кадрам' | 'video_frames' | 'Video'
    """
    is_video = 'идео' in target or 'video' in target.lower() or 'Video' in target
    is_frames = 'кадр' in target or 'frames' in target.lower() or 'Frames' in target
    mode = 'Video' if is_video else 'Image'

    if not _open_settings_popup(page):
        print(f'  WARNING: Could not open settings popup for mode switch')
        return

    # Click Image or Video tab (Playwright locator for proper React event handling)
    if is_video:
        tab = page.locator('button[role="tab"]:has-text("Video"), button[role="tab"]:has-text("Видео")').first
    else:
        tab = page.locator('button[role="tab"]:has-text("Image"), button[role="tab"]:has-text("Изображение")').first
    if tab.count() > 0:
        tab.click()
        human_delay(0.5, 1.0)

    # If video + frames, click Frames sub-tab (may need delay for sub-tabs to render)
    if is_video and is_frames:
        for attempt in range(5):
            human_delay(0.5, 1.0)
            frames_tab = page.locator('button[role="tab"]:has-text("Frames"), button[role="tab"]:has-text("Кадры")').first
            if frames_tab.count() > 0:
                frames_tab.click()
                human_delay(0.5, 1.0)
                mode = 'Video+Frames'
                break

    page.keyboard.press('Escape')
    human_delay(0.5, 1.0)
    print(f'  Mode: {mode}')


def set_variant_count(page, count=4):
    """Set variant count (x1-x4) via settings popup. Available for Video mode."""
    if not _open_settings_popup(page):
        return
    tab = page.locator(f'button[role="tab"]:has-text("x{count}")').first
    if tab.count() > 0:
        tab.click()
        human_delay(0.3, 0.8)
    page.keyboard.press('Escape')
    human_delay(0.3, 0.8)
    print(f'  Variants: x{count}')


# ── Ingredients ──────────────────────────────────────────────────────────────

_last_uploaded = None


def _open_media_dialog(page):
    """Click the '+' button in bottom bar to open media library dialog."""
    clicked = page.evaluate("""() => {
        const h = window.innerHeight;
        for (const btn of document.querySelectorAll('button')) {
            const t = btn.textContent.trim();
            const r = btn.getBoundingClientRect();
            // "+" button has text starting with "add" and is small, in bottom bar
            if (t.startsWith('add') && r.y > h * 0.6 && r.width > 15 && r.width < 80) {
                btn.click(); return true;
            }
        }
        return false;
    }""")
    if not clicked:
        take_screenshot(page, 'add_button_missing')
        print('    "+" button not found in bottom bar')
        return False
    # Wait for dialog to appear
    try:
        page.wait_for_selector('[role="dialog"]', timeout=5000)
    except Exception:
        human_delay(1.5, 3)
    human_delay(0.8, 1.5)
    return True


def _find_in_library(page, filename):
    """Search for image by filename in the media library dialog.
    Returns True if found and selected."""
    # Strip extension for matching
    name_no_ext = Path(filename).stem
    found = page.evaluate("""(name) => {
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return false;
        // Look for img with matching alt text or nearby text
        for (const img of dialog.querySelectorAll('img')) {
            const alt = (img.alt || '').toLowerCase();
            const r = img.getBoundingClientRect();
            if (r.width < 20 || r.height < 20) continue;
            if (alt.includes(name.toLowerCase())) {
                // Click the image or its clickable parent
                const clickable = img.closest('button, [role="option"], [role="button"], a') || img;
                clickable.click();
                return true;
            }
        }
        // Also try text-based match
        for (const el of dialog.querySelectorAll('button, [role="option"], [role="listitem"]')) {
            const t = (el.textContent || '').toLowerCase();
            if (t.includes(name.toLowerCase())) {
                const r = el.getBoundingClientRect();
                if (r.width > 30 && r.height > 20) { el.click(); return true; }
            }
        }
        return false;
    }""", name_no_ext)
    return found


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
        human_delay(3, 5)
        return True
    except Exception as e:
        print(f'    File chooser failed: {e}')
        # Fallback: use hidden input[type=file] directly
        file_input = page.query_selector('input[type="file"][accept="image/*"]')
        if file_input:
            file_input.set_input_files(str(fpath))
            print(f'    Uploaded (input): {fpath.name}')
            human_delay(3, 5)
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


def upload_ingredients(page, ingredient_paths):
    """Upload ingredient images via media library dialog."""
    global _last_uploaded
    if not ingredient_paths:
        return 0
    resolved = []
    for rel in ingredient_paths:
        full = REFS_DIR / rel
        if full.exists():
            resolved.append(full)
        else:
            print(f'  WARNING: ingredient not found: {full}')
    if not resolved:
        return 0

    keys = tuple(str(f) for f in resolved)
    if keys == _last_uploaded:
        print(f'  Ingredients cached ({len(resolved)} files)')
        return len(resolved)

    # Clear old ingredients first
    clear_ingredients(page)

    loaded = 0
    for i, fpath in enumerate(resolved):
        print(f'  Loading ingredient {i+1}/{len(resolved)}: {fpath.name}')

        # Step 1: Open media dialog
        if not _open_media_dialog(page):
            continue

        # Step 2: Try to find image in library first
        if _find_in_library(page, fpath.name):
            print(f'    Selected from library: {fpath.name}')
            loaded += 1
            human_delay(2, 4)
            # Dialog may auto-close after selection, but try closing just in case
            _close_media_dialog(page)
            continue

        # Step 3: Upload via file chooser
        if _upload_in_dialog(page, fpath):
            loaded += 1
            # After upload, the dialog may or may not close
            # Wait for the image to process
            human_delay(2, 4)
            _close_media_dialog(page)
            continue

        # Failed
        print(f'    FAILED to upload {fpath.name}')
        _close_media_dialog(page)

    # Final escape to ensure dialog is closed
    page.keyboard.press('Escape')
    human_delay(0.5, 1.0)

    thumb_count = _count_ingredient_thumbs(page)
    print(f'  Loaded {loaded}/{len(resolved)} ingredients. Thumbs visible: {thumb_count}')
    _last_uploaded = keys if loaded == len(resolved) else None
    return loaded


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

    Clicks the slot DIV ("Первый кадр"/"Последний кадр") which opens
    the same media library dialog as ingredients. Then either finds
    the image in library or uploads it.
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

    # Wait for media dialog
    dialog = page.locator('[role="dialog"]')
    try:
        dialog.wait_for(timeout=5000)
    except Exception:
        print(f'  WARNING: Media dialog did not appear for {slot_name} slot')
        return False

    # Try to find image in library by filename
    fname = Path(frame_path).stem  # e.g. "variant_1"
    found = _find_in_library(page, fname)
    if found:
        print(f'  Selected {slot_name} frame from library: {fname}')
    else:
        # Upload via dialog
        uploaded = _upload_in_dialog(page, frame_path)
        if not uploaded:
            print(f'  WARNING: Failed to upload {slot_name} frame')
            page.keyboard.press('Escape')
            return False
        print(f'  Uploaded {slot_name} frame: {Path(frame_path).name}')

    human_delay(2.0, 4.0)

    # Dismiss crop dialog if it appears
    _dismiss_crop_dialog(page)
    human_delay(1.0, 2.0)

    # Close media dialog if still open
    _close_media_dialog(page)
    human_delay(0.5, 1.0)

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
        human_delay(1.5, 3.5)
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
    """Count error cards currently visible in DOM."""
    return page.evaluate("""() => {
        let count = 0;
        for (const el of document.querySelectorAll('*')) {
            const t = (el.textContent||'').trim();
            if ((t.includes('Что-то пошло не так') || t.includes('Не удалось сгенерировать') ||
                 t.includes('Произошла ошибка')) && t.length < 300) {
                const r = el.getBoundingClientRect();
                if (r.width > 100 && r.height > 20 && r.y >= 0 && r.y < window.innerHeight)
                    count++;
            }
        }
        return count;
    }""")


def _check_new_error(page, errors_before):
    """Check if a new error appeared since errors_before count."""
    current = _count_errors(page)
    if current > errors_before:
        # Get the error text
        err = page.evaluate("""() => {
            for (const el of document.querySelectorAll('*')) {
                const t = (el.textContent||'').trim();
                if ((t.includes('Что-то пошло не так') || t.includes('Не удалось сгенерировать') ||
                     t.includes('Произошла ошибка')) && t.length < 300) {
                    const r = el.getBoundingClientRect();
                    if (r.width > 100 && r.height > 20 && r.y >= 0 && r.y < window.innerHeight)
                        return t;
                }
            }
            return null;
        }""")
        if err:
            print(f'    ERROR: {err[:80]}')
            return 'content_filter' if 'Не удалось сгенерировать' in err else 'server_error'
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


def _open_video_fullview(page):
    """Click last video thumbnail in chat to open full view overlay.
    Returns list of video URLs found in the full view, or empty list.
    """
    # Find and click last video thumbnail
    thumb = page.evaluate("""() => {
        const imgs = document.querySelectorAll('img[alt="Значок видео"]');
        if (imgs.length === 0) return null;
        const last = imgs[imgs.length - 1];
        const r = last.getBoundingClientRect();
        if (r.width < 20) return null;
        return {x: r.x + r.width/2, y: r.y + r.height/2};
    }""")
    if not thumb:
        print('    No video thumbnail found to click')
        return []

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
        # Videos can be <video> elements or <img alt="Значок видео"> thumbnails
        return page.evaluate("""() => {
            let count = 0;
            // Count <video> elements
            for (const v of document.querySelectorAll('video')) {
                if (v.src) count++;
            }
            // Count video thumbnails in chat view
            count += document.querySelectorAll('img[alt="Значок видео"]').length;
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
    count_before = _count_generated_media(page, media)
    # Minimum generation time to avoid false positives (VEO ~60-120s, images ~15-25s)
    min_gen_time = 30 if media == 'video' else 5

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
                # Too fast — likely a false positive (old percentages or flicker)
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
                print(f'    New media: {count_before} → {count_after}')
            return 'success'

        # Check for NEW error (not old ones in chat history)
        if elapsed >= 15 and not generating:
            err = _check_new_error(page, errors_before)
            if err:
                return err

        if elapsed % 30 == 0:
            st = ' (generating...)' if generating else ' (waiting for start...)'
            print(f'    Poll... ({elapsed}s{st})')

    print(f'    TIMEOUT after {timeout_sec}s')
    return 'timeout'


# ── Download media ───────────────────────────────────────────────────────────

def download_via_fetch(page, url, save_path):
    result = page.evaluate("""async (url) => {
        try {
            const resp = await fetch(url);
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
        print(f'  Fetch error: {result["error"]}')
        return False
    data = base64.b64decode(result['data'])
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(data)
    print(f'  Saved: {save_path.name} ({len(data)} bytes)')
    return True


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


def download_all_videos(page, dest_dir, expected_count=4):
    """Download all generated videos by opening full view and navigating.
    Returns list of saved file paths.
    """
    _scroll_chat_bottom(page)
    human_delay(1, 2)

    urls = _open_video_fullview(page)
    if not urls:
        _close_fullview(page)
        return []

    # Navigate to collect more URLs if needed
    if len(urls) < expected_count:
        all_urls = _navigate_fullview_and_collect_urls(page, expected_count)
    else:
        all_urls = urls

    _close_fullview(page)

    if not all_urls:
        print('    No video URLs collected')
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for i, url in enumerate(all_urls):
        dest_path = dest_dir / f'variant_{i+1}.mp4'
        if download_via_fetch(page, url, dest_path):
            saved.append(dest_path)
        else:
            print(f'    Failed to download variant_{i+1}')

    print(f'  Downloaded {len(saved)}/{len(all_urls)} videos')
    return saved


# ── Manifest (review state) ─────────────────────────────────────────────────

def load_manifest(clip_id):
    path = REVIEW_DIR / clip_id / 'manifest.json'
    if path.exists():
        with open(path) as f:
            m = json.load(f)
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
    return {
        'clip_id': clip_id,
        'components': {
            c: {'attempts':[], 'selected_variant_a':None, 'selected_variant_b':None, 'status':'pending'}
            for c in ('nb_first','nb_mid','nb_last','veo')
        }
    }


def save_manifest(clip_id, manifest):
    path = REVIEW_DIR / clip_id / 'manifest.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


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
            for slot, ext in [('selected_variant_a', ''), ('selected_variant_b', '_b')]:
                sel = comp.get(slot)
                if not sel: continue
                entry = comp['attempts'][sel['attempt']-1]
                vfile = entry['variants'][sel['variant']]['file']
                src = REVIEW_DIR / clip_id / comp_name / f'attempt_{sel["attempt"]}' / vfile
                if src.exists():
                    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
                    dest = FRAMES_DIR / f'{clip_id}_{suffix}{ext}.png'
                    shutil.copy2(src, dest)
                    print(f'  Copied → {dest.name}')
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
                print(f'  Copied → {dest.name}')


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

def generate_nb_batch(page, clip_id, component, prompt, attempt, ingredients, dest_dir, num_variants=4):
    """Generate N NB variants (1 per generation run). Retries on server error."""
    validate_nb_prompt(prompt, f'{clip_id}/{component}')
    prompt = sanitize_nb_prompt(prompt)
    print(f'\n  --- {component} for {clip_id} (attempt {attempt}) ---')
    print(f'  Prompt: {prompt[:80]}...')
    print(f'  Generating {num_variants} variants (1 per run)...')

    dest_dir.mkdir(parents=True, exist_ok=True)
    all_saved = []

    for var_idx in range(num_variants):
        print(f'\n  Variant {var_idx+1}/{num_variants}:')

        success = False
        for retry in range(3):
            if retry > 0:
                wait = [45, 60][min(retry-1, 1)]
                print(f'    Server error — waiting {wait}s before retry {retry+1}/3...')
                time.sleep(wait + random.uniform(-5, 10))
                page.reload(timeout=120000, wait_until='domcontentloaded')
                wait_for_flow_ready(page)
                switch_mode(page, 'Создать изображение')
                if ingredients:
                    upload_ingredients(page, ingredients)

            clear_prompt(page)
            fill_prompt(page, prompt)
            if var_idx == 0 and retry == 0:
                take_screenshot(page, f'{clip_id}_{component}_a{attempt}_before')

            # Remember state before generation
            urls_before = _get_all_generated_image_urls(page)
            url_before_last = _get_last_generated_image_url(page)
            errors_before = _count_errors(page)

            click_generate(page)
            result = poll_generation(page, errors_before=errors_before)

            if result == 'success':
                dest_path = dest_dir / f'variant_{var_idx+1}.png'
                # Wait for new image URL to appear in DOM
                new_url = None
                for _wait in range(10):
                    time.sleep(1.5)
                    urls_after = _get_all_generated_image_urls(page)
                    new_urls = urls_after - urls_before
                    if new_urls:
                        new_url = list(new_urls)[0]
                        break
                    # Also check if last image changed
                    url_after_last = _get_last_generated_image_url(page)
                    if url_after_last and url_after_last != url_before_last:
                        new_url = url_after_last
                        break

                if new_url:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    if download_via_fetch(page, new_url, dest_path):
                        all_saved.append(dest_path)
                        print(f'    Saved variant_{var_idx+1}.png')
                    else:
                        print(f'    Download failed for variant_{var_idx+1}')
                else:
                    # Fallback: download whatever is last
                    saved = download_last_image(page, dest_path)
                    if saved:
                        all_saved.append(saved)
                        print(f'    Saved variant_{var_idx+1}.png (fallback)')
                success = True
                break
            if result == 'content_filter':
                print('    Content filter — skipping variant')
                break
            print(f'    FAILED ({result}, retry {retry+1}/3)')

        if success and var_idx < num_variants - 1:
            # Pause between generations to avoid rate limit
            pause = random.uniform(8, 15)
            print(f'    Pause {pause:.0f}s...')
            time.sleep(pause)

    print(f'  Downloaded {len(all_saved)}/{num_variants} variants')
    return all_saved


# ── Review mode ──────────────────────────────────────────────────────────────

def review_nano_banana(page, clip, manifest, component, attempt, prompt_override=None, first_frame_ref=None):
    clip_id = clip['clip_id']
    prompt_key = {'nb_first':'nano_banana_prompt_first', 'nb_mid':'nano_banana_prompt_mid',
                  'nb_last':'nano_banana_prompt_last'}[component]
    prompt_a = prompt_override or clip[prompt_key]
    prompt_b = clip.get(prompt_key + '_b') if not prompt_override else None
    has_b = prompt_b is not None
    ingredients = list(clip.get('nano_banana_ingredients', []))

    print(f'\n{"="*60}')
    print(f'  REVIEW — {component} {"A+B" if has_b else ""} — {clip_id} — attempt {attempt}')
    print(f'{"="*60}')

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
            ref_suffix = f' Maintain exact visual continuity with Image {ref_num}.'

    prompt_a_full = prompt_a + ref_suffix
    prompt_b_full = (prompt_b + ref_suffix) if has_b else None

    uploaded = upload_ingredients(page, ingredients)
    if uploaded == 0 and any('персонаж' in str(p).lower() for p in ingredients):
        print('  FAILED: no character refs uploaded')
        return []

    attempt_dir = REVIEW_DIR / clip_id / component / f'attempt_{attempt}'
    dest_a = (attempt_dir / 'prompt_a') if has_b else attempt_dir
    variants_a = generate_nb_batch(page, clip_id, component, prompt_a_full, attempt, ingredients, dest_a)

    variants_b = []
    if has_b and prompt_b_full:
        if variants_a:
            print('  Pausing between A/B batches...')
            human_pause_between_generations()
        variants_b = generate_nb_batch(page, clip_id, component, prompt_b_full, attempt, ingredients,
                                       attempt_dir / 'prompt_b')

    all_v = variants_a + variants_b
    record_attempt(manifest, component, attempt, prompt_a_full, all_v,
                   prompt_b=prompt_b_full, batch_a_count=len(variants_a),
                   batch_b_count=len(variants_b) if has_b else None)
    save_manifest(clip_id, manifest)
    if has_b:
        print(f'  TOTAL: {len(all_v)} variants (A={len(variants_a)}, B={len(variants_b)})')
    return all_v


def review_veo_batch(page, clip, clip_id, prompt, first_frame, last_frame, attempt, batch_label, dest_dir, veo_mode='frames', num_variants=4):
    print(f'\n  --- VEO {batch_label} for {clip_id} (x{num_variants}) ---')
    validate_veo_prompt(prompt, f'{clip_id}/veo_{batch_label}')

    # Switch to Video+Frames mode (stay in same project — previously generated images are in library)
    switch_mode(page, 'Видео по кадрам')
    human_delay_long(2, 4)

    # Set variant count
    set_variant_count(page, num_variants)

    # Upload first/last frames to VEO slots
    if first_frame and Path(first_frame).exists() and last_frame and Path(last_frame).exists():
        clear_veo_frame_slots(page)
        upload_frame_for_veo(page, first_frame, 0)
        upload_frame_for_veo(page, last_frame, 1)
    elif first_frame and Path(first_frame).exists():
        clear_veo_frame_slots(page)
        upload_frame_for_veo(page, first_frame, 0)

    clear_prompt(page)
    fill_prompt(page, prompt)
    errors_before = _count_errors(page)
    click_generate(page)
    result = poll_generation(page, errors_before=errors_before, timeout_sec=GENERATION_TIMEOUT, media='video')
    if result != 'success':
        print(f'  VEO {batch_label} FAILED ({result})')
        return []

    # Download all generated videos via full view navigation
    saved = download_all_videos(page, dest_dir, expected_count=num_variants)
    if saved:
        print(f'  Downloaded {len(saved)} video(s) for {batch_label}')
    else:
        # Fallback: try single video download
        dest_path = dest_dir / 'variant_1.mp4'
        dl = download_last_video(page, dest_path)
        if dl:
            saved = [dl]
            print(f'  Downloaded 1 video (fallback) for {batch_label}')
    return saved


def review_veo(page, clip, manifest, attempt, first_frame, last_frame, prompt_override=None,
               veo_mode='frames', first_frame_b=None, last_frame_b=None):
    clip_id = clip['clip_id']
    prompt_a = sanitize_prompt(prompt_override or clip['veo_prompt'])
    prompt_b = sanitize_prompt(clip.get('veo_prompt_b', clip['veo_prompt']))
    dest_dir = REVIEW_DIR / clip_id / 'veo' / f'attempt_{attempt}'

    saved_a = review_veo_batch(page, clip, clip_id, prompt_a, first_frame, last_frame,
                               attempt, 'prompt_a', dest_dir / 'prompt_a', veo_mode)
    if saved_a:
        human_pause_between_generations()
    eff_first_b = first_frame_b if first_frame_b and first_frame_b.exists() else first_frame
    eff_last_b = last_frame_b if last_frame_b and last_frame_b.exists() else last_frame
    saved_b = review_veo_batch(page, clip, clip_id, prompt_b, eff_first_b, eff_last_b,
                               attempt, 'prompt_b', dest_dir / 'prompt_b', veo_mode)

    all_saved = saved_a + saved_b
    record_attempt(manifest, 'veo', attempt, f'A: {prompt_a}\n---\nB: {prompt_b}', all_saved,
                   prompt_b=prompt_b, batch_a_count=len(saved_a), batch_b_count=len(saved_b))
    save_manifest(clip_id, manifest)
    print(f'  VEO TOTAL: {len(all_saved)} videos (A={len(saved_a)}, B={len(saved_b)})')
    return all_saved


# ── CLI Commands ─────────────────────────────────────────────────────────────

def load_clips(clip_filter=None):
    with open(PROMPTS_PATH) as f:
        clips = json.load(f)
    if clip_filter:
        clips = [c for c in clips if c['clip_id'] == clip_filter]
        if not clips:
            print(f'Error: clip "{clip_filter}" not found')
            sys.exit(1)
    return clips


def find_scene_ref(current_clip_id):
    """Find accepted first frame from a previous clip in same scene."""
    with open(PROMPTS_PATH) as f:
        all_clips = json.load(f)
    scene = next((c['scene_id'] for c in all_clips if c['clip_id'] == current_clip_id), None)
    if not scene: return None
    for c in all_clips:
        if c['scene_id'] != scene: continue
        if c['clip_id'] == current_clip_id: break
        frame = FRAMES_DIR / f'{c["clip_id"]}_first.png'
        if frame.exists(): return frame
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


def do_review(pw, clip_filter=None):
    clips = load_clips(clip_filter)
    print(f'Review mode: {len(clips)} clips.\n')

    ctx = launch_browser(pw)
    print('  Launched browser.')
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    print(f'  Page ready, navigating to project...')
    ensure_project(page)
    wait_for_flow_ready(page)

    summary = {'generated': [], 'skipped': [], 'failed': []}

    for i, clip in enumerate(clips):
        clip_id = clip['clip_id']
        print(f'\n[{i+1}/{len(clips)}] Review: {clip_id}')
        manifest = load_manifest(clip_id)

        for component in ('nb_first', 'nb_mid', 'nb_last'):
            if component == 'nb_mid' and not clip.get('nano_banana_prompt_mid'):
                continue
            status = manifest['components'][component].get('status', 'pending')
            if status in ('accepted', 'needs_manual_work'):
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
        veo_status = manifest['components']['veo'].get('status', 'pending')
        if veo_status in ('accepted', 'needs_manual_work'):
            summary['skipped'].append(f'{clip_id}/veo')
        else:
            first_sel = manifest['components']['nb_first'].get('selected_variant_a')
            last_sel = manifest['components']['nb_last'].get('selected_variant_a')
            if first_sel and last_sel:
                fe = manifest['components']['nb_first']['attempts'][first_sel['attempt']-1]
                le = manifest['components']['nb_last']['attempts'][last_sel['attempt']-1]
                fp = REVIEW_DIR / clip_id / 'nb_first' / f'attempt_{first_sel["attempt"]}' / fe['variants'][first_sel['variant']]['file']
                lp = REVIEW_DIR / clip_id / 'nb_last' / f'attempt_{last_sel["attempt"]}' / le['variants'][last_sel['variant']]['file']
                if fp.exists() and lp.exists():
                    attempt = get_next_attempt(manifest, 'veo')
                    if attempt > 0:
                        human_pause_between_generations()
                        # Resolve B frames
                        fp_b = lp_b = None
                        for slot_comp, slot_var in [('nb_first', 'fp_b'), ('nb_last', 'lp_b')]:
                            sel_b = manifest['components'][slot_comp].get('selected_variant_b')
                            if sel_b:
                                be = manifest['components'][slot_comp]['attempts'][sel_b['attempt']-1]
                                bp = REVIEW_DIR / clip_id / slot_comp / f'attempt_{sel_b["attempt"]}' / be['variants'][sel_b['variant']]['file']
                                if bp.exists():
                                    if slot_var == 'fp_b': fp_b = bp
                                    else: lp_b = bp
                        variants = review_veo(page, clip, manifest, attempt, fp, lp,
                                              veo_mode=clip.get('veo_mode','frames'),
                                              first_frame_b=fp_b, last_frame_b=lp_b)
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
    else:
        save_manifest(clip_id, manifest)
        print(f'  BELOW THRESHOLD ({avg:.2f} < {QUALITY_THRESHOLD})')


def do_fail(clip_id, component, attempt, scores_json=None):
    manifest = load_manifest(clip_id)
    scores = json.loads(scores_json) if scores_json else None
    mark_failed(manifest, component, attempt, scores)
    save_manifest(clip_id, manifest)
    print(f'  {clip_id}/{component} attempt {attempt} marked failed')


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
        print(f'  variant_{i+1}: {dur:.1f}s → {frames_dir.name}')
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


# ── Main ─────────────────────────────────────────────────────────────────────

def _timeout_handler(signum, frame):
    print(f'\n  GLOBAL TIMEOUT ({GLOBAL_TIMEOUT_SEC}s) — exiting!')
    if _active_context:
        try: _active_context.close()
        except Exception: pass
    sys.exit(42)


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

    parser.add_argument('--clip', type=str, default=None)
    parser.add_argument('--component', type=str, default=None, choices=['nb_first','nb_mid','nb_last','veo'])
    parser.add_argument('--attempt', type=int, default=None)
    parser.add_argument('--variant', type=int, default=None)
    parser.add_argument('--scores', type=str, default=None)
    parser.add_argument('--trim-start', type=float, default=None)
    parser.add_argument('--trim-end', type=float, default=None)
    parser.add_argument('--batch', type=str, default='a', choices=['a','b'])
    parser.add_argument('--account', type=int, default=1, choices=range(1, len(ACCOUNTS)+1))

    args = parser.parse_args()
    _current_account_idx = args.account - 1

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
            ctx = launch_browser(pw)
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
    elif args.review:
        timeout = GLOBAL_TIMEOUT_SEC
        if timeout > 0:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
            print(f'  Timeout: {timeout}s')
        with sync_playwright() as pw:
            try:
                do_review(pw, args.clip)
            finally:
                signal.alarm(0)
                if _active_context:
                    try: _active_context.close()
                    except Exception: pass


if __name__ == '__main__':
    main()
