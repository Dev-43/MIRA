"""Autonomous Runner and Pipeline Orchestrator for MIRA-Web.

Wires:
1. Knowledge Graph (mira/graph.py)
2. Playwright Web Explorer (mira/explorer.py)
3. 5 Scenario Primitives:
   - auth_gate
   - staleness
   - responsive_reachability
   - status_reality
   - action_efficacy
4. Multimodal Vision Judge (mira/vision_judge.py)
5. Evidence capture (screenshots, video)
6. Hackathon Submission Packaging (mira/reporter.py)
"""

from __future__ import annotations
import argparse
import io
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from mira import explorer, graph, reporter, vision_judge
from mira.primitives import (
    action_efficacy,
    auth_gate,
    responsive_reachability,
    staleness,
    status_reality,
)

logger = logging.getLogger("mira.runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def run_pipeline(
    target_url: str = "http://localhost:4010",
    output_dir: str = "evidence",
    max_depth: int = 2,
    max_pages: int = 10,
    headless: bool = True,
    call_vision: bool = True,
    warm: bool = False,
) -> List[Dict[str, Any]]:
    """Execute complete end-to-end MIRA autonomous testing pipeline."""
    out_path = Path(output_dir)
    screens_dir = out_path / "screenshots"
    videos_dir = out_path / "videos"
    screens_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)

    site_id = explorer._get_site_id(target_url)

    logger.info("=" * 60)
    logger.info("Starting MIRA-Web Autonomous QA Pipeline")
    logger.info("Target: %s | Output: %s | Mode: %s", target_url, output_dir, "Warm" if warm else "Cold")
    logger.info("=" * 60)

    # Step 1: Web Crawl & Element/LiveField Discovery
    logger.info("[Step 1/4] Exploring target website and mapping graph schema...")
    elements, livefields = explorer.explore(
        target_url=target_url,
        max_depth=max_depth,
        max_pages=max_pages,
        sample_interval=2.0,
        headless=headless,
    )
    logger.info("Discovered %d elements, %d livefields across site.", len(elements), len(livefields))

    # Collect unique page URLs
    page_urls = sorted(list({e.get("page_url") for e in elements if e.get("page_url")} | {target_url}))

    all_findings: List[Dict[str, Any]] = []

    # Step 2: Interactive Session & Evidence Recording
    logger.info("[Step 2/4] Launching Playwright session with video and screenshot capture...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(videos_dir),
            record_video_size={"width": 1440, "height": 900},
        )
        page = context.new_page()

        for page_url in page_urls:
            logger.info("Inspecting page: %s", page_url)
            try:
                page.goto(page_url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning("Failed to open %s: %s", page_url, e)
                continue

            # Capture desktop screenshot
            clean_name = urlparse(page_url).path.replace("/", "_").strip("_") or "root"
            screenshot_file = screens_dir / f"{clean_name}_desktop.png"
            page.screenshot(path=str(screenshot_file), full_page=False, timeout=5000, animations="disabled")
            with open(screenshot_file, "rb") as f:
                shot_bytes = f.read()

            # Execute Primitive 1: Auth-Gate Check
            logger.info("Running Primitive 1/5: auth_gate...")
            try:
                ag_findings = auth_gate.check_auth_gate(elements, livefields, page_url)
                for f in ag_findings:
                    f["evidence"]["screenshot_path"] = str(screenshot_file)
                all_findings.extend(ag_findings)
            except Exception as e:
                logger.warning("auth_gate check error: %s", e)

            # Execute Primitive 2: Staleness & Freeze Check
            logger.info("Running Primitive 2/5: staleness...")
            try:
                st_findings = staleness.check_staleness(elements, livefields, page_url)
                for f in st_findings:
                    f["evidence"]["screenshot_path"] = str(screenshot_file)
                all_findings.extend(st_findings)
            except Exception as e:
                logger.warning("staleness check error: %s", e)

            # Execute Primitive 3: Responsive Reachability Check
            logger.info("Running Primitive 3/5: responsive_reachability...")
            try:
                rr_findings = responsive_reachability.check_responsive_reachability(elements, 375, 667)
                for f in rr_findings:
                    f["evidence"]["screenshot_path"] = str(screenshot_file)
                all_findings.extend(rr_findings)
            except Exception as e:
                logger.warning("responsive_reachability check error: %s", e)

            # Execute Primitive 4: Status Reality Check (Multimodal)
            logger.info("Running Primitive 4/5: status_reality (Vision Judge)...")
            try:
                sr_findings = status_reality.check_status_reality(
                    elements, livefields, page_url, screenshot_bytes=shot_bytes, call_vision=call_vision
                )
                for f in sr_findings:
                    f["evidence"]["screenshot_path"] = str(screenshot_file)
                all_findings.extend(sr_findings)
            except Exception as e:
                logger.warning("status_reality check error: %s", e)

            # Execute Primitive 5: Action Efficacy Check (Safe probes)
            logger.info("Running Primitive 5/5: action_efficacy...")
            try:
                ae_findings = action_efficacy.check_action_efficacy(
                    elements, page_url, page=page, screenshot_bytes=shot_bytes, call_vision=call_vision
                )
                for f in ae_findings:
                    f["evidence"]["screenshot_path"] = str(screenshot_file)
                all_findings.extend(ae_findings)
            except Exception as e:
                logger.warning("action_efficacy check error: %s", e)

        # Close page and context to flush recorded video
        page.close()
        context.close()
        browser.close()

    # Step 3: Deduplicate findings and associate recorded video
    logger.info("[Step 3/4] Aggregating and finalizing findings...")
    recorded_videos = list(videos_dir.glob("*.webm"))
    primary_video = str(recorded_videos[0]) if recorded_videos else ""

    deduped_findings: Dict[str, Dict[str, Any]] = {}
    for f in all_findings:
        fid = f.get("finding_id", f"MIRA-{hash(f.get('description', ''))}")
        if fid not in deduped_findings:
            if not f.get("evidence", {}).get("video_path") and primary_video:
                f["evidence"]["video_path"] = primary_video
            deduped_findings[fid] = f

    final_findings = list(deduped_findings.values())

    # Export findings.json
    findings_file = out_path / "findings.json"
    with open(findings_file, "w", encoding="utf-8") as f:
        json.dump(final_findings, f, indent=2)
    logger.info("Exported %d findings to %s", len(final_findings), findings_file)

    # Step 4: Generate Hackathon Submission Package
    logger.info("[Step 4/4] Generating submission package via reporter...")
    sub_dir = out_path / "submission"
    reporter.generate_submission_package(final_findings, output_dir=str(sub_dir))
    logger.info("Submission package successfully generated at %s", sub_dir)

    print("\n" + "=" * 60)
    print(f"PIPELINE COMPLETE: {len(final_findings)} total findings discovered.")
    for idx, f in enumerate(final_findings[:10], 1):
        safe_desc = f["description"][:70].encode("ascii", "replace").decode("ascii")
        print(f"  [{idx}] {f['finding_id']} | {f['verdict'].upper()} | {f['category']} | {safe_desc}...")
    print("=" * 60 + "\n")

    return final_findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MIRA Autonomous Test Runner")
    parser.add_argument("--target", default="http://localhost:4010", help="Target URL")
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
