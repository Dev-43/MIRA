"""Acceptance test for Task 7 (mira/primitives/status_reality.py)."""

import unittest
from datetime import datetime, timezone
from mira.primitives import status_reality


class TestStatusReality(unittest.TestCase):
    def test_healthy_cockpit_no_false_positive(self):
        now_ts = datetime.now(timezone.utc).timestamp()
        elements = [
            {"id": "el_1", "role": "status", "name": "Socket Connected", "page_url": "http://localhost:4010", "bbox": {}},
            {"id": "el_2", "role": "heading", "name": "Cockpit Fleet View", "page_url": "http://localhost:4010", "bbox": {}},
        ]
        livefields = [
            {"id": "lf_1", "page_url": "http://localhost:4010", "last_changed_ts": now_ts - 1.0, "freshness_claim": True},
        ]

        findings = status_reality.check_status_reality(elements, livefields, "http://localhost:4010", call_vision=False)
        self.assertEqual(len(findings), 0, "Healthy state must yield 0 false positives")

    def test_broken_telemetry_detects_bug(self):
        now_ts = datetime.now(timezone.utc).timestamp()
        elements = [
            {"id": "el_1", "role": "status", "name": "Socket Connected", "page_url": "http://localhost:4010", "bbox": {}},
        ]
        # Livefields stopped updating 15s ago
        livefields = [
            {"id": "lf_1", "page_url": "http://localhost:4010", "last_changed_ts": now_ts - 15.0, "freshness_claim": True},
        ]

        findings = status_reality.check_status_reality(elements, livefields, "http://localhost:4010", call_vision=False)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["category"], "status_reality")
        self.assertEqual(findings[0]["verdict"], "bug")


if __name__ == "__main__":
    unittest.main()
