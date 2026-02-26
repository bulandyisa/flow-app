#!/usr/bin/env python3
"""Deep exploration of image mode ingredient upload — try everything."""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
EXPLORE_DIR = PROJECT_ROOT / "output" / "explore"
REFS_DIR = PROJECT_ROOT / "refs"

AUTO_PROJECT_URL = "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869"

TEST_IMAGE = REFS_DIR / "персонажи" / "char_karim_full.jpeg"


def screenshot(page, name):
    path = EXPLORE_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  Screenshot (full_page): {path}")


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
        time.sleep(8)

        # Ensure image mode
        combo = page.query_selector('button[role="combobox"]')
        if combo:
            t = combo.text_content() or ""
            if "Создать изображение" not in t:
                combo.click()
                time.sleep(1)
                opt = page.query_selector('div[role="option"]:has-text("Создать изображение")')
                if opt:
                    opt.click()
                    time.sleep(2)

        # === TEST 1: Click "+" and look for ANY new DOM elements ===
        print("\n=== TEST 1: Click + and check full DOM ===")

        # Snapshot before
        before_count = page.evaluate("() => document.querySelectorAll('*').length")
        print(f"  DOM elements before click: {before_count}")

        # Click add
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                if (btn.textContent.trim() === 'add' && rect.y > 700) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }""")
        time.sleep(3)

        after_count = page.evaluate("() => document.querySelectorAll('*').length")
        print(f"  DOM elements after click: {after_count} (diff: {after_count - before_count})")

        screenshot(page, "50_image_add_fullpage")

        # Look for HIDDEN elements with upload text
        hidden_upload = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const text = (el.textContent || '').trim().toLowerCase();
                if (text.includes('загруз') || text.includes('upload')) {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        text: text.substring(0, 100),
                        visible: rect.width > 0 && rect.height > 0,
                        display: style.display,
                        visibility: style.visibility,
                        opacity: style.opacity,
                        overflow: style.overflow,
                        x: Math.round(rect.x), y: Math.round(rect.y),
                        w: Math.round(rect.width), h: Math.round(rect.height),
                    });
                }
            });
            return results;
        }""")
        print(f"\n  Hidden/visible upload elements: {len(hidden_upload)}")
        for el in hidden_upload:
            if el['tag'] not in ['html', 'body']:
                print(f"    [{el['tag']}] vis={el['visible']} display={el['display']} opacity={el['opacity']} ({el['x']},{el['y']}) {el['w']}x{el['h']}")

        # Check for file inputs (including hidden ones)
        file_inputs_info = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('input').forEach(el => {
                results.push({
                    type: el.type,
                    accept: el.accept,
                    hidden: el.hidden,
                    display: window.getComputedStyle(el).display,
                    name: el.name,
                    id: el.id,
                });
            });
            return results;
        }""")
        print(f"\n  All input elements:")
        for fi in file_inputs_info:
            print(f"    type={fi['type']} accept={fi['accept']} hidden={fi['hidden']} display={fi['display']}")

        # === TEST 2: Check if the ingredient panel scrolled below viewport ===
        print("\n=== TEST 2: Check for elements below viewport ===")
        below_viewport = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('button, div[role], input').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.y > 900 && rect.width > 0) {
                    results.push({
                        tag: el.tagName.toLowerCase(),
                        text: (el.textContent || '').trim().substring(0, 100),
                        role: el.getAttribute('role') || '',
                        y: Math.round(rect.y),
                    });
                }
            });
            return results;
        }""")
        print(f"  Elements below viewport: {len(below_viewport)}")
        for el in below_viewport:
            print(f"    [{el['tag']}] y={el['y']}: {el['text'][:60]}")

        # Close the ingredient toggle
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                if (btn.textContent.trim() === 'close' && rect.y > 700) {
                    btn.click();
                    return true;
                }
            }
            // Try clicking the same area in case icon changed
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                const t = btn.textContent.trim();
                if ((t === 'add' || t === 'close') && rect.y > 700 && rect.x < 500) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }""")
        time.sleep(1)

        # === TEST 3: Try the file chooser approach ===
        print("\n=== TEST 3: Try expect_file_chooser with '+' click ===")
        try:
            with page.expect_file_chooser(timeout=5000) as fc_info:
                page.evaluate("""() => {
                    const btns = document.querySelectorAll('button');
                    for (const btn of btns) {
                        const rect = btn.getBoundingClientRect();
                        if (btn.textContent.trim() === 'add' && rect.y > 700) {
                            btn.click();
                            return true;
                        }
                    }
                }""")
            file_chooser = fc_info.value
            print(f"  FILE CHOOSER OPENED! multiple={file_chooser.is_multiple}")
            # Upload a test file
            file_chooser.set_files(str(TEST_IMAGE))
            time.sleep(3)
            screenshot(page, "51_after_file_upload")
            print("  File uploaded successfully!")
        except Exception as e:
            print(f"  No file chooser from '+' click: {e}")

        # === TEST 4: Try scrolling down to see if there's an ingredient area below ===
        print("\n=== TEST 4: Scroll down and check ===")
        page.evaluate("window.scrollTo(0, 500)")
        time.sleep(2)
        screenshot(page, "52_scrolled_down")

        # Check current scroll state
        scroll_info = page.evaluate("""() => ({
            scrollY: window.scrollY,
            scrollHeight: document.documentElement.scrollHeight,
            clientHeight: document.documentElement.clientHeight,
        })""")
        print(f"  Scroll: y={scroll_info['scrollY']}, height={scroll_info['scrollHeight']}, client={scroll_info['clientHeight']}")

        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(1)

        # === TEST 5: Try clicking the "+" and then looking at the prompt area ===
        # Maybe "+" toggles inline ingredient chips in the textarea area
        print("\n=== TEST 5: Click + then check textarea area ===")
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                if (btn.textContent.trim() === 'add' && rect.y > 700) {
                    btn.click();
                    return;
                }
            }
        }""")
        time.sleep(2)

        # Check elements between y=700 and y=900 (prompt bar area) in detail
        prompt_area = page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('*').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.y >= 700 && rect.y <= 900 && rect.width > 10 && rect.height > 10) {
                    const tag = el.tagName.toLowerCase();
                    if (['button', 'div', 'input', 'textarea', 'span', 'label', 'a', 'img'].includes(tag)) {
                        const text = (el.textContent || '').trim().substring(0, 80);
                        if (text || tag === 'input' || tag === 'img') {
                            results.push({
                                tag, text,
                                role: el.getAttribute('role') || '',
                                ariaLabel: el.getAttribute('aria-label') || '',
                                x: Math.round(rect.x), y: Math.round(rect.y),
                                w: Math.round(rect.width), h: Math.round(rect.height),
                            });
                        }
                    }
                }
            });
            return results;
        }""")
        print(f"  Prompt area (y 700-900) elements: {len(prompt_area)}")
        seen = set()
        for el in prompt_area:
            key = f"{el['tag']}-{el['x']}-{el['y']}-{el['w']}-{el['text'][:30]}"
            if key not in seen:
                seen.add(key)
                print(f"    [{el['tag']:<8}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}: {el['text'][:60]}")

        # === TEST 6: Try clicking the textarea first, THEN clicking + ===
        print("\n=== TEST 6: Click textarea, type, then click + ===")
        page.evaluate("""() => {
            const btns = document.querySelectorAll('button');
            for (const btn of btns) {
                const rect = btn.getBoundingClientRect();
                const t = btn.textContent.trim();
                if ((t === 'add' || t === 'close') && rect.y > 700 && rect.x < 500) {
                    btn.click();  // close if open
                    return;
                }
            }
        }""")
        time.sleep(1)

        textarea = page.query_selector('textarea')
        if textarea:
            textarea.click()
            textarea.fill("test prompt with ingredients")
            time.sleep(1)

            # Now click +
            page.evaluate("""() => {
                const btns = document.querySelectorAll('button');
                for (const btn of btns) {
                    const rect = btn.getBoundingClientRect();
                    if (btn.textContent.trim() === 'add' && rect.y > 700) {
                        btn.click();
                        return;
                    }
                }
            }""")
            time.sleep(3)
            screenshot(page, "53_prompt_then_add")

            # Check if anything new appeared
            new_visible = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('*').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && rect.y > 400 && rect.y < 750) {
                        const tag = el.tagName.toLowerCase();
                        const text = (el.textContent || '').trim();
                        if (text && ['button', 'div', 'a', 'span'].includes(tag) && text.length < 50) {
                            results.push({
                                tag, text,
                                x: Math.round(rect.x), y: Math.round(rect.y),
                                w: Math.round(rect.width), h: Math.round(rect.height),
                            });
                        }
                    }
                });
                return results;
            }""")
            print(f"  Elements in y 400-750 after prompt+add:")
            for el in new_visible:
                print(f"    [{el['tag']}] ({el['x']},{el['y']}) {el['w']}x{el['h']}: {el['text']}")

            textarea.fill("")

        print("\n=== Done. Browser open 20s ===")
        time.sleep(20)
        ctx.close()
        print("Done.")


if __name__ == "__main__":
    main()
