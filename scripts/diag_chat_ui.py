#!/usr/bin/env python3
"""Diagnostic: explore new chat-based UI structure of Google Flow.

Goals:
1. Understand how the chat UI works (messages, results, etc.)
2. Find where generated images appear (img, canvas, background-image?)
3. Test if generation actually triggers
4. Check for spinner / loading indicators
"""

import sys, time, json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / '.session'
FLOW_PROJECT_URL = 'https://labs.google/fx/ru/tools/flow/project/38f939b2-1f84-4503-8a12-09fc19e4c4a4'
SCREENSHOT_DIR = PROJECT_ROOT / 'output' / 'screenshots'
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def dump_chat_structure(page, label=""):
    """Dump structural elements of the chat UI."""
    result = page.evaluate("""() => {
        const data = {elements: [], chat_messages: [], images_all: [], buttons: []};

        // Find all significant elements
        document.querySelectorAll('img').forEach((el, i) => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 0) {
                data.images_all.push({
                    i: i,
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                    src: (el.src || '').substring(0, 100),
                    alt: (el.alt || '').substring(0, 60),
                    parent_class: (el.parentElement?.className || '').substring(0, 60),
                    parent_tag: el.parentElement?.tagName
                });
            }
        });

        // Find chat message containers
        document.querySelectorAll('[class*="message"], [class*="Message"], [class*="chat"], [class*="Chat"], [role="listitem"], [role="article"]').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 100 && rect.height > 20) {
                data.chat_messages.push({
                    tag: el.tagName,
                    class: (el.className || '').substring(0, 80),
                    role: el.getAttribute('role'),
                    y: Math.round(rect.y),
                    h: Math.round(rect.height),
                    text: (el.textContent || '').substring(0, 100)
                });
            }
        });

        // Find loading/spinner indicators
        document.querySelectorAll('[class*="loading"], [class*="Loading"], [class*="spinner"], [class*="Spinner"], [class*="progress"], [class*="Progress"], [role="progressbar"]').forEach(el => {
            const rect = el.getBoundingClientRect();
            data.elements.push({
                tag: el.tagName, type: 'loading',
                class: (el.className || '').substring(0, 80),
                x: Math.round(rect.x), y: Math.round(rect.y),
                w: Math.round(rect.width), h: Math.round(rect.height),
                visible: rect.width > 0 && rect.height > 0
            });
        });

        // Find grid/gallery containers
        document.querySelectorAll('[class*="grid"], [class*="Grid"], [class*="gallery"], [class*="Gallery"], [class*="result"], [class*="Result"]').forEach(el => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 100) {
                const imgs = el.querySelectorAll('img').length;
                data.elements.push({
                    tag: el.tagName, type: 'grid/gallery',
                    class: (el.className || '').substring(0, 80),
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                    img_count: imgs,
                    text: (el.textContent || '').substring(0, 60)
                });
            }
        });

        // Count scrollable area
        const scrollables = [];
        document.querySelectorAll('*').forEach(el => {
            if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 100) {
                const rect = el.getBoundingClientRect();
                scrollables.push({
                    tag: el.tagName,
                    class: (el.className || '').substring(0, 60),
                    scrollTop: Math.round(el.scrollTop),
                    scrollHeight: Math.round(el.scrollHeight),
                    clientHeight: Math.round(el.clientHeight),
                    x: Math.round(rect.x),
                    w: Math.round(rect.width)
                });
            }
        });
        data.scrollables = scrollables;

        return data;
    }""")

    print(f"\n{'='*60}")
    print(f"  CHAT UI STRUCTURE ({label})")
    print(f"{'='*60}")

    if result.get('chat_messages'):
        print(f"\n  Chat Messages ({len(result['chat_messages'])}):")
        for msg in result['chat_messages'][:10]:
            print(f"    [{msg['tag']}] role={msg.get('role')} y={msg['y']} h={msg['h']}")
            print(f"      class: {msg['class']}")
            print(f"      text: {msg['text'][:80]}")

    if result.get('elements'):
        print(f"\n  Structural Elements ({len(result['elements'])}):")
        for el in result['elements'][:20]:
            vis = "VIS" if el.get('visible', el.get('w', 0) > 0) else "HID"
            print(f"    [{el['tag']}] {vis} type={el['type']} pos=({el['x']},{el['y']}) {el['w']}x{el['h']}")
            print(f"      class: {el['class']}")
            if el.get('img_count'):
                print(f"      imgs: {el['img_count']}")

    if result.get('scrollables'):
        print(f"\n  Scrollable areas ({len(result['scrollables'])}):")
        for sc in result['scrollables']:
            print(f"    [{sc['tag']}] x={sc['x']} w={sc['w']} scroll={sc['scrollTop']}/{sc['scrollHeight']} client={sc['clientHeight']}")
            print(f"      class: {sc['class']}")

    if result.get('images_all'):
        print(f"\n  All Images ({len(result['images_all'])}):")
        for img in result['images_all']:
            print(f"    [{img['i']:2d}] ({img['x']:4d},{img['y']:4d}) {img['w']:4d}x{img['h']:4d} alt='{img['alt']}'")
            print(f"         parent: <{img['parent_tag']}> class={img['parent_class']}")

    return result


