"""
Staleness & Freeze Primitive
Category: staleness
Detects stale telemetry (dashes, NaN), frozen video, out-of-order data.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import hashlib
import math


# Telemetry field names that should show live numeric values
TELEMETRY_FIELD_KEYWORDS = [
    "battery", "altitude", "speed", "heading", "wind",
    "distance", "temperature", "voltage", "satellites",
    "h-speed", "v-speed", "rl", "agl", "asl"
]

# Live indicators in labels
LIVE_KEYWORDS = ["live", "real-time", "online", "connected", "fps", "streaming"]

# Stale value patterns
STALE_PATTERNS = ["—", "–", "-", "n/a", "na", "null", "none", "waiting", "loading", "..."]


def _normalize(text: str) -> str:
    return text.lower().strip()


def _is_stale_value(text: str) -> bool:
    """Check if a value appears stale (dashes, N/A, etc.)"""
    t = _normalize(text)
    return any(p in t for p in STALE_PATTERNS)


def _is_numeric(text: str) -> bool:
    """Check if text represents a valid number"""
    t = _normalize(text).replace(",", "").replace("°", "").replace("m/s", "").replace("m", "").replace("%", "")
    try:
        float(t)
        return True
    except ValueError:
        return False


def _has_live_claim(label: str) -> bool:
    """Check if label claims to be live/real-time"""
    return _contains_any(label, LIVE_KEYWORDS)


def _contains_any(text: str, keywords: List[str]) -> bool:
    t = _normalize(text)
    return any(k in t for k in keywords)


def _generate_finding_id(category: str, element_id: str) -> str:
    suffix = hashlib.md5(f"{category}:{element_id}".encode()).hexdigest()[:6]
    return f"MIRA-{category.upper()}-{suffix}"


def _find_telemetry_elements(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter elements that are likely telemetry fields"""
    telemetry = []
    for e in elements:
        name = _normalize(e.get("name", ""))
        role = _normalize(e.get("role", ""))
        # Telemetry typically shown as text/definition terms
        if role in ("text", "definition", "term", "heading", "cell", "gridcell"):
            if _contains_any(name, TELEMETRY_FIELD_KEYWORDS):
                telemetry.append(e)
    return telemetry


