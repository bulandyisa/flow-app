# Source Generated with Decompyle++
# File: flow_bot.cpython-312.pyc (Python 3.12)

'''
Модуль 4: Playwright бот для Google Flow

Трёхпроходная автоматизация:
  Проход 1 — Nano Banana Pro: генерация ПЕРВОГО кадра (начальная позиция)
  Проход 2 — Nano Banana Pro: генерация ПОСЛЕДНЕГО кадра (конечная позиция)
  Проход 3 — VEO 3.1: анимация First Frame + Last Frame → видеоклип

Использование:
  # Первый запуск — откроет браузер для логина в Google:
  python scripts/flow_bot.py --login

  # Генерация клипов из промптов (быстрый режим, скачивает только последний вариант):
  python scripts/flow_bot.py --run [--clip S02_A]

  # Генерация с проверкой качества (скачивает ВСЕ варианты для ревью):
  python scripts/flow_bot.py --review [--clip S02_A]

  # Статус ревью:
  python scripts/flow_bot.py --status [--clip S02_A]

  # Принять вариант (оценки JSON: char, comp, loc, anim, artifacts, overall, style):
  python scripts/flow_bot.py --select --clip S02_A --component nb_first --attempt 1 --variant 0 \\
      --scores \'{"char":8,"comp":7,"loc":8,"anim":0,"artifacts":9,"overall":8,"style":7}\'

  # Принять VEO-вариант с обрезкой (лучший сегмент):
  python scripts/flow_bot.py --select --clip S02_A --component veo --attempt 1 --variant 0 \\
      --scores \'{"char":8,...}\' --trim-start 1.0 --trim-end 6.0

  # Извлечь кадры из видео-вариантов для анализа:
  python scripts/flow_bot.py --extract-frames --clip S02_A --component veo --attempt 1

  # Отклонить все варианты попытки:
  python scripts/flow_bot.py --fail --clip S02_A --component nb_first --attempt 1

  # Записать новый промпт для повторной генерации (попытка 3):
  python scripts/flow_bot.py --rewrite --clip S02_A --component nb_first --prompt "new prompt..."

  # Сборка сцены в Scene Builder:
  python scripts/flow_bot.py --scene

  # Авто-очистка: после принятия всех 3 компонентов клипа, review-папка
  # автоматически очищается, лог пишется в output/review/cleanup_log.txt
'''
import argparse
import base64
import json
import os
import random
import signal
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, BrowserContext, Page


class GlobalTimeoutError(Exception):
    """Raised when global operation timeout is reached."""
    pass


# Global reference to browser context for cleanup on timeout
_active_context = None
_active_pw = None

GLOBAL_TIMEOUT_SEC = int(os.environ.get('FLOW_TIMEOUT', 600))  # default 10 min


def _global_timeout_handler(signum, frame):
    """Handle SIGALRM — global timeout reached, force cleanup and exit."""
    print(f'\n\n{"="*60}')
    print(f'  GLOBAL TIMEOUT ({GLOBAL_TIMEOUT_SEC}s) — принудительное завершение!')
    print(f'  Закрываю браузер и выхожу...')
    print(f'{"="*60}\n')
    # Try to close browser gracefully
    if _active_context:
        try:
            _active_context.close()
        except Exception:
            pass
    sys.exit(42)  # exit code 42 = timeout

def human_delay(min_s=0.3, max_s=0.8):
    '''Short random delay for micro-interactions (clicks, UI response waits).'''
    base = random.uniform(min_s, max_s)
    if random.random() < 0.1:
        base += random.uniform(0.5, 1.5)
    time.sleep(base)


def human_delay_medium(min_s=1.5, max_s=3.5):
    '''Medium delay for context switches (tab change, panel load).'''
    time.sleep(random.uniform(min_s, max_s))


def human_delay_long(min_s=4.0, max_s=8.0):
    '''Long delay for heavy operations (page reload, settings panel).'''
    time.sleep(random.uniform(min_s, max_s))


def human_pause_between_generations():
    '''Pause between generations (replaces fixed 45s PAUSE_BETWEEN_GENERATIONS).'''
    base = random.uniform(35, 55)
    if random.random() < 0.15:
        base += random.uniform(10, 30)
    time.sleep(base)


def random_mouse_jitter(page):
    '''Small random mouse movement to simulate a live user.'''
    try:
        vp = page.viewport_size
        if not vp:
            return
        x = random.uniform(vp['width'] * 0.1, vp['width'] * 0.9)
        y = random.uniform(vp['height'] * 0.1, vp['height'] * 0.8)
        page.mouse.move(x, y, steps=random.randint(10, 30))
    except Exception:
        pass


def maybe_idle_movement(page, probability=0.3):
    '''With given probability, do a random mouse jitter during a wait.'''
    if random.random() < probability:
        random_mouse_jitter(page)
        human_delay(0.2, 0.6)


def human_click(page=None, selector_or_element=None, timeout=10000):
    '''Click with human-like mouse movement, random offset, and delay.'''
    human_delay(0.1, 0.4)
    if isinstance(selector_or_element, str):
        el = page.wait_for_selector(selector_or_element, timeout=timeout)
    else:
        el = selector_or_element
    if el:
        box = el.bounding_box()
        if box:
            x = box['x'] + box['width'] * random.uniform(0.25, 0.75)
            y = box['y'] + box['height'] * random.uniform(0.25, 0.75)
            page.mouse.move(x, y, steps=random.randint(8, 25))
            human_delay(0.03, 0.12)
            page.mouse.click(x, y)
        else:
            el.click()
    human_delay(0.08, 0.3)


def human_type(page, element, text):
    '''Type text character-by-character with human-like delays.'''
    human_click(page, element)
    base_min, base_max = (0.02, 0.05) if len(text) > 100 else (0.03, 0.08)
    for char in text:
        delay = random.uniform(base_min, base_max)
        if char in '.,:;!?':
            delay += random.uniform(0.1, 0.3)
        if char == ' ':
            delay += random.uniform(0.0, 0.05)
        if random.random() < 0.02:
            delay += random.uniform(0.3, 0.8)
        page.keyboard.type(char, delay=0)
        time.sleep(delay)


def human_clear_field(page, element):
    '''Clear a text field like a human: Cmd+A, Delete.'''
    human_click(page, element)
    modifier = 'Meta' if sys.platform == 'darwin' else 'Control'
    page.keyboard.press(f'{modifier}+a')
    human_delay(0.05, 0.15)
    page.keyboard.press('Delete')
    human_delay(0.1, 0.3)

STEALTH_JS = "\n// Hide webdriver property\nObject.defineProperty(navigator, 'webdriver', {get: () => undefined});\n\n// Mock chrome.runtime to look like a real Chrome\nif (!window.chrome) { window.chrome = {}; }\nif (!window.chrome.runtime) {\n    window.chrome.runtime = {\n        connect: function() {},\n        sendMessage: function() {},\n    };\n}\n\n// Override permissions query to hide automation\nconst originalQuery = window.navigator.permissions.query;\nwindow.navigator.permissions.query = (parameters) =>\n    parameters.name === 'notifications'\n        ? Promise.resolve({state: Notification.permission})\n        : originalQuery(parameters);\n\n// Realistic plugins array\nObject.defineProperty(navigator, 'plugins', {\n    get: () => {\n        const plugins = [\n            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},\n            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},\n            {name: 'Native Client', filename: 'internal-nacl-plugin'},\n        ];\n        plugins.length = 3;\n        return plugins;\n    }\n});\n\n// Realistic languages\nObject.defineProperty(navigator, 'languages', {\n    get: () => ['ru-RU', 'ru', 'en-US', 'en']\n});\n"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / '.session'
PROMPTS_PATH = PROJECT_ROOT / 'output' / 'prompts' / 'all_prompts.json'
REFS_DIR = PROJECT_ROOT
OUTPUT_DIR = PROJECT_ROOT / 'output'
FRAMES_DIR = OUTPUT_DIR / 'frames'
CLIPS_DIR = OUTPUT_DIR / 'clips'
SCREENSHOTS_DIR = OUTPUT_DIR / 'screenshots'
REVIEW_DIR = OUTPUT_DIR / 'review'
FLOW_URL = 'https://labs.google/fx/ru/tools/flow'
FLOW_PROJECT_URL = 'https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869'
ACCOUNTS = [
    {
        'session_dir': PROJECT_ROOT / '.session',
        'project_url': FLOW_PROJECT_URL },
    {
        'session_dir': PROJECT_ROOT / '.session_2',
        'project_url': 'https://labs.google/fx/ru/tools/flow/project/492b843c-217a-4c83-8c2d-4e0b0f0b1dc8' }]
_current_account_idx = 0
PAUSE_BETWEEN_GENERATIONS = 45
PAGE_LOAD_TIMEOUT = 60000
GENERATION_TIMEOUT = 300
POLL_INTERVAL = 5
SCORE_CRITERIA = [
    'char',
    'comp',
    'loc',
    'anim',
    'artifacts',
    'overall',
    'style']
SCORE_THRESHOLD = 9
MAX_ATTEMPTS = 3
CLEANUP_LOG_PATH = OUTPUT_DIR / 'review' / 'cleanup_log.txt'
import re as _re

def sanitize_prompt(prompt = None):
    '''Sanitize prompt per VEO_SAFETY_GUIDE.md rules.

    - Remove age mentions (e.g. "7-year-old", "15yo")
    - Replace trigger words
    - Ensure \'3D Pixar-style animation\' is present
    - Add \'no subtitles\' if missing
    '''
    p = prompt
    p = _re.sub('\\b\\d{1,2}-year-old\\b', 'animated', p)
    p = _re.sub('\\b\\d{1,2}yo\\b', 'animated', p)
    trigger_map = {
        'abandoned': 'old unused',
        'dark warehouse': 'dimly lit storage building',
        'dark alley': 'dimly lit street',
        'fight': 'disagreement',
        'weapon': '',
        'blood': '',
        'steal': 'take',
        'stolen': 'hidden',
        'villain': 'rival',
        'criminal': 'troublemaker' }
    for old, new in trigger_map.items():
        p = _re.sub(_re.escape(old), new, p, flags = _re.IGNORECASE)
    if '3D Pixar' not in p and 'Pixar-style' not in p:
        p = p.rstrip('. ') + '. 3D Pixar-style animation, family-friendly.'
    if 'no subtitle' not in p.lower():
        p = p.rstrip('. ') + '. No subtitles.'
    return p


def get_video_duration(video_path = None):
    '''Get video duration in seconds using ffprobe.'''
    result = subprocess.run([
        'ffprobe',
        '-v',
        'quiet',
        '-print_format',
        'json',
        '-show_format',
        str(video_path)], capture_output = True, text = True)
    if result.returncode != 0:
        print(f'''  ffprobe error: {result.stderr[:200]}''')
        return 0
    info = json.loads(result.stdout)
    return float(info.get('format', { }).get('duration', 0))


def extract_frames(video_path = None, dest_dir = None, fps = None):
    '''Extract frames from video at given fps using ffmpeg.

    Returns list of extracted frame file paths.
    '''
    dest_dir.mkdir(parents = True, exist_ok = True)
    pattern = str(dest_dir / 'frame_%03d.png')
    result = subprocess.run([
        'ffmpeg',
        '-y',
        '-i',
        str(video_path),
        '-vf',
        f'''fps={fps}''',
        pattern], capture_output = True, text = True)
    if result.returncode != 0:
        print(f'''  ffmpeg extract error: {result.stderr[:200]}''')
        return []
    frames = sorted(dest_dir.glob('frame_*.png'))
    print(f'''  Extracted {len(frames)} frames from {video_path.name}''')
    return frames


def trim_video(video_path = None, start_sec = None, end_sec = None, output_path = None):
    '''Trim video from start_sec to end_sec using ffmpeg.

    Returns True on success.
    '''
    duration = end_sec - start_sec
    if duration <= 0:
        print(f'''  ERROR: invalid trim range {start_sec}–{end_sec}''')
        return False
    output_path.parent.mkdir(parents = True, exist_ok = True)
    result = subprocess.run([
        'ffmpeg',
        '-y',
        '-ss',
        f'''{start_sec:.2f}''',
        '-i',
        str(video_path),
        '-t',
        f'''{duration:.2f}''',
        '-c:v',
        'libx264',
        '-preset',
        'medium',
        '-crf',
        '18',
        '-c:a',
        'aac',
        '-b:a',
        '128k',
        '-pix_fmt',
        'yuv420p',
        '-movflags',
        '+faststart',
        str(output_path)], capture_output = True, text = True)
    if result.returncode != 0:
        print(f'''  ffmpeg trim error: {result.stderr[:200]}''')
        return False
    size = output_path.stat().st_size
    print(f'''  Trimmed {video_path.name} [{start_sec:.1f}s–{end_sec:.1f}s] → {output_path.name} ({size} bytes)''')
    return True


def ensure_dirs():
    """Create output directories if they don't exist."""
    SESSION_DIR.mkdir(parents = True, exist_ok = True)
    FRAMES_DIR.mkdir(parents = True, exist_ok = True)
    CLIPS_DIR.mkdir(parents = True, exist_ok = True)
    SCREENSHOTS_DIR.mkdir(parents = True, exist_ok = True)
    REVIEW_DIR.mkdir(parents = True, exist_ok = True)
    (OUTPUT_DIR / 'scene').mkdir(parents = True, exist_ok = True)


