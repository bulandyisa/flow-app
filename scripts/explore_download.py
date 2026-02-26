#!/usr/bin/env python3
"""Explore the download mechanism for generated images in Flow."""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
EXPLORE_DIR = PROJECT_ROOT / "output" / "explore"
AUTO_PROJECT_URL = "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869"


def main():
    EXPLORE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            args=["--disable-blink-features=AutomationControlled"],
            accept_downloads=True,
        )
        page = ctx.new_page()

        print("Opening project...")
        page.goto(AUTO_PROJECT_URL, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_selector("textarea", timeout=60000)
        time.sleep(5)

        # Switch to Images tab
        img_tab = page.query_selector('button[role="radio"]:has-text("Изображения")')
        if img_tab:
            img_tab.click()
            time.sleep(2)

        # Find all gallery items
        print("\n=== Gallery item analysis ===")
        gallery_items = page.evaluate("""() => {
            const results = [];
            // Look for download buttons and their context
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim();
                if (text.includes('download') || text.includes('wrap_text') ||
                    text.includes('prompt_suggestion') || text.includes('more_vert') ||
                    text.includes('favorite') || text.includes('share')) {
                    const rect = btn.getBoundingClientRect();
                    if (rect.width > 0 && rect.y > 100 && rect.y < 700) {
                        results.push({
                            text: text.substring(0, 80),
                            ariaLabel: btn.getAttribute('aria-label') || '',
                            title: btn.getAttribute('title') || '',
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                }
            });
            return results;
        }""")
        print(f"  Gallery action buttons ({len(gallery_items)}):")
        for el in gallery_items:
            extra = f" title='{el['title']}'" if el['title'] else ""
            extra += f" aria='{el['ariaLabel']}'" if el['ariaLabel'] else ""
            print(f"    ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}: {el['text'][:60]}{extra}")

        # Look for images (src URLs)
        print("\n=== Image elements ===")
        images = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('img').forEach(img => {
                const rect = img.getBoundingClientRect();
                if (rect.width > 100 && rect.y > 100 && rect.y < 700) {
                    results.push({
                        src: img.src.substring(0, 200),
                        alt: img.alt,
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"  Large images ({len(images)}):")
        for img in images:
            print(f"    ({img['x']},{img['y']}) {img['w']}x{img['h']}: {img['src'][:120]}")

        # Try clicking on the first image to see if a detail view opens
        print("\n=== Try clicking first image ===")
        first_img = page.query_selector_all('img')
        clickable_img = None
        for img in first_img:
            box = img.bounding_box()
            if box and box['width'] > 100 and box['y'] > 100 and box['y'] < 700:
                clickable_img = img
                break

        if clickable_img:
            box = clickable_img.bounding_box()
            print(f"  Clicking image at ({box['x']:.0f}, {box['y']:.0f})...")
            clickable_img.click()
            time.sleep(3)
            screenshot_path = EXPLORE_DIR / "60_image_detail.png"
            page.screenshot(path=str(screenshot_path))
            print(f"  Screenshot: {screenshot_path}")

            # Check for detail view elements
            detail_btns = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('button, a[download], a[href]').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    const text = (el.textContent || '').trim();
                    if (rect.width > 0 && (
                        text.includes('download') || text.includes('Скачать') ||
                        text.includes('share') || text.includes('favorite') ||
                        text.includes('close') || text.includes('Загруз') ||
                        el.hasAttribute('download'))) {
                        results.push({
                            tag: el.tagName.toLowerCase(),
                            text: text.substring(0, 80),
                            href: el.getAttribute('href') || '',
                            download: el.getAttribute('download') || '',
                            ariaLabel: el.getAttribute('aria-label') || '',
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                });
                return results;
            }""")
            print(f"  Detail view buttons ({len(detail_btns)}):")
            for el in detail_btns:
                extra = f" href={el['href'][:80]}" if el['href'] else ""
                extra += f" download={el['download']}" if el['download'] else ""
                print(f"    [{el['tag']}] ({el['x']},{el['y']}) {el['w']}x{el['h']}: {el['text'][:60]}{extra}")

            # Try clicking download button in detail view
            print("\n=== Try download in detail view ===")
            dl_btn = None
            for btn_data in detail_btns:
                if 'download' in btn_data['text'].lower() or 'скачать' in btn_data['text'].lower():
                    dl_btn = btn_data
                    break

            if dl_btn:
                print(f"  Found download button: {dl_btn['text'][:40]}")
                # Use page.click with coordinates
                x = dl_btn['x'] + dl_btn['w'] // 2
                y = dl_btn['y'] + dl_btn['h'] // 2

                try:
                    with page.expect_download(timeout=10000) as dl_info:
                        page.mouse.click(x, y)
                    download = dl_info.value
                    save_path = EXPLORE_DIR / f"test_download.{download.suggested_filename.split('.')[-1]}"
                    download.save_as(str(save_path))
                    print(f"  Downloaded: {save_path}")
                except Exception as e:
                    print(f"  Download via click failed: {e}")

                    # Try alternative: click and see if it opens a new tab or blob URL
                    page.mouse.click(x, y)
                    time.sleep(3)
                    screenshot_path2 = EXPLORE_DIR / "61_after_download_click.png"
                    page.screenshot(path=str(screenshot_path2))
                    print(f"  Screenshot: {screenshot_path2}")

                    # Check for new pages/tabs
                    all_pages = ctx.pages
                    print(f"  Open pages: {len(all_pages)}")
                    for p in all_pages:
                        print(f"    URL: {p.url[:100]}")

            # Try the "more_vert" (three dots) menu
            page.keyboard.press("Escape")
            time.sleep(1)

        # === Try "more_vert" menu approach ===
        print("\n=== Try 'more_vert' (three dots) menu ===")
        more_btns = page.query_selector_all('button:has-text("more_vert")')
        gallery_more = [b for b in more_btns if (b.bounding_box() or {}).get('y', 0) > 100]
        if gallery_more:
            btn = gallery_more[0]
            box = btn.bounding_box()
            print(f"  Clicking more_vert at ({box['x']:.0f}, {box['y']:.0f})...")
            btn.click()
            time.sleep(2)
            screenshot_path = EXPLORE_DIR / "62_more_menu.png"
            page.screenshot(path=str(screenshot_path))
            print(f"  Screenshot: {screenshot_path}")

            # Dump menu items
            menu_items = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('[role="menuitem"], [role="option"], .menu-item, li').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            text: (el.textContent || '').trim().substring(0, 100),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                        });
                    }
                });
                return results;
            }""")
            print(f"  Menu items ({len(menu_items)}):")
            for item in menu_items:
                print(f"    ({item['x']},{item['y']}): {item['text'][:60]}")

            page.keyboard.press("Escape")
            time.sleep(1)

        # === Try getting image URL directly ===
        print("\n=== Try extracting image URL directly ===")
        img_urls = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('img').forEach(img => {
                const rect = img.getBoundingClientRect();
                if (rect.width > 100 && rect.y > 100) {
                    results.push({
                        src: img.src,
                        naturalWidth: img.naturalWidth,
                        naturalHeight: img.naturalHeight,
                    });
                }
            });
            return results;
        }""")
        print(f"  Gallery images ({len(img_urls)}):")
        for img in img_urls:
            print(f"    {img['naturalWidth']}x{img['naturalHeight']}: {img['src'][:120]}")

        print("\n=== Browser open 20s ===")
        time.sleep(20)
        ctx.close()
        print("Done.")


if __name__ == "__main__":
    main()