def _find_video_livefields(livefields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find livefields that are video-related and claim freshness"""
    video_fields = []
    for lf in livefields:
        label = _normalize(lf.get("label_text", ""))
        if ("fpv" in label or "video" in label or "stream" in label) and lf.get("freshness_claim", False):
            video_fields.append(lf)
    return video_fields


def check_staleness(
    elements: List[Dict[str, Any]],
    livefields: List[Dict[str, Any]],
    page_url: str,
    prev_livefields: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Check for stale telemetry, frozen video, and data dropouts.
    
    Args:
        elements: Accessibility elements with role, name, page_url, bbox
        livefields: Live field regions with label_text, last_value_hash, 
                    last_changed_ts, freshness_claim
        page_url: Current page URL
        prev_livefields: Previous snapshot for delta comparison (optional)
        
    Returns:
        List of Finding dicts matching COWORK.md schema
    """
    findings = []
    current_time = datetime.now(timezone.utc).timestamp()
    
    # Filter to current page
    page_elements = [e for e in elements if e.get("page_url") == page_url]
    page_livefields = [lf for lf in livefields if lf.get("page_url") == page_url]
    
    # Create lookup for previous livefields by id
    prev_lookup = {}
    if prev_livefields:
        for lf in prev_livefields:
            prev_lookup[lf.get("id")] = lf
    
    # --- Check 1: Telemetry Staleness (dashes, NaN, missing values) ---
    telemetry_elements = _find_telemetry_elements(page_elements)
    
    for elem in telemetry_elements:
        name = elem.get("name", "")
        elem_id = elem.get("id", name)
        
        # Check if this telemetry field shows a stale value
        # The value might be in the name itself (e.g., "Battery —") or in a sibling
        value_text = name  # In accessibility tree, value often in name
        
        if _is_stale_value(value_text):
            finding = {
                "finding_id": _generate_finding_id("staleness", elem_id),
                "category": "staleness",
                "verdict": "bug",
                "confidence": 0.9,
                "description": (
                    f"Telemetry field '{name}' displays stale placeholder value "
                    f"('{value_text}') instead of live numeric data."
                ),
                "target_url": page_url,
                "element_id": elem_id,
                "evidence": {
                    "screenshot_path": "",
                    "video_path": "",
                    "reasoning": (
                        f"Element '{name}' shows stale pattern. Expected live numeric "
                        "telemetry (battery %, altitude m, speed m/s, etc.)"
                    ),
                    "telemetry_diff": {"field": name, "observed": value_text, "expected": "numeric value"}
                },
                "reproduction_steps": [
                    f"Navigate to {page_url}",
                    f"Locate telemetry field '{name}'",
                    f"Observe value shows '{value_text}' instead of live number",
                    "Verify socket connection is active (badge shows 'connected')"
                ],
                "discovered_at": datetime.now(timezone.utc).isoformat()
            }
            findings.append(finding)
    
    # --- Check 2: Video Freeze Detection ---
    video_fields = _find_video_livefields(page_livefields)
    
    for vf in video_fields:
        vf_id = vf.get("id", "video_field")
        current_hash = vf.get("last_value_hash", "")
        last_changed = vf.get("last_changed_ts", 0)
        label = vf.get("label_text", "video")
        
        # Check if hash unchanged for >5 seconds while claiming to be live
        time_since_change = current_time - last_changed if last_changed > 0 else float('inf')
        
        # Also compare with previous snapshot
        prev_hash = None
        if vf_id in prev_lookup:
            prev_hash = prev_lookup[vf_id].get("last_value_hash")
        
        is_frozen = False
        freeze_reason = ""
        
        if prev_hash and current_hash == prev_hash and time_since_change > 5:
            is_frozen = True
            freeze_reason = f"Hash unchanged for {time_since_change:.1f}s (prev: {prev_hash[:8]}, current: {current_hash[:8]})"
        elif time_since_change > 10 and current_hash:
            is_frozen = True
            freeze_reason = f"No hash update for {time_since_change:.1f}s"
        
        if is_frozen:
            finding = {
                "finding_id": _generate_finding_id("staleness", vf_id),
                "category": "staleness",
                "verdict": "bug",
                "confidence": 0.85,
                "description": (
                    f"Video tile '{label}' claims to be live (freshness_claim=True) "
                    f"but video frames appear frozen. {freeze_reason}"
                ),
                "target_url": page_url,
                "element_id": vf_id,
                "evidence": {
                    "screenshot_path": "",
                    "video_path": "",
                    "reasoning": (
                        "Video livefield has freshness_claim=True (label contains 'live' "
                        "or 'streaming') but last_value_hash has not changed, indicating "
                        "frozen frames or stalled stream."
                    ),
                    "telemetry_diff": {
                        "field": "video_stream",
                        "hash_unchanged_duration_sec": time_since_change,
                        "label": label
                    }
                },
                "reproduction_steps": [
                    f"Navigate to {page_url}",
                    "Wait for video to start playing (badge shows 'live')",
                    "Inject video-freeze fault via Control API",
                    "Observe video tile badge still shows 'live' while frames are frozen"
                ],
                "discovered_at": datetime.now(timezone.utc).isoformat()
            }
            findings.append(finding)
    
    # --- Check 3: Telemetry Dropout / Stale Data ---
    # Check livefields that claim freshness but haven't updated recently
    for lf in page_livefields:
        if not lf.get("freshness_claim", False):
            continue
            
        lf_id = lf.get("id", "livefield")
        label = lf.get("label_text", "")
        last_changed = lf.get("last_changed_ts", 0)
        current_hash = lf.get("last_value_hash", "")
        
        time_since_change = current_time - last_changed if last_changed > 0 else float('inf')
        
        # Check against previous snapshot
        prev_hash = None
        if lf_id in prev_lookup:
            prev_hash = prev_lookup[lf_id].get("last_value_hash")
        
        # Stale if: claiming live but no update for >8 seconds
        # Or hash same as previous run (for incremental runs)
        is_stale = False
        stale_reason = ""
        
        if prev_hash and current_hash == prev_hash and time_since_change > 5:
            is_stale = True
            stale_reason = f"Hash identical to previous run ({current_hash[:8]}), no update for {time_since_change:.1f}s"
        elif time_since_change > 8:
            is_stale = True
            stale_reason = f"No update for {time_since_change:.1f}s despite freshness claim"
        
        if is_stale:
            # Don't double-report video freezes (already caught above)
            is_video = any(k in _normalize(label) for k in ["fpv", "video", "stream"])
            if is_video:
                continue
                
            finding = {
                "finding_id": _generate_finding_id("staleness", lf_id),
                "category": "staleness",
                "verdict": "bug",
                "confidence": 0.8,
                "description": (
                    f"Live telemetry field '{label}' claims freshness but shows stale data. "
                    f"{stale_reason}"
                ),
                "target_url": page_url,
                "element_id": lf_id,
                "evidence": {
                    "screenshot_path": "",
                    "video_path": "",
                    "reasoning": (
                        "Livefield has freshness_claim=True (label suggests live/real-time/online) "
                        "but last_value_hash indicates no recent updates."
                    ),
                    "telemetry_diff": {
                        "field": label,
                        "last_changed_ts": last_changed,
                        "time_since_change_sec": time_since_change,
                        "hash": current_hash[:8] if current_hash else None
                    }
                },
                "reproduction_steps": [
                    f"Navigate to {page_url}",
                    "Wait for telemetry to stabilize",
                    "Inject socket-drop or socket-delay fault via Control API",
                    f"Observe '{label}' shows stale data while badge claims live"
                ],
                "discovered_at": datetime.now(timezone.utc).isoformat()
            }
            findings.append(finding)
    
    # --- Check 4: Out-of-Order Telemetry (if we have sequence info) ---
    # This would require socket.io message sequence numbers - not in current contract
    # Placeholder for future enhancement
    
    return findings


if __name__ == "__main__":
    # Quick test
    mock_elements = [
        {"id": "el_1", "role": "text", "name": "Battery —", "page_url": "http://localhost:4010", "bbox": {}},
        {"id": "el_2", "role": "text", "name": "Altitude RLT 0.0 m", "page_url": "http://localhost:4010", "bbox": {}},
        {"id": "el_3", "role": "text", "name": "H-Speed —", "page_url": "http://localhost:4010", "bbox": {}},
    ]
    mock_livefields = [
        {"id": "lf_vid", "page_url": "http://localhost:4010", "label_text": "FPV Drone 1 live", "freshness_claim": True, "last_value_hash": "abc123", "last_changed_ts": datetime.now(timezone.utc).timestamp() - 20, "region_bbox": {}},
        {"id": "lf_bat", "page_url": "http://localhost:4010", "label_text": "Battery live", "freshness_claim": True, "last_value_hash": "def456", "last_changed_ts": datetime.now(timezone.utc).timestamp() - 15, "region_bbox": {}},
    ]
    
    results = check_staleness(mock_elements, mock_livefields, "http://localhost:4010")
    for r in results:
        print(f"Finding: {r['finding_id']} - {r['verdict']} - {r['description'][:100]}...")