#!/usr/bin/env python3
"""Explore: Scene Builder part 4 — test Упорядочить and Скачать buttons."""

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
        document.querySelectorAll('button, [role="menuitem"], [role="option"], [role="slider"], [role="dialog"]').forEach(el => {{
            const rect = el.getBoundingClientRect();
            if (rect.width > 3 && rect.y > {y_min} && rect.y < {y_max}) {{
                results.push({{
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    text: (el.textContent || '').trim().substring(0, 100),
                    ariaLabel: el.getAttribute('aria-label') || '',
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
            print(f"    [{el['tag']:<8}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}: {el['text'][:70]}{extra}")


def js_click_by_text(page, tag, text):
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

        # Go to scene builder
        print("\n=== Opening Scene Builder ===")
        js_click_by_text(page, "button", "Конструктор сцен")
        time.sleep(8)  # Wait for scene to load
        screenshot(page, "sb4_01_scene_builder")

        # Check how many clips are in timeline
        timeline_clips = page.evaluate("""() => {
            const results = [];
            // Look for trim handle pairs (each clip has a start + end trim button)
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim();
                if (text.includes('Перетащить для изменения начала') ||
                    text.includes('Перетащить для изменения заключительной')) {
                    const rect = btn.getBoundingClientRect();
                    results.push({
                        text: text.substring(0, 60),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"  Trim handles found: {len(timeline_clips)}")
        for tc in timeline_clips:
            print(f"    ({tc['x']},{tc['y']}) {tc['w']}x{tc['h']}: {tc['text'][:50]}")
        print(f"  Clips in timeline: ~{len(timeline_clips) // 2}")

        # Check duration
        duration = page.evaluate("""() => {
            const els = document.querySelectorAll('*');
            for (const el of els) {
                const text = (el.textContent || '').trim();
                // Match pattern like "0:00 / 0:16" or "0:16"
                if (/\\d+:\\d+\\s*\\/\\s*\\d+:\\d+/.test(text) && text.length < 20) {
                    return text;
                }
            }
            return null;
        }""")
        print(f"  Duration display: {duration}")

        # === Test 1: Click "Упорядочить" (Reorder) ===
        print("\n=== Test 1: Click 'Упорядочить' (Reorder) ===")
        result = js_click_by_text(page, "button", "Упорядочить")
        print(f"  Click result: {result}")
        time.sleep(3)
        screenshot(page, "sb4_02_after_reorder_click")

        # See what changed
        dump_buttons(page, "Elements after 'Упорядочить'")

        # Check for drag handles or reorder controls
        reorder_ui = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const text = (el.textContent || '').trim().toLowerCase();
                const cls = (el.className?.toString() || '').toLowerCase();
                if ((text.includes('перемест') || text.includes('порядок') || text.includes('drag') ||
                     text.includes('reorder') || text.includes('swap') || text.includes('drag_indicator') ||
                     cls.includes('reorder') || cls.includes('drag') || cls.includes('sortable')) &&
                    text.length < 80) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 5 && rect.height > 5) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: text.substring(0, 60),
                            cls: cls.substring(0, 60),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
            });
            // deduplicate
            const seen = new Set();
            return results.filter(r => {
                const key = `${r.tag}-${r.x}-${r.y}`;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
        }""")
        print(f"\n  Reorder-related elements ({len(reorder_ui)}):")
        for r in reorder_ui:
            print(f"    [{r['tag']}] ({r['x']},{r['y']}) {r['w']}x{r['h']}: text={r['text'][:40]} cls={r['cls'][:40]}")

        # Press Escape to dismiss any popup
        page.keyboard.press("Escape")
        time.sleep(2)

        # === Test 2: Click "Скачать" (Download) ===
        print("\n=== Test 2: Click 'Скачать' (Download) in Scene Builder ===")

        # Set up download handler
        download_triggered = []
        page.on("download", lambda d: download_triggered.append(d))

        # Also register DOM mutation observer
        page.evaluate("""() => {
            window.__sb_mutations = [];
            const observer = new MutationObserver((mutations) => {
                for (const m of mutations) {
                    if (m.addedNodes.length > 0) {
                        for (const node of m.addedNodes) {
                            if (node.nodeType === 1) {
                                window.__sb_mutations.push({
                                    type: 'added',
                                    tag: node.tagName?.toLowerCase() || 'text',
                                    text: (node.textContent || '').trim().substring(0, 100),
                                    role: node.getAttribute?.('role') || '',
                                    cls: (node.className?.toString() || '').substring(0, 60),
                                });
                            }
                        }
                    }
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }""")

        # Click the download button specifically in the scene builder toolbar
        result = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = btn.textContent.trim();
                const rect = btn.getBoundingClientRect();
                // The download button near the reorder button (y ~650)
                if (text.includes('Скачать') && rect.y > 600 && rect.y < 700) {
                    btn.click();
                    return { clicked: true, x: Math.round(rect.x), y: Math.round(rect.y) };
                }
            }
            return { clicked: false };
        }""")
        print(f"  Click result: {result}")
        time.sleep(5)
        screenshot(page, "sb4_03_after_download_click")

        # Check mutations
        mutations = page.evaluate("() => window.__sb_mutations || []")
        print(f"\n  DOM mutations ({len(mutations)}):")
        for m in mutations[:15]:
            print(f"    {m['type']} [{m['tag']}] role={m['role']} cls={m['cls'][:30]}: {m['text'][:60]}")

        # Check for dialog/progress
        dialogs = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('[role="dialog"], [role="alertdialog"], [class*="modal"], [class*="progress"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 20) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        role: el.getAttribute('role') || '',
                        text: (el.textContent || '').trim().substring(0, 200),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"\n  Dialogs after download ({len(dialogs)}):")
        for d in dialogs:
            print(f"    [{d['role']}] ({d['x']},{d['y']}) {d['w']}x{d['h']}: {d['text'][:100]}")

        # Check for new buttons (like confirm dialog)
        dump_buttons(page, "Buttons after download click")

        # Check if download was triggered
        print(f"\n  Downloads triggered: {len(download_triggered)}")
        for d in download_triggered:
            print(f"    URL: {d.url[:80]}")
            print(f"    Suggested: {d.suggested_filename}")

        # Wait longer to see if a download starts
        if not download_triggered:
            print("  Waiting 15s more for download...")
            time.sleep(15)
            print(f"  Downloads after wait: {len(download_triggered)}")
            for d in download_triggered:
                print(f"    URL: {d.url[:80]}")
                print(f"    Suggested: {d.suggested_filename}")

        screenshot(page, "sb4_04_final_state")

        # === Test 3: Explore "Добавить клип в конец" button ===
        print("\n=== Test 3: 'Добавить клип в конец' button ===")
        add_end = page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const text = btn.textContent.trim();
                if (text.includes('Добавить клип в конец')) {
                    const rect = btn.getBoundingClientRect();
                    btn.click();
                    return { clicked: true, text: text, x: Math.round(rect.x), y: Math.round(rect.y) };
                }
            }
            return { clicked: false };
        }""")
        print(f"  Click result: {add_end}")
        time.sleep(3)
        screenshot(page, "sb4_05_after_add_clip_end")

        # Check what appeared
        dump_buttons(page, "Elements after 'Добавить клип в конец'")

        # Check if gallery/selection panel appeared
        gallery_in_sb = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('video, img').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 50 && rect.height > 50 && rect.y > 60) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        src: (el.src || '').substring(0, 80),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"\n  Media elements ({len(gallery_in_sb)}):")
        for g in gallery_in_sb:
            print(f"    [{g['tag']}] ({g['x']},{g['y']}) {g['w']}x{g['h']}: {g['src'][:60]}")

        print("\n=== Done. Browser stays open 30s ===")
        time.sleep(30)
        ctx.close()
        print("Done.")


if __name__ == "__main__":
    main()
