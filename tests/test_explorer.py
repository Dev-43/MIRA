"""Acceptance test for Task 2 (mira/explorer.py)."""

import unittest
from mira import explorer, graph


class TestExplorerAcceptance(unittest.TestCase):
    def setUp(self):
        graph.clear_all()

    def test_cockpit_exploration(self):
        """Run explorer against local cockpit (:4010)."""
        target_url = "http://127.0.0.1:4010"
        elements, livefields = explorer.explore(
            target_url=target_url,
            max_depth=1,
            max_pages=2,
            sample_interval=2.0,
            headless=True,
        )

        # 1. Elements must be discovered
        self.assertGreater(len(elements), 0, "Expected interactive elements on cockpit")
        for el in elements:
            self.assertIn("id", el)
            self.assertIn("role", el)
            self.assertIn("name", el)
            self.assertIn("page_url", el)
            self.assertIn("bbox", el)

        # 2. Graph must have elements stored
        stored_elements = graph.get_elements_for_page("http://127.0.0.1:4010/") or graph.get_elements_for_page("http://127.0.0.1:4010")
        if not stored_elements:
            stored_elements = graph.get_elements_for_page("http://localhost:4010/") or graph.get_elements_for_page("http://localhost:4010")
        self.assertGreater(len(stored_elements), 0, "Graph must store discovered elements")

        # 3. LiveFields should be detected or validated
        for lf in livefields:
            self.assertIn("id", lf)
            self.assertIn("page_url", lf)
            self.assertIn("region_bbox", lf)
            self.assertIn("label_text", lf)
            self.assertIn("last_value_hash", lf)
            self.assertIn("freshness_claim", lf)

        print(f"\n[TestExplorer] Cockpit: {len(elements)} elements, {len(livefields)} livefields discovered.")


if __name__ == "__main__":
    unittest.main()
