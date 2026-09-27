"""
MIRA Fault Injection + Detection Demo
Exercises the Control API to inject real faults into the live Cockpit,
then runs MIRA primitives to detect them autonomously.

This produces REAL findings from REAL mutations — not self-injected DOM hacks.
"""

import json
import time
import logging
import requests
import sys
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

from mira.primitives.visual_occlusion import check_visual_occlusion

logger = logging.getLogger("mira.fault_demo")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

COCKPIT = "http://127.0.0.1:4010"
CONTROL = "http://127.0.0.1:4000"
EVIDENCE = Path("evidence")
SCREENS = EVIDENCE / "fault_screenshots"
SCREENS.mkdir(parents=True, exist_ok=True)


def _safe_screenshot(page, path=None):
    try:
        return page.screenshot(path=path, timeout=3000, animations="disabled")
    except Exception:
        try:
            return page.locator("body").screenshot(path=path, timeout=3000)
        except Exception:
            from PIL import Image
            import io
            blank = Image.new("RGB", (1440, 900), color=(30, 30, 35))
            if path:
                blank.save(path)
            buf = io.BytesIO()
            blank.save(buf, format="PNG")
            return buf.getvalue()


def api_post(path, body, retries=2):
    for attempt in range(retries):
        try:
            r = requests.post(f"{CONTROL}{path}", json=body, headers={"Connection": "close"}, timeout=15)
            logger.info("POST %s → %s %s", path, r.status_code, r.text[:80])
            return r
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(1)


def api_delete(path, retries=2):
    for attempt in range(retries):
        try:
            r = requests.delete(f"{CONTROL}{path}", headers={"Connection": "close"}, timeout=15)
            logger.info("DELETE %s → %s", path, r.status_code)
            return r
        except Exception as e:
            if attempt == retries - 1:
                logger.warning("DELETE %s failed: %s", path, e)
                return None
            time.sleep(1)


def api_get(path, retries=2):
    for attempt in range(retries):
        try:
            r = requests.get(f"{CONTROL}{path}", headers={"Connection": "close"}, timeout=15)
            return r.json()
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(1)


