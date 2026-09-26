"""Acceptance test for Task 9 (mira/runner.py)."""

import os
import unittest
from pathlib import Path
from mira import runner


class TestRunnerAcceptance(unittest.TestCase):
    def test_pipeline_execution(self):
        output_dir = "evidence/test_run"
        findings = runner.run_pipeline(
            target_url="http://localhost:4010",
            output_dir=output_dir,
            max_depth=1,
            max_pages=1,
            headless=True,
            call_vision=False,
            warm=False,
        )

        out_path = Path(output_dir)
        findings_json = out_path / "findings.json"
        self.assertTrue(findings_json.exists(), "findings.json must be generated")

        sub_dir = out_path / "submission"
        self.assertTrue(sub_dir.exists(), "Submission directory must be created")


if __name__ == "__main__":
    unittest.main()
