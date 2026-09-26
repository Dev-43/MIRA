"""
Responsive Reachability Primitive
Category: responsive_reachability
Detects critical actions clipped, obscured, or unreachable at mobile viewport (375x667).
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib


# High-priority action keywords that must remain accessible
CRITICAL_ACTION_KEYWORDS = [
    "takeoff", "take off", "land", "arm", "disarm",
    "control panel", "dashboard", "settings", "menu",
    "device", "drone", "select", "connect", "disconnect",
    "start", "stop", "reset", "emergency", "return",
    "home", "pause", "resume", "mode", "flight"
]

# Interactive roles that must be reachable
INTERACTIVE_ROLES = [
    "button", "link", "menuitem", "tab", "checkbox",
    "radio", "slider", "spinbutton", "textbox", "combobox"
]

# Elements that indicate responsive issues
RESPONSIVE_ISSUE_INDICATORS = [
    "overflow", "scroll", "hidden", "clipped", "truncated",
    "ellipsis", "...", "more", "expand", "collapse"
]


def _normalize(text: str) -> str:
    return text.lower().strip()


def _contains_any(text: str, keywords: List[str]) -> bool:
    t = _normalize(text)
    return any(k in t for k in keywords)


def _is_critical_action(name: str, role: str) -> bool:
    """Check if element is a high-priority action"""
    if _normalize(role) not in INTERACTIVE_ROLES:
        return False
    return _contains_any(name, CRITICAL_ACTION_KEYWORDS)


def _generate_finding_id(category: str, element_id: str) -> str:
    suffix = hashlib.md5(f"{category}:{element_id}".encode()).hexdigest()[:6]
    return f"MIRA-{category.upper()}-{suffix}"


def _bbox_fully_visible(bbox: Dict[str, float], viewport_w: int, viewport_h: int) -> bool:
    """Check if bounding box is fully within viewport"""
    x = bbox.get("x", 0)
    y = bbox.get("y", 0)
    w = bbox.get("width", 0)
    h = bbox.get("height", 0)
    
    return (x >= 0 and y >= 0 and 
            x + w <= viewport_w and 
            y + h <= viewport_h)


def _bbox_partially_visible(bbox: Dict[str, float], viewport_w: int, viewport_h: int) -> bool:
    """Check if any part of bounding box is within viewport"""
    x = bbox.get("x", 0)
    y = bbox.get("y", 0)
    w = bbox.get("width", 0)
    h = bbox.get("height", 0)
    
    right = x + w
    bottom = y + h
    
    return not (right <= 0 or bottom <= 0 or x >= viewport_w or y >= viewport_h)


def _get_visible_area_ratio(bbox: Dict[str, float], viewport_w: int, viewport_h: int) -> float:
    """Calculate ratio of element visible in viewport (0.0 to 1.0)"""
    x = bbox.get("x", 0)
    y = bbox.get("y", 0)
    w = bbox.get("width", 0)
    h = bbox.get("height", 0)
    
    if w <= 0 or h <= 0:
        return 0.0
    
    visible_x = max(0, min(x + w, viewport_w) - max(x, 0))
    visible_y = max(0, min(y + h, viewport_h) - max(y, 0))
    
    visible_area = visible_x * visible_y
    total_area = w * h
    
    return min(1.0, visible_area / total_area) if total_area > 0 else 0.0


def _check_overlap(elem_bbox: Dict[str, float], other_elements: List[Dict[str, Any]], 
                   exclude_id: str) -> bool:
    """Check if element overlaps with other interactive elements"""
    x1 = elem_bbox.get("x", 0)
    y1 = elem_bbox.get("y", 0)
    w1 = elem_bbox.get("width", 0)
    h1 = elem_bbox.get("height", 0)
    r1 = x1 + w1
    b1 = y1 + h1
    
    if w1 <= 0 or h1 <= 0:
        return False
    
    for other in other_elements:
        if other.get("id") == exclude_id:
            continue
        other_role = _normalize(other.get("role", ""))
        if other_role not in INTERACTIVE_ROLES:
            continue
            
        obbox = other.get("bbox", {})
        if not obbox:
            continue
            
        x2 = obbox.get("x", 0)
        y2 = obbox.get("y", 0)
        w2 = obbox.get("width", 0)
        h2 = obbox.get("height", 0)
        
        if w2 <= 0 or h2 <= 0:
            continue
            
        r2 = x2 + w2
        b2 = y2 + h2
        
        # Check overlap
        if not (r1 <= x2 or r2 <= x1 or b1 <= y2 or b2 <= y1):
            return True
    
    return False


def check_responsive_reachability(
    elements: List[Dict[str, Any]],
    viewport_width: int = 375,
    viewport_height: int = 667
) -> List[Dict[str, Any]]:
    """
    Check if critical actions are reachable at mobile viewport.
    
    Args:
        elements: Accessibility elements with role, name, page_url, bbox
        viewport_width: Viewport width (default 375 for iPhone SE)
        viewport_height: Viewport height (default 667 for iPhone SE)
        
    Returns:
        List of Finding dicts matching COWORK.md schema
    """
    findings = []
    
    # Filter interactive elements
    interactive_elements = [
        e for e in elements 
        if _normalize(e.get("role", "")) in INTERACTIVE_ROLES
    ]
    
    # Identify critical actions
    critical_actions = [
        e for e in interactive_elements 
        if _is_critical_action(e.get("name", ""), e.get("role", ""))
    ]
    
    # Also check for any element that might be a primary action
    # (e.g., first button in a prominent position)
    all_buttons = [e for e in interactive_elements if _normalize(e.get("role")) == "button"]
    
    # Check each critical action
    for elem in critical_actions:
        elem_id = elem.get("id", elem.get("name", "unknown"))
        name = elem.get("name", "")
        role = elem.get("role", "")
        bbox = elem.get("bbox", {})
        page_url = elem.get("page_url", "unknown")
        
        if not bbox:
            # No position data - can't assess
            finding = {
                "finding_id": _generate_finding_id("responsive_reachability", elem_id),
                "category": "responsive_reachability",
                "verdict": "needs_review",
                "confidence": 0.4,
                "description": (
                    f"Critical action '{name}' (role: {role}) has no bounding box "
                    "data. Cannot verify mobile reachability."
                ),
                "target_url": page_url,
                "element_id": elem_id,
                "evidence": {
                    "screenshot_path": "",
                    "video_path": "",
                    "reasoning": "Missing bbox prevents reachability analysis",
                    "telemetry_diff": None
                },
                "reproduction_steps": [
                    f"Navigate to {page_url} at {viewport_width}x{viewport_height}",
                    f"Locate '{name}' element",
                    "Verify it has position data in accessibility tree"
                ],
                "discovered_at": datetime.now(timezone.utc).isoformat()
            }
            findings.append(finding)
            continue
        
        # Check visibility
        fully_visible = _bbox_fully_visible(bbox, viewport_width, viewport_height)
        partially_visible = _bbox_partially_visible(bbox, viewport_width, viewport_height)
        visible_ratio = _get_visible_area_ratio(bbox, viewport_width, viewport_height)
        
        # Check overlap with other interactive elements
        is_overlapped = _check_overlap(bbox, interactive_elements, elem_id)
        
        # Determine issue severity
        if not partially_visible:
            # Completely outside viewport
            verdict = "bug"
            confidence = 0.95
            issue_type = "completely_offscreen"
            desc = f"Critical action '{name}' is completely outside {viewport_width}x{viewport_height} viewport"
        elif not fully_visible:
            # Partially clipped
            if visible_ratio < 0.3:
                verdict = "bug"
                confidence = 0.9
                issue_type = "severely_clipped"
            elif visible_ratio < 0.6:
                verdict = "bug"
                confidence = 0.8
                issue_type = "partially_clipped"
            else:
                verdict = "needs_review"
                confidence = 0.6
                issue_type = "slightly_clipped"
            desc = f"Critical action '{name}' is {issue_type} at {viewport_width}x{viewport_height} (visible: {visible_ratio*100:.0f}%)"
        elif is_overlapped:
            # Fully visible but overlapped
            verdict = "bug"
            confidence = 0.75
            issue_type = "overlapped"
            desc = f"Critical action '{name}' is overlapped by another interactive element"
        else:
            # Fully visible and not overlapped
            continue  # No issue
        
        # Check if element is below fold (requires scrolling)
        y = bbox.get("y", 0)
        h = bbox.get("height", 0)
        below_fold = (y + h) > viewport_height
        
        finding = {
            "finding_id": _generate_finding_id("responsive_reachability", elem_id),
            "category": "responsive_reachability",
            "verdict": verdict,
            "confidence": confidence,
            "description": desc + (" (below fold, requires scroll)" if below_fold else ""),
            "target_url": page_url,
            "element_id": elem_id,
            "evidence": {
                "screenshot_path": "",
                "video_path": "",
                "reasoning": (
                    f"Element bbox: x={bbox.get('x')}, y={bbox.get('y')}, "
                    f"w={bbox.get('width')}, h={bbox.get('height')}. "
                    f"Viewport: {viewport_width}x{viewport_height}. "
                    f"Visible ratio: {visible_ratio*100:.0f}%. "
                    f"Overlapped: {is_overlapped}. Below fold: {below_fold}."
                ),
                "telemetry_diff": {
                    "viewport": f"{viewport_width}x{viewport_height}",
                    "bbox": bbox,
                    "visible_ratio": visible_ratio,
                    "fully_visible": fully_visible,
                    "overlapped": is_overlapped,
                    "below_fold": below_fold
                }
            }
        }
        
        # Add scroll requirement to reproduction steps
        steps = [
            f"Navigate to {page_url}",
            f"Set viewport to {viewport_width}x{viewport_height} (mobile)",
            f"Locate critical action '{name}' ({role})",
        ]
        if below_fold:
            steps.append("Scroll down to find element (not visible initially)")
        if is_overlapped:
            steps.append("Observe overlapping interactive element blocking access")
        steps.append(f"Verify element is {'not reachable' if verdict == 'bug' else 'reachable but clipped'}")
        
        finding["reproduction_steps"] = steps
        finding["discovered_at"] = datetime.now(timezone.utc).isoformat()
        
        findings.append(finding)
    
    # --- General responsive layout checks ---
    # Check for horizontal overflow indicators
    page_elements_by_url = {}
    for e in elements:
        url = e.get("page_url", "unknown")
        if url not in page_elements_by_url:
            page_elements_by_url[url] = []
        page_elements_by_url[url].append(e)
    
    for page_url, page_elems in page_elements_by_url.items():
        # Check for elements extending beyond viewport width
        overflow_elements = []
        for e in page_elems:
            bbox = e.get("bbox", {})
            if not bbox:
                continue
            x = bbox.get("x", 0)
            w = bbox.get("width", 0)
            if x + w > viewport_width + 10:  # 10px tolerance
                overflow_elements.append(e)
        
        if overflow_elements:
            finding = {
                "finding_id": _generate_finding_id("responsive_reachability", f"horizontal_overflow_{page_url}"),
                "category": "responsive_reachability",
                "verdict": "bug",
                "confidence": 0.85,
                "description": (
                    f"Horizontal overflow detected at {viewport_width}px viewport: "
                    f"{len(overflow_elements)} elements extend beyond viewport width. "
                    "This indicates missing responsive breakpoints or fixed-width layouts."
                ),
                "target_url": page_url,
                "element_id": overflow_elements[0].get("id") if overflow_elements else None,
                "evidence": {
                    "screenshot_path": "",
                    "video_path": "",
                    "reasoning": (
                        f"Elements found with x+width > {viewport_width}px. "
                        "Causes horizontal scrolling on mobile, breaking usability."
                    ),
                    "telemetry_diff": {
                        "viewport_width": viewport_width,
                        "overflow_count": len(overflow_elements),
                        "overflow_elements": [
                            {"id": e.get("id"), "name": e.get("name"), 
                             "x": e.get("bbox", {}).get("x"), 
                             "width": e.get("bbox", {}).get("width"),
                             "right_edge": e.get("bbox", {}).get("x", 0) + e.get("bbox", {}).get("width", 0)}
                            for e in overflow_elements[:5]
                        ]
                    }
                },
                "reproduction_steps": [
                    f"Navigate to {page_url}",
                    f"Set viewport to {viewport_width}x{viewport_height}",
                    "Observe horizontal scrollbar or content cut off",
                    "Check for elements extending beyond right edge"
                ],
                "discovered_at": datetime.now(timezone.utc).isoformat()
            }
            findings.append(finding)
        
        # Check for text truncation/clipping indicators
        truncated_elements = []
        for e in page_elems:
            name = _normalize(e.get("name", ""))
            if any(ind in name for ind in RESPONSIVE_ISSUE_INDICATORS):
                # Check if it's actually truncated (has ellipsis in name or small bbox for long text)
                bbox = e.get("bbox", {})
                if bbox and bbox.get("width", 0) < 50 and len(e.get("name", "")) > 20:
                    truncated_elements.append(e)
        
        if truncated_elements:
            finding = {
                "finding_id": _generate_finding_id("responsive_reachability", f"text_truncation_{page_url}"),
                "category": "responsive_reachability",
                "verdict": "needs_review",
                "confidence": 0.65,
                "description": (
                    f"Potential text truncation at {viewport_width}px viewport: "
                    f"{len(truncated_elements)} elements show truncation indicators. "
                    "Verify if critical information is hidden."
                ),
                "target_url": page_url,
                "element_id": truncated_elements[0].get("id") if truncated_elements else None,
                "evidence": {
                    "screenshot_path": "",
                    "video_path": "",
                    "reasoning": "Elements with truncation indicators and narrow bounding boxes",
                    "telemetry_diff": {
                        "viewport_width": viewport_width,
                        "truncated_count": len(truncated_elements),
                        "elements": [
                            {"id": e.get("id"), "name": e.get("name")[:50], 
                             "width": e.get("bbox", {}).get("width")}
                            for e in truncated_elements[:5]
                        ]
                    }
                },
                "reproduction_steps": [
                    f"Navigate to {page_url}",
                    f"Set viewport to {viewport_width}x{viewport_height}",
                    "Check for truncated text with ellipsis or '...'",
                    "Verify if truncated content is critical information"
                ],
                "discovered_at": datetime.now(timezone.utc).isoformat()
            }
            findings.append(finding)
    
    return findings


if __name__ == "__main__":
    # Quick test
    mock_elements = [
        {"id": "btn_takeoff", "role": "button", "name": "Takeoff", "page_url": "http://localhost:4010", 
         "bbox": {"x": 350, "y": 600, "width": 80, "height": 40}},
        {"id": "btn_land", "role": "button", "name": "Land", "page_url": "http://localhost:4010", 
         "bbox": {"x": 440, "y": 600, "width": 80, "height": 40}},
        {"id": "link_control", "role": "link", "name": "Control panel →", "page_url": "http://localhost:4010", 
         "bbox": {"x": 10, "y": 10, "width": 150, "height": 30}},
        {"id": "btn_settings", "role": "button", "name": "Settings", "page_url": "http://localhost:4010", 
         "bbox": {"x": 10, "y": 700, "width": 100, "height": 40}},  # Below fold
    ]
    
    results = check_responsive_reachability(mock_elements, 375, 667)
    for r in results:
        print(f"Finding: {r['finding_id']} - {r['verdict']} - {r['description'][:100]}...")