"""Acceptance unit test for Task 1 (mira/graph.py)."""

import unittest
from mira import graph


class TestGraphRoundTrip(unittest.TestCase):
    def setUp(self):
        graph.clear_all()

    def test_schema_init(self):
        result = graph.init_schema()
        self.assertTrue(result)

    def test_round_trip_page_element_livefield(self):
        site_id = "site_test_01"
        page_id = "page_test_home"
        page_url = "http://localhost:4010/cockpit"

        # 1. Upsert Site
        site = graph.upsert_site(site_id=site_id, url="http://localhost:4010")
        self.assertEqual(site["id"], site_id)
        self.assertTrue(graph.is_site_known(site_id))

        # 2. Upsert Page
        page = graph.upsert_page(
            site_id=site_id,
            page_id=page_id,
            url=page_url,
            title="Cockpit Fleet View",
            path="/cockpit",
        )
        self.assertEqual(page["url"], page_url)

        # 3. Upsert Element
        element_input = {
            "id": "el_btn_arm_01",
            "role": "button",
            "name": "ARM DRONE 1",
            "page_url": page_url,
            "bbox": {"x": 100, "y": 200, "width": 80, "height": 40},
        }
        upserted_el = graph.upsert_element(site_id=site_id, page_url=page_url, element=element_input)
        self.assertEqual(upserted_el["id"], "el_btn_arm_01")

        # 4. Upsert LiveField
        livefield_input = {
            "id": "lf_telemetry_alt_01",
            "page_url": page_url,
            "region_bbox": {"x": 300, "y": 400, "width": 120, "height": 60},
            "label_text": "Live Altitude: 42.5m",
            "last_value_hash": "a1b2c3d4e5f6",
            "last_changed_ts": 1727330000.0,
            "freshness_claim": True,
        }
        upserted_lf = graph.upsert_livefield(site_id=site_id, page_url=page_url, livefield=livefield_input)
        self.assertEqual(upserted_lf["id"], "lf_telemetry_alt_01")

        # 5. Read back elements
        elements = graph.get_elements_for_page(page_url)
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["id"], "el_btn_arm_01")
        self.assertEqual(elements[0]["name"], "ARM DRONE 1")
        self.assertEqual(elements[0]["role"], "button")
        self.assertEqual(elements[0]["bbox"]["width"], 80)

        # 6. Read back livefields
        livefields = graph.get_livefields_for_page(page_url)
        self.assertEqual(len(livefields), 1)
        self.assertEqual(livefields[0]["id"], "lf_telemetry_alt_01")
        self.assertEqual(livefields[0]["label_text"], "Live Altitude: 42.5m")
        self.assertTrue(livefields[0]["freshness_claim"])
        self.assertEqual(livefields[0]["last_value_hash"], "a1b2c3d4e5f6")


if __name__ == "__main__":
    unittest.main()
