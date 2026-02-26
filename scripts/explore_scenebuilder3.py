#!/usr/bin/env python3
"""Explore: Scene Builder part 3 — add clips and explore full UI.

Uses force=True and JS clicks to bypass overlay interception.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
EXPLORE_DIR = PROJECT_ROOT / "output" / "explore"
FLOW_PROJECT_URL = "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869"


def screenshot(page, name):
    path = EXPLORE_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  Screenshot: {path.name}")


def dump_buttons(page, label, y_min=0, y_max=2000):
    elements = page.evaluate(f"""() => {{
        const results = [];
        document.querySelectorAll('button, a[href], [role="tab"], [role="slider"], [draggable="true"]').forEach(el => {{
            const rect = el.getBoundingClientRect();
            if (rect.width > 3 && rect.y > {y_min} && rect.y < {y_max}) {{
                results.push({{
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    text: (el.textContent || '').trim().substring(0, 100),
                    ariaLabel: el.getAttribute('aria-label') || '',
                    draggable: el.draggable || el.getAttribute('draggable') === 'true',
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                }});
            }}
        }});
        return results.sort((a,b) => a.y - b.y || a.x - b.x);
    }}""")
    seen = set()
    print(f"\n  {label} ({len(elements)} elements):")
    for el in elements:
        key = f"{el['tag']}-{el['x']}-{el['y']}-{el['w']}"
        if key not in seen:
            seen.add(key)
            extra = f" role={el['role']}" if el['role'] else ""
            extra += f" aria='{el['ariaLabel']}'" if el['ariaLabel'] else ""
            extra += " [DRAG]" if el['draggable'] else ""
            print(f"    [{el['tag']:<8}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}: {el['text'][:70]}{extra}")


def js_click(page, selector):
    """Click element via JS to bypass overlay interception."""
    result = page.evaluate(f"""() => {{
        const el = document.querySelector('{selector}');
        if (el) {{
            el.click();
            return true;
        }}
        return false;
    }}""")
    return result


def js_click_by_text(page, tag, text):
    """Click element matching tag and text content via JS."""
    result = page.evaluate(f"""(text) => {{
        const els = document.querySelectorAll('{tag}');
        for (const el of els) {{
            if (el.textContent.trim().includes(text)) {{
                const rect = el.getBoundingClientRect();
                if (rect.width > 0) {{
                    el.click();
                    return {{ clicked: true, x: Math.round(rect.x), y: Math.round(rect.y) }};
                }}
            }}
        }}
        return {{ clicked: false }};
    }}""", text)
    return result


def main():
    EXPLORE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()

        print("Opening project...")
        page.goto(FLOW_PROJECT_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_selector("textarea", timeout=60000)
        time.sleep(5)

        # Make sure we're on video tab
        vid_tab = page.query_selector('button[role="radio"]:has-text("Видео")')
        if vid_tab:
            vid_tab.click()
            time.sleep(2)

        # === Step 1: Add first video to scene via JS click ===
        print("\n=== Step 1: Add video to scene (JS click) ===")
        result = js_click_by_text(page, "button", "Добавить в сцену")
        print(f"  Click result: {result}")
        time.sleep(3)
        screenshot(page, "sb3_01_after_add_to_scene")

        # Check for toast/snackbar
        toasts = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const text = (el.textContent || '').trim();
                if ((text.includes('добавлен') || text.includes('сцен') || text.includes('added')) &&
                    text.length < 100) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 50 && rect.height < 80 && rect.y > 600) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: text,
                            x: Math.round(rect.x), y: Math.round(rect.y),
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"  Toast messages: {toasts}")

        # Add second video to scene
        print("\n  Adding second video to scene...")
        # Find all "Добавить в сцену" buttons and click the second one
        result2 = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            let count = 0;
            for (const btn of btns) {
                if (btn.textContent.trim().includes('Добавить в сцену')) {
                    count++;
                    if (count === 2) {
                        btn.click();
                        return { clicked: true, index: 2 };
                    }
                }
            }
            return { clicked: false, count: count };
        }""")
        print(f"  Second add result: {result2}")
        time.sleep(3)

        # === Step 2: Navigate to Scene Builder ===
        print("\n=== Step 2: Open Scene Builder ===")
        result = js_click_by_text(page, "button", "Конструктор сцен")
        print(f"  Click 'Конструктор сцен': {result}")
        time.sleep(5)
        print(f"  URL: {page.url}")
        screenshot(page, "sb3_02_scene_builder_with_clips")

        # === Step 3: Full UI dump ===
        print("\n=== Step 3: Scene Builder UI with clips ===")
        dump_buttons(page, "All interactive elements")

        # Count clip items
        clip_items = page.evaluate("""() => {
            const results = [];
            // Look for video elements, thumbnails, clip cards
            document.querySelectorAll('video, [class*="clip"], [class*="card"], [class*="thumb"], [class*="item"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 30 && rect.height > 30 && rect.y > 50) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        cls: (el.className?.toString() || '').substring(0, 80),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                        draggable: el.draggable || el.getAttribute('draggable') === 'true',
                    });
                }
            });
            return results;
        }""")
        print(f"\n  Clip/media items ({len(clip_items)}):")
        for c in clip_items:
            drag = " [DRAG]" if c['draggable'] else ""
            print(f"    [{c['tag']}] ({c['x']},{c['y']}) {c['w']}x{c['h']}: cls={c['cls'][:50]}{drag}")

        # Look at the main scene area (y 60-600)
        scene_content = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('video, img').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 50 && rect.y > 60 && rect.y < 700) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        src: (el.src || '').substring(0, 100),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"\n  Videos/images in scene area ({len(scene_content)}):")
        for s in scene_content:
            print(f"    [{s['tag']}] ({s['x']},{s['y']}) {s['w']}x{s['h']}: {s['src'][:80]}")

        # === Step 4: Look for export/render/download ===
        print("\n=== Step 4: Export/render buttons ===")
        export_matches = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button, a').forEach(el => {
                const text = (el.textContent || '').trim().toLowerCase();
                const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                if (text.includes('экспорт') || text.includes('export') || text.includes('render') ||
                    text.includes('рендер') || text.includes('скачать') || text.includes('download') ||
                    text.includes('сохран') || text.includes('save') || text.includes('share') ||
                    text.includes('поделиться') || text.includes('опубликов') ||
                    aria.includes('export') || aria.includes('download') || aria.includes('save') ||
                    aria.includes('share')) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: (el.textContent || '').trim().substring(0, 80),
                            aria: aria.substring(0, 80),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"  Export elements ({len(export_matches)}):")
        for e in export_matches:
            aria = f" aria='{e['aria']}'" if e['aria'] else ""
            print(f"    [{e['tag']}] ({e['x']},{e['y']}): {e['text'][:60]}{aria}")

        # === Step 5: Look for ordering/reorder controls ===
        print("\n=== Step 5: Ordering/reorder controls ===")
        order_matches = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button, [draggable="true"]').forEach(el => {
                const text = (el.textContent || '').trim().toLowerCase();
                const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                if (text.includes('drag') || text.includes('reorder') || text.includes('move') ||
                    text.includes('порядок') || text.includes('перемест') || text.includes('arrow_back') ||
                    text.includes('arrow_forward') || text.includes('swap') ||
                    el.getAttribute('draggable') === 'true') {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: (el.textContent || '').trim().substring(0, 60),
                            aria: aria.substring(0, 60),
                            draggable: el.getAttribute('draggable') === 'true',
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"  Reorder elements ({len(order_matches)}):")
        for o in order_matches:
            drag = " [DRAG]" if o['draggable'] else ""
            print(f"    [{o['tag']}] ({o['x']},{o['y']}) {o['w']}x{o['h']}: {o['text'][:40]}{drag}")

        # === Step 6: Try clicking the "add" button in scene builder ===
        print("\n=== Step 6: Click 'add' in scene builder (center area) ===")
        # The big "add" button at ~(640, 602)
        add_result = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = btn.textContent.trim();
                const rect = btn.getBoundingClientRect();
                // The large add button in the scene area
                if (text === 'add' && rect.y > 500 && rect.y < 700 && rect.width > 100) {
                    btn.click();
                    return { clicked: true, x: Math.round(rect.x), y: Math.round(rect.y) };
                }
            }
            return { clicked: false };
        }""")
        print(f"  Click result: {add_result}")
        time.sleep(3)
        screenshot(page, "sb3_03_after_add_in_builder")

        # Check what appeared
        print("\n  What appeared after clicking 'add':")
        dump_buttons(page, "Elements after clicking add in scene builder")

        # Check for dialog/panel
        dialogs = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('[role="dialog"], [role="menu"], [role="listbox"], [class*="panel"], [class*="drawer"], [class*="sidebar"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 20) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        role: el.getAttribute('role') || '',
                        cls: (el.className?.toString() || '').substring(0, 80),
                        text: (el.textContent || '').trim().substring(0, 200),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"\n  Dialogs/panels ({len(dialogs)}):")
        for d in dialogs:
            print(f"    [{d['tag']}] ({d['x']},{d['y']}) {d['w']}x{d['h']}: role={d['role']} cls={d['cls'][:40]} text={d['text'][:80]}")

        # === Step 7: Check unique button texts in scene builder ===
        print("\n=== Step 7: All unique button texts ===")
        all_btns = page.evaluate("""() => {
            const texts = new Map();
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim().substring(0, 60);
                const rect = btn.getBoundingClientRect();
                if (rect.width > 0 && text.length > 0) {
                    texts.set(text, { x: Math.round(rect.x), y: Math.round(rect.y) });
                }
            });
            return [...texts.entries()].map(([text, pos]) => ({ text, ...pos })).sort((a,b) => a.y - b.y);
        }""")
        print(f"  Unique button texts ({len(all_btns)}):")
        for b in all_btns:
            print(f"    ({b['x']:4},{b['y']:4}): '{b['text']}'")

        # === Step 8: Look for trim/cut/split controls ===
        print("\n=== Step 8: Trim/cut/split controls ===")
        trim_matches = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const text = (el.textContent || '').trim().toLowerCase();
                if ((text.includes('trim') || text.includes('cut') || text.includes('split') ||
                     text.includes('обрез') || text.includes('разрез') || text.includes('длительност') ||
                     text.includes('duration') || text.includes('speed') || text.includes('скорост')) &&
                    text.length < 60) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && rect.y > 60) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: text.substring(0, 60),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                        });
                    }
                }
            });
            // Deduplicate
            const seen = new Set();
            return results.filter(r => {
                const key = `${r.tag}-${r.x}-${r.y}`;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
        }""")
        print(f"  Trim/cut elements ({len(trim_matches)}):")
        for t in trim_matches:
            print(f"    [{t['tag']}] ({t['x']},{t['y']}): {t['text']}")

        print("\n=== Done. Browser stays open 60s ===")
        time.sleep(60)
        ctx.close()
        print("Done.")


if __name__ == "__main__":
    main()