def scroll_chat_and_find_images(page):
    """Scroll the chat area to find all images."""
    print("\n=== SCROLLING CHAT TO TOP ===")
    # Find the main scrollable chat area
    scrolled = page.evaluate("""() => {
        const scrollables = [];
        document.querySelectorAll('*').forEach(el => {
            if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                const rect = el.getBoundingClientRect();
                if (rect.x < 400) {  // Left side = chat area
                    scrollables.push(el);
                }
            }
        });
        if (scrollables.length > 0) {
            const chat = scrollables[0];
            chat.scrollTop = 0;
            return {scrolled: true, from: chat.scrollTop, total: chat.scrollHeight};
        }
        return {scrolled: false};
    }""")
    print(f"  Scroll result: {scrolled}")
    time.sleep(1)

    # Count images after scrolling to top
    imgs = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('img').forEach((el, i) => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 100 && rect.height > 100) {
                results.push({
                    i: i,
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                    src: (el.src || '').substring(0, 120),
                    alt: (el.alt || '').substring(0, 60)
                });
            }
        });
        return results;
    }""")
    print(f"\n  Large images (w>100, h>100) after scroll to top: {len(imgs)}")
    for img in imgs:
        print(f"    ({img['x']:4d},{img['y']:4d}) {img['w']}x{img['h']} alt='{img['alt']}' src={img['src'][:80]}")

    # Now scroll to bottom
    print("\n=== SCROLLING CHAT TO BOTTOM ===")
    page.evaluate("""() => {
        const scrollables = [];
        document.querySelectorAll('*').forEach(el => {
            if (el.scrollHeight > el.clientHeight + 50 && el.clientHeight > 200) {
                const rect = el.getBoundingClientRect();
                if (rect.x < 400) {
                    scrollables.push(el);
                }
            }
        });
        if (scrollables.length > 0) {
            scrollables[0].scrollTop = scrollables[0].scrollHeight;
        }
    }""")
    time.sleep(1)

    imgs_bottom = page.evaluate("""() => {
        const results = [];
        document.querySelectorAll('img').forEach((el, i) => {
            const rect = el.getBoundingClientRect();
            if (rect.width > 100 && rect.height > 100) {
                results.push({
                    i: i,
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                    src: (el.src || '').substring(0, 120),
                    alt: (el.alt || '').substring(0, 60)
                });
            }
        });
        return results;
    }""")
    print(f"\n  Large images after scroll to bottom: {len(imgs_bottom)}")
    for img in imgs_bottom:
        print(f"    ({img['x']:4d},{img['y']:4d}) {img['w']}x{img['h']} alt='{img['alt']}' src={img['src'][:80]}")

    page.screenshot(path=str(SCREENSHOT_DIR / 'diag_scrolled_bottom.png'))


def test_generation(page):
    """Actually generate and watch what changes in the DOM."""
    # Clear and type prompt
    field = page.query_selector('[role="textbox"]') or page.query_selector('[contenteditable="true"]')
    if not field:
        print("ERROR: No prompt field found!")
        return

    field.click()
    time.sleep(0.3)
    page.keyboard.press('Meta+a')
    time.sleep(0.2)
    page.keyboard.press('Delete')
    time.sleep(0.3)

    prompt = "A cute cartoon cat sitting on a windowsill, watching a butterfly. 3D Pixar-style animation, warm sunlight, cinematic."
    page.keyboard.type(prompt, delay=15)
    time.sleep(0.5)

    # Take before screenshot
    page.screenshot(path=str(SCREENSHOT_DIR / 'diag2_before_gen.png'))

    # Snapshot ALL img src URLs (regardless of position filter)
    before_urls = set(page.evaluate("""() => {
        return Array.from(document.querySelectorAll('img')).map(el => el.src);
    }"""))
    print(f"\n  Total img URLs before generation: {len(before_urls)}")

    # Count DOM nodes
    before_count = page.evaluate("() => document.querySelectorAll('*').length")
    print(f"  Total DOM nodes before: {before_count}")

    # Click generate
    gen_btn = page.locator('button:has-text("arrow_forward"), button:has-text("Создать"), button:has-text("Генерировать")')
    if gen_btn.count() > 0:
        gen_btn.first.click()
        print("  Clicked generate button!")
    else:
        print("  ERROR: Generate button not found!")
        return

    # Wait and poll
    print("\n=== POLLING FOR CHANGES ===")
    for i in range(60):  # 5 minutes
        time.sleep(5)
        elapsed = (i + 1) * 5

        current_urls = set(page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img')).map(el => el.src);
        }"""))
        current_count = page.evaluate("() => document.querySelectorAll('*').length")

        new_urls = current_urls - before_urls
        dom_diff = current_count - before_count

        # Check for loading indicators
        loading = page.evaluate("""() => {
            const indicators = [];
            document.querySelectorAll('[class*="load"], [class*="Load"], [class*="spin"], [class*="Spin"], [role="progressbar"], [class*="pulsing"], [class*="generating"]').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0) {
                    indicators.push({
                        tag: el.tagName,
                        class: (el.className || '').substring(0, 60),
                        y: Math.round(rect.y)
                    });
                }
            });
            // Also check for animated elements (CSS animations)
            const animated = document.querySelectorAll('[style*="animation"], [class*="animate"]');
            animated.forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0) {
                    indicators.push({tag: el.tagName, class: 'animated: ' + (el.className || '').substring(0, 40), y: Math.round(rect.y)});
                }
            });
            return indicators;
        }""")

        status = f"  [{elapsed:3d}s] imgs: {len(current_urls)} (+{len(new_urls)}) DOM: {current_count} ({dom_diff:+d})"
        if loading:
            status += f" LOADING: {len(loading)}"
        print(status)

        if new_urls:
            print(f"    NEW URLs:")
            for u in list(new_urls)[:5]:
                print(f"      {u[:100]}")

        if loading and elapsed <= 10:
            print(f"    Loading indicators:")
            for l in loading[:5]:
                print(f"      [{l['tag']}] y={l['y']} class={l['class']}")

        # Take screenshots at key moments
        if elapsed in (5, 15, 30, 60, 120, 180):
            page.screenshot(path=str(SCREENSHOT_DIR / f'diag2_gen_{elapsed}s.png'))

        if elapsed >= 10 and dom_diff == 0 and not new_urls and not loading:
            # Check if error appeared
            error = page.evaluate("""() => {
                const body = document.body.textContent || '';
                if (body.includes('Не удалось') || body.includes('ошибка') || body.includes('error'))
                    return true;
                return false;
            }""")
            if elapsed >= 30 and not new_urls:
                print(f"    No changes for {elapsed}s - checking page state...")
                page.screenshot(path=str(SCREENSHOT_DIR / f'diag2_stalled_{elapsed}s.png'))
                if elapsed >= 60:
                    print("    Seems stuck. Stopping poll.")
                    break

    # Final state
    page.screenshot(path=str(SCREENSHOT_DIR / 'diag2_final.png'))
    final_urls = set(page.evaluate("() => Array.from(document.querySelectorAll('img')).map(el => el.src)"))
    all_new = final_urls - before_urls
    print(f"\n  FINAL: {len(all_new)} new image URLs")
    for u in all_new:
        print(f"    {u[:120]}")


