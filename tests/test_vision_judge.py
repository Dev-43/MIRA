"""Acceptance unit test for Task 6 (mira/vision_judge.py)."""

import io
import unittest
from PIL import Image
from mira import vision_judge


class TestVisionJudge(unittest.TestCase):
    def test_vision_judge_contradiction(self):
        img = Image.new("RGB", (150, 50), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()

        context = {
            "region_description": "status indicator badge",
            "claimed_state": "Yellow warning alert",
            "observed_change": "Badge is static solid blue",
        }

        result = vision_judge.judge(image_bytes, context)
        self.assertIn("verdict", result)
        self.assertIn("reasoning", result)
        self.assertIn("confidence", result)
        self.assertIn(result["verdict"], ("supported", "contradicted", "ambiguous", "needs_review"))
        self.assertGreater(len(result["reasoning"]), 0)


if __name__ == "__main__":
    unittest.main()
