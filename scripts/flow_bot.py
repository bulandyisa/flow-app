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
_active_browser = None  # Set when using CDP mode (connect_over_cdp)
_active_pw = None
_cdp_port = None  # Set via --cdp-port CLI arg

GLOBAL_TIMEOUT_SEC = int(os.environ.get('FLOW_TIMEOUT', 600))  # default 10 min
QUALITY_THRESHOLD = 9.0


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

STEALTH_JS = """
// Hide webdriver property
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

// Mock chrome.runtime to look like a real Chrome
if (!window.chrome) { window.chrome = {}; }
if (!window.chrome.runtime) {
    window.chrome.runtime = {
        connect: function() {},
        sendMessage: function() {},
    };
}

// chrome.app mock (from playwright-stealth)
if (!window.chrome.app) {
    window.chrome.app = {
        isInstalled: false,
        InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
        RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
    };
}

// chrome.csi (from playwright-stealth)
if (!window.chrome.csi) {
    window.chrome.csi = function() {
        return { startE: Date.now(), onloadT: Date.now(), pageT: Math.random() * 1000 + 500, tran: 15 };
    };
}

// chrome.loadTimes (from playwright-stealth)
if (!window.chrome.loadTimes) {
    window.chrome.loadTimes = function() {
        return {
            commitLoadTime: Date.now() / 1000,
            connectionInfo: 'h2',
            finishDocumentLoadTime: Date.now() / 1000 + 0.5,
            finishLoadTime: Date.now() / 1000 + 1,
            firstPaintAfterLoadTime: 0,
            firstPaintTime: Date.now() / 1000 + 0.1,
            navigationType: 'Other',
            npnNegotiatedProtocol: 'h2',
            requestTime: Date.now() / 1000 - 0.5,
            startLoadTime: Date.now() / 1000 - 1,
            wasAlternateProtocolAvailable: false,
            wasFetchedViaSpdy: true,
            wasNpnNegotiated: true,
        };
    };
}

// Override permissions query to hide automation
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({state: Notification.permission})
        : originalQuery(parameters);

// Realistic plugins array
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {name: 'Native Client', filename: 'internal-nacl-plugin'},
        ];
        plugins.length = 3;
        return plugins;
    }
});

// Realistic languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['ru-RU', 'ru', 'en-US', 'en']
});

// WebGL vendor/renderer (Apple M1 Pro / macOS)
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Google Inc. (Apple)';
    if (parameter === 37446) return 'ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)';
    return getParameter.call(this, parameter);
};
if (typeof WebGL2RenderingContext !== 'undefined') {
    const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
    WebGL2RenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Google Inc. (Apple)';
        if (parameter === 37446) return 'ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)';
        return getParameter2.call(this, parameter);
    };
}

// Hardware concurrency (Apple M1 Pro = 10 cores)
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 10 });

// Device memory
Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

// Screen dimensions (MacBook Pro 14" Retina)
Object.defineProperty(screen, 'width', { get: () => 2560 });
Object.defineProperty(screen, 'height', { get: () => 1600 });
Object.defineProperty(screen, 'availWidth', { get: () => 2560 });
Object.defineProperty(screen, 'availHeight', { get: () => 1575 });
Object.defineProperty(screen, 'colorDepth', { get: () => 30 });
Object.defineProperty(screen, 'pixelDepth', { get: () => 30 });

// Connection API
if (navigator.connection) {
    Object.defineProperty(navigator.connection, 'effectiveType', { get: () => '4g' });
    Object.defineProperty(navigator.connection, 'rtt', { get: () => 50 });
    Object.defineProperty(navigator.connection, 'downlink', { get: () => 10 });
}

// Notification permission
Object.defineProperty(Notification, 'permission', { get: () => 'default' });
"""
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / '.session'
PROMPTS_PATH = PROJECT_ROOT / 'output' / 'prompts' / 'all_prompts.json'
REF_TASKS_PATH = PROJECT_ROOT / 'output' / 'prompts' / 'ref_tasks.json'
REFS_DIR = PROJECT_ROOT
OUTPUT_DIR = PROJECT_ROOT / 'output'
GENERATED_REFS_DIR = OUTPUT_DIR / 'generated_refs'
FRAMES_DIR = OUTPUT_DIR / 'frames'
CLIPS_DIR = OUTPUT_DIR / 'clips'
SCREENSHOTS_DIR = OUTPUT_DIR / 'screenshots'
REVIEW_DIR = OUTPUT_DIR / 'review'
FLOW_URL = 'https://labs.google/fx/ru/tools/flow'
ACCOUNTS = [
    {   # Bot 1 — Аккаунт 1, основная сессия (helper1)
        'session_dir': PROJECT_ROOT / '.session',
        'project_url': 'https://labs.google/fx/tools/flow/project/30ef5dbf-fe01-44af-8a3e-63e36b476730',
    },
    {   # Bot 2 — Аккаунт 1, клон сессии (helper2)
        'session_dir': PROJECT_ROOT / '.session_1b',
        'project_url': 'https://labs.google/fx/ru/tools/flow/project/e65e372b-9062-44e6-bfc4-b7ed17de5a4c',
    },
    {   # Bot 3 — Аккаунт 2, основная сессия (helper3)
        'session_dir': PROJECT_ROOT / '.session_2',
        'project_url': 'https://labs.google/fx/ru/tools/flow/project/492b843c-217a-4c83-8c2d-4e0b0f0b1dc8',
    },
    {   # Bot 4 — Аккаунт 2, клон сессии (helper4)
        'session_dir': PROJECT_ROOT / '.session_2b',
        'project_url': 'https://labs.google/fx/ru/tools/flow/project/32329ba5-c927-4be9-a40b-74ae7335d768',
    },
]
_current_account_idx = 0
_disable_gpu = False
_expecting_filechooser = False  # True when bot is about to trigger a file chooser intentionally
PAUSE_BETWEEN_GENERATIONS = 45
PAGE_LOAD_TIMEOUT = 120000
GENERATION_TIMEOUT = 300
POLL_INTERVAL = 5
SCORE_CRITERIA = [
    # Group 1: Character Identity
    'char_face',       # face match to reference
    'char_outfit',     # clothing & accessories match
    'char_count',      # correct number of characters
    # Group 2: Anatomy
    'anatomy_hands',   # fingers count, hand poses
    'anatomy_body',    # body proportions, natural pose
    'anatomy_face',    # facial symmetry, eyes, mouth
    # Group 3: Scale & Physics
    'scale',           # object sizes relative to each other
    'physics',         # gravity, ground contact, no floating
    'spatial',         # no clipping, merging, pass-through
    # Group 4: Scenario Fidelity
    'scenario_action', # correct action per script
    'scenario_emotion',# correct emotion/expression
    'scenario_objects',# right props present, no extras
    # Group 5: Location
    'loc_match',       # location matches reference
    'lighting',        # consistent lighting & shadows
    # Group 6: Technical Quality
    'artifacts',       # no generation artifacts/glitches
    'style_3d',        # consistent Pixar 3D style
    # Group 7: Cinematography
    'composition',     # framing, rule of thirds, focus
    'continuity',      # consistency with prev/next frames (0=n/a)
]
# If ANY critical criterion scores <= 5, auto-reject regardless of average
CRITICAL_CRITERIA = [
    'anatomy_hands',
    'anatomy_body',
    'scale',
    'physics',
    'spatial',
    'char_count',
]
SCORE_THRESHOLD = 9
CRITICAL_MIN_SCORE = 6
MAX_ATTEMPTS = 5
CLEANUP_LOG_PATH = OUTPUT_DIR / 'review' / 'cleanup_log.txt'
import re as _re

def validate_nb_prompt(prompt, clip_id=None):
    '''Validate a Nano Banana prompt against PROMPT_SPEC.md rules.

    Checks for forbidden patterns (appearance descriptions, furniture placement,
    age/gender words, interior details) and required elements.
    Prints warnings but does NOT block generation — just logs issues.
    Returns list of warning strings (empty = clean prompt).
    '''
    warnings = []
    p_lower = prompt.lower()

    # --- FORBIDDEN: clothing/appearance words (regex word boundaries to avoid false positives) ---
    appearance_patterns = [
        (r'\bhoodie\b', 'hoodie'), (r'\bshirt\b', 'shirt'), (r'\bjeans\b', 'jeans'),
        (r'\bpants\b', 'pants'), (r'\bshoes\b', 'shoes'), (r'\bjacket\b', 'jacket'),
        (r'\b(?:base)?cap\b', 'cap'), (r'\bhat\b', 'hat'), (r'\bdress\b', 'dress'),
        (r'\bskirt\b', 'skirt'), (r'\bshorts\b', 'shorts'), (r'\bsneakers\b', 'sneakers'),
        (r'\bboots\b', 'boots'), (r'\bvest\b', 'vest'), (r'\bsweater\b', 'sweater'),
        (r'\bcoat\b', 'coat'), (r'\bscarf\b', 'scarf'), (r'\bgloves\b', 'gloves'),
        (r'\bstriped\b', 'striped'), (r'\bcheckered\b', 'checkered'),
        (r'grey hoodie', 'grey hoodie'), (r'black hoodie', 'black hoodie'),
        (r'\bblonde hair\b', 'blonde hair'), (r'\bbrown hair\b', 'brown hair'),
        (r'\btall\b', 'tall'), (r'\bthin\b', 'thin'), (r'\bmuscular\b', 'muscular'),
    ]
    for pattern, label in appearance_patterns:
        if _re.search(pattern, p_lower):
            warnings.append(f'APPEARANCE: "{label}" — never describe character looks')

    # --- FORBIDDEN: age/gender (word-boundary regex to avoid "old paper", "cape", etc.) ---
    age_gender_patterns = [
        (r'\bboy\b', 'boy'), (r'\bgirl\b', 'girl'), (r'\bchild\b', 'child'),
        (r'\bteen\b', 'teen'), (r'\bteenager\b', 'teenager'),
        (r'\badult\b', 'adult'), (r'\bman\b', 'man'), (r'\bwoman\b', 'woman'),
        (r'\byoung\b', 'young'), (r'\bolderly\b', 'elderly'),
        # "he/she/his/her" — only flag standalone pronouns, not inside words
        (r'\bhe\b(?! [a-z]*s\b)', 'he'), (r'\bshe\b', 'she'),
    ]
    for pattern, label in age_gender_patterns:
        if _re.search(pattern, p_lower):
            warnings.append(f'AGE/GENDER: "{label}" — use "the character" instead')

    # --- FORBIDDEN: spatial placement ---
    spatial_patterns = [
        'on the left side', 'on the right side', 'on the left', 'on the right',
        'in the center', 'in the middle of the room',
        'left side of', 'right side of',
    ]
    for pattern in spatial_patterns:
        if pattern in p_lower:
            warnings.append(f'SPATIAL: "{pattern}" — don\'t control left/right placement')

    # --- FORBIDDEN: interior/exterior description ---
    interior_words = [
        'plain walls', 'wooden floor', 'no photos', 'no pictures', 'no portraits',
        'the walls are', 'the floor is', 'the ceiling',
        'sofa visible', 'workbench visible', 'desk visible',
        'visible on the', 'visible in the',
    ]
    for word in interior_words:
        if word in p_lower:
            warnings.append(f'INTERIOR: "{word}" — location comes from reference image')

    # --- REQUIRED: style tag ---
    if '3d pixar' not in p_lower and 'pixar-style' not in p_lower:
        warnings.append('MISSING: "3D Pixar-style animation" style tag')

    # --- REQUIRED: location reference ---
    if 'as the exact background' not in p_lower and 'as the background' not in p_lower:
        if 'exact background location' not in p_lower:
            warnings.append('MISSING: location reference "Use Image N as the exact background location"')

    # --- REQUIRED: camera angle ---
    camera_angles = ['close-up', 'closeup', 'medium shot', 'wide shot', 'establishing shot',
                     'over-the-shoulder', 'extreme close', 'medium wide']
    if not any(angle in p_lower for angle in camera_angles):
        warnings.append('MISSING: camera angle (close-up, medium shot, wide shot, etc.)')

    # --- RECOMMENDED: identity lock in first 10 words ---
    first_15_words = ' '.join(prompt.split()[:15]).lower()
    has_early_ref = any(x in first_15_words for x in [
        'exact character from image', 'character from image', 'the hand of',
        'over-the-shoulder', 'first, the exact', 'first, the character',
        'the face of', 'three characters',
    ])
    if not has_early_ref:
        warnings.append('IDENTITY: character reference should be in first 10-15 words for identity locking')

    # --- RECOMMENDED: "preserving identical facial features" for first mention ---
    if 'exact character from image' in p_lower and 'preserving identical' not in p_lower:
        warnings.append('IDENTITY: consider adding "preserving identical facial features and proportions"')

    # --- RECOMMENDED: chain-of-thought for multi-character (2+ characters, not counting location) ---
    char_refs = _re.findall(r'(?:exact )?character from image \d', p_lower)
    if len(char_refs) >= 2:
        if not any(w in p_lower for w in ['first,', 'then,', 'finally,']):
            warnings.append('COMPOSITION: use "First... Then..." chain-of-thought for multi-character scenes')

    # --- SCREENPLAY FIDELITY: exaggeration words ---
    exaggeration_patterns = [
        (r'\benormous\b', 'enormous'), (r'\bhuge\b', 'huge'), (r'\bmassive\b', 'massive'),
        (r'\bgigantic\b', 'gigantic'), (r'\btiny\b', 'tiny'), (r'\bcolossal\b', 'colossal'),
        (r'\bimmense\b', 'immense'), (r'\btowering\b', 'towering'),
    ]
    for pattern, label in exaggeration_patterns:
        if _re.search(pattern, p_lower):
            warnings.append(f'FIDELITY: "{label}" — avoid exaggeration; use scale words from screenplay only')

    # --- WARNING: prompt too long ---
    word_count = len(prompt.split())
    if word_count > 100:
        warnings.append(f'LENGTH: {word_count} words — try to keep under 80 (excluding style tag)')

    # --- Print warnings ---
    if warnings:
        label = clip_id or 'prompt'
        print(f'\n  {"!"*50}')
        print(f'  PROMPT VALIDATION WARNINGS for {label}:')
        for w in warnings:
            print(f'    - {w}')
        print(f'  {"!"*50}')

    return warnings


def validate_veo_prompt(prompt, clip_id=None):
    '''Validate a VEO prompt against VEO_PROMPT_SPEC.md rules.

    Checks for: camera movement, audio layer, forbidden patterns
    (appearance, interior, exaggeration), prompt length, and
    screenplay fidelity markers.
    Prints warnings but does NOT block generation.
    Returns list of warning strings (empty = clean prompt).
    '''
    warnings = []
    p_lower = prompt.lower()

    # --- REQUIRED: camera movement ---
    camera_movements = [
        'dolly', 'tracking shot', 'pan left', 'pan right', 'crane',
        'push in', 'pull back', 'pulls back', 'static shot', 'locked-off',
        'handheld', 'slow zoom', 'zoom in', 'zoom out', 'over-the-shoulder',
        'camera follows', 'camera holds', 'camera tracks', 'camera slowly',
        'camera moves', 'camera pulls', 'camera pushes', 'slider',
        'aerial', 'drone shot', 'arc shot', 'orbit',
    ]
    if not any(cm in p_lower for cm in camera_movements):
        warnings.append('CAMERA: no camera movement specified — add dolly/tracking/pan/static/etc.')

    # --- RECOMMENDED: audio layer ---
    audio_markers = ['audio:', 'sfx:', 'ambient:', 'sound of', 'sound:', 'dialogue:',
                     'crackling', 'footsteps', 'silence', 'quiet', 'hum', 'beep',
                     'static', 'crackle', 'whisper']
    if not any(am in p_lower for am in audio_markers):
        warnings.append('AUDIO: no audio direction — consider adding Audio: [SFX/ambient]')

    # --- FORBIDDEN: appearance description (same as NB) ---
    appearance_patterns = [
        (r'\bhoodie\b', 'hoodie'), (r'\bshirt\b', 'shirt'), (r'\bjeans\b', 'jeans'),
        (r'\bjacket\b', 'jacket'), (r'\b(?:base)?cap\b', 'cap'),
        (r'\bdress\b', 'dress'), (r'\bsneakers\b', 'sneakers'),
        (r'\bstriped\b', 'striped'), (r'\bgrey hoodie\b', 'grey hoodie'),
        (r'\bblack hoodie\b', 'black hoodie'),
        (r'\bblonde hair\b', 'blonde hair'), (r'\bbrown hair\b', 'brown hair'),
    ]
    for pattern, label in appearance_patterns:
        if _re.search(pattern, p_lower):
            warnings.append(f'APPEARANCE: "{label}" — VEO sees characters on frames')

    # --- FORBIDDEN: interior/furniture description ---
    interior_words = [
        'wooden workbench', 'tools on wall', 'pegboard', 'sofa visible',
        'plain walls', 'wooden floor', 'the walls are', 'the floor is',
    ]
    for word in interior_words:
        if word in p_lower:
            warnings.append(f'INTERIOR: "{word}" — VEO sees setting from frames')

    # --- FORBIDDEN: exaggeration ---
    exaggeration_patterns = [
        (r'\benormous\b', 'enormous'), (r'\bhuge\b', 'huge'), (r'\bmassive\b', 'massive'),
        (r'\bgigantic\b', 'gigantic'), (r'\bcolossal\b', 'colossal'),
        (r'\btowering\b', 'towering'),
    ]
    for pattern, label in exaggeration_patterns:
        if _re.search(pattern, p_lower):
            warnings.append(f'FIDELITY: "{label}" — avoid exaggeration; use scale words from screenplay')

    # --- REQUIRED: style tag ---
    if '3d pixar' not in p_lower and 'pixar-style' not in p_lower:
        warnings.append('MISSING: "3D Pixar-style animation" style tag')

    # --- WARNING: too many actions (heuristic: count main verbs of motion) ---
    action_verbs = _re.findall(
        r'\b(?:walks|runs|turns|reaches|grabs|picks up|sets down|stands up|sits down|opens|closes|enters|exits|leans|steps)\b',
        p_lower)
    if len(action_verbs) > 4:
        warnings.append(f'OVERLOADED: {len(action_verbs)} action verbs — keep to 1-2 main actions per clip')

    # --- WARNING: prompt length ---
    word_count = len(prompt.split())
    if word_count > 100:
        warnings.append(f'LENGTH: {word_count} words — try to keep VEO prompts under 80 words')

    # --- WARNING: static description instead of motion ---
    static_patterns = [
        (r'\bis sitting\b', 'is sitting'), (r'\bis standing\b', 'is standing'),
        (r'\bis looking\b', 'is looking'), (r'\bis lying\b', 'is lying'),
        (r'\bappears to be\b', 'appears to be'),
    ]
    for pattern, label in static_patterns:
        if _re.search(pattern, p_lower):
            warnings.append(f'STATIC: "{label}" — use motion verbs (sits→reaches, stands→walks)')

    # --- Print warnings ---
    if warnings:
        label = clip_id or 'veo_prompt'
        print(f'\n  {"!"*50}')
        print(f'  VEO PROMPT VALIDATION WARNINGS for {label}:')
        for w in warnings:
            print(f'    - {w}')
        print(f'  {"!"*50}')

    return warnings