def main():
    print("Chat UI diagnostic v2...")

    with sync_playwright() as pw:
        browser = pw.chromium.launch_persistent_context(
            str(SESSION_DIR),
            headless=False,
            viewport={'width': 1440, 'height': 900},
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--disable-background-timer-throttling',
            ]
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        print(f"\nNavigating to: {FLOW_PROJECT_URL}")
        page.goto(FLOW_PROJECT_URL, timeout=30000, wait_until='domcontentloaded')
        time.sleep(5)

        # Dismiss popups
        for _ in range(3):
            for sel in ['button:has-text("Закрыть")', 'button:has-text("Close")', 'button:has-text("OK")', 'button:has-text("Понятно")']:
                try:
                    btn = page.query_selector(sel)
                    if btn:
                        btn.click()
                        time.sleep(0.5)
                except:
                    pass

        # Wait for prompt field
        try:
            page.wait_for_selector('[role="textbox"], [contenteditable="true"]', timeout=15000)
        except:
            print("WARNING: Prompt field not found")

        time.sleep(2)

        # Step 1: Dump chat structure
        dump_chat_structure(page, "INITIAL")

        # Step 2: Scroll and find images
        scroll_chat_and_find_images(page)

        # Step 3: Test actual generation
        test_generation(page)

        time.sleep(2)
        browser.close()
        print("\nDone!")


if __name__ == '__main__':
    main()
