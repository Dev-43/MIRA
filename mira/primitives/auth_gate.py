"""
Auth-Gate Primitive
Category: auth_gate
Detects unauthorized access to protected cockpit views.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
import hashlib


# Indicators that a page is an auth/entry flow (not the full cockpit)
AUTH_FLOW_INDICATORS = [
    "sign in", "sign-in", "login", "log in", "join", "enter",
    "email", "password", "credentials", "authenticate"
]

# Indicators that a page is the full protected cockpit
COCKPIT_INDICATORS = [
    "flytbase cockpit", "drone telemetry", "device list",
    "takeoff", "land", "battery", "altitude", "heading",
    "fpv", "video", "map view", "2d", "3d"
]

# Navigation elements that should be protected
PROTECTED_NAV_ROLES = ["link", "button"]
PROTECTED_NAV_NAMES = ["control panel", "dashboard", "settings", "admin"]


def _normalize(text: str) -> str:
    return text.lower().strip()


def _contains_any(text: str, keywords: List[str]) -> bool:
    t = _normalize(text)
    return any(k in t for k in keywords)


def _generate_finding_id(category: str, element_id: str) -> str:
    """Generate consistent finding ID"""
    suffix = hashlib.md5(f"{category}:{element_id}".encode()).hexdigest()[:6]
    return f"MIRA-{category.upper()}-{suffix}"


def check_auth_gate(
    elements: List[Dict[str, Any]],
    livefields: List[Dict[str, Any]],
    page_url: str
) -> List[Dict[str, Any]]:
    """
    Check if protected cockpit views are accessible without authentication.
    
    Args:
        elements: List of accessibility elements with role, name, page_url, bbox
        livefields: List of live field regions with label_text, freshness_claim
        page_url: Current page URL being analyzed
        
    Returns:
        List of Finding dicts matching the COWORK.md schema
    """
    findings = []
    
    # Check 1: Current page content analysis
    page_elements = [e for e in elements if e.get("page_url") == page_url]
    page_livefields = [lf for lf in livefields if lf.get("page_url") == page_url]
    
    all_text = " ".join([
        _normalize(e.get("name", "")) for e in page_elements
    ] + [
        _normalize(lf.get("label_text", "")) for lf in page_livefields
    ])
    
    is_auth_flow = _contains_any(all_text, AUTH_FLOW_INDICATORS)
    is_cockpit = _contains_any(all_text, COCKPIT_INDICATORS)
    
    # If we're on a cockpit page but see auth flow indicators, that's expected
    # If we're on a cockpit page AND see cockpit indicators WITHOUT auth flow, check if auth was bypassed
    if is_cockpit and not is_auth_flow:
        # Check if there are any auth-related elements visible (should not be on protected page)
        auth_elements = [
            e for e in page_elements
            if e.get("role") in ("textbox", "button", "link") and
            _contains_any(e.get("name", ""), AUTH_FLOW_INDICATORS)
        ]
        
        # If no auth elements but we have cockpit, verify this is a real session
        # by checking for session indicators (socket connected badge, live data)
        has_session_indicators = any(
            lf.get("freshness_claim", False) for lf in page_livefields
        )
        
        if not has_session_indicators:
            # Potential unauthorized access - but could be valid if no auth exists
            # Check for explicit "join" or "enter" flow elements
            join_elements = [
                e for e in page_elements
                if e.get("role") in ("button", "link") and
                _contains_any(e.get("name", ""), ["join", "enter", "start"])
            ]
            
            if not join_elements:
                finding = {
                    "finding_id": _generate_finding_id("auth_gate", page_url),
                    "category": "auth_gate",
                    "verdict": "security_violation",
                    "confidence": 0.85,
                    "description": (
                        f"Full cockpit UI accessible at {page_url} without visible "
                        "authentication/entry flow. No session indicators (live badges, "
                        "real-time data) detected. This may indicate missing auth gate."
                    ),
                    "target_url": page_url,
                    "element_id": None,
                    "evidence": {
                        "screenshot_path": "",
                        "video_path": "",
                        "reasoning": (
                            "Cockpit indicators present (telemetry, map, video) but no "
                            "authentication flow elements found. No live data freshness "
                            "claims detected in livefields."
                        ),
                        "telemetry_diff": None
                    },
                    "reproduction_steps": [
                        f"Navigate directly to {page_url}",
                        "Observe full cockpit dashboard loads without login/join prompt",
                        "Check for socket connected badge and live telemetry",
                        "Verify no authentication redirect occurs"
                    ],
                    "discovered_at": datetime.now(timezone.utc).isoformat()
                }
                findings.append(finding)
    
    # Check 2: Protected navigation elements accessible without auth
    # Look for navigation links/buttons that should lead to protected areas
    for element in page_elements:
        role = _normalize(element.get("role", ""))
        name = _normalize(element.get("name", ""))
        
        if role in PROTECTED_NAV_ROLES and _contains_any(name, PROTECTED_NAV_NAMES):
            # This nav element should lead to protected area
            # If we're already on a protected page, this is expected
            if not is_cockpit and not is_auth_flow:
                finding = {
                    "finding_id": _generate_finding_id("auth_gate", element.get("id", name)),
                    "category": "auth_gate",
                    "verdict": "needs_review",
                    "confidence": 0.7,
                    "description": (
                        f"Navigation element '{element.get('name')}' (role: {role}) "
                        f"leads to potentially protected area but current page shows "
                        "no auth flow. Verify if this should be gated."
                    ),
                    "target_url": page_url,
                    "element_id": element.get("id"),
                    "evidence": {
                        "screenshot_path": "",
                        "video_path": "",
                        "reasoning": "Navigation element found that typically requires authentication",
                        "telemetry_diff": None
                    },
                    "reproduction_steps": [
                        f"Navigate to {page_url}",
                        f"Locate element '{element.get('name')}'",
                        "Click/activate element",
                        "Verify if authentication is required"
                    ],
                    "discovered_at": datetime.now(timezone.utc).isoformat()
                }
                findings.append(finding)
    
    # Check 3: Direct URL access test (informational - requires runner to execute)
    # This finding documents the test that should be performed
    if is_cockpit:
        finding = {
            "finding_id": _generate_finding_id("auth_gate", f"direct_access_{page_url}"),
            "category": "auth_gate",
            "verdict": "needs_review",
            "confidence": 0.6,
            "description": (
                f"Direct access test recommended for {page_url}. "
                "Verify that accessing cockpit URL in fresh browser session "
                "redirects to auth/join flow."
            ),
            "target_url": page_url,
            "element_id": None,
            "evidence": {
                "screenshot_path": "",
                "video_path": "",
                "reasoning": "Automated direct-access test should be run by test runner",
                "telemetry_diff": None
            },
            "reproduction_steps": [
                "Open new incognito/private browser window",
                f"Navigate directly to {page_url}",
                "Observe if redirected to login/join page or if cockpit loads",
                "If cockpit loads, verify session persistence or auth bypass"
            ],
            "discovered_at": datetime.now(timezone.utc).isoformat()
        }
        findings.append(finding)
    
    return findings


if __name__ == "__main__":
    # Quick test with mock data
    mock_elements = [
        {"id": "el_1", "role": "heading", "name": "FlytBase Cockpit", "page_url": "http://localhost:4010", "bbox": {}},
        {"id": "el_2", "role": "text", "name": "Battery 100%", "page_url": "http://localhost:4010", "bbox": {}},
        {"id": "el_3", "role": "link", "name": "Control panel →", "page_url": "http://localhost:4010", "bbox": {}},
    ]
    mock_livefields = [
        {"id": "lf_1", "page_url": "http://localhost:4010", "label_text": "socket connected", "freshness_claim": True, "region_bbox": {}, "last_value_hash": "abc", "last_changed_ts": 0}
    ]
    
    results = check_auth_gate(mock_elements, mock_livefields, "http://localhost:4010")
    for r in results:
        print(f"Finding: {r['finding_id']} - {r['verdict']} - {r['description'][:80]}...")