def launch_browser(pw = None, headless = None, account = None):
    '''Launch Chromium with persistent context (saves cookies/session).

    account: 0-based index into ACCOUNTS list. None uses _current_account_idx.
    '''
    acct = ACCOUNTS[account if account is not None else _current_account_idx]
    session_dir = acct['session_dir']
    session_dir.mkdir(parents=True, exist_ok=True)
    # Remove stale lock files from previous crashed sessions
    for lock_file in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'):
        lock_path = session_dir / lock_file
        if lock_path.exists():
            lock_path.unlink()
    vp_w = 1440
    vp_h = 900
    print(f'  Using account {account if account is not None else _current_account_idx} (session: {session_dir.name})')
    ctx = pw.chromium.launch_persistent_context(
        str(session_dir),
        headless=headless,
        viewport={'width': vp_w, 'height': vp_h},
        locale='ru-RU',
        args=[
            '--disable-blink-features=AutomationControlled',
            '--no-first-run',
            '--no-default-browser-check',
        ],
    )
    ctx.add_init_script(STEALTH_JS)
    global _active_context
    _active_context = ctx
    return ctx


def get_project_url(account = None):
    '''Get project URL for the current (or specified) account.'''
    idx = account if account is not None else _current_account_idx
    return ACCOUNTS[idx]['project_url']


def wait_for_flow_ready(page = None):
    '''Wait until the Flow interface is loaded (textarea visible).'''
    page.wait_for_load_state('domcontentloaded', timeout = PAGE_LOAD_TIMEOUT)
    page.wait_for_selector('textarea', timeout = PAGE_LOAD_TIMEOUT)
    human_delay_long(2.5, 5.0)
    print('  Flow workspace ready.')


def take_debug_screenshot(page = None, name = None):
    '''Save a debug screenshot.'''
    try:
        path = SCREENSHOTS_DIR / f'''{name}.png'''
        page.screenshot(path = str(path))
        print(f'''  Screenshot: {path.name}''')
    except Exception:
        pass


def get_current_mode(page = None):
    '''Read current mode from the combobox button text.'''
    combo = page.query_selector('button[role="combobox"]')
    if combo:
        if not combo.text_content():
            combo.text_content()
        return ''.replace('arrow_drop_down', '').strip()


def switch_mode(page = None, mode_text = None):
    '''Switch the mode dropdown to the given option text.

    mode_text examples:
      "Создать изображение"   — image generation (Nano Banana)
      "Видео по кадрам"       — frames to video (VEO)
    '''
    current = get_current_mode(page)
    if mode_text in current:
        print(f'''  Mode already set: {mode_text}''')
        return None
    print(f'''  Switching mode → {mode_text}''')
    combo = None
    for _wait in range(10):
        combo = page.query_selector('button[role="combobox"]')
        if combo:
            break
        else:
            human_delay_medium(1.5, 3.5)
    if not combo:
        raise RuntimeError('Mode combobox not found after 20s wait')
    human_click(page, combo)
    human_delay(0.8, 1.8)
    option = page.query_selector(f'''div[role="option"]:has-text("{mode_text}")''')
    if not option:
        page.keyboard.press('Escape')
        raise RuntimeError(f'''Mode option \'{mode_text}\' not found in dropdown''')
    human_click(page, option)
    human_delay_medium(1.5, 3.5)
    new_mode = get_current_mode(page)
    print(f'''  Mode is now: {new_mode}''')


def clear_prompt(page = None):
    '''Clear the textarea prompt.'''
    textarea = page.query_selector('textarea')
    if textarea:
        human_clear_field(page, textarea)
        human_delay(0.2, 0.5)
        return None


def fill_prompt(page = None, text = None):
    '''Fill the textarea with prompt text.'''
    textarea = page.query_selector('textarea')
    if not textarea:
        raise RuntimeError('Textarea not found')
    maybe_idle_movement(page)
    human_type(page, textarea, text)
    human_delay(0.3, 0.8)


def dismiss_error_dialog(page = None):
    '''Dismiss any error dialog on the page. Returns True if dismissed.'''
    close_btn = page.query_selector('button:has-text("Закрыть")')
    if close_btn:
        box = close_btn.bounding_box()
        if box and box['width'] > 0:
            human_click(page, close_btn)
            print('  Dismissed error dialog.')
            human_delay(0.8, 1.8)
            return True
    return False


def ensure_enhance_prompt_off(page = None):
    """Ensure 'Enhance prompt' toggle is OFF (VEO Safety Guide rule).

    The toggle might be labeled 'Расширить промт' or have a switch/checkbox.
    """
    for selector in ('button[aria-label*="nhance"]', 'button[aria-label*="асшир"]', 'input[type="checkbox"][aria-label*="nhance"]', 'div[role="switch"]'):
        el = page.query_selector(selector)
        if not el:
            continue
        if not el.get_attribute('aria-checked'):
            el.get_attribute('aria-checked')
        checked = el.get_attribute('aria-pressed')
        if not checked == 'true':
            continue
        human_click(page, el)
        print("  Disabled 'Enhance prompt' toggle.")
        human_delay(0.8, 1.8)
        ('button[aria-label*="nhance"]', 'button[aria-label*="асшир"]', 'input[type="checkbox"][aria-label*="nhance"]', 'div[role="switch"]')
        return None
    toggles = page.query_selector_all('button[role="switch"], div[role="switch"]')
    for t in toggles:
        if not t.text_content():
            t.text_content()
        text = ''.strip().lower()
        if not 'enhance' in text and 'расшир' in text and 'улучш' in text:
            continue
        checked = t.get_attribute('aria-checked')
        if not checked == 'true':
            continue
        human_click(page, t)
        print("  Disabled 'Enhance prompt' toggle.")
        human_delay(0.8, 1.8)
        toggles
        return None


def set_variant_count(page = None, count = None):
    """Set the number of generation variants via Settings panel.

    Opens Settings (Настройки), clicks the 'Результатов на запрос' dropdown,
    and selects the desired count (e.g. 4).
    """
    try:
        settings_btn = page.locator('button:has-text("Настройки"), button:has-text("настройки")')
        if settings_btn.count() > 0:
            human_click(page, settings_btn.first)
        else:
            tune_btns = page.locator('button').filter(has_text = 'tune')
            found = False
            for i in range(tune_btns.count()):
                box = tune_btns.nth(i).bounding_box()
                if not box:
                    continue
                if not box['y'] > 400:
                    continue
                human_click(page, tune_btns.nth(i))
                found = True
                break
            if not found:
                print('  WARNING: Settings button not found — variant count unchanged')
                return None
    except Exception as e:
        print(f'  WARNING: Cannot open Settings panel: {e}')
        return None
    print('  Opened Settings panel')
    human_delay(0.8, 1.8)
    result = page.evaluate('(targetCount) => {\n        // First, find the "Результатов" label to get its Y position\n        const allEls = [...document.querySelectorAll(\'*\')];\n        let labelY = null;\n        for (const el of allEls) {\n            // Match the smallest element containing the label text\n            const text = el.textContent.trim();\n            if (text === \'Результатов на запрос\' || text === \'Results per request\') {\n                labelY = el.getBoundingClientRect().y;\n                break;\n            }\n        }\n        if (labelY === null) {\n            // Try partial match for smaller elements\n            for (const el of allEls) {\n                const text = el.textContent.trim();\n                if (text.includes(\'Результатов\') && text.length < 30) {\n                    labelY = el.getBoundingClientRect().y;\n                    break;\n                }\n            }\n        }\n        if (labelY === null) return {error: \'Label "Результатов на запрос" not found\'};\n\n        // Now find a clickable element near that label whose text is a pure number\n        // The dropdown value ("2") should be within ~60px vertically of the label\n        const candidates = [];\n        for (const el of allEls) {\n            const rect = el.getBoundingClientRect();\n            if (rect.width === 0 || rect.height === 0) continue;\n            const text = el.textContent.trim();\n            // Must be a pure number (1, 2, 3, 4) — no letters allowed\n            if (!/^[1-4]$/.test(text)) continue;\n            // Must be near the label vertically\n            if (Math.abs(rect.y - labelY) > 80) continue;\n            // Must be inside a button or be clickable\n            const btn = el.closest(\'button\') || el;\n            candidates.push({el: btn, text: text, y: Math.round(rect.y), dist: Math.abs(rect.y - labelY)});\n        }\n\n        if (candidates.length === 0) return {error: \'Count dropdown not found\', labelY: Math.round(labelY)};\n\n        // Sort by distance to label, pick closest\n        candidates.sort((a, b) => a.dist - b.dist);\n        const best = candidates[0];\n\n        if (best.text === String(targetCount)) {\n            return {method: \'already_set\', value: targetCount};\n        }\n\n        best.el.click();\n        return {method: \'clicked_dropdown\', current: best.text, y: best.y};\n    }', count)
    if result.get('error'):
        print(f'''  WARNING: {result['error']} — variant count unchanged''')
        page.keyboard.press('Escape')
        time.sleep(0.5)
        return None
    if result.get('method') == 'already_set':
        print(f'''  Variant count already set to {count}''')
        page.keyboard.press('Escape')
        time.sleep(0.5)
        return None
    print(f'''  Clicked variant dropdown (current: {result.get('current', '?')})''')
    time.sleep(0.5)
    selected = page.evaluate('(targetCount) => {\n        const options = document.querySelectorAll(\n            \'[role="option"], [role="menuitem"], li, .mdc-list-item, [class*="option"]\'\n        );\n        for (const opt of options) {\n            const text = opt.textContent.trim();\n            if (text === String(targetCount)) {\n                opt.click();\n                return {selected: true, text: text};\n            }\n        }\n        // Fallback: find any visible leaf element showing the target number\n        const allEls = document.querySelectorAll(\'*\');\n        for (const el of allEls) {\n            const text = el.textContent.trim();\n            const rect = el.getBoundingClientRect();\n            if (text === String(targetCount) && rect.width > 0 && rect.height > 0 &&\n                rect.width < 200 && rect.height < 60 && el.children.length === 0) {\n                el.click();\n                return {selected: true, text: text, tag: el.tagName};\n            }\n        }\n        return {selected: false};\n    }', count)
    if selected.get('selected'):
        print(f'''  Set variant count to {count}''')
    else:
        print(f'''  WARNING: Could not select {count} from dropdown''')
    time.sleep(0.5)
    page.keyboard.press('Escape')
    time.sleep(0.5)
    return None


def set_image_model(page = None, model_name = None):
    """Switch image generation model via Settings panel.

    Opens Settings panel, clicks the 'Модель' combobox, selects the target model.
    Available models: 'Imagen 4', 'Nano Banana', 'Nano Banana Pro'
    """
    settings_opened = page.evaluate('() => {\n        const btns = document.querySelectorAll(\'button\');\n        for (const btn of btns) {\n            const text = btn.textContent.trim().toLowerCase();\n            const rect = btn.getBoundingClientRect();\n            if ((text.includes(\'tune\') || text === \'tune\' ||\n                 text.includes(\'settings\') || text.includes(\'настройки\')) &&\n                rect.y > 600 && rect.width < 100) {\n                btn.click();\n                return true;\n            }\n        }\n        const icons = document.querySelectorAll(\'[class*="icon"], .material-icons, .material-symbols\');\n        for (const icon of icons) {\n            const text = icon.textContent.trim().toLowerCase();\n            const rect = icon.getBoundingClientRect();\n            if ((text === \'tune\' || text === \'settings\') && rect.y > 600) {\n                icon.click();\n                return true;\n            }\n        }\n        return false;\n    }')
    if not settings_opened:
        print('  WARNING: Settings button not found — model unchanged')
        return None
    time.sleep(1.5)
    clicked = page.evaluate('() => {\n        const combos = document.querySelectorAll(\'button[role="combobox"]\');\n        for (const combo of combos) {\n            const text = (combo.textContent || \'\').trim();\n            if (text.includes(\'Модель\') || text.includes(\'Model\')) {\n                combo.click();\n                return text.substring(0, 50);\n            }\n        }\n        return null;\n    }')
    if not clicked:
        print('  WARNING: Model combobox not found — model unchanged')
        page.keyboard.press('Escape')
        return None
    time.sleep(1)
    selected = page.evaluate('(targetModel) => {\n        const opts = document.querySelectorAll(\'div[role="option"]\');\n        for (const opt of opts) {\n            const text = (opt.textContent || \'\').trim();\n            if (targetModel === \'Nano Banana\') {\n                if (text.includes(\'Nano Banana\') && !text.includes(\'Pro\')) {\n                    opt.click();\n                    return text;\n                }\n            } else {\n                if (text.includes(targetModel)) {\n                    opt.click();\n                    return text;\n                }\n            }\n        }\n        return null;\n    }', model_name)
    if selected:
        print(f'''  Model set to: {model_name}''')
    else:
        print(f'''  WARNING: Model \'{model_name}\' not found in dropdown''')
    time.sleep(0.5)
    page.keyboard.press('Escape')
    time.sleep(0.5)


def click_generate(page = None):
    '''Click the Generate (arrow_forward / Создать) button via JS.

    NOTE: Previous version called _dismiss_crop_dialog() and
    ensure_enhance_prompt_off() before clicking, which disrupted
    ingredient/UI state and caused "Что-то пошло не так" errors.
    Now we just find and click the Generate button directly — matching
    the approach used in successful test scripts.
    '''
    dismiss_error_dialog(page)
    clicked = page.evaluate("() => {\n        const btns = document.querySelectorAll('button');\n        for (const btn of btns) {\n            const text = (btn.textContent || '').trim();\n            if (text.includes('Генерировать') || text.includes('Generate') ||\n                text.includes('arrow_forward')) {\n                const rect = btn.getBoundingClientRect();\n                if (rect.width > 0 && rect.height > 0) {\n                    btn.click();\n                    return true;\n                }\n            }\n        }\n        return false;\n    }")
    if not clicked:
        raise RuntimeError('Generate button not found')
    print('  Clicked Generate.')
    time.sleep(2)


