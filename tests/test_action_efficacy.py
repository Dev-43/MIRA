"""Acceptance test for Task 8 (mira/primitives/action_efficacy.py)."""

import unittest
from mira.primitives import action_efficacy


class TestActionEfficacy(unittest.TestCase):
    def test_passive_action_check(self):
        elements = [
            {"id": "btn_arm", "role": "button", "name": "Arm Drone", "page_url": "http://localhost:4010", "bbox": {}},
            {"id": "tab_fpv", "role": "tab", "name": "FPV Feed", "page_url": "http://localhost:4010", "bbox": {}},
        ]
        findings = action_efficacy.check_action_efficacy(elements, "http://localhost:4010", page=None, call_vision=False)
        self.assertEqual(len(findings), 0)


if __name__ == "__main__":
    unittest.main()
