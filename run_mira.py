#!/usr/bin/env python3
"""MIRA-Web Top-Level Execution CLI.

Usage:
    python run_mira.py --target http://localhost:4010
    python run_mira.py --target http://localhost:4010 --warm
"""

import sys
from mira.runner import run_pipeline

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MIRA-Web Autonomous QA Platform")
    parser.add_argument("--target", default="http://localhost:4010", help="Target URL to test")
    parser.add_argument("--output", default="evidence", help="Output evidence directory")
    parser.add_argument("--warm", action="store_true", help="Warm run with graph memory cache")
    parser.add_argument("--headed", action="store_true", help="Run headed browser")
    parser.add_argument("--no-vision", action="store_true", help="Disable multimodal vision judge API")
    args = parser.parse_args()

    run_pipeline(
        target_url=args.target,
        output_dir=args.output,
        headless=not args.headed,
        call_vision=not args.no_vision,
        warm=args.warm,
    )