def _ensure_gallery_tab(page = None, tab = None):
    """Click the gallery tab to ensure it's active."""
    tab_btn = page.query_selector(f'''button[role="radio"]:has-text("{tab}")''')
    if tab_btn:
        tab_btn.click()
        time.sleep(1)
        return None


def get_gallery_urls(page = None, tab = None):
    '''Get current gallery media URLs for the given tab.

    Returns a set of URLs for comparison (detect new items after generation).
    '''
    _ensure_gallery_tab(page, tab)
    media_type = 'video' if tab == 'Видео' else 'img'
    urls = get_gallery_media_urls(page, media_type)
    return set(urls)


def wait_for_new_gallery_item(page = None, initial_urls = None, timeout_sec = GENERATION_TIMEOUT, tab = 'Изображения', min_wait = 15):
    '''Poll until new gallery items appear (URLs change).

    Returns:
        "success" — new items appeared
        "server_error" — "Что-то пошло не так" or similar
        "content_filter" — "Не удалось сгенерировать"
        "timeout" — timed out waiting

    min_wait: minimum seconds before checking for errors (avoids detecting
    old error cards from previous generations).
    '''
    elapsed = 0
    while elapsed < timeout_sec:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        _ensure_gallery_tab(page, tab)
        current_urls = get_gallery_urls(page, tab)
        new_urls = current_urls - initial_urls
        if new_urls:
            print(f'''  Generation complete! ({elapsed}s) — {len(new_urls)} new items''')
            return 'success'
        if elapsed >= min_wait:
            error_text = page.evaluate("() => {\n                const els = document.querySelectorAll('*');\n                for (const el of els) {\n                    const text = (el.textContent || '').trim();\n                    if ((text.includes('Что-то пошло не так') ||\n                         text.includes('Произошла ошибка') ||\n                         text.includes('Не удалось сгенерировать') ||\n                         text.includes('не удалось')) &&\n                        text.length < 300) {\n                        const rect = el.getBoundingClientRect();\n                        if (rect.width > 100 && rect.height > 20) {\n                            return text;\n                        }\n                    }\n                }\n                return null;\n            }")
            if error_text:
                print(f'''  ERROR detected: {error_text[:80]}''')
                if 'Не удалось сгенерировать' in error_text:
                    return 'content_filter'
                return 'server_error'
        if elapsed % 30 == 0:
            print(f'''  Waiting for generation... ({elapsed}s, urls={len(current_urls)})''')
    print(f'''  TIMEOUT after {timeout_sec}s (urls={len(get_gallery_urls(page, tab))})''')
    return 'timeout'


def get_gallery_media_urls(page = None, media_type = None):
    '''Extract src URLs from gallery media elements.

    media_type: "img" for images, "video" for videos.
    '''
    tag = media_type
    urls = page.evaluate(f'''() => {{\n        const results = [];\n        document.querySelectorAll(\'{tag}\').forEach(el => {{\n            const rect = el.getBoundingClientRect();\n            if (rect.width > 100 && rect.y > 100 && rect.y < 800) {{\n                results.push(el.src);\n            }}\n        }});\n        return results;\n    }}''')
    return urls


def download_media_via_fetch(page = None, url = None, save_path = None):
    '''Download media by fetching the URL in browser context.

    Uses page.evaluate + fetch() to download (preserves auth cookies/signed URLs).
    Converts to base64 and saves locally.
    '''
    result = page.evaluate("async (url) => {\n        try {\n            const resp = await fetch(url);\n            if (!resp.ok) return {error: `HTTP ${resp.status}`};\n            const blob = await resp.blob();\n            return {\n                type: blob.type,\n                size: blob.size,\n                data: await new Promise((resolve) => {\n                    const reader = new FileReader();\n                    reader.onload = () => resolve(reader.result.split(',')[1]);\n                    reader.readAsDataURL(blob);\n                })\n            };\n        } catch (e) {\n            return {error: e.message};\n        }\n    }", url)
    if 'error' in result:
        print(f'''  Fetch error: {result['error']}''')
        return False
    data = base64.b64decode(result['data'])
    save_path.write_bytes(data)
    print(f'''  Saved: {save_path.name} ({len(data)} bytes, {result['type']})''')
    return True


def download_latest_image(page = None, save_path = None):
    '''Download the most recent image from the gallery via its src URL.'''
    urls = get_gallery_media_urls(page, 'img')
    if not urls:
        print('  No gallery images found')
        return False
    url = urls[-1]
    print(f'''  Downloading image #{len(urls)}...''')
    return download_media_via_fetch(page, url, save_path)


def download_latest_video(page = None, save_path = None):
    '''Download the most recent video from the gallery.'''
    video_tab = page.query_selector('button[role="radio"]:has-text("Видео")')
    if video_tab:
        video_tab.click()
        time.sleep(2)
    urls = get_gallery_media_urls(page, 'video')
    if not urls:
        urls = page.evaluate("() => {\n            const results = [];\n            document.querySelectorAll('video source, video').forEach(el => {\n                const rect = (el.closest('video') || el).getBoundingClientRect();\n                if (rect.width > 100 && rect.y > 100) {\n                    const src = el.src || el.querySelector('source')?.src;\n                    if (src) results.push(src);\n                }\n            });\n            return results;\n        }")
    if not urls:
        print('  No gallery videos found')
        return False
    url = urls[-1]
    print(f'''  Downloading video #{len(urls)}...''')
    return download_media_via_fetch(page, url, save_path)


def download_all_new_images(page = None, initial_urls = None, dest_dir = None):
    '''Download all NEW images that appeared since initial_urls snapshot.

    Returns list of saved file paths.
    '''
    _ensure_gallery_tab(page, 'Изображения')
    urls = get_gallery_media_urls(page, 'img')
    new_urls = [u for u in urls if u not in initial_urls]
    if not new_urls:
        print('  No new images to download')
        return []
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for i, url in enumerate(new_urls):
        path = dest_dir / f'variant_{i + 1}.png'
        print(f'  Downloading image variant {i + 1}/{len(new_urls)}...')
        if download_media_via_fetch(page, url, path):
            saved.append(path)
    return saved


def download_all_new_videos(page = None, initial_urls = None, dest_dir = None):
    '''Download all NEW videos that appeared since initial_urls snapshot.

    Returns list of saved file paths.
    '''
    _ensure_gallery_tab(page, 'Видео')
    urls = get_gallery_media_urls(page, 'video')
    if not urls:
        urls = page.evaluate("() => {\n            const results = [];\n            document.querySelectorAll('video source, video').forEach(el => {\n                const rect = (el.closest('video') || el).getBoundingClientRect();\n                if (rect.width > 100 && rect.y > 100) {\n                    const src = el.src || el.querySelector('source')?.src;\n                    if (src) results.push(src);\n                }\n            });\n            return results;\n        }")
    new_urls = [u for u in urls if u not in initial_urls]
    if not new_urls:
        print('  No new videos to download')
        return []
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for i, url in enumerate(new_urls):
        path = dest_dir / f'variant_{i + 1}.mp4'
        print(f'  Downloading video variant {i + 1}/{len(new_urls)}...')
        if download_media_via_fetch(page, url, path):
            saved.append(path)
    return saved


def _manifest_path(clip_id = None):
    return REVIEW_DIR / clip_id / 'manifest.json'


def load_manifest(clip_id = None):
    '''Load or create a manifest for a clip.'''
    path = _manifest_path(clip_id)
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {
        'clip_id': clip_id,
        'components': {
            'nb_first': {'attempts': [], 'selected_variant': None, 'status': 'pending'},
            'nb_last': {'attempts': [], 'selected_variant': None, 'status': 'pending'},
            'veo': {'attempts': [], 'selected_variant': None, 'status': 'pending'},
        }
    }


