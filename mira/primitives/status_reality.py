"""Status Reality Primitive for MIRA-Web.

Category: status_reality
Cross-references status indicators/badges claiming operational state
(e.g., 'Connected', 'ARMED', 'Online', 'Streaming') against actual visual
activity and telemetry updates using the Multimodal Vision Judge.
"""

from __future__ import annotations
import hashlib
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

logger = logging.getLogger("mira.primitives.status_reality")

STATUS_CLAIM_KEYWORDS = [
    "connected", "online", "armed", "active", "streaming",
    "ready", "flying", "in flight", "hovering", "operational"
]

DISCONNECTED_KEYWORDS = [
    "disconnected", "offline", "disarmed", "stopped", "lost", "reconnecting", "error"
]


def _normalize(text: str) -> str:
    return text.lower().strip()


def _generate_finding_id(category: str, element_id: str) -> str:
    suffix = hashlib.md5(f"{category}:{element_id}".encode()).hexdigest()[:6]
    return f"MIRA-{category.upper()}-{suffix}"


def check_status_reality(
    elements: List[Dict[str, Any]],
    livefields: List[Dict[str, Any]],
    page_url: str,
    screenshot_bytes: Optional[bytes] = None,
    call_vision: bool = True,
) -> List[Dict[str, Any]]:
    """Check for discrepancy between claimed status badges and visual reality.

    Args:
        elements: List of discovered elements on page
        livefields: List of discovered LiveFields on page
        page_url: Target URL
        screenshot_bytes: Full page screenshot bytes for multimodal inspection
        call_vision: Whether to invoke Gemini Vision Judge

    Returns:
        List of Finding dicts matching standard finding schema
    """
    findings: List[Dict[str, Any]] = []

    page_elements = [e for e in elements if e.get("page_url") == page_url]
    page_livefields = [lf for lf in livefields if lf.get("page_url") == page_url]

    # 1. Identify status elements
    status_elements = []
    for el in page_elements:
        name = _normalize(el.get("name", ""))
        role = _normalize(el.get("role", ""))

        is_status_role = role in ("status", "badge")
        claims_status = any(k in name for k in STATUS_CLAIM_KEYWORDS + DISCONNECTED_KEYWORDS)

        if is_status_role or claims_status:
            status_elements.append(el)

    if not status_elements:
        return findings

    # Evaluate dynamic activity on page
    now_ts = datetime.now(timezone.utc).timestamp()
    has_active_livefields = any(
        (now_ts - lf.get("last_changed_ts", 0)) < 8.0
        for lf in page_livefields
    )

    for el in status_elements:
        name = el.get("name", "")
        norm_name = _normalize(name)
        el_id = el.get("id", name)

        claims_active = any(k in norm_name for k in STATUS_CLAIM_KEYWORDS)
        claims_offline = any(k in norm_name for k in DISCONNECTED_KEYWORDS)

        if claims_active and page_livefields and not has_active_livefields:
            # Badge claims healthy/active, but zero live fields are updating
            observed_behavior = "All dynamic livefields on page have stopped changing for >8 seconds"

            verdict = "bug"
            confidence = 0.85
            reasoning = (
                f"Status element '{name}' claims active state ('{name}'), "
                f"but {len(page_livefields)} livefields report no updates."
            )

            # Multimodal verification if screenshot is available
            if call_vision and screenshot_bytes:
                ctx = {
                    "region_description": f"Status badge '{name}'",
                    "claimed_state": name,
                    "observed_change": observed_behavior,
                }
                judge_result = vision_judge.judge(screenshot_bytes, ctx)
                if judge_result.get("verdict") == "contradicted":
                    confidence = max(confidence, judge_result.get("confidence", 0.9))
                    reasoning = judge_result.get("reasoning", reasoning)
                elif judge_result.get("verdict") == "supported":
                    # Vision judge confirmed visual reality is actually okay (false positive filter)
                    continue

            finding = {
                "finding_id": _generate_finding_id("status_reality", el_id),
                "category": "status_reality",
                "verdict": verdict,
                "confidence": confidence,
                "description": (
                    f"Status indicator '{name}' claims active status but underlying telemetry/visual "
                    "canvas displays no updates or conflicting physical state."
                ),
                "target_url": page_url,
                "element_id": el_id,
                "evidence": {
                    "screenshot_path": "",
                    "video_path": "",
                    "reasoning": reasoning,
                    "telemetry_diff": {
                        "badge_text": name,
                        "livefields_monitored": len(page_livefields),
                        "active_livefields": 0,
                    },
                },
                "reproduction_steps": [
                    f"Navigate to {page_url}",
                    f"Observe status badge '{name}'",
                    "Observe underlying video or telemetry displays frozen/stale data",
                    "Verify discrepancy between badge and actual state",
                ],
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            }
            findings.append(finding)

    return findings


if __name__ == "__main__":
    # Test on healthy mock vs broken mock
    healthy_elements = [
        {"id": "el_stat_1", "role": "status", "name": "Socket Connected", "page_url": "http://localhost:4010", "bbox": {}},
    ]
    healthy_livefields = [
        {"id": "lf_1", "page_url": "http://localhost:4010", "last_changed_ts": datetime.now(timezone.utc).timestamp(), "freshness_claim": True},
    ]

    healthy_res = check_status_reality(healthy_elements, healthy_livefields, "http://localhost:4010", call_vision=False)
    print("Healthy findings count (expect 0):", len(healthy_res))

    broken_livefields = [
        {"id": "lf_1", "page_url": "http://localhost:4010", "last_changed_ts": datetime.now(timezone.utc).timestamp() - 20, "freshness_claim": True},
    ]
    broken_res = check_status_reality(healthy_elements, broken_livefields, "http://localhost:4010", call_vision=False)
    print("Broken findings count (expect 1):", len(broken_res))
    if broken_res:
        print("Finding:", broken_res[0]["finding_id"], broken_res[0]["verdict"])
