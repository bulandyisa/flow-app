#!/usr/bin/env python3
"""Test downloading gallery images by extracting img src URLs."""

import time
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
OUTPUT_DIR = PROJECT_ROOT / "output"
AUTO_PROJECT_URL = "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869"


def main():
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

        # Get full image URLs
        print("\n=== Getting full image URLs ===")
        img_data = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('img').forEach(img => {
                const rect = img.getBoundingClientRect();
                if (rect.width > 100 && rect.y > 100 && rect.y < 800) {
                    results.push({
                        src: img.src,
                        w: img.naturalWidth,
                        h: img.naturalHeight,
                    });
                }
            });
            return results;
        }""")
        for i, img in enumerate(img_data):
            print(f"  Image {i}: {img['w']}x{img['h']}")
            print(f"    URL: {img['src'][:200]}")

        if not img_data:
            print("  No gallery images found!")
            ctx.close()
            return

        # Test 1: Download via fetch in page context
        print("\n=== Test 1: Download via page fetch ===")
        test_url = img_data[-1]['src']  # last image
        save_path = OUTPUT_DIR / "test_frame_download.png"

        result = page.evaluate("""async (url) => {
            try {
                const resp = await fetch(url);
                if (!resp.ok) return {error: `HTTP ${resp.status}`};
                const blob = await resp.blob();
                return {
                    type: blob.type,
                    size: blob.size,
                    // Convert to base64
                    data: await new Promise((resolve) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result.split(',')[1]);
                        reader.readAsDataURL(blob);
                    })
                };
            } catch (e) {
                return {error: e.message};
            }
        }""", test_url)

        if 'error' in result:
            print(f"  Fetch error: {result['error']}")
        else:
            print(f"  Fetched: type={result['type']} size={result['size']}")
            # Save the image
            img_bytes = base64.b64decode(result['data'])
            save_path.write_bytes(img_bytes)
            print(f"  Saved: {save_path} ({len(img_bytes)} bytes)")

        # Test 2: Try the actual download button behavior
        print("\n=== Test 2: Observe download button behavior ===")
        # Let's click download and watch for any new tabs, blobs, etc.
        dl_btn = page.query_selector_all('button:has-text("download")')
        if dl_btn:
            last_dl = dl_btn[-1]
            # Listen for all page events
            page.on("popup", lambda popup: print(f"  POPUP: {popup.url}"))

            print("  Clicking download button...")
            last_dl.click()
            time.sleep(5)

            # Check pages
            pages = ctx.pages
            print(f"  Pages after click: {len(pages)}")
            for p in pages:
                print(f"    {p.url[:100]}")

        print("\n=== Done ===")
        time.sleep(5)
        ctx.close()


if __name__ == "__main__":
    main()