def _sanitize_common(prompt):
    '''Common sanitization: remove ages, replace trigger words.'''
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
    return p


def sanitize_prompt(prompt = None):
    '''Sanitize VEO (video) prompt.

    - Common: remove ages, replace trigger words
    - Ensure \'3D Pixar-style animation\' is present
    - Add \'no subtitles\' if missing
    '''
    p = _sanitize_common(prompt)
    if '3D Pixar' not in p and 'Pixar-style' not in p:
        p = p.rstrip('. ') + '. 3D Pixar-style animation, family-friendly.'
    if 'no subtitle' not in p.lower():
        p = p.rstrip('. ') + '. No subtitles.'
    return p


def sanitize_nb_prompt(prompt = None):
    '''Sanitize NB (image) prompt.

    - Common: remove ages, replace trigger words
    - Ensure Pixar style tag is present (without word "animation")
    - Do NOT add "no subtitles" (irrelevant for images)
    '''
    p = _sanitize_common(prompt)
    if '3D Pixar' not in p and 'Pixar-style' not in p:
        p = p.rstrip('. ') + '. 3D Pixar-style, family-friendly.'
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
    GENERATED_REFS_DIR.mkdir(parents = True, exist_ok = True)


def launch_browser(pw = None, headless = None, account = None, cdp_port = None):
    '''Launch Chromium with persistent context OR connect to existing Chrome via CDP.

    account: 0-based index into ACCOUNTS list. None uses _current_account_idx.
    cdp_port: if set, connect to already-running Chrome on this port instead of launching.
              User must start Chrome manually first with: ./scripts/launch_chrome.sh N
    '''
    global _active_context, _active_browser

    # --- CDP mode: connect to user-launched Chrome ---
    if cdp_port:
        print(f'  Connecting to Chrome via CDP on port {cdp_port}...')
        browser = pw.chromium.connect_over_cdp(f'http://localhost:{cdp_port}')
        _active_browser = browser
        # Use the first (default) context — this is the user's browser context
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        _active_context = ctx
        print(f'  Connected! Contexts: {len(browser.contexts)}, Pages: {len(ctx.pages)}')
        # Setup file chooser handler on existing pages
        def _dismiss_unexpected_fc(fc):
            global _expecting_filechooser
            if _expecting_filechooser:
                return
            try:
                fc.set_files([])
                print('  (auto-dismissed unexpected file chooser dialog)')
            except Exception:
                pass
        for p in ctx.pages:
            p.on('filechooser', _dismiss_unexpected_fc)
        ctx.on('page', lambda p: p.on('filechooser', _dismiss_unexpected_fc))
        return ctx

    # --- Standard mode: launch new Chrome instance ---
    acct = ACCOUNTS[account if account is not None else _current_account_idx]
    session_dir = acct['session_dir']
    session_dir.mkdir(parents=True, exist_ok=True)
    # Remove stale lock files from previous crashed sessions
    for lock_file in ('SingletonLock', 'SingletonCookie', 'SingletonSocket'):
        lock_path = session_dir / lock_file
        if lock_path.exists():
            lock_path.unlink()
    vp_w = 1440 + random.randint(-20, 20)
    vp_h = 900 + random.randint(-15, 15)
    print(f'  Using account {account if account is not None else _current_account_idx} (session: {session_dir.name})')
    print(f'  Viewport: {vp_w}x{vp_h}')
    chrome_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=AutomationControlled',
            '--disable-infobars',
            '--disable-dev-shm-usage',
            '--no-first-run',
            '--no-default-browser-check',
            f'--window-size={vp_w + random.randint(0, 10)},{vp_h + random.randint(50, 80)}',
    ]
    if _disable_gpu:
        chrome_args += [
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-gpu-compositing',
        ]
        print(f'  GPU disabled (CPU rendering)')
    ctx = pw.chromium.launch_persistent_context(
        str(session_dir),
        headless=headless,
        channel='chrome',
        viewport={'width': vp_w, 'height': vp_h},
        locale='ru-RU',
        args=chrome_args,
    )
    print(f'  Browser: system Chrome (channel=chrome)')
    ctx.add_init_script(STEALTH_JS)
    # Auto-dismiss unexpected file chooser dialogs (Flow UI triggers one on page load since Feb 2026)
    def _dismiss_unexpected_fc(fc):
        global _expecting_filechooser
        if _expecting_filechooser:
            return  # Let expect_file_chooser handle it
        try:
            fc.set_files([])
            print('  (auto-dismissed unexpected file chooser dialog)')
        except Exception:
            pass
    for p in ctx.pages:
        p.on('filechooser', _dismiss_unexpected_fc)
    ctx.on('page', lambda p: p.on('filechooser', _dismiss_unexpected_fc))
    _active_context = ctx
    return ctx


def _get_or_create_flow_page(ctx):
    '''Find an existing Flow tab or create a new one.
    In CDP mode, Chrome may have many tabs open — find the one with Flow.
    When multiple Flow tabs exist, prefer the one with the longest title
    (active projects have titles like "Flow - Feb 26 - 22:26", not just "Flow").
    In standard mode (launch_persistent_context), just create a new page.
    '''
    if _cdp_port and ctx.pages:
        # Collect all Flow tabs
        flow_pages = []
        for p in ctx.pages:
            try:
                url = p.url or ''
                if 'labs.google' in url and '/flow' in url:
                    title = ''
                    try:
                        title = p.title() or ''
                    except Exception:
                        pass
                    flow_pages.append((p, url, title))
                    print(f'  Found Flow tab: title="{title[:60]}" url={url[:80]}')
            except Exception:
                continue
        if flow_pages:
            # Prefer tab with longest title (active project has date in title)
            flow_pages.sort(key = lambda x: len(x[2]), reverse = True)
            best = flow_pages[0]
            print(f'  Using Flow tab: "{best[2][:60]}" ({best[1][:80]})')
            return best[0]
        # No Flow tabs — reuse any non-chrome tab
        for p in ctx.pages:
            try:
                url = p.url or ''
                if url and url != 'about:blank' and 'chrome://' not in url:
                    print(f'  No Flow tab found, reusing tab: {url[:50]}')
                    return p
            except Exception:
                continue
        print(f'  No suitable tab found, creating new tab')
        return ctx.new_page()
    return ctx.new_page()


def get_project_url(account = None):
    '''Get project URL for the current (or specified) account.
    Falls back to FLOW_URL if no project URL configured (prevent empty goto).
    '''
    idx = account if account is not None else _current_account_idx
    url = ACCOUNTS[idx]['project_url']
    return url if url else FLOW_URL


