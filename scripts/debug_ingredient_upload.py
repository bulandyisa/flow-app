#!/usr/bin/env python3
"""Debug: What happens when clicking 'Загрузить' in image mode ingredient panel?"""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSION_DIR = PROJECT_ROOT / ".session"
EXPLORE_DIR = PROJECT_ROOT / "output" / "explore"
AUTO_PROJECT_URL = "https://labs.google/fx/ru/tools/flow/project/044de3a8-7fb6-4645-b651-b07efab55869"

TEST_IMAGE = PROJECT_ROOT / "персонажи" / "char_karim_full.jpeg"


def screenshot(page, name):
    path = EXPLORE_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  Screenshot: {path.name}")


def dump_elements_near(page, label, y_min=500, y_max=900):
    """Dump all interactive elements in given Y range."""
    elements = page.evaluate(f"""() => {{
        const results = [];
        document.querySelectorAll('button, input, a, [role="menu"], [role="menuitem"], [role="dialog"], [role="option"]').forEach(el => {{
            const rect = el.getBoundingClientRect();
            if (rect.width > 5 && rect.y > {y_min} && rect.y < {y_max}) {{
                results.push({{
                    tag: el.tagName.toLowerCase(),
                    role: el.getAttribute('role') || '',
                    text: (el.textContent || '').trim().substring(0, 120),
                    type: el.getAttribute('type') || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height),
                }});
            }}
        }});
        return results;
    }}""")
    seen = set()
    print(f"\n  {label} ({len(elements)} elements, y {y_min}-{y_max}):")
    for el in elements:
        key = f"{el['tag']}-{el['x']}-{el['y']}-{el['w']}"
        if key not in seen:
            seen.add(key)
            extra = f" role={el['role']}" if el['role'] else ""
            extra += f" type={el['type']}" if el['type'] else ""
            extra += f" aria={el['ariaLabel']}" if el['ariaLabel'] else ""
            print(f"    [{el['tag']:<8}] ({el['x']:4},{el['y']:4}) {el['w']:3}x{el['h']:3}: {el['text'][:70]}{extra}")


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

        # === Step 1: Click '+' and reload to get ingredient panel ===
        print("\n=== Step 1: Open ingredient panel ===")
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
        time.sleep(2)

        # Reload to trigger panel load
        print("  Reloading page...")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector("textarea", timeout=60000)
        time.sleep(8)

        # Click '+' again
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

        # Wait for 'Загрузить' to appear
        for sec in range(45):
            time.sleep(1)
            btn = page.query_selector('button:has-text("Загрузить")')
            if btn and (btn.bounding_box() or {}).get('width', 0) > 20:
                print(f"  'Загрузить' button appeared at {sec+1}s!")
                break
        else:
            print("  'Загрузить' did not appear in 45s")
            screenshot(page, "debug_no_upload_btn")
            dump_elements_near(page, "All elements after wait", 400, 900)
            time.sleep(20)
            ctx.close()
            return

        # === Step 2: Examine the panel before clicking 'Загрузить' ===
        print("\n=== Step 2: Panel state BEFORE clicking 'Загрузить' ===")
        screenshot(page, "debug_01_before_upload_click")
        dump_elements_near(page, "Elements before click", 400, 900)

        # === Step 3: Click 'Загрузить' and observe what happens ===
        print("\n=== Step 3: Click 'Загрузить' ===")

        # Register DOM mutation observer to see what changes
        page.evaluate("""() => {
            window.__debug_mutations = [];
            const observer = new MutationObserver((mutations) => {
                for (const m of mutations) {
                    if (m.addedNodes.length > 0) {
                        for (const node of m.addedNodes) {
                            if (node.nodeType === 1) {
                                window.__debug_mutations.push({
                                    type: 'added',
                                    tag: node.tagName?.toLowerCase() || 'text',
                                    text: (node.textContent || '').trim().substring(0, 100),
                                    role: node.getAttribute?.('role') || '',
                                });
                            }
                        }
                    }
                }
            });
            observer.observe(document.body, { childList: true, subtree: true });
        }""")

        upload_btn = page.query_selector('button:has-text("Загрузить")')
        if upload_btn:
            box = upload_btn.bounding_box()
            print(f"  Button at ({box['x']:.0f}, {box['y']:.0f}) {box['width']:.0f}x{box['height']:.0f}")

            # Click WITHOUT expecting file chooser to see what happens
            upload_btn.click()
            time.sleep(3)

            # Check what appeared
            screenshot(page, "debug_02_after_upload_click")
            dump_elements_near(page, "Elements AFTER clicking Загрузить", 0, 900)

            # Check mutations
            mutations = page.evaluate("() => window.__debug_mutations || []")
            print(f"\n  DOM mutations after click ({len(mutations)}):")
            for m in mutations[:20]:
                print(f"    {m['type']} [{m['tag']}] role={m['role']}: {m['text'][:80]}")

            # Check for file input that may have been created
            file_inputs = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('input[type="file"]').forEach(el => {
                    results.push({
                        accept: el.accept,
                        multiple: el.multiple,
                        display: window.getComputedStyle(el).display,
                    });
                });
                return results;
            }""")
            print(f"\n  File inputs after click: {file_inputs}")

            # Check if a dialog or popover appeared
            dialogs = page.evaluate("""() => {
                const results = [];
                document.querySelectorAll('[role="dialog"], [role="menu"], [role="listbox"], [role="presentation"]').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0) {
                        results.push({
                            role: el.getAttribute('role'),
                            text: (el.textContent || '').trim().substring(0, 200),
                            x: Math.round(rect.x), y: Math.round(rect.y),
                            w: Math.round(rect.width), h: Math.round(rect.height),
                        });
                    }
                });
                return results;
            }""")
            print(f"\n  Dialogs/menus/listboxes after click ({len(dialogs)}):")
            for d in dialogs:
                print(f"    [{d['role']}] ({d['x']},{d['y']}) {d['w']}x{d['h']}: {d['text'][:100]}")

        # === Step 4: Try clicking Загрузить with expect_file_chooser ===
        print("\n=== Step 4: Try Загрузить with expect_file_chooser ===")
        page.keyboard.press("Escape")
        time.sleep(2)

        # Re-click '+' to re-open panel
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

        upload_btn2 = page.query_selector('button:has-text("Загрузить")')
        if upload_btn2:
            try:
                with page.expect_file_chooser(timeout=10000) as fc_info:
                    upload_btn2.click()
                fc = fc_info.value
                print(f"  FILE CHOOSER OPENED! multiple={fc.is_multiple}")
                fc.set_files(str(TEST_IMAGE))
                time.sleep(5)
                screenshot(page, "debug_03_after_file_upload")
                print("  File uploaded!")

                # Check for crop dialog
                crop_btn = page.query_selector('button:has-text("Кадрировать и сохранить")')
                if crop_btn:
                    print("  Crop dialog found! Clicking...")
                    crop_btn.click()
                    time.sleep(3)
                    screenshot(page, "debug_04_after_crop")

                # Now check state — is 'Загрузить' still available?
                time.sleep(2)
                dump_elements_near(page, "Elements after first upload", 400, 900)

                upload_btn3 = page.query_selector('button:has-text("Загрузить")')
                print(f"\n  'Загрузить' still visible: {upload_btn3 is not None}")
                if upload_btn3:
                    box = upload_btn3.bounding_box()
                    print(f"  Button box: {box}")

            except Exception as e:
                print(f"  File chooser not triggered: {e}")
                screenshot(page, "debug_03_no_file_chooser")
                dump_elements_near(page, "Elements after failed file chooser", 0, 900)

        print("\n=== Done. Browser stays open 30s ===")
        time.sleep(30)
        ctx.close()
        print("Done.")


if __name__ == "__main__":
    main()
