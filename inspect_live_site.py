import os
import json
import time
from playwright.sync_api import sync_playwright

os.makedirs(r"d:\MIRA\evidence", exist_ok=True)

report = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    "cockpit_desktop": {},
    "cockpit_mobile": {},
    "control_dashboard": {}
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    # 1. Inspect Cockpit Desktop
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    
    console_messages = []
    page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
    
    print("Navigating to Cockpit http://localhost:4010 ...")
    page.goto("http://localhost:4010", wait_until="domcontentloaded")
    page.wait_for_timeout(4000) # allow Cesium and WebSockets to connect
    
    cockpit_title = page.title()
    cockpit_screenshot_desktop = r"d:\MIRA\evidence\cockpit_desktop.png"
    page.screenshot(path=cockpit_screenshot_desktop)
    
    aria_snapshot = page.aria_snapshot()
    
    buttons = [btn.inner_text().strip() for btn in page.locator("button").all() if btn.is_visible()]
    headings = [h.inner_text().strip() for h in page.locator("h1, h2, h3, h4, h5").all() if h.is_visible()]
    body_text = page.locator("body").inner_text()
    
    # Check for specific cockpit indicators
    badge = page.locator(".badge, [class*='badge'], [class*='status']").all_inner_texts()
    
    report["cockpit_desktop"] = {
        "url": "http://localhost:4010",
        "title": cockpit_title,
        "screenshot": cockpit_screenshot_desktop,
        "visible_buttons": buttons,
        "visible_headings": headings,
        "status_badges": badge,
        "aria_snapshot": aria_snapshot,
        "console_logs": console_messages[:25],
        "extracted_text_preview": body_text[:2000]
    }
    context.close()
    
    # 2. Inspect Cockpit Mobile (375x667)
    context_mobile = browser.new_context(viewport={"width": 375, "height": 667})
    page_mobile = context_mobile.new_page()
    print("Navigating to Cockpit Mobile (375x667)...")
    page_mobile.goto("http://localhost:4010", wait_until="domcontentloaded")
    page_mobile.wait_for_timeout(3000)
    
    cockpit_screenshot_mobile = r"d:\MIRA\evidence\cockpit_mobile.png"
    page_mobile.screenshot(path=cockpit_screenshot_mobile)
    mobile_buttons = [btn.inner_text().strip() for btn in page_mobile.locator("button").all() if btn.is_visible()]
    mobile_body_text = page_mobile.locator("body").inner_text()
    
    report["cockpit_mobile"] = {
        "viewport": "375x667",
        "screenshot": cockpit_screenshot_mobile,
        "visible_buttons": mobile_buttons,
        "aria_snapshot": page_mobile.aria_snapshot(),
        "extracted_text_preview": mobile_body_text[:1500]
    }
    context_mobile.close()
    
    # 3. Inspect Control Panel (http://localhost:4000/dashboard)
    context_dashboard = browser.new_context(viewport={"width": 1440, "height": 900})
    page_dash = context_dashboard.new_page()
    print("Navigating to Control Dashboard http://localhost:4000/dashboard ...")
    page_dash.goto("http://localhost:4000/dashboard", wait_until="domcontentloaded")
    page_dash.wait_for_timeout(2000)
    
    dash_title = page_dash.title()
    dash_screenshot = r"d:\MIRA\evidence\control_dashboard.png"
    page_dash.screenshot(path=dash_screenshot)
    
    dash_buttons = [btn.inner_text().strip() for btn in page_dash.locator("button").all() if btn.is_visible()]
    dash_headings = [h.inner_text().strip() for h in page_dash.locator("h1, h2, h3, h4").all() if h.is_visible()]
    dash_aria = page_dash.aria_snapshot()
    dash_body_text = page_dash.locator("body").inner_text()
    
    report["control_dashboard"] = {
        "url": "http://localhost:4000/dashboard",
        "title": dash_title,
        "screenshot": dash_screenshot,
        "visible_buttons": dash_buttons,
        "visible_headings": dash_headings,
        "aria_snapshot": dash_aria,
        "extracted_text_preview": dash_body_text[:2000]
    }
    
    context_dashboard.close()
    browser.close()

with open(r"d:\MIRA\evidence\live_check_raw.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("Live check completed successfully! Output saved to d:\\MIRA\\evidence\\live_check_raw.json")