def _create_project_from_main_page(page):
    """Navigate to Flow main page, dismiss modals, click 'Создать проект'.

    Returns new project URL or None.
    """
    print('  Navigating to Flow main page to create/find a project...')
    page.goto(FLOW_URL, timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    # Wait for full load — the page may have JS-rendered content
    try:
        page.wait_for_load_state('networkidle', timeout = 30000)
    except Exception:
        pass  # networkidle may timeout on slow connections, that's OK
    human_delay_long(4.0, 7.0)
    take_debug_screenshot(page, 'main_page_loaded')

    # Check if we landed on a recaptcha or login page
    body_text = ''
    try:
        body_text = (page.text_content('body') or '')[:2000].lower()
    except Exception:
        pass
    if 'recaptcha' in body_text and 'flow' not in body_text[:200]:
        print('  WARNING: Recaptcha detected on main page — cannot auto-create project.')
        print('  Please create a new project manually and pass its URL via --project-url.')
        take_debug_screenshot(page, 'recaptcha_detected')
        return None

    # Dismiss welcome modals ("A new way to Flow", etc.) — multiple rounds
    for _ in range(5):
        dismiss_popups(page)
        human_delay(0.5, 1.0)
        page.keyboard.press('Escape')
        human_delay(0.5, 1.0)

    # Strategy 0: Click "Create with Flow" on the new-style landing page
    for cta_label in ['Create with Flow', 'Создавайте с Flow', 'Начать']:
        cta = page.query_selector(f'a:has-text("{cta_label}")') or page.query_selector(f'button:has-text("{cta_label}")')
        if cta:
            box = cta.bounding_box()
            if box and box['width'] > 0:
                print(f'  Found CTA: "{cta_label}" — clicking...')
                human_click(page, cta)
                # Wait for workspace to load (shows "Загрузка..." then project)
                for _wait in range(30):
                    human_delay(2.0, 3.0)
                    new_url = page.url
                    if '/project/' in new_url:
                        ACCOUNTS[_current_account_idx]['project_url'] = new_url
                        print(f'  Created new project via CTA: {new_url}')
                        return new_url
                    # Check if we're now in a workspace (prompt field visible)
                    pf = page.query_selector('[role="textbox"], [contenteditable="true"]')
                    if pf:
                        box2 = pf.bounding_box()
                        if box2 and box2['width'] > 50:
                            new_url = page.url
                            ACCOUNTS[_current_account_idx]['project_url'] = new_url
                            print(f'  Workspace loaded via CTA: {new_url}')
                            return new_url
                take_debug_screenshot(page, 'cta_wait_timeout')
                print(f'  CTA clicked but workspace did not load in time. URL: {page.url}')
                break

    # Strategy 1: Look for "Создать проект" / "Новый проект" / "Create project" button
    for label in ['Создать проект', 'Новый проект', 'Create project', 'New project']:
        create_btn = page.query_selector(f'button:has-text("{label}")')
        if not create_btn:
            create_btn = page.query_selector(f'a:has-text("{label}")')
        if create_btn:
            box = create_btn.bounding_box()
            if box and box['width'] > 0:
                print(f'  Found button: "{label}" — clicking...')
                human_click(page, create_btn)
                human_delay_long(5.0, 8.0)
                new_url = page.url
                if '/project/' in new_url:
                    ACCOUNTS[_current_account_idx]['project_url'] = new_url
                    print(f'  Created new project: {new_url}')
                    return new_url

    # Strategy 2: try clicking "+" button on main page
    plus_btn = page.query_selector('button:has-text("add")')
    if plus_btn:
        box = plus_btn.bounding_box()
        if box and box['y'] < 200:
            print('  Found "+" button — clicking...')
            human_click(page, plus_btn)
            human_delay_long(5.0, 8.0)
            new_url = page.url
            if '/project/' in new_url:
                ACCOUNTS[_current_account_idx]['project_url'] = new_url
                print(f'  Created new project via "+": {new_url}')
                return new_url

    # Strategy 3: look for project cards — pick ANY existing project
    # (better to use an existing working project than fail)
    project_link = page.query_selector('a[href*="/project/"]')
    if project_link:
        human_click(page, project_link)
        human_delay_long(5.0, 8.0)
        new_url = page.url
        if '/project/' in new_url:
            ACCOUNTS[_current_account_idx]['project_url'] = new_url
            print(f'  Opened existing project: {new_url}')
            return new_url

    # Strategy 4: try clicking any visible card-like element in the grid
    cards = page.query_selector_all('div[role="link"], div[role="button"]')
    for card in cards[:8]:
        try:
            box = card.bounding_box()
            if box and box['width'] > 100 and box['height'] > 80 and box['y'] > 30:
                human_click(page, card)
                human_delay_long(5.0, 8.0)
                new_url = page.url
                if '/project/' in new_url:
                    ACCOUNTS[_current_account_idx]['project_url'] = new_url
                    print(f'  Opened project from grid: {new_url}')
                    return new_url
                break
        except Exception:
            continue

    # Strategy 5: try direct navigation to image generator tool
    # This URL should auto-create a project or open a scratchpad
    print('  Trying direct navigation to image generator tool...')
    page.goto(FLOW_URL + '/image-generator', timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    human_delay_long(5.0, 8.0)
    new_url = page.url
    if '/project/' in new_url:
        ACCOUNTS[_current_account_idx]['project_url'] = new_url
        print(f'  Auto-created project via image-generator: {new_url}')
        return new_url

    print('  WARNING: Could not find or create a project')
    take_debug_screenshot(page, 'create_project_failed')
    return None


def ensure_project(page = None):
    """If project URL is empty or page shows 'Проект не найден', create a new project.

    Navigates to Flow main page, clicks 'Создать проект', saves the new URL.
    Returns True if a new project was created, False if existing project is fine.
    """
    project_url = ACCOUNTS[_current_account_idx]['project_url']
    # If URL is empty — go to main page and create project
    if not project_url:
        print('  No project URL configured — creating new project...')
        return _create_project_from_main_page(page) is not None
    # If URL exists — check if we're already on this project
    current_url = page.url or ''
    # Extract project ID from URLs to compare
    target_id = project_url.split('/project/')[-1].rstrip('/').split('?')[0] if '/project/' in project_url else ''
    current_id = current_url.split('/project/')[-1].rstrip('/').split('?')[0] if '/project/' in current_url else ''
    if target_id and current_id and target_id == current_id:
        print(f'  Already on correct project ({target_id[:12]}...), skipping navigation')
        return False
    # Navigate to project
    if _cdp_port:
        # In CDP mode, page.goto() kills the Flow SPA.
        # If we're not on the right project, we can't navigate there.
        # The user must open the correct project tab manually.
        print(f'  CDP mode: not on correct project (current={current_id[:12]}, target={target_id[:12]})')
        print(f'  Please open the project manually in Chrome: {project_url}')
        raise RuntimeError(f'CDP mode: wrong project tab. Open {project_url} in Chrome manually.')
    page.goto(project_url, timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    human_delay_long(2.0, 4.0)
    body_text = ''
    try:
        body_text = (page.text_content('body') or '')[:500].lower()
    except Exception:
        pass
    if 'не найден' in body_text or 'not found' in body_text:
        print('  Project not found — creating new project...')
        return _create_project_from_main_page(page) is not None
    return False


def dismiss_popups(page = None):
    '''Dismiss any overlay popups (what\'s new, announcements, modals, etc.).

    Google Flow occasionally shows news/changelog dialogs on load.
    This function tries multiple strategies to close them.
    Returns True if any popup was dismissed.
    '''
    dismissed = False
    # Strategy 1: Close buttons with common labels (Russian & English)
    close_labels = [
        'Закрыть', 'Close', 'Понятно', 'Got it', 'OK', 'Ок',
        'Dismiss', 'Пропустить', 'Skip', 'Далее', 'Next',
        'Позже', 'Later', 'Не сейчас', 'Not now',
    ]
    for label in close_labels:
        try:
            btn = page.query_selector(f'button:has-text("{label}")')
            if btn:
                box = btn.bounding_box()
                if box and box['width'] > 0:
                    human_click(page, btn)
                    print(f'  Dismissed popup (button: "{label}")')
                    human_delay(0.5, 1.2)
                    dismissed = True
        except Exception:
            pass
    # Strategy 2: Material Design dialog close (X icon button)
    for selector in [
        'button[aria-label="Close"]',
        'button[aria-label="Закрыть"]',
        'button[aria-label="close"]',
        'mat-dialog-container button.close',
        'div[role="dialog"] button[aria-label*="lose"]',
        'div[role="dialog"] button[aria-label*="акрыть"]',
    ]:
        try:
            btn = page.query_selector(selector)
            if btn:
                box = btn.bounding_box()
                if box and box['width'] > 0:
                    human_click(page, btn)
                    print(f'  Dismissed popup (selector: {selector})')
                    human_delay(0.5, 1.2)
                    dismissed = True
        except Exception:
            pass
    # Strategy 3: Click any visible overlay backdrop to dismiss
    for selector in [
        'div.cdk-overlay-backdrop',
        'div[class*="overlay-backdrop"]',
        'div[class*="modal-backdrop"]',
    ]:
        try:
            el = page.query_selector(selector)
            if el:
                box = el.bounding_box()
                if box and box['width'] > 100:
                    el.click()
                    print(f'  Dismissed overlay backdrop')
                    human_delay(0.5, 1.2)
                    dismissed = True
        except Exception:
            pass
    # Strategy 4: Press Escape to dismiss any modal/overlay
    if not dismissed:
        try:
            # Check if there's any dialog/modal/overlay visible
            dialog = page.query_selector('div[role="dialog"], mat-dialog-container, div[class*="modal"], div[class*="overlay"]')
            if dialog:
                box = dialog.bounding_box()
                if box and box['width'] > 0:
                    page.keyboard.press('Escape')
                    print('  Dismissed popup (Escape key)')
                    human_delay(0.5, 1.2)
                    dismissed = True
        except Exception:
            pass
    return dismissed


def wait_for_flow_ready(page = None):
    '''Wait until the Flow interface is loaded (prompt field visible).

    New UI (Feb 2026): prompt field is [role="textbox"] contenteditable div,
    not textarea. Handles popups/modals on page load.
    Also detects "Проект не найден" and auto-creates a new project.
    '''
    page.wait_for_load_state('domcontentloaded', timeout = PAGE_LOAD_TIMEOUT)
    # First wait a bit for any popups to appear
    human_delay_long(2.0, 4.0)
    # Check if we landed on "Проект не найден" or main page
    body_text = ''
    try:
        body_text = (page.text_content('body') or '')[:500].lower()
    except Exception:
        pass
    if 'не найден' in body_text or 'not found' in body_text:
        print('  Project not found — auto-creating new project...')
        if ensure_project(page):
            page.wait_for_load_state('domcontentloaded', timeout = PAGE_LOAD_TIMEOUT)
            human_delay_long(2.0, 4.0)
    # Try to dismiss any popups/overlays (up to 3 rounds)
    for _round in range(3):
        if not dismiss_popups(page):
            break
        human_delay(0.5, 1.0)
    # Wait for prompt field — new UI uses contenteditable div, old used textarea
    READY_SELECTOR = '[role="textbox"], [contenteditable="true"], textarea'
    try:
        page.wait_for_selector(READY_SELECTOR, timeout = 15000)
    except Exception:
        # Prompt field not found — maybe another popup, or on wrong page
        print('  Prompt field not found — attempting to dismiss popups again...')
        take_debug_screenshot(page, 'flow_ready_retry')
        # Try aggressive dismiss: Escape key multiple times
        for _ in range(3):
            page.keyboard.press('Escape')
            human_delay(0.5, 1.0)
        dismiss_popups(page)
        human_delay(1.0, 2.0)
        # Try clicking outside any modal (top-left corner)
        try:
            page.mouse.click(10, 10)
            human_delay(0.5, 1.0)
        except Exception:
            pass
        # Check if we're on main page (not in project) — need to create/open project
        body_text_2 = ''
        try:
            body_text_2 = (page.text_content('body') or '')[:500].lower()
        except Exception:
            pass
        if 'flow tv' in body_text_2 or 'new way to flow' in body_text_2.lower() or 'создать проект' in body_text_2:
            print('  On main page — need to navigate to project...')
            ensure_project(page)
            human_delay_long(2.0, 4.0)
            dismiss_popups(page)
        page.wait_for_selector(READY_SELECTOR, timeout = PAGE_LOAD_TIMEOUT)
    human_delay_long(1.5, 3.0)
    # Final check for any remaining popups
    dismiss_popups(page)
    print('  Flow workspace ready.')


def take_debug_screenshot(page = None, name = None):
    '''Save a debug screenshot.'''
    try:
        path = SCREENSHOTS_DIR / f'''{name}.png'''
        page.screenshot(path = str(path))
        print(f'''  Screenshot: {path.name}''')
    except Exception:
        pass


def _open_settings_popup(page = None):
    """Click the model chip (e.g. 'Nano Banana x2') to open settings popup.

    New UI (Feb 2026): the chip is at the bottom bar, shows model name + variant count.
    Uses Playwright native click (JS click doesn't open the popup reliably).
    Returns True if popup was opened, False otherwise.
    """
    # Use Playwright native selector — more reliable than JS click for this popup
    chip = page.query_selector('button:has-text("Nano Banana")')
    if not chip:
        chip = page.query_selector('button:has-text("Imagen")')
    if not chip:
        chip = page.query_selector('button:has-text("Veo")')
    if not chip:
        print('  WARNING: Settings chip not found')
        return False
    box = chip.bounding_box()
    if not box or box['width'] < 30:
        print('  WARNING: Settings chip not visible')
        return False
    chip_text = (chip.text_content() or '').strip()[:50]
    chip.click()
    print(f'''  Opened settings popup: {chip_text}''')
    human_delay(0.8, 1.5)
    # Verify popup appeared by checking for role="menu" or role="tab" elements
    popup = page.query_selector('div[role="menu"], button[role="tab"]')
    if not popup:
        human_delay(0.5, 1.0)
    return True


def get_current_mode(page = None):
    """Read current mode (image/video) from the chip icon.

    New UI: chip shows 📷 for image, 🎬/videocam for video.
    Old UI fallback: reads button[role='combobox'] text.
    """
    # New UI: check chip text for mode indicator
    result = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = (btn.textContent || '').trim();
            if (/x[1-4]/.test(text) && (text.includes('Nano Banana') ||
                text.includes('Imagen') || text.includes('Veo'))) {
                if (text.includes('videocam') || text.includes('movie') ||
                    text.includes('Veo')) return 'video';
                return 'image';
            }
        }
        // Old UI fallback
        const combo = document.querySelector('button[role="combobox"]');
        if (combo) return (combo.textContent || '').replace('arrow_drop_down', '').trim();
        return '';
    }""")
    return result


def switch_mode(page = None, mode_text = None):
    """Switch between Image and Video mode.

    New UI (Feb 2026): opens settings popup, clicks Image/Video tab.
    Old UI fallback: uses combobox dropdown.

    mode_text examples:
      "Создать изображение" / "image"  — image generation (Nano Banana)
      "Видео по кадрам" / "video"      — video generation (VEO)
      "Видео по образцам"              — samples-to-video (VEO)
    """
    is_video = 'идео' in mode_text or mode_text == 'video'
    target = 'Video' if is_video else 'Image'
    print(f'''  Switching mode → {target}''')

    # Try new UI: settings popup with Image/Video toggle
    if _open_settings_popup(page):
        # Popup buttons have role="tab" and text like "imageImage" or "videocamVideo"
        clicked = page.evaluate("""(target) => {
            const tabs = document.querySelectorAll('button[role="tab"]');
            for (const tab of tabs) {
                const text = (tab.textContent || '').trim();
                // "imageImage" for Image, "videocamVideo" for Video
                if ((target === 'Image' && (text.includes('Image') || text.includes('Изображение'))) ||
                    (target === 'Video' && (text.includes('Video') || text.includes('Видео')))) {
                    tab.click();
                    return true;
                }
            }
            return false;
        }""", target)
        human_delay(0.5, 1.0)
        page.keyboard.press('Escape')  # close popup
        human_delay(0.5, 1.0)
        if clicked:
            print(f'''  Mode set to: {target}''')
            return None

    # Old UI fallback: combobox dropdown
    combo = page.query_selector('button[role="combobox"]')
    if combo:
        human_click(page, combo)
        human_delay(0.8, 1.8)
        option = page.query_selector(f'''div[role="option"]:has-text("{mode_text}")''')
        if option:
            human_click(page, option)
            human_delay_medium(1.5, 3.5)
            print(f'''  Mode set via combobox: {mode_text}''')
            return None
        page.keyboard.press('Escape')

    print(f'''  WARNING: Could not switch mode to {mode_text}''')


def _get_prompt_field(page = None):
    '''Find the prompt input field.

    New UI (Feb 2026): contenteditable div with role="textbox".
    Old UI: textarea. Tries both for backward compat.
    '''
    for sel in ('[role="textbox"]', '[contenteditable="true"]', 'textarea'):
        el = page.query_selector(sel)
        if el:
            box = el.bounding_box()
            if box and box['width'] > 100:
                return el
    return None


def clear_prompt(page = None):
    '''Clear the prompt field.'''
    field = _get_prompt_field(page)
    if field:
        human_clear_field(page, field)
        human_delay(0.2, 0.5)
        return None


def _dispatch_full_input_events(page):
    '''Dispatch a full set of DOM events on the prompt field so that
    React/Lit/Angular frameworks pick up the content change.'''
    page.evaluate("""() => {
        const el = document.querySelector('[role="textbox"]') ||
                   document.querySelector('[contenteditable="true"]');
        if (!el) return;
        const text = el.textContent || '';
        // beforeinput
        el.dispatchEvent(new InputEvent('beforeinput', {
            bubbles: true, cancelable: true, inputType: 'insertText', data: text
        }));
        // input (the main one for React)
        el.dispatchEvent(new InputEvent('input', {
            bubbles: true, cancelable: true, inputType: 'insertText', data: text
        }));
        // change (for Angular/Lit)
        el.dispatchEvent(new Event('change', { bubbles: true }));
        // compositionend — some frameworks listen for this on contenteditable
        el.dispatchEvent(new CompositionEvent('compositionend', {
            bubbles: true, data: text
        }));
        // keydown/keyup of a generic key — triggers key-based listeners
        el.dispatchEvent(new KeyboardEvent('keydown', {
            bubbles: true, key: 'Unidentified', code: ''
        }));
        el.dispatchEvent(new KeyboardEvent('keyup', {
            bubbles: true, key: 'Unidentified', code: ''
        }));
    }""")


def _verify_prompt_filled(page, expected_text):
    '''Check that the prompt field contains text AND the framework registered it.

    Two checks:
    1. DOM textContent is non-empty
    2. Generate button is NOT disabled (framework accepted the input)
    '''
    result = page.evaluate("""() => {
        const el = document.querySelector('[role="textbox"]') ||
                   document.querySelector('[contenteditable="true"]');
        const text = el ? el.textContent.trim() : '';
        // Check if Generate button is disabled
        const btn = document.querySelector('button:has(span.material-symbols-outlined)') ||
                    document.querySelector('button[aria-label*="arrow_forward"]');
        const btnDisabled = btn ? (btn.disabled || btn.getAttribute('aria-disabled') === 'true') : null;
        return { text_len: text.length, btn_disabled: btnDisabled };
    }""")
    text_ok = result.get('text_len', 0) > 10
    btn_disabled = result.get('btn_disabled')
    if text_ok and btn_disabled is True:
        print(f'  DOM has text ({result["text_len"]} chars) but Generate button is disabled — framework did not register input')
        return False
    return text_ok


def _try_fill_prompt_once(page, text):
    '''Try all 3 strategies to fill the prompt field. Returns True on success.'''
    field = _get_prompt_field(page)
    if not field:
        raise RuntimeError('Prompt field not found (no [role="textbox"] or textarea)')
    maybe_idle_movement(page)
    human_click(page, field)
    human_delay(0.2, 0.5)

    # In CDP mode, skip JS-based strategies (execCommand, clipboard) — they break
    # React's internal state and cause "Application error" crashes on Generate click.
    # Use keyboard.type() directly which triggers all native browser events properly.
    if _cdp_port:
        human_click(page, field)
        page.keyboard.press(f'{"Meta" if sys.platform == "darwin" else "Control"}+a')
        human_delay(0.1, 0.2)
        page.keyboard.press('Backspace')
        human_delay(0.2, 0.4)
        human_type(page, field, text)
        human_delay(0.5, 1.0)
        if _verify_prompt_filled(page, text):
            print('  Prompt filled (keyboard.type, CDP mode).')
            return True
        return False

    # Strategy 1: JS execCommand('insertText') + full event dispatch
    success = page.evaluate("""(text) => {
        const el = document.querySelector('[role="textbox"]') ||
                   document.querySelector('[contenteditable="true"]');
        if (!el) return false;
        el.focus();
        // Clear existing content
        const sel = window.getSelection();
        sel.selectAllChildren(el);
        sel.deleteFromDocument();
        // Insert via execCommand — triggers same events as real paste
        const ok = document.execCommand('insertText', false, text);
        if (!ok) return false;
        return true;
    }""", text)

    if success:
        _dispatch_full_input_events(page)
        human_delay(0.3, 0.5)
        if _verify_prompt_filled(page, text):
            print('  Prompt filled (JS execCommand + events).')
            human_delay(0.3, 0.8)
            return True

    # Strategy 2: Clipboard paste via Cmd+V
    print('  execCommand failed, trying clipboard paste...')
    page.evaluate("(text) => navigator.clipboard.writeText(text)", text)
    human_delay(0.2, 0.4)
    mod = 'Meta' if sys.platform == 'darwin' else 'Control'
    page.keyboard.press(f'{mod}+a')
    human_delay(0.1, 0.2)
    page.keyboard.press(f'{mod}+v')
    human_delay(0.5, 1.0)
    _dispatch_full_input_events(page)
    human_delay(0.3, 0.5)
    if _verify_prompt_filled(page, text):
        print('  Prompt filled (clipboard paste + events).')
        human_delay(0.3, 0.8)
        return True

    # Strategy 3: Fallback to keyboard.type() — inherently triggers all native events
    print('  Clipboard paste failed, falling back to keyboard.type()...')
    # Clear field first
    human_click(page, field)
    page.keyboard.press(f'{"Meta" if sys.platform == "darwin" else "Control"}+a')
    human_delay(0.1, 0.2)
    page.keyboard.press('Backspace')
    human_delay(0.2, 0.4)
    human_type(page, field, text)
    human_delay(0.5, 1.0)
    return _verify_prompt_filled(page, text)


def fill_prompt(page = None, text = None):
    '''Fill the prompt field with text.

    Uses JS-based insertion (execCommand/insertText + InputEvent dispatch)
    instead of keyboard.type() to avoid CDP input detection by Google.
    Falls back to clipboard paste, then to keyboard.type().
    Retries up to 3 times if verification fails.
    '''
    MAX_RETRIES = 3
    for attempt in range(1, MAX_RETRIES + 1):
        check_page_crash(page)
        if _try_fill_prompt_once(page, text):
            return
        print(f'  WARNING: Prompt field empty after attempt {attempt}/{MAX_RETRIES}, retrying...')
        check_page_crash(page)
        human_delay(1.0, 2.0)
    raise RuntimeError(f'fill_prompt FAILED: prompt field still empty after {MAX_RETRIES} attempts')


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


def check_page_crash(page):
    '''Detect if the Flow page has crashed ("Application error" in title).

    If crashed, reloads the page and waits for it to recover.
    In CDP mode, reload/goto kill the SPA, so we only detect but do NOT reload.
    Returns True if a crash was detected, False if page is fine.
    '''
    try:
        title = page.title() or ''
    except Exception:
        title = ''
    if 'application error' not in title.lower():
        return False
    if _cdp_port:
        # In CDP mode, page.reload() and page.goto() kill the Flow SPA.
        # Google Flow often sets "Application error" in title during/after generation
        # but the page content continues to work normally. In CDP mode we NEVER
        # trust the title — always ignore it and let polling handle results/errors.
        print(f'  PAGE CRASH title detected in CDP mode (title="{title[:80]}") — ignoring (CDP).')
        return False
    print(f'  PAGE CRASH detected (title="{title[:80]}") — reloading...')
    page.reload(wait_until='domcontentloaded')
    human_delay_long(4.0, 8.0)
    READY_SELECTOR = '[role="textbox"], [contenteditable="true"], textarea'
    try:
        page.wait_for_selector(READY_SELECTOR, timeout=PAGE_LOAD_TIMEOUT)
    except Exception:
        pass
    human_delay_long(2.0, 4.0)
    # Verify recovery
    try:
        title = page.title() or ''
    except Exception:
        title = ''
    if 'application error' in title.lower():
        print('  Page still crashed after reload — re-navigating to project...')
        page.goto(get_project_url(), timeout=PAGE_LOAD_TIMEOUT, wait_until='domcontentloaded')
        human_delay_long(4.0, 8.0)
        try:
            page.wait_for_selector(READY_SELECTOR, timeout=PAGE_LOAD_TIMEOUT)
        except Exception:
            pass
        human_delay_long(2.0, 4.0)
    print('  Page recovered after crash.')
    return True


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
    """Set the number of generation variants.

    New UI (Feb 2026): opens settings popup, clicks x1/x2/x3/x4 button.
    Old UI fallback: Settings panel → 'Результатов на запрос' dropdown.
    """
    if not _open_settings_popup(page):
        print('  WARNING: Settings popup not found — variant count unchanged')
        return None
    # New UI: x1, x2, x3, x4 are role="tab" buttons in popup
    clicked = page.evaluate("""(count) => {
        const target = 'x' + count;
        const tabs = document.querySelectorAll('button[role="tab"]');
        for (const tab of tabs) {
            const text = (tab.textContent || '').trim();
            if (text === target) {
                tab.click();
                return {clicked: true, text: text};
            }
        }
        // Fallback: any button with exact text
        const btns = document.querySelectorAll('button');
        for (const btn of btns) {
            const text = (btn.textContent || '').trim();
            if (text === target) {
                btn.click();
                return {clicked: true, text: text};
            }
        }
        return {clicked: false};
    }""", str(count))
    if clicked.get('clicked'):
        print(f'''  Set variant count to x{count}''')
    else:
        print(f'''  WARNING: x{count} button not found in popup''')
    human_delay(0.3, 0.8)
    page.keyboard.press('Escape')
    human_delay(0.3, 0.8)
    return None


def set_image_model(page = None, model_name = None):
    """Switch image generation model.

    New UI (Feb 2026): opens settings popup, clicks model dropdown.
    Available models: 'Imagen 4', 'Nano Banana', 'Nano Banana Pro'
    """
    if not _open_settings_popup(page):
        print('  WARNING: Settings popup not found — model unchanged')
        return None
    # Find the model dropdown button inside the popup and click with Playwright native click
    # (JS click doesn't reliably open Radix UI dropdowns)
    dd_btn = page.query_selector('button:has-text("arrow_drop_down"):has-text("Nano Banana")')
    if not dd_btn:
        dd_btn = page.query_selector('button:has-text("arrow_drop_down"):has-text("Imagen")')
    if not dd_btn:
        dd_btn = page.query_selector('button[aria-haspopup="menu"]')
    if not dd_btn:
        # Fallback: find by evaluating all buttons
        dd_btn = page.evaluate_handle("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = (btn.textContent || '').trim();
                if (text.includes('arrow_drop_down') &&
                    (text.includes('Nano') || text.includes('Imagen') || text.includes('Veo'))) {
                    return btn;
                }
            }
            return null;
        }""")
        if dd_btn and dd_btn.as_element():
            dd_btn = dd_btn.as_element()
        else:
            dd_btn = None
    if not dd_btn:
        print(f'  WARNING: Model dropdown not found in popup — model unchanged')
        page.keyboard.press('Escape')
        human_delay(0.3, 0.8)
        return None
    dd_text = (dd_btn.text_content() or '').strip()[:50]
    print(f'  Clicking model dropdown: {dd_text}')
    dd_btn.click()  # Playwright native click — required for Radix UI
    human_delay(1.5, 2.5)  # Extra wait for dropdown to render
    # Log all visible elements for debugging and select target model
    selected = page.evaluate("""(targetModel) => {
        // Collect all menu-like items with multiple selector strategies
        const selectors = [
            '[role="menuitem"]', '[role="option"]', '[role="menuitemradio"]',
            '[role="menu"] > *', '[data-radix-popper-content-wrapper] div',
            'ul > li', 'div[role="listbox"] > *'
        ];
        let allItems = [];
        for (const sel of selectors) {
            const items = document.querySelectorAll(sel);
            for (const item of items) allItems.push(item);
        }
        // Deduplicate by element reference
        allItems = [...new Set(allItems)];
        // Collect text of visible items for logging
        const visibleTexts = [];
        for (const item of allItems) {
            const text = (item.textContent || '').trim();
            if (text.length > 0 && text.length < 100 && item.offsetHeight > 0) {
                visibleTexts.push(text.substring(0, 50));
            }
        }
        // Try to find and click target model
        for (const item of allItems) {
            const text = (item.textContent || '').trim();
            if (item.offsetHeight === 0) continue;
            if (targetModel === 'Nano Banana Pro') {
                if (text.includes('Nano Banana') && text.includes('Pro')) {
                    item.click();
                    return {found: true, text: text, available: visibleTexts};
                }
            } else if (targetModel === 'Nano Banana') {
                if (text.includes('Nano Banana') && !text.includes('Pro')) {
                    item.click();
                    return {found: true, text: text, available: visibleTexts};
                }
            } else {
                if (text.includes(targetModel)) {
                    item.click();
                    return {found: true, text: text, available: visibleTexts};
                }
            }
        }
        // Last resort: scan ALL elements on page for "Pro" text inside any overlay/popup
        const allEls = document.querySelectorAll('div, span, button, li, a');
        for (const el of allEls) {
            if (el.offsetHeight === 0 || el.offsetWidth === 0) continue;
            const rect = el.getBoundingClientRect();
            // Must be in popup/overlay area (z-index, floating position)
            const style = window.getComputedStyle(el);
            const zIndex = parseInt(style.zIndex) || 0;
            const text = (el.textContent || '').trim();
            if (targetModel === 'Nano Banana Pro' &&
                text.includes('Nano Banana') && text.includes('Pro') &&
                text.length < 50 && zIndex > 0) {
                el.click();
                return {found: true, text: text, available: visibleTexts, strategy: 'z-index'};
            }
        }
        return {found: false, available: visibleTexts};
    }""", model_name)
    if selected.get('found'):
        strat = selected.get('strategy', 'standard')
        print(f'''  Model set to: {model_name} (via {strat})''')
    else:
        avail = selected.get('available', [])
        print(f'''  WARNING: Model '{model_name}' not found in dropdown. Visible items: {avail[:10]}''')
    human_delay(0.3, 0.8)
    page.keyboard.press('Escape')
    human_delay(0.3, 0.8)