def save_manifest(clip_id = None, manifest = None):
    '''Save manifest to disk.'''
    path = _manifest_path(clip_id)
    path.parent.mkdir(parents = True, exist_ok = True)
    with open(path, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def find_scene_ref_frame(clips = None, current_clip_id = None):
    '''Find an accepted first frame from a previous clip in the same scene.

    Looks at clips with the same scene_id that appear before current_clip_id,
    checking for accepted nb_first frames in their manifests.
    Returns the path to the most recent accepted first frame, or None.
    '''
    current_scene = None
    current_idx = -1
    for i, clip in enumerate(clips):
        if not clip['clip_id'] == current_clip_id:
            continue
        current_scene = clip['scene_id']
        current_idx = i
        break
    if current_scene is None:
        return None
    all_clips = [c for c in clips if c['scene_id'] == current_scene]
    candidates = []
    for clip in all_clips:
        cid = clip['clip_id']
        if cid == current_clip_id:
            break
        frame_path = FRAMES_DIR / f'{cid}_first.png'
        if frame_path.exists():
            candidates.append(frame_path)
    if candidates:
        print(f'  Scene ref: found accepted frame from {candidates[-1].stem}')
        return candidates[-1]
    return None


def get_component_status(manifest = None, component = None):
    """Get status of a component: 'pending', 'accepted', or 'needs_manual_work'."""
    return manifest['components'].get(component, { }).get('status', 'pending')


def get_next_attempt(manifest = None, component = None):
    '''Return the next attempt number (1-based). Returns 0 if max attempts exceeded.'''
    comp = manifest['components'].get(component, { })
    n = len(comp.get('attempts', []))
    if n >= MAX_ATTEMPTS:
        return 0
    return n + 1


def record_attempt(manifest, component = None, attempt_num = None, prompt = None, variant_paths = None):
    '''Record a generation attempt in the manifest.'''
    comp = manifest['components'][component]
    attempt_entry = {
        'attempt': attempt_num,
        'prompt': prompt,
        'variants': [{'file': p.name, 'scores': None, 'avg': None} for p in variant_paths],
        'best_variant': None,
        'best_avg': None,
    }
    comp['attempts'].append(attempt_entry)
    return attempt_entry


def mark_selected(manifest, component, attempt = None, variant_idx = None, scores = None, avg = None):
    '''Mark a variant as selected (passed review).'''
    comp = manifest['components'][component]
    attempt_entry = comp['attempts'][attempt - 1]
    attempt_entry['variants'][variant_idx]['scores'] = scores
    attempt_entry['variants'][variant_idx]['avg'] = avg
    attempt_entry['best_variant'] = variant_idx
    attempt_entry['best_avg'] = avg
    comp['selected_variant'] = {
        'attempt': attempt,
        'variant': variant_idx }
    comp['status'] = 'accepted'


def mark_failed(manifest = None, component = None, attempt = None, scores_per_variant = None):
    '''Mark an attempt as failed. If max attempts reached, set needs_manual_work.'''
    comp = manifest['components'][component]
    attempt_entry = comp['attempts'][attempt - 1]
    if scores_per_variant:
        for i, scores in enumerate(scores_per_variant):
            if i < len(attempt_entry['variants']):
                v = attempt_entry['variants'][i]
                v['scores'] = scores
                if scores:
                    non_zero = [s for s in scores.values() if s > 0]
                    v['avg'] = sum(non_zero) / len(non_zero) if non_zero else 0
    if len(comp['attempts']) >= MAX_ATTEMPTS:
        comp['status'] = 'needs_manual_work'


def copy_selected_to_output(clip_id = None, manifest = None, trim_start = None, trim_end = None):
    '''Copy accepted variants to output/frames/ and output/clips/.

    For VEO component, if trim_start/trim_end provided, trims the video.
    '''
    for component in ('nb_first', 'nb_last', 'veo'):
        comp = manifest['components'][component]
        sel = comp.get('selected_variant')
        if not sel:
            continue
        attempt_dir = REVIEW_DIR / clip_id / component / f'attempt_{sel["attempt"]}'
        attempt_entry = comp['attempts'][sel['attempt'] - 1]
        variant_data = attempt_entry['variants'][sel['variant']]
        variant_file = attempt_dir / variant_data['file']
        if not variant_file.exists():
            print(f'  WARNING: selected file not found: {variant_file}')
            continue
        if component == 'nb_first':
            dest = FRAMES_DIR / f'{clip_id}_first.png'
            shutil.copy2(variant_file, dest)
        elif component == 'nb_last':
            dest = FRAMES_DIR / f'{clip_id}_last.png'
            shutil.copy2(variant_file, dest)
        elif component == 'veo':
            dest = CLIPS_DIR / f'{clip_id}_clip.mp4'
            if trim_start is not None and trim_end is not None:
                ok = trim_video(variant_file, trim_start, trim_end, dest)
                if not ok:
                    print('  WARN: trim failed, copying full video')
                    shutil.copy2(variant_file, dest)
            else:
                shutil.copy2(variant_file, dest)
        print(f'  Copied {variant_file.name} → {dest.name}')


def _all_components_done(manifest = None):
    '''Check if all 3 components are accepted or needs_manual_work.'''
    for comp in ('nb_first', 'nb_last', 'veo'):
        status = manifest['components'][comp]['status']
        if status not in ('accepted', 'needs_manual_work'):
            return False
    return True


def cleanup_component(clip_id = None, component = None):
    '''Delete all review files for a component. Returns list of deleted paths.'''
    comp_dir = REVIEW_DIR / clip_id / component
    deleted = []
    if not comp_dir.exists():
        return deleted
    for f in comp_dir.rglob('*'):
        if not f.is_file():
            continue
        rel = str(f.relative_to(REVIEW_DIR))
        f.unlink()
        deleted.append(rel)
    for d in sorted(comp_dir.rglob('*'), reverse = True):
        if not d.is_dir():
            continue
        if any(d.iterdir()):
            continue
        d.rmdir()
    if comp_dir.exists() and not any(comp_dir.iterdir()):
        comp_dir.rmdir()
    return deleted


def cleanup_clip_review(clip_id = None, manifest = None):
    '''Clean up review folder for a clip after all components are done.

    Archives manifest, deletes all variant files, removes the clip folder.
    Logs all deletions to cleanup_log.txt.
    '''
    clip_dir = REVIEW_DIR / clip_id
    if not clip_dir.exists():
        return None
    all_deleted = []
    for component in ('nb_first', 'nb_last', 'veo'):
        deleted = cleanup_component(clip_id, component)
        all_deleted.extend(deleted)
    manifest_src = clip_dir / 'manifest.json'
    manifest_dst = REVIEW_DIR / f'''{clip_id}_manifest_archive.json'''
    if manifest_src.exists():
        shutil.copy2(manifest_src, manifest_dst)
        manifest_src.unlink()
        all_deleted.append(f'''{clip_id}/manifest.json''')
        print(f'''  Archived manifest → {manifest_dst.name}''')
    if clip_dir.exists():
        for d in sorted(clip_dir.rglob('*'), reverse = True):
            if not d.is_dir():
                continue
            if any(d.iterdir()):
                continue
            d.rmdir()
        if clip_dir.exists() and not any(clip_dir.iterdir()):
            clip_dir.rmdir()
    CLEANUP_LOG_PATH.parent.mkdir(parents = True, exist_ok = True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(CLEANUP_LOG_PATH, 'a') as f:
        f.write(f'\n[{timestamp}] Cleanup: {clip_id} — {len(all_deleted)} files deleted\n')
        for rel in all_deleted:
            f.write(f'  - {rel}\n')
    print(f'  Cleanup: deleted {len(all_deleted)} review files for {clip_id}')
    print(f'  Log: {CLEANUP_LOG_PATH}')


def _wait_for_upload_button(page = None, timeout_sec = None):
    """Poll DOM until an upload button appears (ingredient panel loaded).

    Looks for 'Загрузить' or 'Upload' or 'upload_file' icon button.
    """
    for sec in range(timeout_sec):
        time.sleep(1)
        for selector in ('button:has-text("Загрузить")', 'button:has-text("Upload")', 'button:has-text("upload_file")'):
            btn = page.query_selector(selector)
            if not btn:
                continue
            box = btn.bounding_box()
            if not box:
                continue
            if not box['width'] > 20:
                continue
            ('button:has-text("Загрузить")', 'button:has-text("Upload")', 'button:has-text("upload_file")')
            range(timeout_sec)
            return True
    return False


def _find_ingredient_add_button(page = None):
    """Find and click the '+' (add) button for ingredient panel.

    Strategy: find button with 'add' icon text, near the prompt bar area,
    wider than gallery card buttons (>40px), and in the lower portion of page.
    Uses includes() instead of === for more robust matching.
    """
    result = page.evaluate("() => {\n        const btns = document.querySelectorAll('button');\n        const candidates = [];\n        for (const btn of btns) {\n            const text = btn.textContent.trim();\n            const rect = btn.getBoundingClientRect();\n            // Must contain 'add', be near prompt bar (y > 750), and wide (> 50px)\n            // to distinguish from gallery card buttons (~w=32, y~685)\n            if (text.includes('add') && !text.includes('download') &&\n                rect.y > 750 && rect.width > 50 && rect.height > 30) {\n                candidates.push({\n                    text: text.substring(0, 30),\n                    y: rect.y, x: rect.x,\n                    w: rect.width, h: rect.height\n                });\n                btn.click();\n                return {clicked: true, btn: candidates[candidates.length - 1]};\n            }\n        }\n        // Fallback: try 'add' button in lower area but still require decent width\n        for (const btn of btns) {\n            const text = btn.textContent.trim();\n            const rect = btn.getBoundingClientRect();\n            if (text === 'add' && rect.y > 700 && rect.width > 40) {\n                btn.click();\n                return {clicked: true, btn: {text, y: rect.y, w: rect.width}};\n            }\n        }\n        // Debug: list all 'add'-like buttons\n        const debug = [];\n        for (const btn of btns) {\n            const text = btn.textContent.trim();\n            if (text.includes('add')) {\n                const rect = btn.getBoundingClientRect();\n                debug.push({text: text.substring(0, 30), y: Math.round(rect.y),\n                           w: Math.round(rect.width), h: Math.round(rect.height)});\n            }\n        }\n        return {clicked: false, debug};\n    }")
    if result.get('clicked'):
        btn_info = result.get('btn', { })
        print(f'''  Clicked ingredient \'+\' button (y={btn_info.get('y', '?'):.0f}, w={btn_info.get('w', '?'):.0f})''')
        return True
    debug = result.get('debug', [])
    if debug:
        print(f'''  DEBUG: found {len(debug)} \'add\' buttons but none matched:''')
        for d in debug[:5]:
            print(f'''    text=\'{d['text']}\' y={d['y']} w={d['w']} h={d['h']}''')
        return False
    print("  DEBUG: no 'add' buttons found on page")
    return False


def _open_ingredient_panel(page = None):
    """Open the ingredient upload panel in image mode.

    Strategy:
      1. Dismiss any error dialogs
      2. Wait for page to be fully stable
      3. Click '+' button, wait for upload panel
      4. Retry with page reload if needed
    Returns True if panel opened.
    """
    dismiss_error_dialog(page)
    time.sleep(1)
    if _find_ingredient_add_button(page):
        print('  Waiting for ingredient panel to load (attempt 1/3)...')
        if _wait_for_upload_button(page, timeout_sec = 30):
            print('  Ingredient panel loaded.')
            return True
    else:
        print("  Could not find '+' button (attempt 1/3)")
    print('  Panel not loaded — reloading page (attempt 2/3)...')
    page.reload(wait_until = 'domcontentloaded')
    time.sleep(5)
    page.wait_for_selector('textarea', timeout = PAGE_LOAD_TIMEOUT)
    time.sleep(5)
    switch_mode(page, 'Создать изображение')
    time.sleep(3)
    if _find_ingredient_add_button(page) and _wait_for_upload_button(page, timeout_sec = 30):
        print('  Ingredient panel loaded after reload.')
        return True
    print('  Panel not loaded — re-navigating to project (attempt 3/3)...')
    page.goto(get_project_url(), timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    time.sleep(5)
    page.wait_for_selector('textarea', timeout = PAGE_LOAD_TIMEOUT)
    time.sleep(5)
    switch_mode(page, 'Создать изображение')
    time.sleep(3)
    if _find_ingredient_add_button(page) and _wait_for_upload_button(page, timeout_sec = 30):
        print('  Ingredient panel loaded after re-navigation.')
        return True
    take_debug_screenshot(page, 'ingredient_panel_failed')
    print('  WARNING: ingredient panel did not load after 3 attempts')
    return False


def _dismiss_crop_dialog(page = None):
    """Dismiss crop dialog using JavaScript click (bypasses ReactCrop overlay).

    The crop overlay (ReactCrop__crop-selection) intercepts pointer events,
    so Playwright's .click() times out. Use JS click instead.
    """
    dismissed = page.evaluate("() => {\n        const btns = document.querySelectorAll('button');\n        for (const btn of btns) {\n            const text = btn.textContent.trim();\n            if (text.includes('Кадрировать и сохранить') || text.includes('Сохранить')) {\n                const rect = btn.getBoundingClientRect();\n                if (rect.width > 50) {\n                    btn.click();\n                    return true;\n                }\n            }\n        }\n        return false;\n    }")
    if dismissed:
        print('  Crop dialog: saved (JS click).')
        time.sleep(3)
    return dismissed


def _upload_single_file(page = None, file_path = None):
    '''Upload one file to the ingredient panel.

    Strategy 1: Find <input type="file"> and set_input_files() directly.
    Strategy 2: Click 'Загрузить' button + file chooser (fallback).
    Handles crop dialog after upload.
    Returns True on success, False on failure.
    '''
    _dismiss_crop_dialog(page)
    # Strategy 1: direct input[type="file"]
    file_input = None
    for _try in range(3):
        file_input = page.query_selector('input[type="file"]')
        if file_input:
            break
        time.sleep(2)
    if file_input:
        try:
            file_input.set_input_files(str(file_path))
            print('    (set_input_files directly)')
            time.sleep(3)
            for _ in range(15):
                if _dismiss_crop_dialog(page):
                    return True
                time.sleep(1)
            return True
        except Exception as e:
            print(f'    (direct input failed: {e}, trying button click)')
    # Strategy 2: click upload button + file chooser
    upload_btn = None
    for selector in ('button:has-text("Загрузить")', 'button:has-text("Upload")', 'button:has-text("upload_file")'):
        upload_btn = page.query_selector(selector)
        if upload_btn:
            box = upload_btn.bounding_box()
            if box and box.get('width', 0) > 20:
                break
            else:
                upload_btn = None
    if not upload_btn:
        _dismiss_crop_dialog(page)
        time.sleep(2)
        for selector in ('button:has-text("Загрузить")', 'button:has-text("Upload")'):
            upload_btn = page.query_selector(selector)
            if upload_btn:
                box = upload_btn.bounding_box()
                if box and box.get('width', 0) > 20:
                    break
                else:
                    upload_btn = None
    if not upload_btn:
        print(f'  WARNING: Upload button not found for {file_path.name}')
        return False
    try:
        page.evaluate('(el) => el.click()', upload_btn)
        fc_info = page.expect_file_chooser(timeout=10000)
        with fc_info as file_chooser:
            file_chooser.set_files(str(file_path))
        time.sleep(3)
        for _ in range(15):
            if _dismiss_crop_dialog(page):
                return True
            time.sleep(1)
        return True
    except Exception as e:
        print(f'  WARNING: file chooser failed for {file_path.name}: {e}')
        return False


def upload_ingredients(page = None, ingredient_paths = None):
    """Upload ingredient images for Nano Banana image generation.

    Opens the ingredient panel once, then uploads files one by one.
    Uses input[type='file'] set_input_files() for reliability after first crop.
    If that fails, tries closing/reopening panel.
    Returns number of successfully uploaded files.
    """
    if not ingredient_paths:
        return 0
    resolved = []
    for rel_path in ingredient_paths:
        full = resolve_ingredient_path(rel_path)
        if full.exists():
            resolved.append(full)
            continue
        print(f'''  WARNING: ingredient not found: {full}''')
    if not resolved:
        print('  No valid ingredient files to upload')
        return 0
    if not _open_ingredient_panel(page):
        print('  SKIP ingredients — panel not available')
        return 0
    uploaded = 0
    for i, fpath in enumerate(resolved):
        print(f'''  Uploading ingredient {i + 1}/{len(resolved)}: {fpath.name}''')
        if _upload_single_file(page, fpath):
            uploaded += 1
            time.sleep(2)
            continue
        print(f'''  Retrying {fpath.name} with panel reopen...''')
        page.keyboard.press('Escape')
        time.sleep(3)
        _dismiss_crop_dialog(page)
        time.sleep(2)
        if not _find_ingredient_add_button(page):
            continue
        if not _wait_for_upload_button(page, timeout_sec = 20):
            continue
        if _upload_single_file(page, fpath):
            uploaded += 1
            time.sleep(2)
            continue
        print(f'''  WARNING: Skipping {fpath.name} after retry failed''')
    page.keyboard.press('Escape')
    time.sleep(1)
    print(f'''  Uploaded {uploaded}/{len(resolved)} ingredients.''')
    return uploaded


def clear_veo_frame_slots(page = None):
    '''Remove any pre-uploaded frames from VEO frame slots.

    After a previous VEO session, the frame slots may already contain images.
    We need to clear them before uploading new frames.
    '''
    cleared = 0
    for _pass in range(2):
        close_btns = []
        for btn in page.query_selector_all('button'):
            text = (btn.text_content() or '').strip()
            box = btn.bounding_box()
            if not text == 'close':
                continue
            if not box:
                continue
            if not box['y'] > 600:
                continue
            close_btns.append(btn)
        if not close_btns:
            break
        close_btns[0].click()
        cleared += 1
        time.sleep(1)
    if cleared:
        print(f'''  Cleared {cleared} pre-filled frame slot(s)''')
        time.sleep(1)
        return None


def upload_frame_for_veo(page = None, frame_path = None, slot_index = None):
    '''Upload a frame image to a specific slot in VEO Frames-to-Video mode.

    In "Видео по кадрам" mode there are two frame slots:
      slot_index=0 — First Frame (начальный кадр)
      slot_index=1 — Last Frame (конечный кадр)

    Steps:
      1. Click the nth "+" button to open upload panel
      2. Click "Загрузить" to trigger file dialog
      3. Handle the crop dialog ("Кадрировать и сохранить")
      4. Close the upload panel overlay
    '''
    slot_name = 'First Frame' if slot_index == 0 else 'Last Frame'
    clicked_slot = page.evaluate("() => {\n        const btns = document.querySelectorAll('button');\n        for (const btn of btns) {\n            const text = btn.textContent.trim();\n            const rect = btn.getBoundingClientRect();\n            if (text === 'add' && rect.y > 700 && rect.width > 40) {\n                btn.click();\n                return {y: rect.y, w: rect.width};\n            }\n        }\n        return null;\n    }")
    if not clicked_slot:
        take_debug_screenshot(page, f'''veo_no_add_btn_slot{slot_index}''')
        raise RuntimeError(f'''{slot_name} \'+\' button not found (no frame-slot add buttons)''')
    print(f'''  Clicking \'+\' for {slot_name} (slot {slot_index})...''')
    time.sleep(2)
    upload_btn = None
    for _retry in range(5):
        upload_btn = page.query_selector('button:has-text("Загрузить")')
        if not upload_btn:
            upload_btn = page.query_selector('button:has-text("upload")')
        if upload_btn:
            break
        elif _retry == 2:
            page.keyboard.press('Escape')
            time.sleep(1)
            page.evaluate("() => {\n                const btns = document.querySelectorAll('button');\n                for (const btn of btns) {\n                    const text = btn.textContent.trim();\n                    const rect = btn.getBoundingClientRect();\n                    if (text === 'add' && rect.y > 700 && rect.width > 40) {\n                        btn.click();\n                        return true;\n                    }\n                }\n                return false;\n            }")
        time.sleep(2)
    if not upload_btn:
        take_debug_screenshot(page, f'''veo_no_upload_btn_slot{slot_index}''')
        raise RuntimeError(f'''Upload (\'Загрузить\') button not found for {slot_name}''')
    print(f'''  Uploading {frame_path.name} as {slot_name}...''')
    uploaded = False
    file_input = page.query_selector('input[type="file"]')
    if file_input:
        try:
            file_input.set_input_files(str(frame_path))
            print('    (set_input_files directly)')
            uploaded = True
        except Exception as e:
            print(f'    (direct input failed: {e})')
    if not uploaded:
        try:
            page.evaluate("() => {\n                const btns = document.querySelectorAll('button');\n                for (const btn of btns) {\n                    const text = btn.textContent.trim();\n                    const rect = btn.getBoundingClientRect();\n                    if ((text.includes('Загрузить') || text.includes('upload')) && rect.width > 20) {\n                        btn.click();\n                        return true;\n                    }\n                }\n                return false;\n            }")
            fc_info = page.expect_file_chooser(timeout=10000)
            with fc_info as file_chooser:
                file_chooser.set_files(str(frame_path))
            uploaded = True
        except Exception as e:
            print(f'    (JS click + file chooser failed: {e})')
    if not uploaded:
        raise RuntimeError(f'Failed to upload {frame_path.name}')
    time.sleep(3)
    _dismiss_crop_dialog(page)
    time.sleep(2)
    print(f'  {slot_name} uploaded and cropped.')


def do_login(pw):
    '''Open Flow in visible browser for manual Google login.
    Session is saved to .session/ (or .session_2/ for account 2) for reuse.
    Polls page until user completes login and reaches workspace.
    '''
    acct = ACCOUNTS[_current_account_idx]
    print(f'''Opening Flow for Google login (account {_current_account_idx + 1})...''')
    print(f'''Session will be saved to: {acct['session_dir']}''')
    print()
    ctx = launch_browser(pw, headless = False)
    page = ctx.new_page()
    page.goto(FLOW_URL, timeout = PAGE_LOAD_TIMEOUT)
    page.wait_for_load_state('networkidle', timeout = 15000)
    create_btn = page.query_selector('button:has-text("Create with Flow")')
    if create_btn:
        print("Found 'Create with Flow' button — clicking to trigger Google login...")
        create_btn.click()
        time.sleep(3)
    print()
    print('════════════════════════════════════════════════════════════')
    print('  Waiting for you to complete Google login...')
    print('  Log in, then navigate to the Flow workspace.')
    print("  The script will detect when you're in the workspace.")
    print('════════════════════════════════════════════════════════════')
    print()
    max_wait = 300
    poll_interval = 3
    elapsed = 0
    workspace_detected = False
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        current_url = page.url
        has_prompt = page.query_selector('[contenteditable="true"]') is not None
        has_textarea = page.query_selector('textarea') is not None
        is_login_page = 'accounts.google.com' in current_url
        is_landing = current_url.endswith('/flow/about') or ('Create with Flow' in (page.text_content('body') or '')[:500])
        if (has_prompt or has_textarea) and not is_login_page:
            print(f'''\n  Workspace detected! URL: {current_url}''')
            workspace_detected = True
            break
        elif elapsed % 15 == 0:
            if is_login_page:
                status = 'login page'
            elif is_landing:
                status = 'landing'
            else:
                status = current_url[:60]
            print(f'''  Still waiting... ({elapsed}s) — {status}''')
    if not workspace_detected:
        print(f'''\n  Timeout after {max_wait}s. Taking screenshot of current state...''')
    screenshot_path = OUTPUT_DIR / 'flow_login_screenshot.png'
    page.screenshot(path = str(screenshot_path))
    print(f'''  Screenshot saved: {screenshot_path}''')
    print(f'''  Final URL: {page.url}''')
    time.sleep(2)
    ctx.close()
    if workspace_detected:
        print('\nSession saved. You can now run: python scripts/flow_bot.py --run')
        return None
    print('\nSession saved (but workspace not confirmed). Try --login again if needed.')


def load_clips(prompts_path = None, clip_filter = None):
    '''Load clip prompts from JSON. Optionally filter by clip_id.'''
    with open(prompts_path, 'r') as f:
        clips = json.load(f)
    if clip_filter:
        clips = [c for c in clips if c['clip_id'] == clip_filter]
        if not clips:
            print(f"Error: clip '{clip_filter}' not found in {prompts_path}")
            sys.exit(1)
    return clips


def resolve_ingredient_path(relative_path = None):
    """Resolve an ingredient path like 'персонажи/char_amin_full.png' to absolute."""
    full_path = REFS_DIR / relative_path
    if not full_path.exists():
        print(f'''  WARNING: ingredient not found: {full_path}''')
    return full_path


def _generate_single_frame(page, clip_id, frame_type = None, prompt = None, save_path = None, initial_urls = None):
    '''Generate a single frame (first or last) with Nano Banana.

    Assumes image mode and ingredients are already set up.
    Returns True on success.
    '''
    prompt = sanitize_prompt(prompt)
    print(f'''\n  --- Generating {frame_type} frame for {clip_id} ---''')
    print(f'''  Prompt: {prompt[:80]}...''')
    clear_prompt(page)
    fill_prompt(page, prompt)
    take_debug_screenshot(page, f'''{clip_id}_{frame_type}_before_gen''')
    click_generate(page)
    result = wait_for_new_gallery_item(page, initial_urls)
    if result != 'success':
        take_debug_screenshot(page, f'''{clip_id}_{frame_type}_timeout''')
        print(f'''  FAILED: {frame_type} frame generation for {clip_id} ({result})''')
        return False
    take_debug_screenshot(page, f'''{clip_id}_{frame_type}_after_gen''')
    if download_latest_image(page, save_path):
        return True
    print(f'''  FAILED: could not download {frame_type} frame for {clip_id}''')
    return False


def _generate_frame_review(page, clip_id, component = None, prompt = None, attempt = None, initial_urls = None, ingredients = None):
    '''Generate a frame with Nano Banana and download ALL variants.

    Saves variants to output/review/{clip_id}/{component}/attempt_{N}/.
    Retries up to 3 times for server errors ("Что-то пошло не так").
    On retry, reloads page and re-uploads ingredients for a clean state.
    Returns list of saved variant paths.
    '''
    prompt = sanitize_prompt(prompt)
    frame_label = 'first' if component == 'nb_first' else 'last'
    print(f'''\n  --- Generating {frame_label} frame for {clip_id} (attempt {attempt}) ---''')
    print(f'''  Prompt: {prompt[:80]}...''')
    SERVER_RETRY_WAITS = [
        45,
        60]
    for retry in range(3):
        if retry > 0:
            wait_time = SERVER_RETRY_WAITS[retry - 1]
            print(f'''  Server error — waiting {wait_time}s before retry {retry + 1}/3...''')
            time.sleep(wait_time)
            print('  Reloading page for clean retry...')
            page.goto(get_project_url(), timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
            wait_for_flow_ready(page)
            switch_mode(page, 'Создать изображение')
            if ingredients:
                upload_ingredients(page, ingredients)
        current_urls = get_gallery_urls(page)
        clear_prompt(page)
        fill_prompt(page, prompt)
        if retry == 0:
            take_debug_screenshot(page, f'''{clip_id}_{component}_a{attempt}_before_gen''')
        click_generate(page)
        result = wait_for_new_gallery_item(page, current_urls)
        if result == 'success':
            take_debug_screenshot(page, f'''{clip_id}_{component}_a{attempt}_after_gen''')
            dest_dir = REVIEW_DIR / clip_id / component / f'''attempt_{attempt}'''
            saved = download_all_new_images(page, current_urls, dest_dir)
            print(f'''  Downloaded {len(saved)} variants for {component} attempt {attempt}''')
            return saved
        take_debug_screenshot(page, f'''{clip_id}_{component}_a{attempt}_retry{retry}''')
        if result == 'content_filter':
            print('  Content filter blocked prompt — no retry')
            return []
        print(f'''  FAILED: {frame_label} frame for {clip_id} ({result}, retry {retry + 1}/3)''')
    return []


def run_nano_banana_pass(page = None, clip = None):
    '''Generate FIRST and LAST keyframes using Nano Banana Pro.

    Steps:
      1. Switch to "Создать изображение" mode
      2. Upload ingredients (character/location references) — once for both frames
      3. Generate first frame (nano_banana_prompt_first)
      4. Generate last frame (nano_banana_prompt_last)
      5. Download both frames

    Returns (first_frame_path, last_frame_path). Either can be None on failure.
    '''
    clip_id = clip['clip_id']
    print(f'''\n{'============================================================'}''')
    print(f'''  PASS 1+2 — Nano Banana Pro (First + Last frames) — {clip_id}''')
    print(f'''{'============================================================'}''')
    prompt_first = clip['nano_banana_prompt_first']
    prompt_last = clip['nano_banana_prompt_last']
    ingredients = clip.get('nano_banana_ingredients', [])
    print(f'''  First prompt: {prompt_first[:60]}...''')
    print(f'''  Last prompt:  {prompt_last[:60]}...''')
    print(f'''  Ingredients: {len(ingredients)} files''')
    first_path = FRAMES_DIR / f'''{clip_id}_first.png'''
    last_path = FRAMES_DIR / f'''{clip_id}_last.png'''
    if first_path.exists() and last_path.exists():
        print('  Both frames already exist — skipping generation')
        return (first_path, last_path)
    switch_mode(page, 'Создать изображение')
    img_tab = page.query_selector('button[role="radio"]:has-text("Изображения")')
    if img_tab:
        img_tab.click()
        time.sleep(1)
    set_image_model(page, 'Nano Banana Pro')
    if ingredients:
        upload_ingredients(page, ingredients)
    if not first_path.exists():
        initial_urls = get_gallery_urls(page)
        print(f'''  Gallery URLs before first frame: {len(initial_urls)}''')
        ok = _generate_single_frame(page, clip_id, 'first', prompt_first, first_path, initial_urls)
        if not ok:
            return (None, None)
        print(f'''  Pausing {PAUSE_BETWEEN_GENERATIONS}s before last frame...''')
        time.sleep(PAUSE_BETWEEN_GENERATIONS)
    else:
        print(f'''  First frame already exists: {first_path.name}''')
    if not last_path.exists():
        initial_urls = get_gallery_urls(page)
        print(f'''  Gallery URLs before last frame: {len(initial_urls)}''')
        ok = _generate_single_frame(page, clip_id, 'last', prompt_last, last_path, initial_urls)
        if not ok:
            return (first_path, None)
    else:
        print(f'''  Last frame already exists: {last_path.name}''')
    return (first_path, last_path)


def _run_veo_single_batch(page, clip_id, prompt, first_frame, last_frame, dest_dir, label):
    '''Generate 4 VEO video variants for a single prompt.

    Uploads frames, sets 4 variants, generates, downloads all to dest_dir.
    Returns list of saved file paths.
    '''
    print(f'\n  --- VEO batch "{label}" for {clip_id} ---')
    print(f'  Prompt: {prompt[:80]}...')

    # Check if already have 4 variants
    existing = sorted(dest_dir.glob('*.mp4')) if dest_dir.exists() else []
    if len(existing) >= 4:
        print(f'  Already have {len(existing)} variants in {dest_dir.name} — skipping')
        return existing

    # Reload page for clean state
    print('  Reloading page for clean VEO state...')
    page.goto(get_project_url(), timeout=PAGE_LOAD_TIMEOUT, wait_until='domcontentloaded')
    wait_for_flow_ready(page)

    switch_mode(page, 'Видео по кадрам')
    video_tab = page.query_selector('button[role="radio"]:has-text("Видео")')
    if video_tab:
        video_tab.click()
        time.sleep(2)

    # Stabilize gallery URL count before taking "before" snapshot
    prev_count = -1
    stable_count = 0
    for _ in range(10):
        urls = get_gallery_media_urls(page, 'video')
        if len(urls) == prev_count:
            stable_count += 1
            if stable_count >= 3:
                break
        else:
            stable_count = 0
        prev_count = len(urls)
        time.sleep(2)
    initial_urls = set(get_gallery_media_urls(page, 'video'))
    print(f'  Gallery URLs before: {len(initial_urls)}')

    clear_veo_frame_slots(page)
    upload_frame_for_veo(page, first_frame, 0)
    upload_frame_for_veo(page, last_frame, 1)
    ensure_enhance_prompt_off(page)
    set_variant_count(page, 4)
    clear_prompt(page)
    fill_prompt(page, prompt)
    take_debug_screenshot(page, f'{clip_id}_veo_{label}_before_gen')
    click_generate(page)

    result = wait_for_new_gallery_item(page, initial_urls, tab='Видео')
    if result != 'success':
        take_debug_screenshot(page, f'{clip_id}_veo_{label}_fail')
        print(f'  FAILED: VEO generation for {clip_id}/{label} ({result})')
        return []

    take_debug_screenshot(page, f'{clip_id}_veo_{label}_after_gen')
    saved = download_all_new_videos(page, initial_urls, dest_dir)
    print(f'  Downloaded {len(saved)} video variants for {label}')
    return saved


def run_veo_pass(page = None, clip = None, first_frame = None, last_frame = None):
    '''Pass 3: Generate 8 VEO video variants (4 per prompt × 2 prompts).

    Uses veo_prompt (prompt A) and veo_prompt_b (prompt B).
    Saves to clips/{clip_id}/a1.mp4..a4.mp4 and b1.mp4..b4.mp4.

    Returns path to clip directory, or None on failure.
    '''
    clip_id = clip['clip_id']
    print(f'''\n{'============================================================'}''')
    print(f'''  PASS 3 — VEO 3.1 Variants — {clip_id}''')
    print(f'''{'============================================================'}''')
    print(f'''  First frame: {first_frame.name}''')
    print(f'''  Last frame:  {last_frame.name}''')

    clip_dir = CLIPS_DIR / clip_id
    clip_dir.mkdir(parents=True, exist_ok=True)
    prompt_a_dir = clip_dir / 'prompt_a'
    prompt_b_dir = clip_dir / 'prompt_b'

    prompt_a = sanitize_prompt(clip['veo_prompt'])
    prompt_b = sanitize_prompt(clip.get('veo_prompt_b', clip['veo_prompt']))

    # Batch A: 4 variants with prompt A
    saved_a = _run_veo_single_batch(page, clip_id, prompt_a, first_frame, last_frame, prompt_a_dir, 'prompt_a')

    if saved_a:
        print(f'  Waiting {PAUSE_BETWEEN_GENERATIONS}s (rate limiting)...')
        time.sleep(PAUSE_BETWEEN_GENERATIONS)

    # Batch B: 4 variants with prompt B
    saved_b = _run_veo_single_batch(page, clip_id, prompt_b, first_frame, last_frame, prompt_b_dir, 'prompt_b')

    total = len(saved_a) + len(saved_b)
    if total > 0:
        print(f'  TOTAL: {total} video variants for {clip_id} (A={len(saved_a)}, B={len(saved_b)})')
        return clip_dir
    print(f'  FAILED: no video variants generated for {clip_id}')
    return None


def review_nano_banana(page, clip, manifest = None, component = None, attempt = None, prompt_override = None, first_frame_ref = None):
    '''Generate Nano Banana frame variants for review.

    Sets up image mode, uploads ingredients, generates, downloads all variants.
    Updates manifest with the attempt record.

    If first_frame_ref is provided (for nb_last), the selected first frame is
    added as an extra ingredient to ensure visual consistency between frames.
    Returns list of variant paths.
    '''
    clip_id = clip['clip_id']
    frame_label = 'first' if component == 'nb_first' else 'last'
    prompt_key = 'nano_banana_prompt_first' if component == 'nb_first' else 'nano_banana_prompt_last'
    prompt = prompt_override if prompt_override else clip[prompt_key]
    ingredients = list(clip.get('nano_banana_ingredients', []))
    print(f'''\n{'============================================================'}''')
    print(f'''  REVIEW — Nano Banana ({frame_label}) — {clip_id} — attempt {attempt}''')
    print(f'''{'============================================================'}''')
    print(f'''  Prompt: {prompt[:70]}...''')
    switch_mode(page, 'Создать изображение')
    img_tab = page.query_selector('button[role="radio"]:has-text("Изображения")')
    if img_tab:
        img_tab.click()
        time.sleep(1)
    image_model = clip.get('nano_banana_model_name', 'Nano Banana Pro')
    set_image_model(page, image_model)
    set_variant_count(page, 4)
    if first_frame_ref and first_frame_ref.exists():
        ref_image_num = len(ingredients) + 1
        ingredients.append(str(first_frame_ref))
        prompt += f''' Maintain exact visual continuity with Image {ref_image_num}.'''
        print(f'''  Added first frame as ingredient {ref_image_num} for consistency: {first_frame_ref.name}''')
    uploaded = upload_ingredients(page, ingredients)
    if uploaded == 0:
        char_count = sum(1 for ing in ingredients if 'персонаж' in ing.lower())
        if char_count > 0:
            print(f'  FAILED: No ingredients uploaded (0/{len(ingredients)}) — cannot generate without character references')
            return []
    elif uploaded < len(ingredients):
        print(f'  WARNING: Only {uploaded}/{len(ingredients)} ingredients loaded (need character refs for consistency)')
    try:
        variant_paths = _generate_frame_review(page, clip_id, component, prompt, attempt, ingredients=ingredients)
        record_attempt(manifest, component, attempt, prompt, variant_paths)
        save_manifest(clip_id, manifest)
        return variant_paths
    except Exception as e:
        print(f'  ERROR in review_nano_banana: {e}')
        take_debug_screenshot(page, f'{clip_id}_{component}_a{attempt}_error')
        return []


def review_veo(page, clip, manifest = None, attempt = None, first_frame = None, last_frame = None, prompt_override = None):
    '''Generate VEO video variants for review.

    Uploads frames, generates, downloads all video variants.
    Updates manifest with the attempt record.
    Returns list of variant paths.
    '''
    clip_id = clip['clip_id']
    prompt = sanitize_prompt(prompt_override if prompt_override else clip['veo_prompt'])
    print(f'''\n{'============================================================'}''')
    print(f'''  REVIEW — VEO 3.1 — {clip_id} — attempt {attempt}''')
    print(f'''{'============================================================'}''')
    print(f'''  Prompt: {prompt[:70]}...''')
    print(f'''  First frame: {first_frame.name}''')
    print(f'''  Last frame:  {last_frame.name}''')
    print('  Reloading page to clear VEO state...')
    page.goto(get_project_url(), timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    wait_for_flow_ready(page)
    switch_mode(page, 'Видео по кадрам')
    video_tab = page.query_selector('button[role="radio"]:has-text("Видео")')
    if video_tab:
        video_tab.click()
        time.sleep(2)
    # Stabilize gallery URL count before taking "before" snapshot
    prev_count = -1
    stable_count = 0
    for _ in range(10):
        urls = get_gallery_media_urls(page, 'video')
        if len(urls) == prev_count:
            stable_count += 1
            if stable_count >= 3:
                break
        else:
            stable_count = 0
        prev_count = len(urls)
        time.sleep(2)
    initial_urls = set(get_gallery_media_urls(page, 'video'))
    clear_veo_frame_slots(page)
    upload_frame_for_veo(page, first_frame, 0)
    upload_frame_for_veo(page, last_frame, 1)
    ensure_enhance_prompt_off(page)
    # Allow overriding VEO model (e.g. "Veo 3.1 - Quality" instead of default Fast)
    veo_model_override = clip.get('veo_model_override')
    if veo_model_override:
        set_image_model(page, veo_model_override)
        time.sleep(1)
    veo_variant_count = clip.get('veo_variant_count', 4)
    set_variant_count(page, veo_variant_count)
    clear_prompt(page)
    fill_prompt(page, prompt)
    take_debug_screenshot(page, f'{clip_id}_veo_a{attempt}_before_gen')
    click_generate(page)
    result = wait_for_new_gallery_item(page, initial_urls, tab='Видео')
    if result != 'success':
        take_debug_screenshot(page, f'{clip_id}_veo_a{attempt}_timeout')
        print(f'  FAILED: VEO generation for {clip_id} ({result})')
        return []
    dest_dir = REVIEW_DIR / clip_id / 'veo' / f'attempt_{attempt}'
    saved = download_all_new_videos(page, initial_urls, dest_dir)
    print(f'  Downloaded {len(saved)} video variants for attempt {attempt}')
    # Extract frames for review
    for i, vpath in enumerate(saved):
        frames_dir = dest_dir / f'variant_{i + 1}_frames'
        extract_frames(vpath, frames_dir, fps=1)
        if i < len(saved):
            record_entry = {'file': vpath.name, 'scores': None, 'avg': None,
                           'frames_dir': frames_dir.name, 'duration': get_video_duration(vpath)}
    record_attempt(manifest, 'veo', attempt, prompt, saved)
    save_manifest(clip_id, manifest)
    return saved


def process_clip(page = None, clip = None):
    '''Process a single clip: Nano Banana (first+last frames) → VEO animation.'''
    clip_id = clip['clip_id']
    print(f'''\n{'############################################################'}''')
    print(f'''  Processing clip: {clip_id}''')
    print(f'''  Scene: {clip['scene_id']} | Location: {clip['location']}''')
    print(f'''  Description: {clip['scene_description_ru']}''')
    print(f'''{'############################################################'}''')
    (first_frame, last_frame) = run_nano_banana_pass(page, clip)
    missing = []
    if not first_frame:
        missing.append('first')
    if not last_frame:
        missing.append('last')
    if missing:
        print(f'  SKIP VEO pass — missing frame(s): {", ".join(missing)}')
        return (first_frame, last_frame, None)
    print(f'  Waiting {PAUSE_BETWEEN_GENERATIONS}s (rate limiting)...')
    time.sleep(PAUSE_BETWEEN_GENERATIONS)
    video_path = run_veo_pass(page, clip, first_frame, last_frame)
    if video_path:
        print(f'  DONE: {clip_id}')
    else:
        print(f'  {clip_id} — VEO generation failed')
    return (first_frame, last_frame, video_path)

SCENE_DIR = OUTPUT_DIR / 'scene'

def _js_click_by_text(page = None, tag = None, text = None):
    '''Click element via JS to bypass overlay interception.'''
    return page.evaluate(f'''(text) => {{\n        const els = document.querySelectorAll(\'{tag}\');\n        for (const el of els) {{\n            if (el.textContent.trim().includes(text)) {{\n                const rect = el.getBoundingClientRect();\n                if (rect.width > 0) {{\n                    el.click();\n                    return {{ clicked: true, x: Math.round(rect.x), y: Math.round(rect.y) }};\n                }}\n            }}\n        }}\n        return {{ clicked: false }};\n    }}''', text)


def _add_clip_to_scene_by_prompt(page = None, veo_prompt = None):
    """Find a video in gallery by its VEO prompt and click 'Добавить в сцену'.

    The gallery shows videos with their prompt text. Each video card has
    an 'Добавить в сцену' button. We match by the first 50 chars of the prompt.
    """
    prompt_prefix = veo_prompt[:50]
    result = page.evaluate('(promptPrefix) => {\n        // Find all prompt text elements (shown as buttons below each video)\n        const promptBtns = [];\n        document.querySelectorAll(\'button\').forEach(btn => {\n            const text = btn.textContent.trim();\n            const rect = btn.getBoundingClientRect();\n            // Prompt buttons are wide (>400px) and in the gallery area\n            if (rect.width > 400 && rect.y > 100 && text.length > 30) {\n                promptBtns.push({ el: btn, text: text, y: rect.y });\n            }\n        });\n\n        // Find the prompt that matches\n        for (const pb of promptBtns) {\n            if (pb.text.substring(0, 50).includes(promptPrefix.substring(0, 40))) {\n                // Found matching video. Now find the closest "Добавить в сцену" button\n                // (it\'s above the prompt text in the same card)\n                const addBtns = document.querySelectorAll(\'button\');\n                let bestAdd = null;\n                let bestDist = Infinity;\n                for (const ab of addBtns) {\n                    if (ab.textContent.trim().includes(\'Добавить в сцену\')) {\n                        const aRect = ab.getBoundingClientRect();\n                        // Must be above the prompt (lower y) and relatively close\n                        const dist = Math.abs(aRect.y - pb.y);\n                        if (dist < bestDist && dist < 500) {\n                            bestDist = dist;\n                            bestAdd = ab;\n                        }\n                    }\n                }\n                if (bestAdd) {\n                    bestAdd.click();\n                    return {\n                        found: true,\n                        clicked: true,\n                        promptText: pb.text.substring(0, 60),\n                    };\n                }\n                return { found: true, clicked: false, reason: \'no add button near prompt\' };\n            }\n        }\n        return { found: false, clicked: false, promptPrefix: promptPrefix };\n    }', prompt_prefix)
    if result.get('clicked'):
        print(f'''    Added to scene: {result.get('promptText', '')[:50]}...''')
        return True
    if result.get('found'):
        print("    WARNING: found video but no 'Добавить в сцену' button")
        return False
    print(f'''    WARNING: video not found for prompt: {prompt_prefix[:40]}...''')
    return False


def _scroll_gallery_to_find_all(page = None):
    '''Scroll down in gallery to load all items.'''
    for _ in range(5):
        page.evaluate('window.scrollBy(0, 600)')
        time.sleep(1)
    page.evaluate('window.scrollTo(0, 0)')
    time.sleep(1)


def add_clips_to_scene(page = None, clips = None):
    """Add all clips to Scene Builder in order from the gallery.

    Steps:
      1. Ensure we're on the gallery view, video tab
      2. Scroll to load all videos
      3. For each clip (in order), find its video by VEO prompt and click 'Добавить в сцену'
    """
    print(f'''\n{'============================================================'}''')
    print(f'''  Adding {len(clips)} clips to Scene Builder''')
    print(f'''{'============================================================'}''')
    page.goto(get_project_url(), timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    wait_for_flow_ready(page)
    vid_tab = page.query_selector('button[role="radio"]:has-text("Видео")')
    if vid_tab:
        vid_tab.click()
        time.sleep(2)
    _scroll_gallery_to_find_all(page)
    added = 0
    for i, clip in enumerate(clips):
        clip_id = clip['clip_id']
        veo_prompt = clip['veo_prompt']
        print(f'''\n  [{i + 1}/{len(clips)}] Adding {clip_id}...''')
        if _add_clip_to_scene_by_prompt(page, veo_prompt):
            added += 1
            time.sleep(2)
            continue
        take_debug_screenshot(page, f'''scene_add_fail_{clip_id}''')
    print(f'''\n  Added {added}/{len(clips)} clips to scene.''')
    return added


def open_scene_builder(page = None):
    """Navigate to Scene Builder by clicking 'Конструктор сцен' in breadcrumb."""
    print('  Opening Scene Builder...')
    result = _js_click_by_text(page, 'button', 'Конструктор сцен')
    if not result.get('clicked'):
        page.goto(get_project_url(), timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
        wait_for_flow_ready(page)
        result = _js_click_by_text(page, 'button', 'Конструктор сцен')
    time.sleep(8)
    for _ in range(15):
        play = page.query_selector('button:has-text("play_arrow")')
        if play:
            box = play.bounding_box()
            if box and box['y'] > 500:
                print('  Scene Builder ready.')
                return True
        time.sleep(2)
    print('  WARNING: Scene Builder may not be fully loaded')
    return False


def _exit_reorder_mode(page = None):
    """Click 'Готово' if we're in reorder mode."""
    done_btn = page.query_selector('button:has-text("Готово")')
    if done_btn:
        box = done_btn.bounding_box()
        if box:
            if box['width'] > 0:
                done_btn.click()
                time.sleep(2)
                print('  Exited reorder mode.')
                return None
            return None
        return None


def download_scene(page = None, save_path = None):
    '''Download the scene from Scene Builder.

    Clicks the download button and handles the download.
    Returns True on success.
    '''
    _exit_reorder_mode(page)
    time.sleep(1)
    result = page.evaluate("() => {\n        const btns = document.querySelectorAll('button');\n        for (const btn of btns) {\n            const text = btn.textContent.trim();\n            const rect = btn.getBoundingClientRect();\n            const aria = btn.getAttribute('aria-label') || '';\n            // Download button near bottom-right of scene area\n            if ((text.includes('download') || text.includes('Скачать') || aria.includes('Скачать')) &&\n                rect.y > 600 && rect.y < 700) {\n                btn.click();\n                return { clicked: true, x: Math.round(rect.x), y: Math.round(rect.y) };\n            }\n        }\n        return { clicked: false };\n    }")
    if not result.get('clicked'):
        print('  WARNING: Download button not found in Scene Builder')
        take_debug_screenshot(page, 'scene_no_download_btn')
        return False
    print('  Clicked download. Waiting for rendering/download...')
    download_started = False
    for sec in range(120):
        time.sleep(2)
        progress = page.evaluate("() => {\n            const els = document.querySelectorAll('*');\n            for (const el of els) {\n                const text = (el.textContent || '').trim();\n                if ((text.includes('Рендеринг') || text.includes('Обработка') ||\n                     text.includes('Rendering') || text.includes('Загрузк') ||\n                     text.includes('Экспорт') || text.includes('%')) &&\n                    text.length < 100) {\n                    const rect = el.getBoundingClientRect();\n                    if (rect.width > 0) {\n                        return text;\n                    }\n                }\n            }\n            return null;\n        }")
        if progress:
            if sec % 10 == 0:
                print(f'''  Rendering: {progress[:60]}... ({sec * 2}s)''')
            continue
        scene_url = page.evaluate('() => {\n            // Check for a download link or video source that might be the rendered scene\n            const links = document.querySelectorAll(\'a[download], a[href*="scene"], a[href*="export"]\');\n            for (const a of links) {\n                if (a.href) return a.href;\n            }\n            return null;\n        }')
        if scene_url:
            print(f'''  Scene download URL found: {scene_url[:80]}...''')
            download_started = True
            return download_media_via_fetch(page, scene_url, save_path)
        if sec > 10 and not progress:
            break
    # Try to find scene video URL from video elements
    video_urls = page.evaluate("() => {\n        const results = [];\n        document.querySelectorAll('video').forEach(v => {\n            const rect = v.getBoundingClientRect();\n            if (rect.width > 200 && rect.y > 60 && rect.y < 600) {\n                const src = v.src || v.querySelector('source')?.src || '';\n                if (src) results.push(src);\n            }\n        });\n        return results;\n    }")
    if video_urls:
        print('  Found scene video URL, downloading...')
        url = video_urls[-1]
        return download_media_via_fetch(page, url, save_path)
    print('  WARNING: could not download scene')
    take_debug_screenshot(page, 'scene_download_failed')
    return False


def do_build_scene(pw = None, clip_filter = None):
    '''Build a scene in Scene Builder from generated clips.'''
    SCENE_DIR.mkdir(parents = True, exist_ok = True)
    if not PROMPTS_PATH.exists():
        print(f'''Error: prompts not found: {PROMPTS_PATH}''')
        sys.exit(1)
    clips = load_clips(PROMPTS_PATH, clip_filter)
    ready_clips = []
    for clip in clips:
        clip_id = clip['clip_id']
        video = CLIPS_DIR / f'''{clip_id}_clip.mp4'''
        if video.exists():
            ready_clips.append(clip)
            continue
        print(f'''  WARNING: clip {clip_id} not generated — skipping''')
    if not ready_clips:
        print('Error: no generated clips found. Run --run first.')
        sys.exit(1)
    print(f'''Building scene from {len(ready_clips)} clips.\n''')
    ctx = launch_browser(pw, headless = False)
    page = ctx.new_page()
    added = add_clips_to_scene(page, ready_clips)
    if added == 0:
        print('ERROR: no clips were added to scene')
        ctx.close()
        return None
    open_scene_builder(page)
    take_debug_screenshot(page, 'scene_builder_loaded')
    scene_path = SCENE_DIR / 'full_scene.mp4'
    if download_scene(page, scene_path):
        print(f'''\n  Scene saved: {scene_path}''')
        print(f'''  Size: {scene_path.stat().st_size} bytes''')
    else:
        print('\n  Scene download failed.')
    print('\n  Browser stays open 15s for inspection...')
    time.sleep(15)
    ctx.close()
    print('Scene build complete.')


def do_run(pw = None, clip_filter = None):
    '''Main bot run: process clips from prompts JSON.'''
    if not PROMPTS_PATH.exists():
        print(f'''Error: prompts not found: {PROMPTS_PATH}''')
        print('Run parse_scenario.py and generate_prompts.py first.')
        sys.exit(1)
    clips = load_clips(PROMPTS_PATH, clip_filter)
    print(f'''Loaded {len(clips)} clips to process.\n''')
    ctx = launch_browser(pw, headless = False)
    page = ctx.new_page()
    print("Navigating to project 'Автоматизация'...")
    page.goto(get_project_url(), timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    wait_for_flow_ready(page)
    results = {
        'ok': [],
        'fail': [] }
    for i, clip in enumerate(clips):
        clip_id = clip['clip_id']
        print(f'''\n[{i + 1}/{len(clips)}]''')
        process_clip(page, clip)
        first_f = FRAMES_DIR / f'''{clip_id}_first.png'''
        last_f = FRAMES_DIR / f'''{clip_id}_last.png'''
        video = CLIPS_DIR / f'''{clip_id}_clip.mp4'''
        if i < len(clips) - 1:
            print(f'''\nPausing {PAUSE_BETWEEN_GENERATIONS}s before next clip...''')
            time.sleep(PAUSE_BETWEEN_GENERATIONS)
    print(f'''\n{'============================================================'}''')
    print(f'''  Finished processing {len(clips)} clips.''')
    print(f'''  OK:   {results['ok']}''')
    print(f'''  FAIL: {results['fail']}''')
    print(f'''  Frames: {FRAMES_DIR}''')
    print(f'''  Clips:  {CLIPS_DIR}''')
    print(f'''{'============================================================'}''')
    ctx.close()


def _switch_account(pw, ctx, page):
    '''Switch to the other account. Closes current browser, opens new one.

    Returns (new_ctx, new_page) or (None, None) if second account not available.
    '''
    global _current_account_idx
    other = 1 - _current_account_idx
    other_session = ACCOUNTS[other]['session_dir']
    if not other_session.exists():
        print(f'''  Account {other + 1} session not found ({other_session.name}).''')
        print(f'''  Run: python scripts/flow_bot.py --login --account {other + 1}''')
        return (None, None)
    print(f'''\n  >>> Switching to account {other + 1} ({other_session.name})...''')
    ctx.close()
    _current_account_idx = other
    new_ctx = launch_browser(pw, headless = False, account = other)
    new_page = new_ctx.new_page()
    project_url = get_project_url(other)
    new_page.goto(project_url, timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    wait_for_flow_ready(new_page)
    return (new_ctx, new_page)


def do_review(pw = None, clip_filter = None):
    '''Generate variants for quality review.

    For each clip and component (nb_first, nb_last, veo):
      - Skip if already accepted or needs_manual_work
      - Determine attempt number
      - Generate variants and save to review folder
      - Update manifest

    On consecutive generation failures, auto-switches to the other account.
    '''
    if not PROMPTS_PATH.exists():
        print(f'''Error: prompts not found: {PROMPTS_PATH}''')
        sys.exit(1)
    clips = load_clips(PROMPTS_PATH, clip_filter)
    print(f'''Review mode: {len(clips)} clips to process.\n''')
    ctx = launch_browser(pw, headless = False)
    page = ctx.new_page()
    project_url = get_project_url()
    print("Navigating to project 'Автоматизация'...")
    page.goto(project_url, timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    wait_for_flow_ready(page)
    summary = {
        'generated': [],
        'skipped': [],
        'failed': [] }
    consecutive_errors = 0
    MAX_ERRORS_BEFORE_SWITCH = 2
    for i, clip in enumerate(clips):
        clip_id = clip['clip_id']
        print(f'''\n[{i + 1}/{len(clips)}] Review: {clip_id}''')
        manifest = load_manifest(clip_id)
        for component in ('nb_first', 'nb_last'):
            status = get_component_status(manifest, component)
            if status in ('accepted', 'needs_manual_work'):
                print(f'''  {component}: {status} — skipping''')
                summary['skipped'].append(f'''{clip_id}/{component}''')
                continue
            attempt = get_next_attempt(manifest, component)
            if attempt == 0:
                print(f'''  {component}: max attempts reached — marking needs_manual_work''')
                manifest['components'][component]['status'] = 'needs_manual_work'
                save_manifest(clip_id, manifest)
                summary['failed'].append(f'''{clip_id}/{component}''')
                continue
            prompt_override = None
            if attempt == 3:
                comp_data = manifest['components'][component]
                last_attempt = comp_data['attempts'][-1] if comp_data['attempts'] else None
                if last_attempt and last_attempt.get('rewritten_prompt'):
                    prompt_override = last_attempt['rewritten_prompt']
            first_frame_ref = None
            if component == 'nb_first':
                scene_ref = find_scene_ref_frame(clips, clip_id)
                if scene_ref:
                    first_frame_ref = scene_ref
                    print(f'''  Cross-clip ref: using {scene_ref.name} for scene consistency''')
            elif component == 'nb_last':
                first_sel = manifest['components']['nb_first'].get('selected_variant')
                if first_sel:
                    first_attempt_data = manifest['components']['nb_first']['attempts'][first_sel['attempt'] - 1]
                    first_file = first_attempt_data['variants'][first_sel['variant']]['file']
                    first_frame_path = REVIEW_DIR / clip_id / 'nb_first' / f'''attempt_{first_sel['attempt']}''' / first_file
                    if first_frame_path.exists():
                        first_frame_ref = first_frame_path
                        print(f'''  Using selected first frame as ingredient: {first_file}''')
                    else:
                        print(f'''  WARNING: Selected first frame not found: {first_frame_path}''')
                else:
                    print('  nb_last: waiting for nb_first selection — skipping (select first frame first)')
                    summary['skipped'].append(f'''{clip_id}/nb_last (waiting for first frame selection)''')
                    continue
            variants = review_nano_banana(page, clip, manifest, component, attempt, prompt_override, first_frame_ref = first_frame_ref)
            if variants:
                summary['generated'].append(f'''{clip_id}/{component}/a{attempt} ({len(variants)} variants)''')
                consecutive_errors = 0
            else:
                summary['failed'].append(f'''{clip_id}/{component}/a{attempt}''')
                consecutive_errors += 1
                if consecutive_errors >= MAX_ERRORS_BEFORE_SWITCH:
                    (new_ctx, new_page) = _switch_account(pw, ctx, page)
                    if new_ctx:
                        page = new_page
                        ctx = new_ctx
                        consecutive_errors = 0
                    else:
                        print('  No second account available — continuing with current.')
            if component == 'nb_first':
                print(f'''  Pausing {PAUSE_BETWEEN_GENERATIONS}s...''')
                time.sleep(PAUSE_BETWEEN_GENERATIONS)
        veo_status = get_component_status(manifest, 'veo')
        if veo_status in ('accepted', 'needs_manual_work'):
            print(f'''  veo: {veo_status} — skipping''')
            summary['skipped'].append(f'''{clip_id}/veo''')
        else:
            first_sel = manifest['components']['nb_first'].get('selected_variant')
            last_sel = manifest['components']['nb_last'].get('selected_variant')
            if not first_sel or not last_sel:
                print('  veo: waiting for frame selection — skipping')
                summary['skipped'].append(f'''{clip_id}/veo (waiting for frames)''')
            else:
                first_attempt = manifest['components']['nb_first']['attempts'][first_sel['attempt'] - 1]
                first_file = first_attempt['variants'][first_sel['variant']]['file']
                first_path = REVIEW_DIR / clip_id / 'nb_first' / f'''attempt_{first_sel['attempt']}''' / first_file
                last_attempt = manifest['components']['nb_last']['attempts'][last_sel['attempt'] - 1]
                last_file = last_attempt['variants'][last_sel['variant']]['file']
                last_path = REVIEW_DIR / clip_id / 'nb_last' / f'''attempt_{last_sel['attempt']}''' / last_file
                if not first_path.exists() or not last_path.exists():
                    print('  veo: selected frame files not found — skipping')
                    summary['skipped'].append(f'''{clip_id}/veo (missing frames)''')
                else:
                    attempt = get_next_attempt(manifest, 'veo')
                    if attempt == 0:
                        manifest['components']['veo']['status'] = 'needs_manual_work'
                        save_manifest(clip_id, manifest)
                        summary['failed'].append(f'''{clip_id}/veo''')
                    else:
                        prompt_override = None
                        if attempt == 3:
                            comp_data = manifest['components']['veo']
                            last_a = comp_data['attempts'][-1] if comp_data['attempts'] else None
                            if last_a and last_a.get('rewritten_prompt'):
                                prompt_override = last_a['rewritten_prompt']
                        print(f'''  Pausing {PAUSE_BETWEEN_GENERATIONS}s before VEO...''')
                        time.sleep(PAUSE_BETWEEN_GENERATIONS)
                        variants = review_veo(page, clip, manifest, attempt, first_path, last_path, prompt_override)
                        if variants:
                            summary['generated'].append(f'''{clip_id}/veo/a{attempt} ({len(variants)} variants)''')
                            consecutive_errors = 0
                        else:
                            summary['failed'].append(f'''{clip_id}/veo/a{attempt}''')
                            consecutive_errors += 1
                            if consecutive_errors >= MAX_ERRORS_BEFORE_SWITCH:
                                (new_ctx, new_page) = _switch_account(pw, ctx, page)
                                if new_ctx:
                                    page = new_page
                                    ctx = new_ctx
                                    consecutive_errors = 0
                                    print(f'''  Pausing {PAUSE_BETWEEN_GENERATIONS}s...''')
                                    time.sleep(PAUSE_BETWEEN_GENERATIONS)
        if i < len(clips) - 1:
            print(f'''\nPausing {PAUSE_BETWEEN_GENERATIONS}s before next clip...''')
            time.sleep(PAUSE_BETWEEN_GENERATIONS)
    print(f'''\n{'============================================================'}''')
    print('  Review generation complete.')
    print(f'''  Generated: {len(summary['generated'])}''')
    for g in summary['generated']:
        print(f'''    {g}''')
    print(f'''  Skipped:   {len(summary['skipped'])}''')
    for s in summary['skipped']:
        print(f'''    {s}''')
    print(f'''  Failed:    {len(summary['failed'])}''')
    for f in summary['failed']:
        print(f'''    {f}''')
    print(f'''\n  Review files: {REVIEW_DIR}''')
    print('  Use --status to see overview, --select to accept variants.')
    print(f'''{'============================================================'}''')
    ctx.close()


def do_select(clip_id, component, attempt = None, variant = None, scores_json = None, trim_start = None, trim_end = None):
    '''Select a variant and record its scores.

    If avg >= threshold: mark accepted, copy to output (trim VEO if params given).
    If avg < threshold: leave as pending for retry.
    Auto-cleans review folder when all 3 components are done.
    '''
    scores = json.loads(scores_json)
    for key in scores:
        if key not in SCORE_CRITERIA:
            print(f'''Warning: unknown score criterion \'{key}\'''')
    manifest = load_manifest(clip_id)
    comp = manifest['components'].get(component)
    if not comp:
        print(f'''Error: unknown component \'{component}\'''')
        sys.exit(1)
    if attempt > len(comp['attempts']):
        print(f'''Error: attempt {attempt} not found (only {len(comp['attempts'])} attempts recorded)''')
        sys.exit(1)
    attempt_entry = comp['attempts'][attempt - 1]
    if variant >= len(attempt_entry['variants']):
        print(f'''Error: variant {variant} not found''')
        sys.exit(1)
    non_zero = [v for v in scores.values() if v > 0]
    avg = sum(non_zero) / len(non_zero) if non_zero else 0
    print(f'''  Clip: {clip_id} | Component: {component} | Attempt: {attempt} | Variant: {variant}''')
    print(f'''  Scores: {scores}''')
    print(f'''  Average: {avg:.2f} (threshold: {QUALITY_THRESHOLD})''')
    if trim_start is not None or trim_end is not None:
        print(f'''  Trim: {trim_start}s — {trim_end}s''')
    if avg >= QUALITY_THRESHOLD:
        mark_selected(manifest, component, attempt, variant, scores, avg)
        if trim_start is not None:
            attempt_entry['variants'][variant]['trim_start'] = trim_start
        if trim_end is not None:
            attempt_entry['variants'][variant]['trim_end'] = trim_end
        save_manifest(clip_id, manifest)
        copy_selected_to_output(clip_id, manifest, trim_start, trim_end)
        print('  ACCEPTED — variant copied to output.')
        if _all_components_done(manifest):
            print(f'''\n  All components done for {clip_id} — cleaning up review files...''')
            cleanup_clip_review(clip_id, manifest)
    else:
        save_manifest(clip_id, manifest)
        print(f'''  BELOW THRESHOLD — score {avg:.2f}. Run --review to retry.''')


def do_fail(clip_id = None, component = None, attempt = None, scores_json = None):
    '''Mark all variants of an attempt as failed.'''
    manifest = load_manifest(clip_id)
    scores_per_variant = None
    if scores_json:
        scores_per_variant = json.loads(scores_json)
    mark_failed(manifest, component, attempt, scores_per_variant)
    save_manifest(clip_id, manifest)
    status = get_component_status(manifest, component)
    print(f'''  {clip_id}/{component} attempt {attempt} marked failed. Status: {status}''')
    if _all_components_done(manifest):
        print(f'''\n  All components done for {clip_id} — cleaning up review files...''')
        cleanup_clip_review(clip_id, manifest)
        return None


def do_extract_frames(clip_id = None, component = None, attempt = None):
    '''Extract frames from all video variants of an attempt.

    Creates frame_NNN.png files in variant_N_frames/ directories.
    Claude Code then reads these images to evaluate quality and pick best segment.
    '''
    manifest = load_manifest(clip_id)
    comp = manifest['components'].get(component)
    if not comp:
        print(f'''Error: unknown component \'{component}\'''')
        sys.exit(1)
    if attempt > len(comp['attempts']):
        print(f'''Error: attempt {attempt} not found (only {len(comp['attempts'])} attempts)''')
        sys.exit(1)
    attempt_entry = comp['attempts'][attempt - 1]
    attempt_dir = REVIEW_DIR / clip_id / component / f'''attempt_{attempt}'''
    print(f'''  Extracting frames for {clip_id}/{component}/attempt_{attempt}''')
    print(f'''  {len(attempt_entry['variants'])} variants\n''')
    for i, var in enumerate(attempt_entry['variants']):
        video_path = attempt_dir / var['file']
        if not video_path.exists():
            print(f'''  WARNING: {video_path.name} not found, skipping''')
            continue
        duration = get_video_duration(video_path)
        frames_dir = attempt_dir / f'''variant_{i + 1}_frames'''
        frames = extract_frames(video_path, frames_dir, fps = 1)
        var['frames_dir'] = frames_dir.name
        var['duration'] = duration
        print(f'''  variant_{i + 1}: {duration:.1f}s, {len(frames)} frames → {frames_dir.name}''')
    save_manifest(clip_id, manifest)
    print(f'''\n  Frames saved to: {attempt_dir}''')
    print('  Read frame images to evaluate quality and determine best trim segment.')


def do_status(clip_filter = None):
    '''Print status overview of all clips and their review state.'''
    if not PROMPTS_PATH.exists():
        print(f'''Error: prompts not found: {PROMPTS_PATH}''')
        sys.exit(1)
    clips = load_clips(PROMPTS_PATH, clip_filter)
    print(f'''\n{'======================================================================'}''')
    print(f'''  {'CLIP':<10} {'NB_FIRST':<18} {'NB_LAST':<18} {'VEO':<18}''')
    print(f'''  {'----------'} {'------------------'} {'------------------'} {'------------------'}''')
    cols = {'total': 0, 'accepted': 0, 'awaiting': 0, 'pending': 0, 'manual': 0}
    for clip in clips:
        clip_id = clip['clip_id']
        manifest = load_manifest(clip_id)
        cols['total'] += 1
        comp = []
        for c in ('nb_first', 'nb_last', 'veo'):
            status = get_component_status(manifest, c)
            n_attempts = len(manifest['components'][c]['attempts'])
            if status == 'accepted':
                cols['accepted'] += 1
                comp.append('ACCEPTED')
            elif status == 'needs_manual_work':
                cols['manual'] += 1
                comp.append('MANUAL')
            elif n_attempts > 0:
                cols['awaiting'] += 1
                best = manifest['components'][c]['attempts'][-1].get('best_avg')
                if best:
                    comp.append(f'''a{n_attempts} best={best:.1f} awaiting''')
                else:
                    comp.append(f'''a{n_attempts} awaiting''')
            else:
                cols['pending'] += 1
                comp.append('pending')
        print(f'''  {clip_id:<10} {comp[0]:<18} {comp[1]:<18} {comp[2]:<18}''')
    print(f'''{'======================================================================'}''')
    print(f'''  Total: {cols['total']} | Accepted: {cols['accepted']} | Awaiting review: {cols['awaiting']} | Pending: {cols['pending']} | Manual: {cols['manual']}''')


def do_set_rewrite(clip_id = None, component = None, new_prompt = None):
    '''Store a rewritten prompt for the next attempt (attempt 3).'''
    manifest = load_manifest(clip_id)
    comp = manifest['components'].get(component)
    if not comp:
        print(f'''Error: unknown component \'{component}\'''')
        sys.exit(1)
    if not comp['attempts']:
        print(f'''Error: no attempts recorded yet for {clip_id}/{component}''')
        sys.exit(1)
    comp['attempts'][-1]['rewritten_prompt'] = new_prompt
    save_manifest(clip_id, manifest)
    print(f'''  Rewritten prompt stored for {clip_id}/{component}.''')
    print('  Run --review to generate with new prompt.')


def main():
    global _current_account_idx
    parser = argparse.ArgumentParser(description = 'Flow automation bot')
    group = parser.add_mutually_exclusive_group(required = True)
    group.add_argument('--login', action = 'store_true', help = 'Open browser for Google login (first time setup)')
    group.add_argument('--run', action = 'store_true', help = 'Run bot to generate clips')
    group.add_argument('--scene', action = 'store_true', help = 'Build scene in Scene Builder from generated clips')
    group.add_argument('--review', action = 'store_true', help = 'Generate variants for quality review')
    group.add_argument('--select', action = 'store_true', help = 'Accept a variant with scores')
    group.add_argument('--fail', action = 'store_true', help = 'Mark an attempt as failed')
    group.add_argument('--status', action = 'store_true', help = 'Show review status of all clips')
    group.add_argument('--rewrite', action = 'store_true', help = 'Store a rewritten prompt for retry')
    group.add_argument('--extract-frames', action = 'store_true', help = 'Extract frames from video variants for visual review')
    parser.add_argument('--clip', type = str, default = None, help = 'Process only this clip (e.g. S02_A)')
    parser.add_argument('--component', type = str, default = None, choices = [
        'nb_first',
        'nb_last',
        'veo'], help = 'Component for --select/--fail/--rewrite/--extract-frames')
    parser.add_argument('--attempt', type = int, default = None, help = 'Attempt number for --select/--fail/--extract-frames')
    parser.add_argument('--variant', type = int, default = None, help = 'Variant index (0-based) for --select')
    parser.add_argument('--scores', type = str, default = None, help = 'JSON scores for --select/--fail, e.g. \'{"char":8,"comp":7,"loc":8,"anim":0,"artifacts":9,"overall":8,"style":7}\'')
    parser.add_argument('--trim-start', type = float, default = None, help = 'Trim start time in seconds for VEO --select')
    parser.add_argument('--trim-end', type = float, default = None, help = 'Trim end time in seconds for VEO --select')
    parser.add_argument('--prompt', type = str, default = None, help = 'New prompt text for --rewrite')
    parser.add_argument('--headless', action = 'store_true', help = 'Run in headless mode (not recommended for first run)')
    parser.add_argument('--account', type = int, default = 1, choices = [
        1,
        2], help = 'Account number (1 or 2). Use --login --account 2 to set up second account')
    args = parser.parse_args()
    _current_account_idx = args.account - 1
    ensure_dirs()
    if args.select:
        if not all([args.clip, args.component, args.attempt, args.variant is not None, args.scores]):
            parser.error('--select requires --clip, --component, --attempt, --variant, --scores')
        do_select(args.clip, args.component, args.attempt, args.variant, args.scores, args.trim_start, args.trim_end)
    elif args.fail:
        if not all([args.clip, args.component, args.attempt]):
            parser.error('--fail requires --clip, --component, --attempt')
        do_fail(args.clip, args.component, args.attempt, args.scores)
    elif args.rewrite:
        if not all([args.clip, args.component, args.prompt]):
            parser.error('--rewrite requires --clip, --component, --prompt')
        do_set_rewrite(args.clip, args.component, args.prompt)
    elif args.extract_frames:
        if not all([args.clip, args.component, args.attempt]):
            parser.error('--extract-frames requires --clip, --component, --attempt')
        do_extract_frames(args.clip, args.component, args.attempt)
    elif args.status:
        do_status(args.clip)
    else:
        # Set global timeout to prevent infinite hangs
        timeout = GLOBAL_TIMEOUT_SEC
        if args.login:
            timeout = 600  # 10 min for login (manual interaction)
        signal.signal(signal.SIGALRM, _global_timeout_handler)
        signal.alarm(timeout)
        print(f'  Global timeout: {timeout}s ({timeout // 60}m)')

        with sync_playwright() as pw:
            global _active_pw
            _active_pw = pw
            try:
                if args.login:
                    do_login(pw)
                elif args.run:
                    do_run(pw, args.clip)
                elif args.review:
                    do_review(pw, args.clip)
                elif args.scene:
                    do_build_scene(pw, args.clip)
            except GlobalTimeoutError:
                print('\nTimeout — exiting.')
                sys.exit(42)
            finally:
                signal.alarm(0)  # cancel alarm
                if _active_context:
                    try:
                        _active_context.close()
                    except Exception:
                        pass


if __name__ == '__main__':
    main()
