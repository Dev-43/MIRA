import re
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
target_url = os.getenv("TARGET_URL", "http://localhost:8085")

pages_to_test = [
    ("Login (v1)", "/index.html"),
    ("Dashboard", "/dashboard.html"),
    ("Settings", "/settings.html"),
    ("Login (v2 mutated)", "/index_v2.html")
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    for name, path in pages_to_test:
        full_url = target_url.rstrip("/") + path
        page.goto(full_url)
        snapshot = page.aria_snapshot()
        elements = re.findall(r'-\s*(heading|textbox|button|link|checkbox)\s*"([^"]+)"', snapshot)
        print(f"=== {name} ({path}) ===")
        print(f"Title: {page.title()}")
        print(f"Elements ({len(elements)}):")
        for role, el_name in elements:
            print(f"  [{role}] {el_name}")
        print()
        
    browser.close()
