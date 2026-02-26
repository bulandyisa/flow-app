#!/usr/bin/env python3
"""Debug: Understand gallery item counting and generation detection."""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
EXPLORE_DIR = PROJECT_ROOT / "output" / "explore"
AUTO_PROJECT_URL = "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869"


def screenshot(page, name):
    path = EXPLORE_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  Screenshot: {path.name}")


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
        page.goto(AUTO_PROJECT_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_selector("textarea", timeout=60000)
        time.sleep(8)

        # === Analyze download buttons ===
        print("\n=== Download button analysis ===")
        dl_buttons = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim();
                if (text.includes('download') || text.includes('Скачать')) {
                    const rect = btn.getBoundingClientRect();
                    results.push({
                        text: text.substring(0, 80),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                        visible: rect.width > 0 && rect.height > 0,
                        ariaLabel: btn.getAttribute('aria-label') || '',
                    });
                }
            });
            return results;
        }""")
        print(f"  Total 'download' buttons: {len(dl_buttons)}")
        for btn in dl_buttons:
            vis = "VIS" if btn['visible'] else "HID"
            print(f"    [{vis}] ({btn['x']:4},{btn['y']:4}) {btn['w']:3}x{btn['h']:3}: {btn['text'][:60]}")

        # === Analyze by tab ===
        print("\n=== Tab analysis ===")
        tabs = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button[role="radio"]').forEach(btn => {
                results.push({
                    text: btn.textContent.trim(),
                    selected: btn.getAttribute('aria-selected') || '',
                    x: Math.round(btn.getBoundingClientRect().x),
                    y: Math.round(btn.getBoundingClientRect().y),
                });
            });
            return results;
        }""")
        for tab in tabs:
            print(f"  Tab: '{tab['text']}' selected={tab['selected']} ({tab['x']},{tab['y']})")

        # === Switch to Images tab and count ===
        print("\n=== Images tab ===")
        img_tab = page.query_selector('button[role="radio"]:has-text("Изображения")')
        if img_tab:
            img_tab.click()
            time.sleep(2)

        dl_after_img = page.query_selector_all('button:has-text("download")')
        print(f"  Download buttons on Images tab: {len(dl_after_img)}")

        # Count <img> elements in gallery
        img_elements = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('img').forEach(img => {
                const rect = img.getBoundingClientRect();
                if (rect.width > 80 && rect.y > 50 && rect.y < 750) {
                    results.push({
                        src: img.src.substring(0, 100),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"  Gallery images: {len(img_elements)}")
        for img in img_elements:
            print(f"    ({img['x']:4},{img['y']:4}) {img['w']:3}x{img['h']:3}: {img['src'][:80]}")

        # === Switch to Videos tab and count ===
        print("\n=== Videos tab ===")
        vid_tab = page.query_selector('button[role="radio"]:has-text("Видео")')
        if vid_tab:
            vid_tab.click()
            time.sleep(2)

        dl_after_vid = page.query_selector_all('button:has-text("download")')
        print(f"  Download buttons on Videos tab: {len(dl_after_vid)}")

        vid_elements = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('video').forEach(vid => {
                const rect = vid.getBoundingClientRect();
                if (rect.width > 80 && rect.y > 50 && rect.y < 750) {
                    results.push({
                        src: vid.src ? vid.src.substring(0, 100) : 'no src',
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"  Gallery videos: {len(vid_elements)}")
        for vid in vid_elements:
            print(f"    ({vid['x']:4},{vid['y']:4}) {vid['w']:3}x{vid['h']:3}: {vid['src'][:80]}")

        # === Check for loading spinner ===
        print("\n=== Loading indicators ===")
        spinners = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('[role="progressbar"], .spinner, [class*="loading"], [class*="progress"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                results.push({
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    class: el.className.toString().substring(0, 80),
                    visible: rect.width > 0 && rect.height > 0,
                    x: Math.round(rect.x), y: Math.round(rect.y),
                });
            });
            return results;
        }""")
        print(f"  Spinner/progress elements: {len(spinners)}")
        for s in spinners:
            print(f"    [{s['tag']}] role={s['role']} vis={s['visible']} class={s['class'][:60]}")

        # === Alternative: Check gallery group structure ===
        print("\n=== Gallery structure ===")
        gallery_groups = page.evaluate("""() => {
            const results = [];
            // Look for prompt-labeled groups in gallery
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim();
                const rect = btn.getBoundingClientRect();
                if (text.includes('prompt_suggestion') && rect.y > 100 && rect.y < 800) {
                    results.push({
                        text: text.substring(0, 120),
                        x: Math.round(rect.x), y: Math.round(rect.y),
                    });
                }
            });
            return results;
        }""")
        print(f"  Gallery groups (prompt_suggestion): {len(gallery_groups)}")
        for g in gallery_groups:
            print(f"    ({g['x']},{g['y']}): {g['text'][:80]}")

        # === Check for generation status elements ===
        print("\n=== Generation status ===")
        status_els = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const text = (el.textContent || '').trim();
                if ((text.includes('Генерация') || text.includes('Создание') || text.includes('Ожидание')) &&
                    text.length < 100) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
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
        print(f"  Status elements: {len(status_els)}")
        for s in status_els:
            print(f"    [{s['tag']}] ({s['x']},{s['y']}): {s['text'][:80]}")

        screenshot(page, "debug_gallery_count")

        print("\n=== Done ===")
        time.sleep(10)
        ctx.close()


if __name__ == "__main__":
    main()
