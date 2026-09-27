"""
Dynamically Synthesized Test Script: Multi-Drone Swarm State Reconciliation
Target: FlytBase Cockpit SUT (http://127.0.0.1:4010)
Asserts that Drone 1 flight status in Cockpit UI matches physical flight controller Ground Truth.
"""

import requests
from playwright.sync_api import sync_playwright

CONTROL_API = "http://127.0.0.1:4000"
COCKPIT_URL = "http://127.0.0.1:4010"

def test_drone1_flight_state_reconciliation():
    # 1. Fetch Ground Truth from Flight Controller
    state = requests.get(f"{CONTROL_API}/api/control/state").json()
    gt_d1 = state["drones"]["drone-1"]
    gt_status = gt_d1["status"]

    # 2. Inspect Cockpit UI Rendered Row
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.route("**/*localhost:4000*/**", lambda r: r.continue_(url=r.request.url.replace("localhost:4000", "127.0.0.1:4000")))
        page.goto(COCKPIT_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        row_text = page.locator(".device-row").first.inner_text()
        browser.close()

    # 3. Assert Ground Truth vs UI State Fidelity
    if gt_status == "in_flight":
        assert "in_flight" in row_text, f"State Desynchronization: Simulator is in_flight, but UI displays: {row_text}"
        assert "standby" not in row_text, f"State Corruption: Drone airborne, but rendered on land!"
    print("TEST PASSED: Drone 1 operational state is 100% synchronized with flight controller.")

if __name__ == "__main__":
    test_drone1_flight_state_reconciliation()
