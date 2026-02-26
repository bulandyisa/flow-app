#!/usr/bin/env python3
"""Explore: Scene Builder (Конструктор сцен) UI in Google Flow — part 2.

Clicks "Конструктор сцен" to enter the scene builder and dumps its UI.
Also explores "Добавить в сцену" button behavior.
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
    """Dump all interactive elements."""
    elements = page.evaluate(f"""() => {{
        const results = [];
        document.querySelectorAll('button, a[href], [role="tab"], [role="radio"], [role="menuitem"], [role="slider"], input, [draggable]').forEach(el => {{
            const rect = el.getBoundingClientRect();
            if (rect.width > 3 && rect.y > {y_min} && rect.y < {y_max}) {{
                results.push({{
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    text: (el.textContent || '').trim().substring(0, 100),
                    ariaLabel: el.getAttribute('aria-label') || '',
                    draggable: el.draggable || false,
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


def dump_structure(page, label):
    """Dump the DOM structure of key areas."""
    structure = page.evaluate("""() => {
        const results = [];
        // Look for timeline/track/scene-related containers
        document.querySelectorAll('*').forEach(el => {
            const cls = el.className?.toString() || '';
            const id = el.id || '';
            if (cls.includes('timeline') || cls.includes('track') || cls.includes('scene') ||
                cls.includes('clip') || cls.includes('drag') || cls.includes('thumb') ||
                id.includes('timeline') || id.includes('scene')) {
                const rect = el.getBoundingClientRect();
                if (rect.width > 10) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        cls: cls.substring(0, 100),
                        id: id,
                        children: el.children.length,
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            }
        });
        return results;
    }""")
    print(f"\n  {label} ({len(structure)} containers):")
    for s in structure:
        extra = f" id={s['id']}" if s['id'] else ""
        print(f"    [{s['tag']}] ({s['x']},{s['y']}) {s['w']}x{s['h']}: cls={s['cls'][:60]}{extra} children={s['children']}")


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

        # === Step 1: Click "Конструктор сцен" ===
        print("\n=== Step 1: Click 'Конструктор сцен' (Scene Builder) ===")
        sb_btn = page.query_selector('button:has-text("Конструктор сцен")')
        if sb_btn:
            box = sb_btn.bounding_box()
            print(f"  Found 'Конструктор сцен' at ({box['x']:.0f}, {box['y']:.0f})")
            sb_btn.click()
            time.sleep(5)
            print(f"  URL after click: {page.url}")
            screenshot(page, "sb2_01_scene_builder_opened")
        else:
            print("  'Конструктор сцен' NOT FOUND!")
            # Try alternative texts
            for alt in ["Scene Builder", "scene builder", "конструктор", "Scenes"]:
                alt_btn = page.query_selector(f'button:has-text("{alt}")')
                if alt_btn:
                    print(f"  Found alternative: '{alt}'")
                    alt_btn.click()
                    time.sleep(5)
                    break
            screenshot(page, "sb2_01_no_scene_builder")

        # === Step 2: Dump the Scene Builder UI ===
        print("\n=== Step 2: Scene Builder UI dump ===")
        dump_buttons(page, "All interactive elements in Scene Builder")
        dump_structure(page, "Timeline/scene/track containers")

        # Check for video/clip items in the scene builder
        clip_items = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('video, img, [class*="clip"], [class*="item"], [class*="card"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 30 && rect.height > 30) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        cls: (el.className?.toString() || '').substring(0, 80),
                        src: (el.src || '').substring(0, 80),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                        draggable: el.draggable || false,
                    });
                }
            });
            return results;
        }""")
        print(f"\n  Media/clip elements ({len(clip_items)}):")
        for c in clip_items:
            drag = " [DRAG]" if c['draggable'] else ""
            print(f"    [{c['tag']}] ({c['x']},{c['y']}) {c['w']}x{c['h']}: cls={c['cls'][:50]} src={c['src'][:40]}{drag}")

        # === Step 3: Look for export/render/download buttons ===
        print("\n=== Step 3: Export/Render/Download options ===")
        export_matches = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button, a').forEach(el => {
                const text = (el.textContent || '').toLowerCase().trim();
                const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                if (text.includes('экспорт') || text.includes('export') || text.includes('render') ||
                    text.includes('рендер') || text.includes('скачать') || text.includes('download') ||
                    text.includes('сохран') || text.includes('save') || text.includes('publish') ||
                    text.includes('опубликов') || text.includes('share') ||
                    aria.includes('export') || aria.includes('download') || aria.includes('save')) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: text.substring(0, 80),
                            aria: aria.substring(0, 80),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"  Export-related elements ({len(export_matches)}):")
        for e in export_matches:
            aria = f" aria='{e['aria']}'" if e['aria'] else ""
            print(f"    [{e['tag']}] ({e['x']},{e['y']}) {e['w']}x{e['h']}: {e['text'][:60]}{aria}")

        # === Step 4: Look for timeline track and its structure ===
        print("\n=== Step 4: Timeline structure ===")
        # Look for horizontal scrollable areas, tracks, or timeline-like elements
        timeline = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                // Look for wide horizontal elements that could be a timeline
                if (rect.width > 500 && rect.height > 30 && rect.height < 200 &&
                    rect.y > 400) {
                    const hasOverflow = style.overflowX === 'scroll' || style.overflowX === 'auto';
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        cls: (el.className?.toString() || '').substring(0, 80),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                        overflow: hasOverflow,
                        children: el.children.length,
                    });
                }
            });
            return results.sort((a,b) => a.y - b.y);
        }""")
        print(f"  Potential timeline elements ({len(timeline)}):")
        for t in timeline:
            ovf = " [SCROLL]" if t['overflow'] else ""
            print(f"    [{t['tag']}] ({t['x']},{t['y']}) {t['w']}x{t['h']}: cls={t['cls'][:50]} children={t['children']}{ovf}")

        # === Step 5: Look for "add" or "+" buttons in scene builder ===
        print("\n=== Step 5: Add/plus buttons ===")
        add_btns = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim();
                if (text === 'add' || text === '+' || text === 'add_circle' ||
                    text.includes('Добавить') || text.includes('transition_push')) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            text: text.substring(0, 60),
                            ariaLabel: btn.getAttribute('aria-label') || '',
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"  Add buttons ({len(add_btns)}):")
        for b in add_btns:
            aria = f" aria='{b['ariaLabel']}'" if b['ariaLabel'] else ""
            print(f"    ({b['x']:4},{b['y']:4}) {b['w']:3}x{b['h']:3}: {b['text'][:40]}{aria}")

        # === Step 6: Check for drag-drop areas ===
        print("\n=== Step 6: Drag-drop and sortable areas ===")
        dnd = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('[draggable="true"], [data-drag], [data-drop], [class*="sortable"], [class*="draggable"], [class*="droppable"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 10) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        cls: (el.className?.toString() || '').substring(0, 80),
                        text: (el.textContent || '').trim().substring(0, 60),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"  Drag-drop elements ({len(dnd)}):")
        for d in dnd:
            print(f"    [{d['tag']}] ({d['x']},{d['y']}) {d['w']}x{d['h']}: cls={d['cls'][:50]} text={d['text'][:40]}")

        screenshot(page, "sb2_02_scene_builder_full")

        # === Step 7: Go back to gallery and try "Добавить в сцену" ===
        print("\n=== Step 7: Go back and try 'Добавить в сцену' ===")
        # Navigate back
        page.go_back()
        time.sleep(5)
        page.wait_for_selector("textarea", timeout=60000)
        time.sleep(3)

        # Switch to video tab
        vid_tab = page.query_selector('button[role="radio"]:has-text("Видео")')
        if vid_tab:
            vid_tab.click()
            time.sleep(2)

        # Click "Добавить в сцену"
        add_scene_btn = page.query_selector('button:has-text("Добавить в сцену")')
        if add_scene_btn:
            box = add_scene_btn.bounding_box()
            print(f"  Found 'Добавить в сцену' at ({box['x']:.0f}, {box['y']:.0f})")
            add_scene_btn.click()
            time.sleep(3)
            screenshot(page, "sb2_03_after_add_to_scene")

            # Check for toast/notification/dialog
            toasts = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('[role="alert"], [role="status"], [class*="toast"], [class*="snack"], [class*="notification"]').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: (el.textContent || '').trim().substring(0, 200),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                        });
                    }
                });
                return results;
            }""")
            print(f"\n  Toasts/notifications after add ({len(toasts)}):")
            for t in toasts:
                print(f"    [{t['tag']}] ({t['x']},{t['y']}): {t['text'][:100]}")

            dump_buttons(page, "Buttons after 'Добавить в сцену'")

            # Now go to scene builder to see if the clip appeared
            print("\n  Going to Scene Builder to check...")
            sb_btn2 = page.query_selector('button:has-text("Конструктор сцен")')
            if sb_btn2:
                sb_btn2.click()
                time.sleep(5)
                screenshot(page, "sb2_04_scene_builder_with_clip")
                dump_buttons(page, "Scene Builder after adding clip")

                # Check for clips in timeline
                clips_in_sb = page.evaluate("""() => {
                    const results = [];
                    document.querySelectorAll('video, [class*="clip"], [class*="thumb"]').forEach(el => {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 20) {
                            results.push({
                                tag: el.tagName.toLowerCase(),
                                cls: (el.className?.toString() || '').substring(0, 80),
                                x: Math.round(rect.x), y: Math.round(rect.y),
                                w: Math.round(rect.width), h: Math.round(rect.height),
                            });
                        }
                    });
                    return results;
                }""")
                print(f"\n  Clips in Scene Builder ({len(clips_in_sb)}):")
                for c in clips_in_sb:
                    print(f"    [{c['tag']}] ({c['x']},{c['y']}) {c['w']}x{c['h']}: cls={c['cls'][:50]}")
        else:
            print("  'Добавить в сцену' NOT FOUND!")

        print("\n=== Done. Browser stays open 60s ===")
        time.sleep(60)
        ctx.close()
        print("Done.")


if __name__ == "__main__":
    main()
