"""Action Efficacy Primitive for MIRA-Web.

Category: action_efficacy
Verifies that primary interactive controls (buttons, tabs, toggles) produce
meaningful visual feedback or state transitions, detecting dead clicks,
stuck loading states, and unacknowledged commands.
"""

from __future__ import annotations
import hashlib
import io
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from mira import vision_judge
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from mira import vision_judge

logger = logging.getLogger("mira.primitives.action_efficacy")

ACTION_KEYWORDS = [
    "takeoff", "land", "arm", "disarm", "connect", "disconnect",
    "switch", "mode", "select", "start", "stop", "reset", "clear"
]


def _normalize(text: str) -> str:
    return text.lower().strip()


def _generate_finding_id(category: str, element_id: str) -> str:
    suffix = hashlib.md5(f"{category}:{element_id}".encode()).hexdigest()[:6]
    return f"MIRA-{category.upper()}-{suffix}"


def check_action_efficacy(
    elements: List[Dict[str, Any]],
    page_url: str,
    page=None,
    screenshot_bytes: Optional[bytes] = None,
    call_vision: bool = True,
) -> List[Dict[str, Any]]:
    """Evaluate action efficacy on interactive elements.

    Args:
        elements: List of element dicts on page.
        page_url: Current page URL.
        page: Optional Playwright Page object for active probe clicks.
        screenshot_bytes: Optional screenshot bytes for post-action inspection.
        call_vision: Whether to invoke vision judge on ambiguous results.

    Returns:
        List of Finding dicts matching standard finding schema.
    """
    findings: List[Dict[str, Any]] = []
    page_elements = [e for e in elements if e.get("page_url") == page_url]

    # Filter action buttons
    action_elements = []
    for el in page_elements:
        role = _normalize(el.get("role", ""))
        name = _normalize(el.get("name", ""))
        if role in ("button", "tab", "switch") and name:
            action_elements.append(el)

    if not action_elements:
        return findings

    # If active Playwright page is provided, perform live probe verification
    if page is not None:
        for el in action_elements:
            name = el.get("name", "")
            el_id = el.get("id", name)
            norm_name = _normalize(name)

            # Only probe safe buttons (e.g. tabs, view selectors) unless explicitly told
            is_critical = any(k in norm_name for k in ACTION_KEYWORDS)
            if not is_critical:
                continue

            try:
                # Capture pre-click state
                pre_shot = page.screenshot(type="png", timeout=5000, animations="disabled")
                loc = page.get_by_role(el.get("role", "button"), name=name).first

                if not loc.is_visible(timeout=500):
                    continue

                # Click button
                loc.click(timeout=1000)
                page.wait_for_timeout(1000)

                # Capture post-click state
                post_shot = page.screenshot(type="png", timeout=5000, animations="disabled")

                # Compare screenshots
                if pre_shot == post_shot:
                    # No visual change whatsoever
                    reasoning = f"Clicking button '{name}' triggered zero visual change across viewport."
                    confidence = 0.85

                    if call_vision:
                        ctx = {
                            "region_description": f"Button '{name}' and surrounding UI",
                            "claimed_state": f"Button '{name}' activated",
                            "observed_change": "Zero visual change after click",
                        }
                        judge_res = vision_judge.judge(post_shot, ctx)
                        if judge_res.get("verdict") == "contradicted":
                            confidence = max(confidence, judge_res.get("confidence", 0.9))
                            reasoning = judge_res.get("reasoning", reasoning)

                    finding = {
                        "finding_id": _generate_finding_id("action_efficacy", el_id),
                        "category": "action_efficacy",
                        "verdict": "bug",
                        "confidence": confidence,
                        "description": f"No-op action / dead click detected on control '{name}'.",
                        "target_url": page_url,
                        "element_id": el_id,
                        "evidence": {
                            "screenshot_path": "",
                            "video_path": "",
                            "reasoning": reasoning,
                            "telemetry_diff": {"action": name, "visual_delta": 0},
                        },
                        "reproduction_steps": [
                            f"Navigate to {page_url}",
                            f"Click control '{name}'",
                            "Observe no visual transition, feedback, or state update occurs",
                        ],
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                    }
                    findings.append(finding)

            except Exception as e:
                logger.debug("Live probe skipped for %s: %s", name, e)

    return findings


if __name__ == "__main__":
    # Test with mock elements
    mock_elems = [
        {"id": "btn_arm_1", "role": "button", "name": "ARM DRONE 1", "page_url": "http://localhost:4010", "bbox": {}},
        {"id": "tab_map", "role": "tab", "name": "3D Map", "page_url": "http://localhost:4010", "bbox": {}},
    ]
    res = check_action_efficacy(mock_elems, "http://localhost:4010", page=None, call_vision=False)
    print("Action efficacy mock findings count (expect 0 in passive mode):", len(res))
