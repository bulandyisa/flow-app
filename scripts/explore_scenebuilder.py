#!/usr/bin/env python3
"""Explore: Scene Builder UI in Google Flow.

Opens the Flow project, navigates to Scene Builder, and dumps all
interactive elements, buttons, and structure to understand the UI
for automation.
"""

import time
import json
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
    """Dump all buttons in given Y range."""
    elements = page.evaluate(f"""() => {{
        const results = [];
        document.querySelectorAll('button, a, [role="tab"], [role="radio"], [role="menuitem"]').forEach(el => {{
            const rect = el.getBoundingClientRect();
            if (rect.width > 5 && rect.y > {y_min} && rect.y < {y_max}) {{
                results.push({{
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    text: (el.textContent || '').trim().substring(0, 120),
                    ariaLabel: el.getAttribute('aria-label') || '',
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                }});
            }}
        }});
        return results;
    }}""")
    seen = set()
    print(f"\n  {label} ({len(elements)} elements):")
    for el in elements:
        key = f"{el['tag']}-{el['x']}-{el['y']}"
        if key not in seen:
            seen.add(key)
            extra = f" role={el['role']}" if el['role'] else ""
            extra += f" aria='{el['ariaLabel']}'" if el['ariaLabel'] else ""
            print(f"    [{el['tag']:<8}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}: {el['text'][:70]}{extra}")