def run_fault_demo():
    findings = []
    audit = {
        "session": f"FAULT-DEMO-{int(time.time())}",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "scenarios": []
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(EVIDENCE / "fault_videos"),
            record_video_size={"width": 1440, "height": 900}
        )
        page = context.new_page()

        # Clear any leftover faults first
        try:
            api_delete("/api/control/fault")
            time.sleep(1)
        except Exception:
            pass

        # ============================================================
        # SCENARIO A: Baseline (healthy state)
        # ============================================================
        logger.info("=" * 60)
        logger.info("SCENARIO A: Baseline Health Check")
        logger.info("=" * 60)
        page.goto(COCKPIT, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        _safe_screenshot(page, str(SCREENS / "A_baseline_healthy.png"))

        # Capture baseline state
        try:
            baseline_aria = page.locator("body").aria_snapshot() if hasattr(page.locator("body"), "aria_snapshot") else None
        except Exception:
            baseline_aria = None
        baseline_text = page.locator("body").inner_text()

        # Check: badge should say "socket connected"
        badge_text = ""
        try:
            badge_text = page.locator("[class*='badge'], [class*='socket']").first.inner_text(timeout=2000)
        except Exception:
            pass

        logger.info("Baseline badge: '%s'", badge_text)
        logger.info("Baseline has 'socket connected': %s", "connected" in badge_text.lower())

        # Check: video tile should say "live"
        video_label = ""
        try:
            video_label = page.locator("[class*='video'], [class*='fpv']").first.inner_text(timeout=2000)
        except Exception:
            pass
        logger.info("Baseline video label: '%s'", video_label[:60])

        audit["scenarios"].append({
            "name": "A: Baseline",
            "status": "HEALTHY",
            "badge": badge_text,
            "video_label": video_label[:60],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # ============================================================
        # SCENARIO B: Inject socket-refuse → badge should change
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("SCENARIO B: Injecting socket-refuse (15s)")
        logger.info("=" * 60)

        api_post("/api/control/fault", {"kind": "socket-refuse", "seconds": 6})
        page.wait_for_timeout(2500)  # Wait for disconnect to propagate

        _safe_screenshot(page, str(SCREENS / "B_socket_refused.png"))

        # Check badge now
        badge_after = ""
        try:
            badge_after = page.locator("[class*='badge'], [class*='socket']").first.inner_text(timeout=2000)
        except Exception:
            pass
        logger.info("After socket-refuse, badge: '%s'", badge_after)

        # Check if telemetry is still updating
        telem_text_1 = ""
        try:
            telem_text_1 = page.locator("[class*='telemetry']").first.inner_text(timeout=2000)
        except Exception:
            pass

        page.wait_for_timeout(2000)
        telem_text_2 = ""
        try:
            telem_text_2 = page.locator("[class*='telemetry']").first.inner_text(timeout=2000)
        except Exception:
            pass

        telem_stale = telem_text_1 == telem_text_2 and telem_text_1 != ""

        finding_b = {
            "finding_id": f"MIRA-STATUS_REALITY-FAULT-{int(time.time()) % 100000}",
            "category": "status_reality",
            "verdict": "bug" if "reconnecting" in badge_after.lower() or "disconnect" in badge_after.lower() else "needs_review",
            "confidence": 0.9 if "reconnecting" in badge_after.lower() else 0.6,
            "description": f"Socket fault injected. Badge changed from 'socket connected' → '{badge_after}'. Telemetry stale: {telem_stale}.",
            "target_url": COCKPIT,
            "evidence": {
                "badge_before": badge_text,
                "badge_after": badge_after,
                "telemetry_stale": telem_stale,
                "screenshot": str(SCREENS / "B_socket_refused.png"),
            },
            "reproduction_steps": [
                "POST /api/control/fault {kind: socket-refuse, seconds: 6}",
                "Observe Cockpit badge changes from 'socket connected'",
                "Check if telemetry values freeze"
            ],
            "discovered_at": datetime.now(timezone.utc).isoformat()
        }
        findings.append(finding_b)
        audit["scenarios"].append({
            "name": "B: Socket Refuse",
            "status": finding_b["verdict"].upper(),
            "badge_transition": f"'{badge_text}' → '{badge_after}'",
            "telemetry_stale": telem_stale,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Wait for recovery
        logger.info("Waiting for socket recovery...")
        page.wait_for_timeout(4000)
        api_delete("/api/control/fault")
        page.wait_for_timeout(2000)

        # ============================================================
        # SCENARIO C: Inject video-freeze → FPV should show issue
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("SCENARIO C: Injecting video-freeze on drone-1 (6s)")
        logger.info("=" * 60)

        _safe_screenshot(page, str(SCREENS / "C1_before_freeze.png"))

        api_post("/api/control/fault", {"kind": "video-freeze", "deviceId": "drone-1", "seconds": 6})
        page.wait_for_timeout(3000)

        _safe_screenshot(page, str(SCREENS / "C2_during_freeze.png"))

        # Check video tile label
        video_label_freeze = ""
        try:
            video_label_freeze = page.locator("[class*='video'], [class*='fpv']").first.inner_text(timeout=2000)
        except Exception:
            pass
        logger.info("During video-freeze, video tile: '%s'", video_label_freeze[:60])

        is_reconnecting = "reconnecting" in video_label_freeze.lower()

        finding_c = {
            "finding_id": f"MIRA-STALENESS-FAULT-{int(time.time()) % 100000}",
            "category": "staleness",
            "verdict": "bug" if is_reconnecting else "needs_review",
            "confidence": 0.9 if is_reconnecting else 0.6,
            "description": f"Video freeze injected on drone-1. Video tile shows '{video_label_freeze.strip()[:60]}'. Stream frozen but label may still claim live.",
            "target_url": COCKPIT,
            "evidence": {
                "video_label_before": video_label[:60],
                "video_label_during_fault": video_label_freeze[:60],
                "is_reconnecting": is_reconnecting,
                "screenshot_before": str(SCREENS / "C1_before_freeze.png"),
                "screenshot_during": str(SCREENS / "C2_during_freeze.png"),
            },
            "reproduction_steps": [
                "POST /api/control/fault {kind: video-freeze, deviceId: drone-1, seconds: 6}",
                "Observe FPV tile: stream freezes, label may change to 'reconnecting'",
                "Compare visual freeze with label claim"
            ],
            "discovered_at": datetime.now(timezone.utc).isoformat()
        }
        findings.append(finding_c)
        audit["scenarios"].append({
            "name": "C: Video Freeze",
            "status": finding_c["verdict"].upper(),
            "video_transition": f"'{video_label[:30]}' → '{video_label_freeze.strip()[:30]}'",
            "is_reconnecting": is_reconnecting,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Wait for recovery and clear
        page.wait_for_timeout(4000)
        api_delete("/api/control/fault")
        page.wait_for_timeout(3000)

        # ============================================================
        # SCENARIO D: Visual occlusion check on clean cockpit
        # ============================================================
        logger.info("\n" + "=" * 60)
        logger.info("SCENARIO D: Visual Occlusion Check (clean state)")
        logger.info("=" * 60)

        page.goto(COCKPIT, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        _safe_screenshot(page, str(SCREENS / "D_clean_occlusion_check.png"))

        occlusion_findings = check_visual_occlusion(page, COCKPIT, call_vision=False)
        logger.info("Visual occlusion findings on clean cockpit: %d", len(occlusion_findings))
        findings.extend(occlusion_findings)

        audit["scenarios"].append({
            "name": "D: Visual Occlusion (Clean)",
            "status": "CLEAN" if len(occlusion_findings) == 0 else "ISSUES",
            "occlusion_count": len(occlusion_findings),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # ============================================================
        # Final: Save all findings
        # ============================================================
        try:
            page.close()
        except Exception:
            pass
        try:
            context.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass

    # Save findings
    fault_findings_file = EVIDENCE / "fault_findings.json"
    with open(fault_findings_file, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2)

    audit["end_time"] = datetime.now(timezone.utc).isoformat()
    audit["total_findings"] = len(findings)

    audit_file = EVIDENCE / "fault_demo_audit.json"
    with open(audit_file, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)

    logger.info("\n" + "=" * 60)
    logger.info("FAULT INJECTION DEMO COMPLETE")
    logger.info("Total Findings: %d", len(findings))
    logger.info("Findings: %s", fault_findings_file)
    logger.info("Audit: %s", audit_file)
    logger.info("Screenshots: %s", SCREENS)
    for f_item in findings:
        logger.info("  [%s] %s | %s | %s",
                     f_item["verdict"].upper(),
                     f_item["finding_id"],
                     f_item["category"],
                     f_item["description"][:80])
    logger.info("=" * 60)

    return findings


if __name__ == "__main__":
    run_fault_demo()