def click_generate(page = None):
    '''Click the Generate / Submit button.

    New UI (Feb 2026): round "→" button to the right of prompt field.
    Text contains "arrow_forward" (material icon name).
    IMPORTANT: "Создать" also appears in other buttons (e.g. "+ Создать подборку"),
    so we use a priority search: arrow_forward first, then specific fallbacks.
    Uses Playwright native click (not JS) for reliability.
    '''
    check_page_crash(page)
    dismiss_error_dialog(page)
    # Priority 1: button with arrow_forward icon (the actual submit button)
    btn = page.query_selector('button:has-text("arrow_forward")')
    if btn:
        box = btn.bounding_box()
        if box and box['width'] > 0:
            # Verify it's the submit button (near bottom of page, circular shape)
            btn.click()
            print('  Clicked Generate (arrow_forward).')
            human_delay_medium(1.5, 3.5)
            return
    # Priority 2: button with "Генерировать" or "Generate" text
    for text in ['Генерировать', 'Generate']:
        btn = page.query_selector(f'button:has-text("{text}")')
        if btn:
            box = btn.bounding_box()
            if box and box['width'] > 0:
                btn.click()
                print(f'  Clicked Generate ({text}).')
                human_delay_medium(1.5, 3.5)
                return
    # Priority 3: button with "Создать" but NOT "подборку" (avoid "Создать подборку")
    btns = page.query_selector_all('button:has-text("Создать")')
    for b in btns:
        text = (b.text_content() or '').strip()
        if 'подборку' in text.lower() or 'подбор' in text.lower():
            continue
        box = b.bounding_box()
        if box and box['width'] > 0 and box['height'] > 0:
            b.click()
            print(f'  Clicked Generate (Создать).')
            human_delay_medium(1.5, 3.5)
            return
    raise RuntimeError('Generate button not found')


def _ensure_gallery_tab(page = None, tab = None):
    """Click the gallery tab to ensure it's active."""
    tab_btn = page.query_selector(f'''button[role="radio"]:has-text("{tab}")''')
    if tab_btn:
        human_click(page, tab_btn)
        human_delay(0.8, 1.8)
        return None


def get_gallery_urls(page = None, tab = None):
    '''Get current gallery media URLs for the given tab.

    Returns a set of URLs for comparison (detect new items after generation).
    '''
    _ensure_gallery_tab(page, tab)
    media_type = 'video' if tab == 'Видео' else 'img'
    urls = get_gallery_media_urls(page, media_type)
    return set(urls)


def _scroll_chat_to_bottom(page):
    '''Scroll the main chat container to the bottom to reveal new content.'''
    page.evaluate("""() => {
        // Find scrollable containers on the left side (chat area)
        const els = document.querySelectorAll('*');
        for (const el of els) {
            if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                const rect = el.getBoundingClientRect();
                if (rect.x < 400 && rect.width > 200) {
                    el.scrollTop = el.scrollHeight;
                    return true;
                }
            }
        }
        return false;
    }""")


def _is_generating(page):
    '''Check if generation is in progress.

    ONLY checks for visual indicators — progress placeholder cards showing "NN%".
    Does NOT check body text because keywords like "Генерация", "генерируем",
    "Generating", "Создание" are permanently present in i18n/help strings.
    '''
    return page.evaluate("""() => {
        // Progress placeholders — grey cards showing "NN%" — the ONLY reliable signal
        const els = document.querySelectorAll('*');
        for (const el of els) {
            const text = (el.textContent || '').trim();
            const rect = el.getBoundingClientRect();
            // Match elements whose ONLY visible text is "NN%" and are large enough
            // to be generation placeholder cards (not tiny UI labels)
            if (/^\\d{1,3}%$/.test(text) && rect.width > 150 && rect.height > 80 &&
                rect.y >= 0 && rect.y < window.innerHeight) {
                return true;
            }
        }
        return false;
    }""")


def wait_for_new_gallery_item(page = None, initial_urls = None, timeout_sec = GENERATION_TIMEOUT, tab = 'Изображения', min_wait = 15):
    '''Poll until generation completes and new gallery items appear.

    New UI (Feb 2026) strategy:
    - DO NOT scroll during polling (virtual scroll removes elements from DOM)
    - Detect generation-in-progress via "Генерация" text in page
    - Wait until generating text disappears = generation complete
    - Then check for new img URLs

    Returns:
        "success" — new items appeared
        "server_error" — "Что-то пошло не так" or similar
        "content_filter" — "Не удалось сгенерировать"
        "timeout" — timed out waiting

    min_wait: minimum seconds before checking for errors (avoids detecting
    old error cards from previous generations).
    '''
    elapsed = 0
    was_generating = False
    # Scroll chat to bottom right away so generation placeholders are visible
    _scroll_chat_to_bottom(page)
    while elapsed < timeout_sec:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        # Check for page crash (Flow client-side exception)
        if check_page_crash(page):
            return 'server_error'
        maybe_idle_movement(page, probability=0.15)

        # Periodically scroll chat to bottom to keep new content visible
        if elapsed % 15 == 0:
            _scroll_chat_to_bottom(page)

        # Check if generation is in progress
        generating = _is_generating(page)
        if generating and not was_generating:
            print(f'  Generation started ({elapsed}s)')
            was_generating = True

        # Check for new images (scroll first to ensure they're in DOM)
        current_urls = get_gallery_urls(page, tab)
        new_urls = current_urls - initial_urls
        if new_urls:
            print(f'  Generation complete! ({elapsed}s) — {len(new_urls)} new items')
            return 'success'

        # Generation was active but text disappeared = generation finished
        # But could be success OR error — check both
        if was_generating and not generating:
            print(f'  Generation text disappeared ({elapsed}s) — checking for results...')
            time.sleep(3)
            # Check for new images first
            current_urls = get_gallery_urls(page, tab)
            new_urls = current_urls - initial_urls
            if new_urls:
                print(f'  Found {len(new_urls)} new items after generation')
                return 'success'
            # No new images — check if error cards appeared instead
            error_text = page.evaluate("""() => {
                const els = document.querySelectorAll('*');
                for (const el of els) {
                    const text = (el.textContent || '').trim();
                    if ((text.includes('Что-то пошло не так') ||
                         text.includes('Произошла ошибка') ||
                         text.includes('Не удалось сгенерировать') ||
                         text.includes('не удалось')) &&
                        text.length < 300) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 100 && rect.height > 20 &&
                            rect.y >= 0 && rect.y < window.innerHeight) {
                            return text;
                        }
                    }
                }
                return null;
            }""")
            if error_text:
                print(f'  ERROR after generation: {error_text[:80]}')
                if 'Не удалось сгенерировать' in error_text:
                    return 'content_filter'
                return 'server_error'
            # Generation finished, no errors visible, but no new URLs
            # (images may have scrolled out of virtual viewport)
            print(f'  Generation completed but new URLs not visible in viewport — treating as success')
            return 'success'

        # Only check for errors if:
        # 1. Enough time has passed (min_wait) to avoid old error text
        # 2. Generation is NOT actively in progress (no progress placeholders)
        if elapsed >= min_wait and not generating:
            error_text = page.evaluate("""() => {
                // Look for error cards — they have warning icon + "Ошибка" + error text
                // Scope: only elements currently visible in viewport (y > 0 && y < window.innerHeight)
                const els = document.querySelectorAll('*');
                for (const el of els) {
                    const text = (el.textContent || '').trim();
                    if ((text.includes('Что-то пошло не так') ||
                         text.includes('Произошла ошибка') ||
                         text.includes('Не удалось сгенерировать') ||
                         text.includes('не удалось')) &&
                        text.length < 300) {
                        const rect = el.getBoundingClientRect();
                        // Must be visible in viewport and reasonably sized
                        if (rect.width > 100 && rect.height > 20 &&
                            rect.y >= 0 && rect.y < window.innerHeight) {
                            return text;
                        }
                    }
                }
                return null;
            }""")
            if error_text:
                print(f'  ERROR detected: {error_text[:80]}')
                if 'Не удалось сгенерировать' in error_text:
                    return 'content_filter'
                return 'server_error'
        if elapsed % 30 == 0:
            gen_status = ' (generating...)' if generating else ''
            print(f'  Waiting for generation... ({elapsed}s, urls={len(current_urls)}{gen_status})')
    print(f'  TIMEOUT after {timeout_sec}s (urls={len(get_gallery_urls(page, tab))})')
    return 'timeout'


def get_gallery_media_urls(page = None, media_type = None):
    '''Extract src URLs from gallery media elements.

    media_type: "img" for images, "video" for videos.

    New UI (Feb 2026): chat-based interface where images appear as
    chat messages in a scrollable container. Generated images have
    alt="Сгенерированное изображение" and are large (w>100).
    Old position filter (y>100, y<800) fails because chat scrolls.
    We filter by alt text + minimum size instead.
    '''
    tag = media_type
    if tag == 'img':
        urls = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('img').forEach(el => {
                const rect = el.getBoundingClientRect();
                const alt = (el.alt || '').trim();
                // Match generated images by alt text (new UI)
                // OR by size + position (legacy fallback)
                if (rect.width > 100 && el.src) {
                    if (alt === 'Сгенерированное изображение' ||
                        alt === 'Generated image') {
                        results.push(el.src);
                    }
                }
            });
            return results;
        }""")
    else:
        urls = page.evaluate(f"""() => {{
            const results = [];
            document.querySelectorAll('{tag}').forEach(el => {{
                const rect = el.getBoundingClientRect();
                if (rect.width > 100 && el.src) {{
                    results.push(el.src);
                }}
            }});
            return results;
        }}""")
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
        human_click(page, video_tab)
        human_delay_medium(1.5, 3.5)
    urls = get_gallery_media_urls(page, 'video')
    if not urls:
        urls = page.evaluate("() => {\n            const results = [];\n            document.querySelectorAll('video source, video').forEach(el => {\n                const rect = (el.closest('video') || el).getBoundingClientRect();\n                if (rect.width > 100 && rect.y > 100) {\n                    const src = el.src || el.querySelector('source')?.src;\n                    if (src) results.push(src);\n                }\n            });\n            return results;\n        }")
    if not urls:
        print('  No gallery videos found')
        return False
    url = urls[-1]
    print(f'''  Downloading video #{len(urls)}...''')
    return download_media_via_fetch(page, url, save_path)


def _scroll_chat_to_results(page):
    '''Scroll the chat container UP to reveal the latest generation results.

    In the new chat UI, after generation completes the viewport shows the
    prompt input at the bottom. Generated images are above it. We scroll
    up by one viewport height to reveal them.
    '''
    page.evaluate("""() => {
        const els = document.querySelectorAll('*');
        for (const el of els) {
            if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                const rect = el.getBoundingClientRect();
                if (rect.x < 600 && rect.width > 200) {
                    // Scroll up by one viewport to show results above prompt
                    el.scrollTop = Math.max(0, el.scrollHeight - el.clientHeight * 2);
                    return true;
                }
            }
        }
        return false;
    }""")
    time.sleep(1.5)


def download_all_new_images(page = None, initial_urls = None, dest_dir = None):
    '''Download all NEW images that appeared since initial_urls snapshot.

    In new chat UI (Feb 2026), after generation the viewport may have scrolled
    past the results. We try multiple scroll positions to find all new images.

    Returns list of saved file paths.
    '''
    _ensure_gallery_tab(page, 'Изображения')

    # Try to find new images at current scroll position
    urls = get_gallery_media_urls(page, 'img')
    new_urls = [u for u in urls if u not in initial_urls]

    # If not enough new URLs, scroll up to find results
    if len(new_urls) < 2:
        print('  Scrolling to find generation results...')
        _scroll_chat_to_results(page)
        urls = get_gallery_media_urls(page, 'img')
        new_urls = [u for u in urls if u not in initial_urls]

    # If still not enough, scroll up more aggressively
    if len(new_urls) < 2:
        page.evaluate("""() => {
            const els = document.querySelectorAll('*');
            for (const el of els) {
                if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                    const rect = el.getBoundingClientRect();
                    if (rect.x < 600 && rect.width > 200) {
                        el.scrollTop = Math.max(0, el.scrollTop - el.clientHeight);
                        return true;
                    }
                }
            }
            return false;
        }""")
        time.sleep(1.5)
        urls = get_gallery_media_urls(page, 'img')
        new_urls = [u for u in urls if u not in initial_urls]

    if not new_urls:
        print('  No new images to download')
        return []
    print(f'  Found {len(new_urls)} new images to download')
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


def _migrate_selected_variant(comp):
    '''Migrate old selected_variant to selected_variant_a (backward compat).'''
    if 'selected_variant' in comp and comp['selected_variant'] is not None:
        if 'selected_variant_a' not in comp or comp['selected_variant_a'] is None:
            comp['selected_variant_a'] = comp['selected_variant']
        del comp['selected_variant']
    # Ensure both slots exist
    if 'selected_variant_a' not in comp:
        comp['selected_variant_a'] = None
    if 'selected_variant_b' not in comp:
        comp['selected_variant_b'] = None


def load_manifest(clip_id = None):
    '''Load or create a manifest for a clip.'''
    path = _manifest_path(clip_id)
    if path.exists():
        with open(path, 'r') as f:
            manifest = json.load(f)
        # Migration: add nb_mid component if missing (backward compat)
        if 'nb_mid' not in manifest.get('components', {}):
            manifest['components']['nb_mid'] = {'attempts': [], 'selected_variant_a': None, 'selected_variant_b': None, 'status': 'pending'}
        # Migration: selected_variant → selected_variant_a for all components
        for comp_name in ('nb_first', 'nb_mid', 'nb_last', 'veo'):
            if comp_name in manifest.get('components', {}):
                _migrate_selected_variant(manifest['components'][comp_name])
        return manifest
    manifest = {
        'clip_id': clip_id,
        'components': {
            'nb_first': {'attempts': [], 'selected_variant_a': None, 'selected_variant_b': None, 'status': 'pending'},
            'nb_mid': {'attempts': [], 'selected_variant_a': None, 'selected_variant_b': None, 'status': 'pending'},
            'nb_last': {'attempts': [], 'selected_variant_a': None, 'selected_variant_b': None, 'status': 'pending'},
            'veo': {'attempts': [], 'selected_variant_a': None, 'selected_variant_b': None, 'status': 'pending'},
        }
    }
    return manifest


def save_manifest(clip_id = None, manifest = None):
    '''Save manifest to disk.'''
    path = _manifest_path(clip_id)
    path.parent.mkdir(parents = True, exist_ok = True)
    with open(path, 'w') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def find_scene_ref_frame(clips = None, current_clip_id = None):
    '''Find an accepted first frame from a previous clip in the same scene.

    Loads ALL clips from prompts JSON (not the filtered list) to find
    previous clips in the same scene with accepted nb_first frames.
    Returns the path to the most recent accepted first frame, or None.
    '''
    # Load ALL clips to find scene context, regardless of --clip filter
    with open(PROMPTS_PATH, 'r') as f:
        all_clips_full = json.load(f)
    current_scene = None
    for clip in all_clips_full:
        if clip['clip_id'] == current_clip_id:
            current_scene = clip['scene_id']
            break
    if current_scene is None:
        return None
    scene_clips = [c for c in all_clips_full if c['scene_id'] == current_scene]
    candidates = []
    for clip in scene_clips:
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


def record_attempt(manifest, component = None, attempt_num = None, prompt = None, variant_paths = None, prompt_b = None, batch_a_count = None, batch_b_count = None):
    '''Record a generation attempt in the manifest.

    For A/B prompts, variant_paths contains both batches concatenated.
    batch_a_count/batch_b_count track how many variants belong to each batch.
    '''
    comp = manifest['components'][component]
    attempt_entry = {
        'attempt': attempt_num,
        'prompt': prompt,
        'variants': [{'file': str(p.relative_to(p.parent.parent)) if 'prompt_' in str(p.parent.name) else p.name, 'scores': None, 'avg': None} for p in variant_paths],
        'best_variant': None,
        'best_avg': None,
    }
    if prompt_b:
        attempt_entry['prompt_b'] = prompt_b
    if batch_a_count is not None:
        attempt_entry['batch_a_count'] = batch_a_count
    if batch_b_count is not None:
        attempt_entry['batch_b_count'] = batch_b_count
    comp['attempts'].append(attempt_entry)
    return attempt_entry


def mark_selected(manifest, component, attempt = None, variant_idx = None, scores = None, avg = None, batch = 'a'):
    '''Mark a variant as selected (passed review).

    batch: 'a' or 'b' — which slot to write to (selected_variant_a or selected_variant_b).
    Status is set to 'accepted' when slot A is filled (and B too, if prompt B exists).
    '''
    comp = manifest['components'][component]
    attempt_entry = comp['attempts'][attempt - 1]
    attempt_entry['variants'][variant_idx]['scores'] = scores
    attempt_entry['variants'][variant_idx]['avg'] = avg
    attempt_entry['best_variant'] = variant_idx
    attempt_entry['best_avg'] = avg
    slot_key = f'selected_variant_{batch}'
    comp[slot_key] = {
        'attempt': attempt,
        'variant': variant_idx }
    # Status = accepted when slot A is filled
    # (if prompt B generated variants, slot B must also be filled)
    if comp.get('selected_variant_a') is not None:
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


def _resolve_variant_file(comp, slot_key, clip_id, component):
    '''Resolve the file path for a selected variant slot.

    Returns (variant_file_path, attempt_entry, variant_data) or (None, None, None).
    '''
    sel = comp.get(slot_key)
    if not sel:
        return (None, None, None)
    attempt_dir = REVIEW_DIR / clip_id / component / f'attempt_{sel["attempt"]}'
    attempt_entry = comp['attempts'][sel['attempt'] - 1]
    variant_data = attempt_entry['variants'][sel['variant']]
    variant_file = attempt_dir / variant_data['file']
    if not variant_file.exists():
        print(f'  WARNING: selected file not found: {variant_file}')
        return (None, None, None)
    return (variant_file, attempt_entry, variant_data)


def copy_selected_to_output(clip_id = None, manifest = None, trim_start = None, trim_end = None):
    '''Copy accepted variants to output/frames/ and output/clips/.

    For NB components, copies both A and B variants:
      selected_variant_a → {clip}_first.png (main)
      selected_variant_b → {clip}_first_b.png (alternative)

    For VEO component, if trim_start/trim_end provided, trims the video.
    '''
    frame_suffixes = {'nb_first': 'first', 'nb_mid': 'mid', 'nb_last': 'last'}

    for component in ('nb_first', 'nb_mid', 'nb_last', 'veo'):
        comp = manifest['components'][component]

        if component in frame_suffixes:
            suffix = frame_suffixes[component]
            # Copy slot A (main)
            (variant_file_a, _, _) = _resolve_variant_file(comp, 'selected_variant_a', clip_id, component)
            if variant_file_a:
                dest = FRAMES_DIR / f'{clip_id}_{suffix}.png'
                shutil.copy2(variant_file_a, dest)
                print(f'  Copied {variant_file_a.name} → {dest.name}')
            # Copy slot B (alternative)
            (variant_file_b, _, _) = _resolve_variant_file(comp, 'selected_variant_b', clip_id, component)
            if variant_file_b:
                dest_b = FRAMES_DIR / f'{clip_id}_{suffix}_b.png'
                shutil.copy2(variant_file_b, dest_b)
                print(f'  Copied {variant_file_b.name} → {dest_b.name}')

        elif component == 'veo':
            # VEO: copy slot A as main clip
            (variant_file, _, variant_data) = _resolve_variant_file(comp, 'selected_variant_a', clip_id, component)
            if not variant_file:
                continue
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
    '''Check if all components are accepted or needs_manual_work.

    nb_mid is optional: if it has 0 attempts and status pending, it is
    considered "not required" and does not block completion.

    For NB components with A/B prompts, both selected_variant_a and
    selected_variant_b must be filled for status to be "accepted".
    '''
    for comp_name in ('nb_first', 'nb_mid', 'nb_last', 'veo'):
        comp = manifest['components'].get(comp_name, {})
        status = comp.get('status', 'pending')
        # nb_mid with 0 attempts and pending = not required (backward compat)
        if comp_name == 'nb_mid' and status == 'pending' and len(comp.get('attempts', [])) == 0:
            continue
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
    for component in ('nb_first', 'nb_mid', 'nb_last', 'veo'):
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
        human_delay(0.8, 1.8)
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
    """Find and click the '+' (add) button near prompt field.

    New UI (Feb 2026): '+' button to the left of the prompt input field.
    Opens a menu with 'Загрузить изображение' / 'Создать подборку'.
    Old UI: '+' (add) button below prompt area.
    """
    result = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        const candidates = [];
        for (const btn of btns) {
            const text = btn.textContent.trim();
            const rect = btn.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) continue;
            // New UI: '+' or 'add' button in bottom area near prompt
            if ((text === 'add' || text === '+' || text.includes('add')) &&
                !text.includes('download') && !text.includes('медиаконтент') && rect.y > 500) {
                candidates.push({
                    text: text.substring(0, 30),
                    y: rect.y, x: rect.x,
                    w: rect.width, h: rect.height
                });
                btn.click();
                return {clicked: true, btn: candidates[candidates.length - 1]};
            }
        }
        // Debug: list all potential add buttons
        const debug = [];
        for (const btn of btns) {
            const text = btn.textContent.trim();
            if (text.includes('add') || text === '+') {
                const rect = btn.getBoundingClientRect();
                debug.push({text: text.substring(0, 30), y: Math.round(rect.y),
                           w: Math.round(rect.width), h: Math.round(rect.height)});
            }
        }
        return {clicked: false, debug};
    }""")
    if result.get('clicked'):
        btn_info = result.get('btn', { })
        print(f'''  Clicked '+' button (y={btn_info.get('y', '?'):.0f}, w={btn_info.get('w', '?'):.0f})''')
        return True
    debug = result.get('debug', [])
    if debug:
        print(f'''  DEBUG: found {len(debug)} add-like buttons but none matched:''')
        for d in debug[:5]:
            print(f'''    text='{d['text']}' y={d['y']} w={d['w']} h={d['h']}''')
        return False
    print("  DEBUG: no 'add' or '+' buttons found on page")
    return False


