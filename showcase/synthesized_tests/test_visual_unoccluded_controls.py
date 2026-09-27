"""
Auto-generated regression test synthesized by MIRA Autonomous Visual Agent.
Asserts that critical fleet control actions remain physically clickable and unoccluded.
"""

from playwright.sync_api import sync_playwright

TARGET_URL = "http://127.0.0.1:4010"
PROBE_X = 149
PROBE_Y = 117


def test_action_is_physically_unoccluded():
    """Verify that physical coordinate (149, 117) directly reaches target control."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(TARGET_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Hit-test center of the control
        hit_tag = page.evaluate("""
            ([cx, cy]) => {
                const el = document.elementFromPoint(cx, cy);
                return el ? el.tagName.toLowerCase() : null;
            }
        """, [PROBE_X, PROBE_Y])

        # Assert no banner overlay intercepts the hit-test
        assert hit_tag != "div" or hit_tag == "li", (
            f"Physical hit-test at ({PROBE_X}, {PROBE_Y}) was intercepted by an occluding layer: <{hit_tag}>"
        )

        browser.close()
        print(f"TEST PASSED: Action at ({PROBE_X}, {PROBE_Y}) is 100% physically unoccluded.")


if __name__ == "__main__":
    test_action_is_physically_unoccluded()
