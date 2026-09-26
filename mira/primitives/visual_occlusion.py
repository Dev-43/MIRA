"""
Visual Occlusion and Collision Primitive
Category: visual_occlusion

Detects visual element occlusion, overlapping headers/banners, and unclickable
actions where standard DOM queries pass but human physical mouse clicks fail.
Uses browser hit-testing (document.elementFromPoint) and bounding box geometry.
"""

from __future__ import annotations
import hashlib
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

try:
    from mira import vision_judge
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from mira import vision_judge

logger = logging.getLogger("mira.primitives.visual_occlusion")

INTERACTIVE_TAGS = ["button", "a", "input", "select", "textarea", "li", "div"]


def _generate_finding_id(category: str, element_id: str) -> str:
    suffix = hashlib.md5(f"{category}:{element_id}".encode()).hexdigest()[:6]
    return f"MIRA-{category.upper()}-{suffix}"


def check_visual_occlusion(
    page,
    page_url: str,
    target_selectors: Optional[List[str]] = None,
    call_vision: bool = True,
    screenshot_bytes: Optional[bytes] = None,
) -> List[Dict[str, Any]]:
    """
    Probe the live page using physical coordinate hit-testing.
    For each target element, checks if document.elementFromPoint at its center
    actually hits the element, or if it is blocked by an overlapping overlay/header.
    """
    findings: List[Dict[str, Any]] = []

    if target_selectors is None:
        # Generic interactive targets if none specified
        target_selectors = [
            "button",
            "a",
            "[role='button']",
            ".device-row",
            "[data-testid*='device']",
            "[data-testid*='control']",
            ".dashboard-link",
        ]

    # Evaluate physical hit-testing in page context
    js_probe = """
    (selectors) => {
        const results = [];
        const seen = new Set();

        for (const sel of selectors) {
            const elements = document.querySelectorAll(sel);
            for (const el of elements) {
                if (!el || seen.has(el)) continue;
                seen.add(el);

                const rect = el.getBoundingClientRect();
                // Skip off-screen or invisible elements
                if (rect.width <= 4 || rect.height <= 4) continue;
                if (rect.bottom < 0 || rect.top > window.innerHeight) continue;

                const cx = rect.left + rect.width / 2;
                const cy = rect.top + rect.height / 2;

                const hitElement = document.elementFromPoint(cx, cy);
                const isDirectHit = hitElement && (hitElement === el || el.contains(hitElement) || hitElement.contains(el));

                if (!isDirectHit && hitElement) {
                    const hitRect = hitElement.getBoundingClientRect();
                    results.push({
                        target: {
                            tag: el.tagName.toLowerCase(),
                            text: (el.innerText || el.textContent || '').trim().slice(0, 60),
                            className: el.className || '',
                            id: el.id || '',
                            rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                        },
                        occluder: {
                            tag: hitElement.tagName.toLowerCase(),
                            text: (hitElement.innerText || hitElement.textContent || '').trim().slice(0, 60),
                            className: hitElement.className || '',
                            id: hitElement.id || '',
                            zIndex: window.getComputedStyle(hitElement).zIndex,
                            rect: { x: hitRect.x, y: hitRect.y, width: hitRect.width, height: hitRect.height }
                        },
                        probe_coords: { x: cx, y: cy }
                    });
                }
            }
        }
        return results;
    }
    """

    try:
        collisions = page.evaluate(js_probe, target_selectors)
    except Exception as e:
        logger.warning("Error running physical hit-test probe: %s", e)
        return []

    for col in collisions:
        target = col["target"]
        occluder = col["occluder"]
        coords = col["probe_coords"]

        target_name = target["text"] or f"<{target['tag']}.{target['className']}>"
        occluder_name = occluder["text"] or f"<{occluder['tag']}.{occluder['className']}>"

        elem_id = f"{target['tag']}_{int(coords['x'])}_{int(coords['y'])}"
        finding_id = _generate_finding_id("visual_occlusion", elem_id)

        description = (
            f"Visual Collision: Action '{target_name}' at screen coordinates ({int(coords['x'])}, {int(coords['y'])}) "
            f"is physically occluded by {occluder['tag']}.{occluder['className']} (z-index: {occluder['zIndex']}). "
            f"A human mouse click hits the overlapping layer, blocking user interaction."
        )

        # Multimodal Vision Judge corroboration
        judge_verdict = "BUG"
        if call_vision and screenshot_bytes:
            try:
                verdict = vision_judge.judge(
                    screenshot_bytes=screenshot_bytes,
                    context={
                        "region_description": f"Target action '{target_name}' at ({int(coords['x'])}, {int(coords['y'])})",
                        "claimed_state": "Element should be physically clickable and unoccluded",
                        "observed_change": f"Physically blocked by overlapping '{occluder_name}' (z-index: {occluder['zIndex']})"
                    }
                )
                if verdict.get("verdict") == "contradicted":
                    judge_verdict = "BUG"
                else:
                    judge_verdict = verdict.get("verdict", "BUG").upper()
            except Exception as e:
                logger.warning("Vision judge check skipped: %s", e)

        finding = {
            "finding_id": finding_id,
            "category": "visual_occlusion",
            "severity": "HIGH",
            "verdict": judge_verdict,
            "target_url": page_url,
            "element_id": elem_id,
            "description": description,
            "evidence": {
                "target_element": target,
                "occluding_element": occluder,
                "hit_coords": coords,
                "collision_type": "physical_hit_test_mismatch",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
        findings.append(finding)

    return findings