def dump_all_text(page, label, y_min=0, y_max=2000):
    """Dump all visible text elements."""
    elements = page.evaluate(f"""() => {{
        const results = [];
        const tags = ['h1','h2','h3','h4','h5','p','span','div','label'];
        tags.forEach(tag => {{
            document.querySelectorAll(tag).forEach(el => {{
                const rect = el.getBoundingClientRect();
                const text = (el.textContent || '').trim();
                if (rect.width > 10 && rect.y > {y_min} && rect.y < {y_max} &&
                    text.length > 2 && text.length < 150 &&
                    el.children.length === 0) {{
                    results.push({{
                        tag: tag,
                        text: text,
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    }});
                }}
            }});
        }});
        return results.sort((a, b) => a.y - b.y || a.x - b.x);
    }}""")
    print(f"\n  {label} ({len(elements)} text elements):")
    for el in elements:
        print(f"    [{el['tag']:<5}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}: {el['text'][:80]}")


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

        # === Step 1: Look for Scene Builder entry point ===
        print("\n=== Step 1: Looking for Scene Builder entry point ===")
        screenshot(page, "sb_01_main_view")
        dump_buttons(page, "All buttons on main page")

        # Look for anything with "scene" or "сцен" or "builder" or "timeline"
        sb_matches = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const text = (el.textContent || '').toLowerCase().trim();
                const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                if ((text.includes('scene') || text.includes('сцен') ||
                     text.includes('timeline') || text.includes('builder') ||
                     text.includes('монтаж') || text.includes('таймлайн') ||
                     aria.includes('scene') || aria.includes('timeline')) &&
                    text.length < 100) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: text.substring(0, 80),
                            aria: aria.substring(0, 80),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                            clickable: el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button',
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"\n  Scene-related elements ({len(sb_matches)}):")
        for m in sb_matches:
            click_tag = " [CLICKABLE]" if m['clickable'] else ""
            print(f"    [{m['tag']}] ({m['x']},{m['y']}) {m['w']}x{m['h']}: {m['text'][:60]}{click_tag}")

        # === Step 2: Look for navigation/sidebar ===
        print("\n=== Step 2: Looking for sidebar/navigation ===")
        # Check left side for nav items
        dump_buttons(page, "Left sidebar buttons (x < 200)", y_min=0, y_max=900)

        # Check for tabs at top
        tabs = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('[role="tab"], [role="tablist"], nav a, nav button').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        text: (el.textContent || '').trim().substring(0, 80),
                        role: el.getAttribute('role') || '',
                        x: Math.round(rect.x), y: Math.round(rect.y),
                    });
                }
            });
            return results;
        }""")
        print(f"\n  Tab/nav elements ({len(tabs)}):")
        for t in tabs:
            print(f"    [{t['tag']}] ({t['x']},{t['y']}): {t['text']} role={t['role']}")

        # === Step 3: Check the gallery for videos that can be added to Scene Builder ===
        print("\n=== Step 3: Check gallery videos ===")
        # Switch to video tab
        vid_tab = page.query_selector('button[role="radio"]:has-text("Видео")')
        if vid_tab:
            vid_tab.click()
            time.sleep(2)

        # Look for context menus or "add to scene" buttons on video items
        vid_buttons = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button').forEach(btn => {
                const rect = btn.getBoundingClientRect();
                const text = btn.textContent.trim();
                // Look at gallery area (y between 100 and 700)
                if (rect.y > 100 && rect.y < 700 && rect.width > 0) {
                    results.push({
                        text: text.substring(0, 80),
                        ariaLabel: btn.getAttribute('aria-label') || '',
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"\n  Gallery area buttons ({len(vid_buttons)}):")
        for b in vid_buttons:
            aria = f" aria='{b['ariaLabel']}'" if b['ariaLabel'] else ""
            print(f"    ({b['x']:4},{b['y']:4}) {b['w']:3}x{b['h']:3}: {b['text'][:60]}{aria}")

        screenshot(page, "sb_02_video_gallery")

        # === Step 4: Try clicking on a video to see its options ===
        print("\n=== Step 4: Click on a video to see its options ===")
        # Find the first video element
        first_video = page.query_selector('video')
        if first_video:
            box = first_video.bounding_box()
            if box:
                print(f"  Found video at ({box['x']:.0f}, {box['y']:.0f})")
                first_video.click()
                time.sleep(2)
                screenshot(page, "sb_03_video_clicked")
                dump_buttons(page, "Buttons after clicking video")

                # Check for popover/menu
                menus = page.evaluate("""() => {
                    const results = [];
                    document.querySelectorAll('[role="menu"], [role="dialog"], [role="tooltip"], [class*="popover"], [class*="menu"]').forEach(el => {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0) {
                            results.push({
                                role: el.getAttribute('role') || '',
                                text: (el.textContent || '').trim().substring(0, 200),
                                x: Math.round(rect.x), y: Math.round(rect.y),
                                w: Math.round(rect.width), h: Math.round(rect.height),
                            });
                        }
                    });
                    return results;
                }""")
                print(f"\n  Menus/dialogs after click ({len(menus)}):")
                for m in menus:
                    print(f"    [{m['role']}] ({m['x']},{m['y']}) {m['w']}x{m['h']}: {m['text'][:100]}")

        # === Step 5: Look for "more" / three-dot menu on video items ===
        print("\n=== Step 5: Look for more_vert / three-dot menus ===")
        more_btns = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim();
                if (text === 'more_vert' || text === 'more_horiz' || text === '⋮' ||
                    text.includes('menu') || (btn.getAttribute('aria-label') || '').includes('More')) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            text: text.substring(0, 40),
                            ariaLabel: btn.getAttribute('aria-label') || '',
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"  'More' buttons ({len(more_btns)}):")
        for b in more_btns:
            aria = f" aria='{b['ariaLabel']}'" if b['ariaLabel'] else ""
            print(f"    ({b['x']:4},{b['y']:4}) {b['w']:3}x{b['h']:3}: {b['text'][:40]}{aria}")

        # Click first more_vert if found
        if more_btns:
            first_more = more_btns[0]
            print(f"\n  Clicking first 'more' button at ({first_more['x']}, {first_more['y']})...")
            page.click(f"text=more_vert >> nth=0", timeout=5000)
            time.sleep(2)
            screenshot(page, "sb_04_more_menu")
            dump_buttons(page, "Buttons after clicking 'more'")

            # Check for menu items
            menu_items = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('[role="menuitem"], [role="option"]').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            text: (el.textContent || '').trim().substring(0, 80),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                        });
                    }
                });
                return results;
            }""")
            print(f"\n  Menu items ({len(menu_items)}):")
            for mi in menu_items:
                print(f"    ({mi['x']},{mi['y']}): {mi['text']}")

            page.keyboard.press("Escape")
            time.sleep(1)

        # === Step 6: Look for Scene Builder in the bottom bar or toolbar ===
        print("\n=== Step 6: Looking for Scene Builder in toolbar/bottom ===")
        # Check very bottom of page
        dump_buttons(page, "Bottom area buttons (y > 800)")

        # Check for any icon that might be scene builder
        icon_btns = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim();
                if (text === 'movie' || text === 'video_library' || text === 'playlist_play' ||
                    text === 'view_timeline' || text === 'edit' || text === 'movie_creation' ||
                    text === 'theaters' || text === 'videocam' || text === 'stacks') {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            text: text,
                            ariaLabel: btn.getAttribute('aria-label') || '',
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"\n  Media icon buttons ({len(icon_btns)}):")
        for b in icon_btns:
            aria = f" aria='{b['ariaLabel']}'" if b['ariaLabel'] else ""
            print(f"    ({b['x']:4},{b['y']:4}) {b['w']:3}x{b['h']:3}: {b['text']}{aria}")

        # === Step 7: Try navigating to Scene Builder URL directly ===
        print("\n=== Step 7: Try Scene Builder URL patterns ===")
        sb_urls = [
            FLOW_PROJECT_URL + "/scene-builder",
            FLOW_PROJECT_URL + "/scenebuilder",
            FLOW_PROJECT_URL + "/timeline",
            "https://labs.google/fx/ru/tools/flow/scene-builder",
        ]
        for url in sb_urls:
            print(f"\n  Trying: {url}")
            try:
                page.goto(url, timeout=15000, wait_until="domcontentloaded")
                time.sleep(3)
                current = page.url
                print(f"  Landed on: {current}")
                if current != url:
                    print(f"  (Redirected)")
                # Check if anything scene-builder-like loaded
                has_timeline = page.query_selector('[class*="timeline"]') is not None
                has_tracks = page.query_selector('[class*="track"]') is not None
                print(f"  Timeline elements: {has_timeline}, Track elements: {has_tracks}")
                screenshot(page, f"sb_url_test_{sb_urls.index(url)}")
            except Exception as e:
                print(f"  Error: {e}")

        # Go back to project
        print("\n  Returning to project...")
        page.goto(FLOW_PROJECT_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_selector("textarea", timeout=60000)
        time.sleep(5)

        # === Step 8: Full dump of all unique button texts ===
        print("\n=== Step 8: All unique button texts on page ===")
        all_btn_texts = page.evaluate("""() => {
            const texts = new Set();
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim().substring(0, 60);
                const rect = btn.getBoundingClientRect();
                if (rect.width > 0 && text.length > 0) {
                    texts.add(text);
                }
            });
            return [...texts].sort();
        }""")
        print(f"  Unique button texts ({len(all_btn_texts)}):")
        for t in all_btn_texts:
            print(f"    '{t}'")

        # === Step 9: Check for links ===
        print("\n=== Step 9: All links on page ===")
        all_links = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('a').forEach(a => {
                const rect = a.getBoundingClientRect();
                if (rect.width > 0) {
                    results.push({
                        text: (a.textContent || '').trim().substring(0, 80),
                        href: a.href || '',
                        x: Math.round(rect.x), y: Math.round(rect.y),
                    });
                }
            });
            return results;
        }""")
        print(f"  Links ({len(all_links)}):")
        for l in all_links:
            print(f"    ({l['x']},{l['y']}): {l['text'][:40]} → {l['href'][:80]}")

        print("\n=== Done. Browser stays open 60s for manual inspection ===")
        screenshot(page, "sb_final")
        time.sleep(60)
        ctx.close()
        print("Done.")


if __name__ == "__main__":
    main()