def _open_ingredient_panel(page = None):
    """Open the ingredient upload panel.

    New UI (Feb 2026): clicks '+' → menu appears → clicks 'Загрузить изображение'.
    Old UI: clicks '+' → panel with upload button opens.
    Returns True if ready for file upload.
    """
    READY_SELECTOR = '[role="textbox"], [contenteditable="true"], textarea'
    dismiss_error_dialog(page)
    human_delay(0.8, 1.8)
    if _find_ingredient_add_button(page):
        human_delay(0.5, 1.0)
        # New UI: menu appears with 'Загрузить изображение'
        upload_menu_item = page.query_selector('button:has-text("Загрузить изображение")')
        if not upload_menu_item:
            upload_menu_item = page.query_selector(':text("Загрузить изображение")')
        if upload_menu_item:
            box = upload_menu_item.bounding_box()
            if box and box['width'] > 0:
                human_click(page, upload_menu_item)
                print('  Clicked "Загрузить изображение" menu item.')
                human_delay(1.0, 2.0)
                return True
        # Old UI fallback: wait for upload button in panel
        print('  Waiting for ingredient panel to load (attempt 1/3)...')
        if _wait_for_upload_button(page, timeout_sec = 30):
            print('  Ingredient panel loaded.')
            return True
    else:
        print("  Could not find '+' button (attempt 1/3)")
    # Retry 2: reload page
    print('  Panel not loaded — reloading page (attempt 2/3)...')
    page.reload(wait_until = 'domcontentloaded')
    human_delay_long(4.0, 8.0)
    try:
        page.wait_for_selector(READY_SELECTOR, timeout = PAGE_LOAD_TIMEOUT)
    except Exception:
        pass
    human_delay_long(2.5, 5.0)
    if _find_ingredient_add_button(page):
        human_delay(0.5, 1.0)
        upload_menu_item = page.query_selector('button:has-text("Загрузить изображение")')
        if upload_menu_item:
            human_click(page, upload_menu_item)
            human_delay(1.0, 2.0)
            return True
        if _wait_for_upload_button(page, timeout_sec = 30):
            print('  Ingredient panel loaded after reload.')
            return True
    # Retry 3: re-navigate to project
    print('  Panel not loaded — re-navigating to project (attempt 3/3)...')
    page.goto(get_project_url(), timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    human_delay_long(4.0, 8.0)
    try:
        page.wait_for_selector(READY_SELECTOR, timeout = PAGE_LOAD_TIMEOUT)
    except Exception:
        pass
    human_delay_long(2.5, 5.0)
    if _find_ingredient_add_button(page):
        human_delay(0.5, 1.0)
        upload_menu_item = page.query_selector('button:has-text("Загрузить изображение")')
        if upload_menu_item:
            human_click(page, upload_menu_item)
            human_delay(1.0, 2.0)
            return True
        if _wait_for_upload_button(page, timeout_sec = 30):
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
        human_delay_long(2.5, 5.0)
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
        human_delay_medium(1.5, 3.5)
    if file_input:
        try:
            file_input.set_input_files(str(file_path))
            print('    (set_input_files directly)')
            human_delay_long(2.5, 5.0)
            for _ in range(15):
                if _dismiss_crop_dialog(page):
                    return True
                human_delay(0.8, 1.8)
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
        human_delay_medium(1.5, 3.5)
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
        global _expecting_filechooser
        _expecting_filechooser = True
        page.evaluate('(el) => el.click()', upload_btn)
        fc_info = page.expect_file_chooser(timeout=10000)
        with fc_info as file_chooser:
            file_chooser.set_files(str(file_path))
        _expecting_filechooser = False
        human_delay_long(2.5, 5.0)
        for _ in range(15):
            if _dismiss_crop_dialog(page):
                return True
            human_delay(0.8, 1.8)
        return True
    except Exception as e:
        _expecting_filechooser = False
        print(f'  WARNING: file chooser failed for {file_path.name}: {e}')
        return False


def _select_ingredient_from_library(page, filename):
    '''Try to select an ingredient by filename from the "Recently Used" library.

    After clicking "+", the panel shows "Поиск объектов" search + "Recently Used" list.
    Each item shows the original filename. We search for it and click to select.

    Returns True if found and selected, False otherwise.
    '''
    # The panel should already be open (after clicking "+")
    human_delay(0.3, 0.6)
    # Try to find the item by filename text in the list
    found = page.evaluate("""(filename) => {
        // Look for list items/buttons that contain the filename
        // Items are rows with thumbnail + filename text
        const allEls = document.querySelectorAll('button, [role="option"], [role="listitem"], li, div');
        for (const el of allEls) {
            const text = (el.textContent || '').trim();
            if (!text.includes(filename)) continue;
            const rect = el.getBoundingClientRect();
            // Must be visible and in the panel area
            if (rect.width < 50 || rect.height < 20 || rect.width > 800) continue;
            if (rect.y < 0 || rect.y > window.innerHeight) continue;
            // Check it's a clickable ingredient item (has small image nearby)
            const img = el.querySelector('img');
            if (img || el.closest('[role="listbox"]') || el.closest('[role="list"]')) {
                el.click();
                return true;
            }
            // Fallback: click if it looks like a list item
            if (rect.height > 30 && rect.height < 120) {
                el.click();
                return true;
            }
        }
        return false;
    }""", filename)
    if found:
        print(f'    Selected "{filename}" from library')
        human_delay(0.5, 1.0)
    return found


def _select_or_upload_ingredient(page, fpath):
    '''Try to select ingredient from Recently Used library, fall back to upload.

    1. Click "+" to open ingredient panel
    2. Look for filename in the list → click to select
    3. If not found → click upload icon / "Загрузить изображение" → upload file

    Returns True on success.
    '''
    filename = fpath.name
    # Click "+" to open the panel
    if not _find_ingredient_add_button(page):
        print(f'    Could not open ingredient panel for {filename}')
        return False
    human_delay(0.5, 1.0)
    # Try to find in Recently Used
    if _select_ingredient_from_library(page, filename):
        return True
    # Not found in library — upload
    print(f'    "{filename}" not in library, uploading...')
    # Click "Загрузить изображение" in the panel
    upload_btn = page.query_selector('button:has-text("Загрузить изображение")')
    if not upload_btn:
        upload_btn = page.query_selector(':text("Загрузить изображение")')
    if upload_btn:
        box = upload_btn.bounding_box()
        if box and box['width'] > 0:
            human_click(page, upload_btn)
            human_delay(1.0, 2.0)
    if _upload_single_file(page, fpath):
        return True
    return False


def clear_ingredients(page):
    '''Remove all existing ingredient thumbnails from the prompt area.

    In the new Flow UI (Feb 2026), ingredients appear as small image thumbnails
    near the prompt field, each with a "close" (×) button.
    '''
    cleared = 0
    for _pass in range(10):  # max 10 ingredients
        # Look for close/remove buttons on ingredient thumbnails near the prompt area
        close_btn = page.evaluate("""() => {
            // Ingredient thumbnails have close buttons — small × buttons near the bottom of page
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = (btn.textContent || '').trim().toLowerCase();
                if (text !== 'close' && text !== '×' && text !== 'cancel') continue;
                const rect = btn.getBoundingClientRect();
                // Ingredients are near the bottom (prompt area), small buttons
                if (rect.width > 0 && rect.width < 40 && rect.height < 40 &&
                    rect.y > window.innerHeight * 0.5) {
                    btn.click();
                    return true;
                }
            }
            // Also try aria-label based buttons
            const removeBtns = document.querySelectorAll('button[aria-label*="emov"], button[aria-label*="удал"], button[aria-label*="lose"], button[aria-label*="крыт"]');
            for (const btn of removeBtns) {
                const rect = btn.getBoundingClientRect();
                if (rect.width > 0 && rect.y > window.innerHeight * 0.5) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }""")
        if not close_btn:
            break
        cleared += 1
        human_delay(0.3, 0.6)
    if cleared:
        print(f'  Cleared {cleared} existing ingredient(s)')
        human_delay(0.5, 1.0)
    return cleared


def _count_current_ingredients(page):
    '''Count how many ingredient thumbnails are currently attached near the prompt area.'''
    count = page.evaluate("""() => {
        // Ingredient thumbnails are small images near the prompt area (bottom of page)
        const imgs = document.querySelectorAll('img');
        let count = 0;
        for (const img of imgs) {
            const rect = img.getBoundingClientRect();
            // Thumbnails: small images (< 120px) in the bottom half of the page
            if (rect.width > 10 && rect.width < 120 && rect.height > 10 && rect.height < 120 &&
                rect.y > window.innerHeight * 0.5) {
                count++;
            }
        }
        return count;
    }""")
    return count or 0


def upload_ingredients(page = None, ingredient_paths = None):
    """Upload ingredient images for Nano Banana image generation.

    Checks if the correct number of ingredients is already attached.
    If so, skips upload entirely. Otherwise clears and re-uploads.
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
    # Check if the exact same set of ingredients is already loaded (by file paths)
    resolved_keys = tuple(str(f) for f in resolved)
    if resolved_keys == upload_ingredients._last_uploaded:
        current_count = _count_current_ingredients(page)
        if current_count == len(resolved):
            print(f'  Ingredients already loaded ({len(resolved)} files, same set) — skipping upload')
            return len(resolved)
        else:
            print(f'  Same ingredient set but count mismatch ({current_count} vs {len(resolved)}) — re-uploading')
    # Different set or first upload — clear old and load new
    current_count = _count_current_ingredients(page)
    if current_count > 0:
        print(f'  Clearing {current_count} old ingredient(s) before loading new set')
        clear_ingredients(page)
    loaded = 0
    for i, fpath in enumerate(resolved):
        print(f'''  Loading ingredient {i + 1}/{len(resolved)}: {fpath.name}''')
        # Try: select from library first, upload only if not found
        if _select_or_upload_ingredient(page, fpath):
            loaded += 1
            human_delay_medium(1.5, 3.5)
            continue
        # Retry with panel reopen
        print(f'''  Retrying {fpath.name}...''')
        page.keyboard.press('Escape')
        human_delay_long(2.5, 5.0)
        _dismiss_crop_dialog(page)
        human_delay_medium(1.5, 3.5)
        if _select_or_upload_ingredient(page, fpath):
            loaded += 1
            human_delay_medium(1.5, 3.5)
            continue
        print(f'''  WARNING: Skipping {fpath.name} after retry failed''')
    page.keyboard.press('Escape')
    human_delay(0.8, 1.8)
    print(f'''  Loaded {loaded}/{len(resolved)} ingredients.''')
    # Remember what we loaded so we can skip next time if same set
    if loaded == len(resolved):
        upload_ingredients._last_uploaded = resolved_keys
    else:
        upload_ingredients._last_uploaded = None
    return loaded

upload_ingredients._last_uploaded = None  # init


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
        human_click(page, close_btns[0])
        cleared += 1
        human_delay(0.8, 1.8)
    if cleared:
        print(f'''  Cleared {cleared} pre-filled frame slot(s)''')
        human_delay(0.8, 1.8)
        return None


def upload_frame_for_veo(page = None, frame_path = None, slot_index = None):
    '''Upload a frame image to a VEO slot.

    In VEO mode there are frame slots (first/last frame).
    New UI (Feb 2026): may use same '+' → 'Загрузить изображение' flow.
    Old UI: dedicated '+' (add) buttons for each slot.

    slot_index=0 — First Frame, slot_index=1 — Last Frame
    '''
    slot_name = 'First Frame' if slot_index == 0 else 'Last Frame'
    # Try clicking an 'add' button for the frame slot
    clicked_slot = page.evaluate("""() => {
        const btns = document.querySelectorAll('button');
        const addBtns = [];
        for (const btn of btns) {
            const text = btn.textContent.trim();
            const rect = btn.getBoundingClientRect();
            if ((text === 'add' || text === '+') && rect.y > 600 && rect.width > 20) {
                addBtns.push({btn, y: rect.y, w: rect.width});
            }
        }
        if (addBtns.length === 0) return null;
        // Click the first available add button
        const target = addBtns[0];
        target.btn.click();
        return {y: target.y, w: target.w};
    }""")
    if not clicked_slot:
        take_debug_screenshot(page, f'''veo_no_add_btn_slot{slot_index}''')
        raise RuntimeError(f'''{slot_name} '+' button not found''')
    print(f'''  Clicking '+' for {slot_name} (slot {slot_index})...''')
    human_delay_medium(1.5, 3.5)
    # New UI: check for 'Загрузить изображение' menu item
    upload_menu = page.query_selector('button:has-text("Загрузить изображение")')
    if upload_menu:
        human_click(page, upload_menu)
        human_delay(1.0, 2.0)
    # Find upload mechanism
    upload_btn = None
    for _retry in range(5):
        upload_btn = page.query_selector('button:has-text("Загрузить")')
        if not upload_btn:
            upload_btn = page.query_selector('button:has-text("upload")')
        if upload_btn:
            break
        # Also check for file input (may appear directly)
        file_input = page.query_selector('input[type="file"]')
        if file_input:
            break
        human_delay_medium(1.5, 3.5)
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
    if not uploaded and upload_btn:
        try:
            global _expecting_filechooser
            _expecting_filechooser = True
            page.evaluate("(el) => el.click()", upload_btn)
            fc_info = page.expect_file_chooser(timeout=10000)
            with fc_info as file_chooser:
                file_chooser.set_files(str(frame_path))
            _expecting_filechooser = False
            uploaded = True
        except Exception as e:
            _expecting_filechooser = False
            print(f'    (button click + file chooser failed: {e})')
    if not uploaded:
        raise RuntimeError(f'Failed to upload {frame_path.name}')
    human_delay_long(2.5, 5.0)
    _dismiss_crop_dialog(page)
    human_delay_medium(1.5, 3.5)
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
    ctx = launch_browser(pw, headless = False, cdp_port = _cdp_port)
    page = _get_or_create_flow_page(ctx)
    try:
        page.goto(FLOW_URL, timeout = PAGE_LOAD_TIMEOUT, wait_until = 'commit')
    except Exception as e:
        print(f'  Navigation warning: {e}')
        print('  Browser is open — you can navigate manually.')
    try:
        page.wait_for_load_state('networkidle', timeout = 30000)
    except Exception:
        print('  (networkidle timeout — continuing, page may still be loading)')
    # Try clicking any login/create button on landing page
    for btn_text in ('Create with Flow', 'Создать с Flow', 'Войти', 'Sign in'):
        create_btn = page.query_selector(f'button:has-text("{btn_text}")')
        if create_btn:
            print(f"Found '{btn_text}' button — clicking...")
            human_click(page, create_btn)
            human_delay_long(2.5, 5.0)
            break
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
        time.sleep(poll_interval + random.uniform(-1, 2))
        elapsed += poll_interval
        try:
            current_url = page.url
            has_prompt = page.query_selector('[role="textbox"], [contenteditable="true"]') is not None
            has_textarea = page.query_selector('textarea') is not None
            is_login_page = 'accounts.google.com' in current_url
            is_landing = current_url.endswith('/flow/about') or current_url.endswith('/flow')
        except Exception:
            # Navigation in progress (e.g. OAuth redirect) — skip this poll
            continue
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
    human_delay_medium(1.5, 3.5)
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
    validate_nb_prompt(prompt, clip_id=f'{clip_id}/{frame_type}')
    prompt = sanitize_nb_prompt(prompt)
    print(f'''\n  --- Generating {frame_type} frame for {clip_id} ---''')
    print(f'''  Prompt: {prompt[:80]}...''')
    clear_prompt(page)
    fill_prompt(page, prompt)
    take_debug_screenshot(page, f'''{clip_id}_{frame_type}_before_gen''')
    maybe_idle_movement(page)
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


def _generate_frame_review(page, clip_id, component = None, prompt = None, attempt = None, initial_urls = None, ingredients = None, dest_dir = None):
    '''Generate a frame with Nano Banana and download ALL variants.

    Saves variants to dest_dir (or output/review/{clip_id}/{component}/attempt_{N}/ by default).
    Retries up to 3 times for server errors ("Что-то пошло не так").
    On retry, reloads page and re-uploads ingredients for a clean state.
    Returns list of saved variant paths.
    '''
    validate_nb_prompt(prompt, clip_id=f'{clip_id}/{component}')
    prompt = sanitize_nb_prompt(prompt)
    frame_label = {'nb_first': 'first', 'nb_mid': 'mid', 'nb_last': 'last'}.get(component, component)
    print(f'''\n  --- Generating {frame_label} frame for {clip_id} (attempt {attempt}) ---''')
    print(f'''  Prompt: {prompt[:80]}...''')
    SERVER_RETRY_WAITS = [
        45,
        60]
    for retry in range(3):
        if retry > 0:
            wait_time = SERVER_RETRY_WAITS[retry - 1]
            print(f'''  Server error — waiting {wait_time}s before retry {retry + 1}/3...''')
            time.sleep(wait_time + random.uniform(-5, 10))
            if _cdp_port:
                # In CDP mode, page.goto() and page.reload() kill the Flow SPA state.
                # Just wait and retry without reloading — the page is still functional.
                print('  CDP mode — skipping page reload, retrying in place...')
                human_delay_long(3.0, 5.0)
                _scroll_chat_to_bottom(page)
            else:
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
        maybe_idle_movement(page)
        click_generate(page)
        result = wait_for_new_gallery_item(page, current_urls)
        if result == 'success':
            take_debug_screenshot(page, f'''{clip_id}_{component}_a{attempt}_after_gen''')
            if dest_dir is None:
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
    '''Generate FIRST, MID (optional), and LAST keyframes using Nano Banana Pro.

    Steps:
      1. Switch to "Создать изображение" mode
      2. Upload ingredients (character/location references) — once for all frames
      3. Generate first frame (nano_banana_prompt_first)
      4. Generate mid frame (nano_banana_prompt_mid) — if present in clip config
         Mid uses accepted first frame as extra ingredient for consistency.
      5. Generate last frame (nano_banana_prompt_last)
         Last uses accepted mid frame (or first if no mid) as ingredient.
      6. Download all frames

    Returns (first_frame_path, mid_frame_path, last_frame_path).
    mid_frame_path is None if no mid prompt configured. Others can be None on failure.
    '''
    clip_id = clip['clip_id']
    prompt_mid = clip.get('nano_banana_prompt_mid')
    has_mid = prompt_mid is not None
    label = 'First + Mid + Last' if has_mid else 'First + Last'
    print(f'''\n{'============================================================'}''')
    print(f'''  PASS 1+2{'(+3)' if has_mid else ''} — Nano Banana Pro ({label} frames) — {clip_id}''')
    print(f'''{'============================================================'}''')
    prompt_first = clip['nano_banana_prompt_first']
    prompt_last = clip['nano_banana_prompt_last']
    ingredients = clip.get('nano_banana_ingredients', [])
    print(f'''  First prompt: {prompt_first[:60]}...''')
    if has_mid:
        print(f'''  Mid prompt:   {prompt_mid[:60]}...''')
    print(f'''  Last prompt:  {prompt_last[:60]}...''')
    print(f'''  Ingredients: {len(ingredients)} files''')
    first_path = FRAMES_DIR / f'''{clip_id}_first.png'''
    mid_path = FRAMES_DIR / f'''{clip_id}_mid.png''' if has_mid else None
    last_path = FRAMES_DIR / f'''{clip_id}_last.png'''
    # Check if all frames already exist
    all_exist = first_path.exists() and last_path.exists()
    if has_mid:
        all_exist = all_exist and mid_path.exists()
    if all_exist:
        print('  All frames already exist — skipping generation')
        return (first_path, mid_path, last_path)
    switch_mode(page, 'Создать изображение')
    img_tab = page.query_selector('button[role="radio"]:has-text("Изображения")')
    if img_tab:
        human_click(page, img_tab)
        human_delay(0.8, 1.8)
    set_image_model(page, 'Nano Banana Pro')
    if ingredients:
        upload_ingredients(page, ingredients)
    # Generate first frame
    if not first_path.exists():
        initial_urls = get_gallery_urls(page)
        print(f'''  Gallery URLs before first frame: {len(initial_urls)}''')
        ok = _generate_single_frame(page, clip_id, 'first', prompt_first, first_path, initial_urls)
        if not ok:
            return (None, None, None)
        print(f'''  Pausing {PAUSE_BETWEEN_GENERATIONS}s before next frame...''')
        human_pause_between_generations()
    else:
        print(f'''  First frame already exists: {first_path.name}''')
    # Generate mid frame (if configured)
    if has_mid and not mid_path.exists():
        # Add first frame as extra ingredient for mid consistency
        mid_ingredients = list(ingredients)
        mid_ingredients.append(str(first_path))
        ref_num = len(mid_ingredients)
        mid_prompt_with_ref = prompt_mid + f' Maintain exact visual continuity with Image {ref_num}.'
        # Re-upload with first frame added
        upload_ingredients(page, mid_ingredients)
        initial_urls = get_gallery_urls(page)
        print(f'''  Gallery URLs before mid frame: {len(initial_urls)}''')
        ok = _generate_single_frame(page, clip_id, 'mid', mid_prompt_with_ref, mid_path, initial_urls)
        if not ok:
            return (first_path, None, None)
        print(f'''  Pausing {PAUSE_BETWEEN_GENERATIONS}s before last frame...''')
        human_pause_between_generations()
    elif has_mid:
        print(f'''  Mid frame already exists: {mid_path.name}''')
    # Generate last frame — use mid (if available) or first as ingredient
    if not last_path.exists():
        ref_frame = mid_path if (has_mid and mid_path and mid_path.exists()) else first_path
        last_ingredients = list(ingredients)
        last_ingredients.append(str(ref_frame))
        ref_num = len(last_ingredients)
        last_prompt_with_ref = prompt_last + f' Maintain exact visual continuity with Image {ref_num}.'
        # Re-upload with ref frame added
        upload_ingredients(page, last_ingredients)
        initial_urls = get_gallery_urls(page)
        print(f'''  Gallery URLs before last frame: {len(initial_urls)}''')
        ok = _generate_single_frame(page, clip_id, 'last', last_prompt_with_ref, last_path, initial_urls)
        if not ok:
            return (first_path, mid_path if has_mid else None, None)
    else:
        print(f'''  Last frame already exists: {last_path.name}''')
    return (first_path, mid_path, last_path)


def _upload_veo_samples(page, sample_frames):
    '''Upload 2-3 reference frames as ingredients for «Видео по образцам» mode.

    Uses the same ingredient upload UI as Nano Banana Pro.
    sample_frames: list of Path objects (first, [mid], last).

    TODO: verify UI after first manual run — «по образцам» may use
    a different upload mechanism than ingredient panel.
    '''
    str_paths = [str(f) for f in sample_frames]
    uploaded = upload_ingredients(page, str_paths)
    if uploaded < len(sample_frames):
        print(f'  WARNING: Only {uploaded}/{len(sample_frames)} sample frames uploaded')
    return uploaded


def _run_veo_single_batch(page, clip_id, prompt, first_frame, last_frame, dest_dir, label, mid_frame=None, veo_mode='frames'):
    '''Generate 4 VEO video variants for a single prompt.

    Uploads frames, sets 4 variants, generates, downloads all to dest_dir.

    veo_mode:
      'frames' — «Видео по кадрам» (first + last, default)
      'samples' — «Видео по образцам» (first + mid + last as ingredients)

    Returns list of saved file paths.
    '''
    print(f'\n  --- VEO batch "{label}" for {clip_id} (mode={veo_mode}) ---')
    print(f'  Prompt: {prompt[:80]}...')
    validate_veo_prompt(prompt, clip_id=f'{clip_id}/veo_{label}')

    # Check if already have 4 variants
    existing = sorted(dest_dir.glob('*.mp4')) if dest_dir.exists() else []
    if len(existing) >= 4:
        print(f'  Already have {len(existing)} variants in {dest_dir.name} — skipping')
        return existing

    # Reload page for clean state
    print('  Reloading page for clean VEO state...')
    page.goto(get_project_url(), timeout=PAGE_LOAD_TIMEOUT, wait_until='domcontentloaded')
    wait_for_flow_ready(page)

    if veo_mode == 'samples':
        # «Видео по образцам» mode — upload frames as ingredients
        switch_mode(page, 'Видео по образцам')
    else:
        switch_mode(page, 'Видео по кадрам')
    video_tab = page.query_selector('button[role="radio"]:has-text("Видео")')
    if video_tab:
        human_click(page, video_tab)
        human_delay_medium(1.5, 3.5)

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
        human_delay_medium(1.5, 3.5)
    initial_urls = set(get_gallery_media_urls(page, 'video'))
    print(f'  Gallery URLs before: {len(initial_urls)}')

    if veo_mode == 'samples':
        # «Видео по образцам» — upload 2-3 reference frames as ingredients
        sample_frames = [first_frame]
        if mid_frame and mid_frame.exists():
            sample_frames.append(mid_frame)
        sample_frames.append(last_frame)
        print(f'  Uploading {len(sample_frames)} sample frames as ingredients...')
        _upload_veo_samples(page, sample_frames)
    else:
        # «Видео по кадрам» — upload first/last to frame slots
        clear_veo_frame_slots(page)
        upload_frame_for_veo(page, first_frame, 0)
        upload_frame_for_veo(page, last_frame, 1)
    ensure_enhance_prompt_off(page)
    set_variant_count(page, 4)
    clear_prompt(page)
    fill_prompt(page, prompt)
    take_debug_screenshot(page, f'{clip_id}_veo_{label}_before_gen')
    maybe_idle_movement(page)
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


def run_veo_pass(page = None, clip = None, first_frame = None, last_frame = None, mid_frame = None, veo_mode = 'frames',
                 first_frame_b = None, last_frame_b = None, mid_frame_b = None):
    '''Pass 3: Generate 8 VEO video variants (4 per prompt × 2 prompts).

    Each batch uses its own set of keyframes:
      Batch A: first_frame + mid_frame + last_frame → veo_prompt
      Batch B: first_frame_b + mid_frame_b + last_frame_b → veo_prompt_b

    If *_b frames are not provided, falls back to the A frames.

    mid_frame: optional mid keyframe path (for 'samples' mode).
    veo_mode: 'frames' (first+last) or 'samples' (first+mid+last as ingredients).

    Returns path to clip directory, or None on failure.
    '''
    clip_id = clip['clip_id']

    # Resolve B frames: use B variants if available, fall back to A
    eff_first_b = first_frame_b if first_frame_b and first_frame_b.exists() else first_frame
    eff_last_b = last_frame_b if last_frame_b and last_frame_b.exists() else last_frame
    eff_mid_b = mid_frame_b if mid_frame_b and mid_frame_b.exists() else mid_frame

    print(f'''\n{'============================================================'}''')
    print(f'''  PASS 3 — VEO 3.1 Variants — {clip_id} (mode={veo_mode})''')
    print(f'''{'============================================================'}''')
    print(f'''  Batch A: first={first_frame.name}, last={last_frame.name}''')
    if mid_frame:
        print(f'''           mid={mid_frame.name}''')
    print(f'''  Batch B: first={eff_first_b.name}, last={eff_last_b.name}''')
    if eff_mid_b:
        print(f'''           mid={eff_mid_b.name}''')

    clip_dir = CLIPS_DIR / clip_id
    clip_dir.mkdir(parents=True, exist_ok=True)
    prompt_a_dir = clip_dir / 'prompt_a'
    prompt_b_dir = clip_dir / 'prompt_b'

    prompt_a = sanitize_prompt(clip['veo_prompt'])
    prompt_b = sanitize_prompt(clip.get('veo_prompt_b', clip['veo_prompt']))

    # Batch A: 4 variants with prompt A + A frames
    saved_a = _run_veo_single_batch(page, clip_id, prompt_a, first_frame, last_frame, prompt_a_dir, 'prompt_a', mid_frame=mid_frame, veo_mode=veo_mode)

    if saved_a:
        print(f'  Waiting {PAUSE_BETWEEN_GENERATIONS}s (rate limiting)...')
        human_pause_between_generations()

    # Batch B: 4 variants with prompt B + B frames
    saved_b = _run_veo_single_batch(page, clip_id, prompt_b, eff_first_b, eff_last_b, prompt_b_dir, 'prompt_b', mid_frame=eff_mid_b, veo_mode=veo_mode)

    total = len(saved_a) + len(saved_b)
    if total > 0:
        print(f'  TOTAL: {total} video variants for {clip_id} (A={len(saved_a)}, B={len(saved_b)})')
        return clip_dir
    print(f'  FAILED: no video variants generated for {clip_id}')
    return None


def review_nano_banana(page, clip, manifest = None, component = None, attempt = None, prompt_override = None, first_frame_ref = None):
    '''Generate Nano Banana frame variants for review.

    Sets up image mode, uploads ingredients, generates, downloads all variants.
    If clip has a prompt B (prompt_key + '_b'), generates a second batch of 4 variants.
    Updates manifest with the attempt record.

    If first_frame_ref is provided (for nb_last), the selected first frame is
    added as an extra ingredient to ensure visual consistency between frames.
    Returns list of variant paths (4 for single prompt, 8 for A+B).
    '''
    clip_id = clip['clip_id']
    frame_label = {'nb_first': 'first', 'nb_mid': 'mid', 'nb_last': 'last'}.get(component, component)
    prompt_key = {'nb_first': 'nano_banana_prompt_first', 'nb_mid': 'nano_banana_prompt_mid', 'nb_last': 'nano_banana_prompt_last'}[component]
    prompt_a = prompt_override if prompt_override else clip[prompt_key]
    prompt_b = clip.get(prompt_key + '_b')
    has_b = prompt_b is not None and not prompt_override
    ingredients = list(clip.get('nano_banana_ingredients', []))

    label = f'{frame_label} A+B' if has_b else frame_label
    print(f'''\n{'============================================================'}''')
    print(f'''  REVIEW — Nano Banana ({label}) — {clip_id} — attempt {attempt}''')
    print(f'''{'============================================================'}''')
    print(f'''  Prompt A: {prompt_a[:70]}...''')
    if has_b:
        print(f'''  Prompt B: {prompt_b[:70]}...''')

    dismiss_popups(page)
    switch_mode(page, 'Создать изображение')
    img_tab = page.query_selector('button[role="radio"]:has-text("Изображения")')
    if img_tab:
        human_click(page, img_tab)
        human_delay(0.8, 1.8)
    image_model = clip.get('nano_banana_model_name', 'Nano Banana Pro')
    set_image_model(page, image_model)
    set_variant_count(page, 4)

    # Build ref suffix for prompts
    ref_suffix = ''
    if first_frame_ref and first_frame_ref.exists():
        ref_image_num = len(ingredients) + 1
        ingredients.append(str(first_frame_ref))
        if component == 'nb_first':
            ref_suffix = f''' Use Image {ref_image_num} as reference for the exact room layout, furniture placement, and all visible objects.'''
        else:
            ref_suffix = f''' Maintain exact visual continuity with Image {ref_image_num}.'''
        print(f'''  Added first frame as ingredient {ref_image_num} for consistency: {first_frame_ref.name}''')

    prompt_a_full = prompt_a + ref_suffix
    prompt_b_full = (prompt_b + ref_suffix) if has_b else None

    uploaded = upload_ingredients(page, ingredients)
    if uploaded == 0:
        char_count = sum(1 for ing in ingredients if 'персонаж' in ing.lower())
        if char_count > 0:
            print(f'  FAILED: No ingredients uploaded (0/{len(ingredients)}) — cannot generate without character references')
            return []
    elif uploaded < len(ingredients):
        print(f'  WARNING: Only {uploaded}/{len(ingredients)} ingredients loaded (need character refs for consistency)')

    attempt_dir = REVIEW_DIR / clip_id / component / f'attempt_{attempt}'

    try:
        # Batch A: 4 variants with prompt A
        dest_a = attempt_dir / 'prompt_a' if has_b else None  # None = default path (backward compat for single prompt)
        variants_a = _generate_frame_review(page, clip_id, component, prompt_a_full, attempt, ingredients=ingredients, dest_dir=dest_a)

        # Batch B: 4 variants with prompt B (if exists)
        variants_b = []
        if has_b and prompt_b_full:
            if variants_a:
                print(f'  Pausing between A/B batches...')
                human_pause_between_generations()
            dest_b = attempt_dir / 'prompt_b'
            variants_b = _generate_frame_review(page, clip_id, component, prompt_b_full, attempt, ingredients=ingredients, dest_dir=dest_b)

        all_variants = variants_a + variants_b
        record_attempt(manifest, component, attempt, prompt_a_full, all_variants,
                       prompt_b=prompt_b_full,
                       batch_a_count=len(variants_a),
                       batch_b_count=len(variants_b) if has_b else None)
        save_manifest(clip_id, manifest)

        if has_b:
            print(f'  TOTAL: {len(all_variants)} variants (A={len(variants_a)}, B={len(variants_b)})')

        return all_variants
    except Exception as e:
        print(f'  ERROR in review_nano_banana: {e}')
        take_debug_screenshot(page, f'{clip_id}_{component}_a{attempt}_error')
        return []


def _review_veo_single_batch(page, clip, clip_id, prompt, first_frame, last_frame, attempt, batch_label, dest_dir, mid_frame=None, veo_mode='frames'):
    '''Generate one batch of VEO video variants (4 videos from one prompt).

    veo_mode:
      'frames' — «Видео по кадрам» (first + last)
      'samples' — «Видео по образцам» (first + mid + last as ingredients)

    Returns list of saved video paths.
    '''
    print(f'''\n  --- VEO Batch {batch_label} (mode={veo_mode}) ---''')
    print(f'''  Prompt: {prompt[:70]}...''')
    validate_veo_prompt(prompt, clip_id=f'{clip_id}/veo_{batch_label}_a{attempt}')
    print('  Reloading page to clear VEO state...')
    page.goto(get_project_url(), timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
    wait_for_flow_ready(page)
    if veo_mode == 'samples':
        switch_mode(page, 'Видео по образцам')
    else:
        switch_mode(page, 'Видео по кадрам')
    video_tab = page.query_selector('button[role="radio"]:has-text("Видео")')
    if video_tab:
        human_click(page, video_tab)
        human_delay_medium(1.5, 3.5)
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
        human_delay_medium(1.5, 3.5)
    initial_urls = set(get_gallery_media_urls(page, 'video'))
    if veo_mode == 'samples':
        # «Видео по образцам» — upload reference frames as ingredients
        sample_frames = [first_frame]
        if mid_frame and mid_frame.exists():
            sample_frames.append(mid_frame)
        sample_frames.append(last_frame)
        print(f'  Uploading {len(sample_frames)} sample frames as ingredients...')
        _upload_veo_samples(page, sample_frames)
    else:
        clear_veo_frame_slots(page)
        upload_frame_for_veo(page, first_frame, 0)
        upload_frame_for_veo(page, last_frame, 1)
    ensure_enhance_prompt_off(page)
    veo_model_override = clip.get('veo_model_override')
    if veo_model_override:
        set_image_model(page, veo_model_override)
        human_delay(0.8, 1.8)
    veo_variant_count = clip.get('veo_variant_count', 4)
    set_variant_count(page, veo_variant_count)
    clear_prompt(page)
    fill_prompt(page, prompt)
    take_debug_screenshot(page, f'{clip_id}_veo_a{attempt}_{batch_label}_before_gen')
    maybe_idle_movement(page)
    click_generate(page)
    result = wait_for_new_gallery_item(page, initial_urls, tab='Видео')
    if result != 'success':
        take_debug_screenshot(page, f'{clip_id}_veo_a{attempt}_{batch_label}_timeout')
        print(f'  FAILED: VEO {batch_label} for {clip_id} ({result})')
        return []
    saved = download_all_new_videos(page, initial_urls, dest_dir)
    print(f'  Downloaded {len(saved)} video variants for {batch_label}')
    for i, vpath in enumerate(saved):
        frames_dir = dest_dir / f'variant_{i + 1}_frames'
        extract_frames(vpath, frames_dir, fps=1)
    return saved


def review_veo(page, clip, manifest = None, attempt = None,
               first_frame = None, last_frame = None, prompt_override = None,
               mid_frame = None, veo_mode = 'frames',
               first_frame_b = None, last_frame_b = None, mid_frame_b = None):
    '''Generate VEO video variants for review: 8 videos total (4×prompt_a + 4×prompt_b).

    Each batch uses its own set of keyframes:
      Batch A: first_frame + mid_frame + last_frame → veo_prompt
      Batch B: first_frame_b + mid_frame_b + last_frame_b → veo_prompt_b

    If *_b frames are not provided, falls back to the A frames.

    mid_frame: optional mid keyframe path (for 'samples' mode).
    veo_mode: 'frames' or 'samples'.

    Returns list of all variant paths.
    '''
    clip_id = clip['clip_id']
    prompt_a = sanitize_prompt(prompt_override if prompt_override else clip['veo_prompt'])
    prompt_b = sanitize_prompt(clip.get('veo_prompt_b', clip['veo_prompt']))

    # Resolve B frames: use B variants if available, fall back to A
    eff_first_b = first_frame_b if first_frame_b and first_frame_b.exists() else first_frame
    eff_last_b = last_frame_b if last_frame_b and last_frame_b.exists() else last_frame
    eff_mid_b = mid_frame_b if mid_frame_b and mid_frame_b.exists() else mid_frame

    print(f'''\n{'============================================================'}''')
    print(f'''  REVIEW — VEO 3.1 — {clip_id} — attempt {attempt} (2 batches × 4 variants, mode={veo_mode})''')
    print(f'''{'============================================================'}''')
    print(f'''  Batch A frames: first={first_frame.name}, last={last_frame.name}''')
    if mid_frame:
        print(f'''                   mid={mid_frame.name}''')
    print(f'''  Batch B frames: first={eff_first_b.name}, last={eff_last_b.name}''')
    if eff_mid_b:
        print(f'''                   mid={eff_mid_b.name}''')

    dest_dir = REVIEW_DIR / clip_id / 'veo' / f'attempt_{attempt}'

    # Batch A: 4 variants with prompt_a + A frames
    dest_a = dest_dir / 'prompt_a'
    saved_a = _review_veo_single_batch(page, clip, clip_id, prompt_a, first_frame, last_frame, attempt, 'prompt_a', dest_a, mid_frame=mid_frame, veo_mode=veo_mode)

    # Pause between batches
    if saved_a:
        print(f'  Pausing between VEO batches...')
        human_pause_between_generations()

    # Batch B: 4 variants with prompt_b + B frames
    dest_b = dest_dir / 'prompt_b'
    saved_b = _review_veo_single_batch(page, clip, clip_id, prompt_b, eff_first_b, eff_last_b, attempt, 'prompt_b', dest_b, mid_frame=eff_mid_b, veo_mode=veo_mode)

    all_saved = saved_a + saved_b
    total = len(all_saved)
    print(f'  TOTAL: {total} video variants for {clip_id} (A={len(saved_a)}, B={len(saved_b)})')

    # Record both batches in manifest
    record_attempt(manifest, 'veo', attempt, f'A: {prompt_a}\n---\nB: {prompt_b}', all_saved,
                   prompt_b=prompt_b, batch_a_count=len(saved_a), batch_b_count=len(saved_b))
    save_manifest(clip_id, manifest)
    return all_saved


def process_clip(page = None, clip = None):
    '''Process a single clip: Nano Banana (first+mid+last frames) → VEO animation.'''
    clip_id = clip['clip_id']
    print(f'''\n{'############################################################'}''')
    print(f'''  Processing clip: {clip_id}''')
    print(f'''  Scene: {clip['scene_id']} | Location: {clip['location']}''')
    print(f'''  Description: {clip['scene_description_ru']}''')
    print(f'''{'############################################################'}''')
    (first_frame, mid_frame, last_frame) = run_nano_banana_pass(page, clip)
    missing = []
    if not first_frame:
        missing.append('first')
    if not last_frame:
        missing.append('last')
    if missing:
        print(f'  SKIP VEO pass — missing frame(s): {", ".join(missing)}')
        return (first_frame, mid_frame, last_frame, None)
    print(f'  Waiting {PAUSE_BETWEEN_GENERATIONS}s (rate limiting)...')
    human_pause_between_generations()
    veo_mode = clip.get('veo_mode', 'frames')
    video_path = run_veo_pass(page, clip, first_frame, last_frame, mid_frame=mid_frame, veo_mode=veo_mode)
    if video_path:
        print(f'  DONE: {clip_id}')
    else:
        print(f'  {clip_id} — VEO generation failed')
    return (first_frame, mid_frame, last_frame, video_path)

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
        human_delay(0.8, 1.8)
    page.evaluate('window.scrollTo(0, 0)')
    human_delay(0.8, 1.8)


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
        human_click(page, vid_tab)
        human_delay_medium(1.5, 3.5)
    _scroll_gallery_to_find_all(page)
    added = 0
    for i, clip in enumerate(clips):
        clip_id = clip['clip_id']
        veo_prompt = clip['veo_prompt']
        print(f'''\n  [{i + 1}/{len(clips)}] Adding {clip_id}...''')
        if _add_clip_to_scene_by_prompt(page, veo_prompt):
            added += 1
            human_delay_medium(1.5, 3.5)
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
    human_delay_long(6.0, 12.0)
    for _ in range(15):
        play = page.query_selector('button:has-text("play_arrow")')
        if play:
            box = play.bounding_box()
            if box and box['y'] > 500:
                print('  Scene Builder ready.')
                return True
        human_delay_medium(1.5, 3.5)
    print('  WARNING: Scene Builder may not be fully loaded')
    return False


def _exit_reorder_mode(page = None):
    """Click 'Готово' if we're in reorder mode."""
    done_btn = page.query_selector('button:has-text("Готово")')
    if done_btn:
        box = done_btn.bounding_box()
        if box:
            if box['width'] > 0:
                human_click(page, done_btn)
                human_delay_medium(1.5, 3.5)
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
    human_delay(0.8, 1.8)
    result = page.evaluate("() => {\n        const btns = document.querySelectorAll('button');\n        for (const btn of btns) {\n            const text = btn.textContent.trim();\n            const rect = btn.getBoundingClientRect();\n            const aria = btn.getAttribute('aria-label') || '';\n            // Download button near bottom-right of scene area\n            if ((text.includes('download') || text.includes('Скачать') || aria.includes('Скачать')) &&\n                rect.y > 600 && rect.y < 700) {\n                btn.click();\n                return { clicked: true, x: Math.round(rect.x), y: Math.round(rect.y) };\n            }\n        }\n        return { clicked: false };\n    }")
    if not result.get('clicked'):
        print('  WARNING: Download button not found in Scene Builder')
        take_debug_screenshot(page, 'scene_no_download_btn')
        return False
    print('  Clicked download. Waiting for rendering/download...')
    download_started = False
    for sec in range(120):
        human_delay_medium(1.5, 3.5)
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
    ctx = launch_browser(pw, headless = False, cdp_port = _cdp_port)
    page = _get_or_create_flow_page(ctx)
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
    time.sleep(random.uniform(12, 18))
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
    ctx = launch_browser(pw, headless = False, cdp_port = _cdp_port)
    page = _get_or_create_flow_page(ctx)
    print(f"Navigating to project...")
    ensure_project(page)
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
            human_pause_between_generations()
    print(f'''\n{'============================================================'}''')
    print(f'''  Finished processing {len(clips)} clips.''')
    print(f'''  OK:   {results['ok']}''')
    print(f'''  FAIL: {results['fail']}''')
    print(f'''  Frames: {FRAMES_DIR}''')
    print(f'''  Clips:  {CLIPS_DIR}''')
    print(f'''{'============================================================'}''')
    ctx.close()


def _switch_account(pw, ctx, page):
    '''On consecutive errors: try creating a new project (old one may be broken).

    Account switching is disabled — each bot stays on its own account.
    Instead, we try to create a fresh project within the same account.
    Returns (new_ctx, new_page) if project was created, (None, None) otherwise.
    '''
    old_url = ACCOUNTS[_current_account_idx].get('project_url', '')
    print(f'  Too many consecutive errors — trying to create a new project...')
    print(f'  (old project: {old_url})')
    new_url = _create_project_from_main_page(page)
    if new_url and new_url != old_url:
        print(f'  Switched to new project: {new_url}')
        # Stay on same context/page, just update the project URL
        try:
            page.goto(new_url, timeout = PAGE_LOAD_TIMEOUT, wait_until = 'domcontentloaded')
            wait_for_flow_ready(page)
            return (ctx, page)  # return same ctx/page — just new project
        except Exception as e:
            print(f'  Failed to navigate to new project: {e}')
            return (None, None)
    else:
        print('  Could not create a new project — continuing with current.')
        return (None, None)


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
    ctx = launch_browser(pw, headless = False, cdp_port = _cdp_port)
    page = _get_or_create_flow_page(ctx)
    print(f"Navigating to project...")
    ensure_project(page)
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
        for component in ('nb_first', 'nb_mid', 'nb_last'):
            # nb_mid: skip if clip has no mid prompt
            if component == 'nb_mid' and not clip.get('nano_banana_prompt_mid'):
                continue
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
            elif component == 'nb_mid':
                # nb_mid: use accepted first frame (slot A) as ingredient
                first_sel = manifest['components']['nb_first'].get('selected_variant_a')
                if first_sel:
                    first_attempt_data = manifest['components']['nb_first']['attempts'][first_sel['attempt'] - 1]
                    first_file = first_attempt_data['variants'][first_sel['variant']]['file']
                    first_frame_path = REVIEW_DIR / clip_id / 'nb_first' / f'''attempt_{first_sel['attempt']}''' / first_file
                    if first_frame_path.exists():
                        first_frame_ref = first_frame_path
                        print(f'''  Using selected first frame as ingredient for mid: {first_file}''')
                    else:
                        print(f'''  WARNING: Selected first frame not found: {first_frame_path}''')
                else:
                    print('  nb_mid: waiting for nb_first selection — skipping')
                    summary['skipped'].append(f'''{clip_id}/nb_mid (waiting for first frame selection)''')
                    continue
            elif component == 'nb_last':
                # nb_last: use accepted mid frame (if exists) or first frame as ingredient
                # Chain: first → mid → last
                ref_component = None
                mid_sel = manifest['components']['nb_mid'].get('selected_variant_a')
                if mid_sel:
                    ref_component = 'nb_mid'
                    ref_sel = mid_sel
                else:
                    # No mid frame accepted — check if mid is even configured
                    has_mid_prompt = clip.get('nano_banana_prompt_mid')
                    mid_status = get_component_status(manifest, 'nb_mid')
                    if has_mid_prompt and mid_status not in ('accepted', 'needs_manual_work'):
                        # Mid is configured but not yet accepted — wait
                        print('  nb_last: waiting for nb_mid selection — skipping')
                        summary['skipped'].append(f'''{clip_id}/nb_last (waiting for mid frame selection)''')
                        continue
                    # No mid prompt or mid failed — fall back to first frame
                    first_sel = manifest['components']['nb_first'].get('selected_variant_a')
                    if first_sel:
                        ref_component = 'nb_first'
                        ref_sel = first_sel
                    else:
                        print('  nb_last: waiting for nb_first selection — skipping (select first frame first)')
                        summary['skipped'].append(f'''{clip_id}/nb_last (waiting for first frame selection)''')
                        continue
                ref_attempt_data = manifest['components'][ref_component]['attempts'][ref_sel['attempt'] - 1]
                ref_file = ref_attempt_data['variants'][ref_sel['variant']]['file']
                ref_path = REVIEW_DIR / clip_id / ref_component / f'''attempt_{ref_sel['attempt']}''' / ref_file
                if ref_path.exists():
                    first_frame_ref = ref_path
                    ref_label = 'mid' if ref_component == 'nb_mid' else 'first'
                    print(f'''  Using selected {ref_label} frame as ingredient: {ref_file}''')
                else:
                    print(f'''  WARNING: Selected {ref_component} frame not found: {ref_path}''')
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
            if component in ('nb_first', 'nb_mid'):
                print(f'''  Pausing {PAUSE_BETWEEN_GENERATIONS}s...''')
                human_pause_between_generations()
        veo_status = get_component_status(manifest, 'veo')
        if veo_status in ('accepted', 'needs_manual_work'):
            print(f'''  veo: {veo_status} — skipping''')
            summary['skipped'].append(f'''{clip_id}/veo''')
        else:
            first_sel_a = manifest['components']['nb_first'].get('selected_variant_a')
            last_sel_a = manifest['components']['nb_last'].get('selected_variant_a')
            # Check if nb_mid is required and wait for it
            has_mid_prompt = clip.get('nano_banana_prompt_mid')
            mid_sel_a = manifest['components']['nb_mid'].get('selected_variant_a')
            if has_mid_prompt and not mid_sel_a:
                mid_status = get_component_status(manifest, 'nb_mid')
                if mid_status not in ('needs_manual_work',):
                    if not first_sel_a or not last_sel_a:
                        print('  veo: waiting for frame selection — skipping')
                        summary['skipped'].append(f'''{clip_id}/veo (waiting for frames)''')
                    else:
                        print('  veo: waiting for nb_mid selection — skipping')
                        summary['skipped'].append(f'''{clip_id}/veo (waiting for mid frame)''')
                    first_sel_a = None  # force skip below
            if not first_sel_a or not last_sel_a:
                if first_sel_a is None and last_sel_a is None:
                    pass  # already printed message above
                else:
                    print('  veo: waiting for frame selection — skipping')
                    summary['skipped'].append(f'''{clip_id}/veo (waiting for frames)''')
            else:
                # --- Resolve A frame paths ---
                first_attempt_a = manifest['components']['nb_first']['attempts'][first_sel_a['attempt'] - 1]
                first_file_a = first_attempt_a['variants'][first_sel_a['variant']]['file']
                first_path_a = REVIEW_DIR / clip_id / 'nb_first' / f'''attempt_{first_sel_a['attempt']}''' / first_file_a
                last_attempt_a = manifest['components']['nb_last']['attempts'][last_sel_a['attempt'] - 1]
                last_file_a = last_attempt_a['variants'][last_sel_a['variant']]['file']
                last_path_a = REVIEW_DIR / clip_id / 'nb_last' / f'''attempt_{last_sel_a['attempt']}''' / last_file_a
                # Resolve mid A frame path (optional)
                mid_path_a = None
                if mid_sel_a:
                    mid_attempt_a = manifest['components']['nb_mid']['attempts'][mid_sel_a['attempt'] - 1]
                    mid_file_a = mid_attempt_a['variants'][mid_sel_a['variant']]['file']
                    mid_path_a = REVIEW_DIR / clip_id / 'nb_mid' / f'''attempt_{mid_sel_a['attempt']}''' / mid_file_a
                    if not mid_path_a.exists():
                        print(f'''  WARNING: Selected mid frame A not found: {mid_path_a}''')
                        mid_path_a = None

                # --- Resolve B frame paths (for VEO batch B) ---
                first_sel_b = manifest['components']['nb_first'].get('selected_variant_b')
                last_sel_b = manifest['components']['nb_last'].get('selected_variant_b')
                mid_sel_b = manifest['components']['nb_mid'].get('selected_variant_b')

                first_path_b = None
                if first_sel_b:
                    fb_attempt = manifest['components']['nb_first']['attempts'][first_sel_b['attempt'] - 1]
                    fb_file = fb_attempt['variants'][first_sel_b['variant']]['file']
                    first_path_b = REVIEW_DIR / clip_id / 'nb_first' / f'''attempt_{first_sel_b['attempt']}''' / fb_file
                    if not first_path_b.exists():
                        first_path_b = None

                last_path_b = None
                if last_sel_b:
                    lb_attempt = manifest['components']['nb_last']['attempts'][last_sel_b['attempt'] - 1]
                    lb_file = lb_attempt['variants'][last_sel_b['variant']]['file']
                    last_path_b = REVIEW_DIR / clip_id / 'nb_last' / f'''attempt_{last_sel_b['attempt']}''' / lb_file
                    if not last_path_b.exists():
                        last_path_b = None

                mid_path_b = None
                if mid_sel_b:
                    mb_attempt = manifest['components']['nb_mid']['attempts'][mid_sel_b['attempt'] - 1]
                    mb_file = mb_attempt['variants'][mid_sel_b['variant']]['file']
                    mid_path_b = REVIEW_DIR / clip_id / 'nb_mid' / f'''attempt_{mid_sel_b['attempt']}''' / mb_file
                    if not mid_path_b.exists():
                        mid_path_b = None

                if not first_path_a.exists() or not last_path_a.exists():
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
                        veo_mode = clip.get('veo_mode', 'frames')
                        print(f'''  Pausing {PAUSE_BETWEEN_GENERATIONS}s before VEO...''')
                        human_pause_between_generations()
                        variants = review_veo(page, clip, manifest, attempt,
                                              first_frame=first_path_a, last_frame=last_path_a,
                                              prompt_override=prompt_override,
                                              mid_frame=mid_path_a, veo_mode=veo_mode,
                                              first_frame_b=first_path_b, last_frame_b=last_path_b,
                                              mid_frame_b=mid_path_b)
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
                                    human_pause_between_generations()
        if i < len(clips) - 1:
            print(f'''\nPausing {PAUSE_BETWEEN_GENERATIONS}s before next clip...''')
            human_pause_between_generations()
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


def do_select(clip_id, component, attempt = None, variant = None, scores_json = None, trim_start = None, trim_end = None, batch = 'a'):
    '''Select a variant and record its scores.

    batch: 'a' or 'b' — which slot to write to (selected_variant_a or selected_variant_b).

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
    print(f'''  Clip: {clip_id} | Component: {component} | Attempt: {attempt} | Variant: {variant} | Batch: {batch}''')
    print(f'''  Scores: {scores}''')
    print(f'''  Average: {avg:.2f} (threshold: {QUALITY_THRESHOLD})''')
    if trim_start is not None or trim_end is not None:
        print(f'''  Trim: {trim_start}s — {trim_end}s''')

    # Check critical criteria — auto-reject if any critical score <= CRITICAL_MIN_SCORE - 1
    critical_failures = []
    for crit in CRITICAL_CRITERIA:
        if crit in scores and scores[crit] < CRITICAL_MIN_SCORE:
            critical_failures.append(f'{crit}={scores[crit]}')
    if critical_failures:
        print(f'  REJECTED — critical criteria failed: {", ".join(critical_failures)}')
        print(f'  (Critical minimum: {CRITICAL_MIN_SCORE} for {", ".join(CRITICAL_CRITERIA)})')
        save_manifest(clip_id, manifest)
        return

    if avg >= QUALITY_THRESHOLD:
        mark_selected(manifest, component, attempt, variant, scores, avg, batch=batch)
        if trim_start is not None:
            attempt_entry['variants'][variant]['trim_start'] = trim_start
        if trim_end is not None:
            attempt_entry['variants'][variant]['trim_end'] = trim_end
        save_manifest(clip_id, manifest)
        copy_selected_to_output(clip_id, manifest, trim_start, trim_end)
        print(f'  ACCEPTED (batch {batch.upper()}) — variant copied to output.')
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


def _format_status_cell(comp_data, clip, comp_name):
    '''Format a single status cell for do_status() output.'''
    status = comp_data.get('status', 'pending')
    n_attempts = len(comp_data.get('attempts', []))

    # nb_mid with no attempts = not configured
    if comp_name == 'nb_mid' and n_attempts == 0 and status == 'pending':
        if not clip.get('nano_banana_prompt_mid'):
            return ('—', None)

    sel_a = comp_data.get('selected_variant_a')
    sel_b = comp_data.get('selected_variant_b')

    if status == 'accepted':
        # Show which slots are filled
        slots = 'A' if sel_a else ''
        slots += '+B' if sel_b else ''
        if slots and slots != 'A':
            return (f'ACCEPTED ({slots})', 'accepted')
        return ('ACCEPTED', 'accepted')
    elif status == 'needs_manual_work':
        return ('MANUAL', 'manual')
    elif n_attempts > 0:
        # Show variant count per batch
        last_attempt = comp_data['attempts'][-1]
        a_count = last_attempt.get('batch_a_count')
        b_count = last_attempt.get('batch_b_count')
        best = last_attempt.get('best_avg')

        parts = f'a{n_attempts}'
        if a_count is not None and b_count is not None and b_count > 0:
            parts += f' ({a_count}+{b_count})'
        if best:
            parts += f' best={best:.1f}'

        # Show slot status
        slot_info = []
        if sel_a:
            slot_info.append('A')
        if sel_b:
            slot_info.append('B')
        if slot_info:
            parts += f' sel={"+".join(slot_info)}'
        else:
            parts += ' awaiting'
        return (parts, 'awaiting')
    else:
        return ('pending', 'pending')


def do_status(clip_filter = None):
    '''Print status overview of all clips and their review state.'''
    if not PROMPTS_PATH.exists():
        print(f'''Error: prompts not found: {PROMPTS_PATH}''')
        sys.exit(1)
    clips = load_clips(PROMPTS_PATH, clip_filter)
    print(f'''\n{'========================================================================================'}''')
    print(f'''  {'CLIP':<10} {'NB_FIRST':<22} {'NB_MID':<22} {'NB_LAST':<22} {'VEO':<22}''')
    print(f'''  {'----------'} {'----------------------'} {'----------------------'} {'----------------------'} {'----------------------'}''')
    cols = {'total': 0, 'accepted': 0, 'awaiting': 0, 'pending': 0, 'manual': 0}
    for clip in clips:
        clip_id = clip['clip_id']
        manifest = load_manifest(clip_id)
        cols['total'] += 1
        cells = []
        for c in ('nb_first', 'nb_mid', 'nb_last', 'veo'):
            comp_data = manifest['components'].get(c, {})
            (label, category) = _format_status_cell(comp_data, clip, c)
            cells.append(label)
            if category:
                cols[category] = cols.get(category, 0) + 1
        print(f'''  {clip_id:<10} {cells[0]:<22} {cells[1]:<22} {cells[2]:<22} {cells[3]:<22}''')
    print(f'''{'========================================================================================'}''')
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


def do_generate_refs(pw=None, task_filter=None, tasks_file=None):
    '''Generate additional character reference images via NB Pro.

    Reads tasks from ref_tasks.json. For each task:
      - Uploads character ingredient(s)
      - Enters the prompt
      - Generates 4 variants
      - Downloads all to output/generated_refs/{task_id}/

    Use --ref-task to filter to a specific task_id.
    '''
    ref_path = Path(tasks_file) if tasks_file else REF_TASKS_PATH
    if not ref_path.exists():
        print(f'Error: ref tasks not found: {ref_path}')
        sys.exit(1)
    with open(ref_path, 'r') as f:
        data = json.load(f)
    tasks = data.get('tasks', [])
    if task_filter:
        tasks = [t for t in tasks if t['task_id'] == task_filter]
    if not tasks:
        print('No tasks to process.')
        return

    # Skip already generated tasks
    pending_tasks = []
    for task in tasks:
        dest_dir = GENERATED_REFS_DIR / task['task_id']
        existing = list(dest_dir.glob('variant_*.png')) if dest_dir.exists() else []
        if existing:
            print(f'  {task["task_id"]}: already has {len(existing)} variants — skipping')
        else:
            pending_tasks.append(task)

    if not pending_tasks:
        print('All reference tasks already generated.')
        return

    # Sort by priority
    pending_tasks.sort(key=lambda t: t.get('priority', 99))
    print(f'Reference generation: {len(pending_tasks)} tasks to process.\n')

    ctx = launch_browser(pw, headless=False, cdp_port=_cdp_port)
    page = _get_or_create_flow_page(ctx)
    print("Navigating to project...")
    ensure_project(page)
    wait_for_flow_ready(page)

    generated = []
    failed = []

    for i, task in enumerate(pending_tasks):
        task_id = task['task_id']
        prompt = task['prompt']
        ingredients = task.get('ingredients', [])

        print(f'\n{"=" * 60}')
        print(f'  [{i+1}/{len(pending_tasks)}] REF: {task_id} ({task.get("character", task.get("location", ""))})')
        print(f'  Purpose: {task["purpose"]}')
        print(f'  Prompt: {prompt[:80]}...')
        print(f'{"=" * 60}')

        # Set up NB Pro mode
        switch_mode(page, 'Создать изображение')
        img_tab = page.query_selector('button[role="radio"]:has-text("Изображения")')
        if img_tab:
            human_click(page, img_tab)
            human_delay(0.8, 1.8)
        set_image_model(page, 'Nano Banana Pro')
        set_variant_count(page, 4)

        # Upload ingredients
        uploaded = upload_ingredients(page, ingredients)
        if uploaded == 0:
            print(f'  FAILED: No ingredients uploaded — skipping {task_id}')
            failed.append(task_id)
            continue

        # Generate
        dest_dir = GENERATED_REFS_DIR / task_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        current_urls = get_gallery_urls(page)
        clear_prompt(page)
        sanitized = sanitize_nb_prompt(prompt)
        fill_prompt(page, sanitized)
        take_debug_screenshot(page, f'ref_{task_id}_before_gen')
        maybe_idle_movement(page)
        click_generate(page)

        result = wait_for_new_gallery_item(page, current_urls)
        if result == 'success':
            take_debug_screenshot(page, f'ref_{task_id}_after_gen')
            saved = download_all_new_images(page, current_urls, dest_dir)
            print(f'  Downloaded {len(saved)} variants for {task_id}')
            generated.append(f'{task_id} ({len(saved)} variants)')
        else:
            print(f'  FAILED: {task_id} — {result}')
            failed.append(task_id)

        # Pause between generations
        if i < len(pending_tasks) - 1:
            print(f'  Pausing between generations...')
            human_pause_between_generations()

    # Summary
    print(f'\n{"=" * 60}')
    print(f'  REFERENCE GENERATION SUMMARY')
    print(f'{"=" * 60}')
    print(f'  Generated: {len(generated)}')
    for g in generated:
        print(f'    ✓ {g}')
    if failed:
        print(f'  Failed: {len(failed)}')
        for f_id in failed:
            print(f'    ✗ {f_id}')
    print()


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
    group.add_argument('--generate-refs', action = 'store_true', help = 'Generate additional character reference images via NB Pro')
    parser.add_argument('--clip', type = str, default = None, help = 'Process only this clip (e.g. S02_A)')
    parser.add_argument('--component', type = str, default = None, choices = [
        'nb_first',
        'nb_mid',
        'nb_last',
        'veo'], help = 'Component for --select/--fail/--rewrite/--extract-frames')
    parser.add_argument('--attempt', type = int, default = None, help = 'Attempt number for --select/--fail/--extract-frames')
    parser.add_argument('--variant', type = int, default = None, help = 'Variant index (0-based) for --select')
    parser.add_argument('--scores', type = str, default = None, help = 'JSON scores for --select/--fail, e.g. \'{"char":8,"comp":7,"loc":8,"anim":0,"artifacts":9,"overall":8,"style":7}\'')
    parser.add_argument('--trim-start', type = float, default = None, help = 'Trim start time in seconds for VEO --select')
    parser.add_argument('--trim-end', type = float, default = None, help = 'Trim end time in seconds for VEO --select')
    parser.add_argument('--prompt', type = str, default = None, help = 'New prompt text for --rewrite')
    parser.add_argument('--ref-task', type = str, default = None, help = 'Process only this ref task (e.g. ref_amin_sitting) for --generate-refs')
    parser.add_argument('--batch', type = str, default = 'a', choices = ['a', 'b'], help = 'Batch slot for --select: a (default) or b')
    parser.add_argument('--ref-tasks-file', type = str, default = None, help = 'Path to ref tasks JSON file (default: output/prompts/ref_tasks.json)')
    parser.add_argument('--headless', action = 'store_true', help = 'Run in headless mode (not recommended for first run)')
    parser.add_argument('--disable-gpu', action = 'store_true', help = 'Disable GPU acceleration (allows 4 bots simultaneously)')
    parser.add_argument('--account', type = int, default = 1, choices = [
        1, 2, 3, 4], help = 'Bot number (1-4). Bots 1-2 use account 1, bots 3-4 use account 2')
    parser.add_argument('--session-dir', type = str, default = None, help = 'Custom session directory (overrides --account session)')
    parser.add_argument('--project-url', type = str, default = None, help = 'Custom project URL (overrides --account project)')
    parser.add_argument('--new-project', action = 'store_true', help = 'Force create a new project instead of using existing one')
    parser.add_argument('--cdp-port', type = int, default = None, help = 'Connect to existing Chrome via CDP (e.g. 9222). Launch Chrome first with ./scripts/launch_chrome.sh')
    args = parser.parse_args()
    _current_account_idx = args.account - 1
    global _disable_gpu, _cdp_port
    _disable_gpu = args.disable_gpu
    _cdp_port = args.cdp_port
    # Override session dir and project URL if provided
    if args.session_dir:
        custom_session = Path(args.session_dir)
        if not custom_session.is_absolute():
            custom_session = PROJECT_ROOT / args.session_dir
        ACCOUNTS[_current_account_idx]['session_dir'] = custom_session
    if args.project_url:
        ACCOUNTS[_current_account_idx]['project_url'] = args.project_url
    if args.new_project:
        ACCOUNTS[_current_account_idx]['project_url'] = ''
        print(f'  --new-project: will create a new project on launch')
    ensure_dirs()
    if args.select:
        if not all([args.clip, args.component, args.attempt, args.variant is not None, args.scores]):
            parser.error('--select requires --clip, --component, --attempt, --variant, --scores')
        do_select(args.clip, args.component, args.attempt, args.variant, args.scores, args.trim_start, args.trim_end, batch=args.batch)
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
        # Set global timeout to prevent infinite hangs (0 = no timeout)
        timeout = GLOBAL_TIMEOUT_SEC
        if args.login:
            timeout = 600  # 10 min for login (manual interaction)
        if timeout > 0:
            signal.signal(signal.SIGALRM, _global_timeout_handler)
            signal.alarm(timeout)
            print(f'  Global timeout: {timeout}s ({timeout // 60}m)')
        else:
            print(f'  No timeout — bot runs until task completion')

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
                elif args.generate_refs:
                    do_generate_refs(pw, args.ref_task, args.ref_tasks_file)
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
