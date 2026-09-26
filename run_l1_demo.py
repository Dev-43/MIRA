#!/usr/bin/env python3
"""
MIRA Level 1 Autonomous Demonstration Runner
Runs the complete L1 Visual Bug Detection, Test Synthesis, and Self-Healing loop.

Usage:
    python run_l1_demo.py
    python run_l1_demo.py --target http://localhost:4010
"""

import argparse
import sys
from mira.healer import AutonomousVisualAgent


def main():
    parser = argparse.ArgumentParser(description="MIRA Level 1 Autonomous Visual Healing Loop")
    parser.add_argument("--target", default="http://localhost:4010", help="Target URL (default: http://localhost:4010)")
    parser.add_argument("--no-video", action="store_true", help="Disable Playwright session video recording")
    args = parser.parse_args()

    agent = AutonomousVisualAgent(target_url=args.target)
    results = agent.run_demonstration_loop(record_video=not args.no_video)

    if results.get("status") == "COMPLETED":
        print("\n[SUCCESS] Level 1 Demonstration finished successfully!")
        sys.exit(0)
    else:
        print("\n[FAILURE] Level 1 Demonstration did not complete as expected.")
        sys.exit(1)


if __name__ == "__main__":
    main()
