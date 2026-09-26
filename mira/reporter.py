"""
Hackathon Report Generator
Generates evaluation submission package from primitive findings.
"""

import json
import os
import shutil
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


CATEGORY_LABELS = {
    "auth_gate": "Authentication / Access Control",
    "staleness": "Data Staleness / Freeze Detection",
    "responsive_reachability": "Responsive Layout / Mobile Reachability",
    "status_reality": "Status Badge vs Reality",
    "action_efficacy": "Action Efficacy / Command Follow-through"
}

VERDICT_LABELS = {
    "bug": "BUG",
    "security_violation": "SECURITY VIOLATION",
    "needs_review": "NEEDS REVIEW"
}

VERDICT_EMOJI = {
    "bug": "🔴",
    "security_violation": "🔴🔒",
    "needs_review": "🟡"
}


def _generate_scenario_id(category: str, index: int) -> str:
    return f"SCN-{category.upper()[:4]}-{index:03d}"


def _group_findings_by_category(findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped = {}
    for f in findings:
        cat = f.get("category", "unknown")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(f)
    return grouped


def _group_findings_by_scenario(findings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group findings by scenario based on target_url and category"""
    scenarios = {}
    for f in findings:
        # Create scenario key from URL and category
        url = f.get("target_url", "unknown")
        cat = f.get("category", "unknown")
        key = f"{cat}:{url}"
        if key not in scenarios:
            scenarios[key] = []
        scenarios[key].append(f)
    return scenarios


def generate_system_design(findings: List[Dict[str, Any]], 
                           scenarios_config: List[Dict[str, Any]] = None) -> str:
    """Generate SYSTEM_DESIGN.md content"""
    
    grouped = _group_findings_by_category(findings)
    total_findings = len(findings)
    bugs = sum(1 for f in findings if f.get("verdict") == "bug")
    security = sum(1 for f in findings if f.get("verdict") == "security_violation")
    needs_review = sum(1 for f in findings if f.get("verdict") == "needs_review")
    
    lines = [
        "# MIRA-FlytBase: Agentic Testing System - System Design",
        "",
        f"**Generated:** {_utcnow()}",
        f"**Total Findings:** {total_findings} ({bugs} bugs, {security} security, {needs_review} needs review)",
        "",
        "## Architecture Overview",
        "",
        "```",
        "┌─────────────────────────────────────────────────────────────────┐",
        "│                    MIRA-FlytBase Testing Agent                  │",
        "├─────────────────────────────────────────────────────────────────┤",
        "│                                                                 │",
        "│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐ │",
        "│  │ Playwright   │    │  Control     │    │   Primitive      │ │",
        "│  │ Explorer     │───►│  API Client  │    │   Detectors      │ │",
        "│  │ (ARIA Snap)  │    │ (Fault Inj)  │    │                  │ │",
        "│  └──────────────┘    └──────────────┘    └────────┬─────────┘ │",
        "│         │                       │                 │           │",
        "│         └───────────────────────┼─────────────────┘           │",
        "│                                 ▼                             │",
        "│                    ┌────────────────────────┐                 │",
        "│                    │   Finding Aggregator   │                 │",
        "│                    │   & Report Generator   │                 │",
        "│                    └────────────────────────┘                 │",
        "│                                                                 │",
        "└─────────────────────────────────────────────────────────────────┘",
        "```",
        "",
        "## Core Components",
        "",
        "### 1. Playwright Explorer (`mira/explorer.py` - Antigravity)",
        "- Navigates Cockpit (4010) and Control Panel (4000/dashboard)",
        "- Captures ARIA accessibility snapshots at multiple viewports (1440px, 375px, 768px)",
        "- Extracts `elements[]` (role, name, bbox) and `livefields[]` (label, hash, freshness)",
        "- Records Playwright videos per scenario",
        "",
        "### 2. Control API Client (`demo/control_client.py`)",
        "- Typed Python client for `http://localhost:4000/api/control/*`",
        "- Fault injection: `socket-kick`, `socket-refuse`, `socket-delay`, `socket-drop`, `sim-offline`, `video-freeze`, `video-stutter`, `video-degrade`, `video-flicker`",
        "- Drone commands: `takeoff`, `land`, `add_drone`, `remove_drone`",
        "- Simulator control: `start`, `stop`, `reset`, speed multiplier",
        "",
        "### 3. Primitive Detectors (OpenCode)",
        "",
    ]
    
    for cat, cat_findings in grouped.items():
        label = CATEGORY_LABELS.get(cat, cat)
        lines.append(f"#### {label} (`mira/primitives/{cat}.py`)")
        lines.append(f"**Findings:** {len(cat_findings)}")
        lines.append("")
        
        # Show unique issue types
        issue_types = set()
        for f in cat_findings:
            desc = f.get("description", "")
            # Extract issue type from description
            if "stale" in desc.lower() or "dash" in desc.lower():
                issue_types.add("Stale telemetry (dashes/NaN)")
            elif "frozen" in desc.lower() or "freeze" in desc.lower():
                issue_types.add("Video freeze with live badge")
            elif "offscreen" in desc.lower() or "clipped" in desc.lower():
                issue_types.add("Mobile viewport clipping")
            elif "overflow" in desc.lower():
                issue_types.add("Horizontal overflow")
            elif "unauthorized" in desc.lower() or "auth" in desc.lower():
                issue_types.add("Missing auth gate")
            elif "overlap" in desc.lower():
                issue_types.add("Element overlap")
            else:
                issue_types.add("Other")
        
        for issue in sorted(issue_types):
            lines.append(f"- {issue}")
        lines.append("")
    
    lines.extend([
        "### 4. Memory Graph (`mira/graph.py` - Antigravity)",
        "- Neo4j graph storing page→element mappings across runs",
        "- Enables incremental runs: Run 2+ only diffs changed elements",
        "- Self-healing: tracks element renames, additions, removals",
        "",
        "### 5. Vision Judge (`mira/vision_judge.py` - Antigravity)",
        "- Multimodal LLM (NVIDIA NIM / Gemini) for semantic visual assertions",
        "- Validates Cesium 3D canvas, WebRTC video, map entities",
        "- Prompt-based: `assert_visual(\"Is drone altitude live and visible?\")`",
        "",
        "## Mutation Detection Strategy",
        "",
        "Each scenario follows this pattern:",
        "",
        "```",
        "1. RESET: POST /api/control/sim {action: \"reset\"} → clean state",
        "2. BASELINE: Capture ARIA snapshot + screenshot + video start",
        "3. INJECT: POST /api/control/fault {kind, params} → introduce mutation",
        "4. OBSERVE: Wait for UI to reflect (2-5s), capture snapshot + screenshot",
        "5. DETECT: Run primitive detectors on before/after snapshots",
        "6. VERDICT: Vision judge confirms semantic correctness",
        "7. EVIDENCE: Package video + screenshots + findings JSON",
        "```",
        "",
        "## Scenarios Tested",
        "",
    ])
    
    if scenarios_config:
        for i, sc in enumerate(scenarios_config, 1):
            lines.append(f"### Scenario {i}: {sc.get('name', 'Unnamed')}")
            lines.append(f"**Trigger:** {sc.get('trigger', 'N/A')}")
            lines.append(f"**Expected:** {sc.get('expected', 'N/A')}")
            lines.append(f"**Mutation Detected:** {sc.get('mutation', 'N/A')}")
            lines.append("")
    else:
        # Infer from findings
        scenario_groups = _group_findings_by_scenario(findings)
        for i, (key, sc_findings) in enumerate(scenario_groups.items(), 1):
            cat, url = key.split(":", 1) if ":" in key else ("unknown", key)
            lines.append(f"### Scenario {i}: {CATEGORY_LABELS.get(cat, cat)}")
            lines.append(f"**Target:** {url}")
            lines.append(f"**Findings:** {len(sc_findings)}")
            lines.append("")
    
    lines.extend([
        "## Reproducibility",
        "",
        "- All mutations injected via Control API (deterministic, scriptable)",
        "- Simulator uses fixed seed (42) for reproducible drone positions",
        "- Playwright videos recorded for every scenario (mandatory for evaluation)",
        "- Findings include exact reproduction steps via Control API",
        "",
        "## Scalability",
        "",
        "- Parallel scenario execution via Playwright contexts",
        "- Memory graph enables O(changed) incremental runs",
        "- Vision judge batched for efficiency",
        "- Control API stateless - horizontal scaling trivial",
        "",
        "---",
        "",
        "*Generated by MIRA-FlytBase Reporter*"
    ])
    
    return "\n".join(lines)


def generate_scenario_report(findings: List[Dict[str, Any]], 
                             scenario_name: str,
                             scenario_id: str,
                             trigger: str,
                             expected: str,
                             mutation: str,
                             video_path: str = "",
                             screenshots: List[str] = None) -> str:
    """Generate individual scenario report"""
    
    if screenshots is None:
        screenshots = []
    
    lines = [
        f"# Scenario Report: {scenario_name}",
        "",
        f"**Scenario ID:** {scenario_id}",
        f"**Generated:** {_utcnow()}",
        "",
        "## Summary",
        "",
        f"**Trigger:** {trigger}",
        f"**Expected Behavior:** {expected}",
        f"**Injected Mutation:** {mutation}",
        f"**Video Evidence:** {video_path or 'Not available'}",
        "",
        "## Findings",
        "",
    ]
    
    if not findings:
        lines.append("No findings detected.")
    else:
        for i, f in enumerate(findings, 1):
            verdict = f.get("verdict", "unknown")
            conf = f.get("confidence", 0)
            desc = f.get("description", "")
            elem_id = f.get("element_id", "N/A")
            
            lines.append(f"### Finding {i}: {VERDICT_EMOJI.get(verdict, '⚪')} {VERDICT_LABELS.get(verdict, verdict.upper())}")
            lines.append(f"- **Confidence:** {conf*100:.0f}%")
            lines.append(f"- **Element:** `{elem_id}`")
            lines.append(f"- **Description:** {desc}")
            lines.append("")
            
            # Evidence
            evidence = f.get("evidence", {})
            reasoning = evidence.get("reasoning", "")
            if reasoning:
                lines.append(f"- **Reasoning:** {reasoning}")
            
            # Reproduction steps
            steps = f.get("reproduction_steps", [])
            if steps:
                lines.append("- **Reproduction Steps:**")
                for step in steps:
                    lines.append(f"  1. {step}")
            lines.append("")
    
    # Screenshots
    if screenshots:
        lines.append("## Screenshots")
        lines.append("")
        for sc in screenshots:
            lines.append(f"![{os.path.basename(sc)}]({sc})")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append("*Generated by MIRA-FlytBase Reporter*")
    
    return "\n".join(lines)


def generate_submission(findings: List[Dict[str, Any]], 
                        scenarios: List[Dict[str, Any]],
                        output_dir: str = "submission",
                        video_dir: str = "evidence/videos",
                        screenshot_dir: str = "evidence/screenshots") -> str:
    """
    Generate complete hackathon evaluation submission package.
    
    Args:
        findings: List of all primitive findings
        scenarios: List of scenario configs with name, trigger, expected, mutation, video_path
        output_dir: Output directory for submission package
        video_dir: Directory containing scenario videos
        screenshot_dir: Directory containing screenshots
        
    Returns:
        Path to submission directory
    """
    
    # Create output structure
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (out_path / "scenarios").mkdir(exist_ok=True)
    (out_path / "evidence").mkdir(exist_ok=True)
    
    # 1. Generate SYSTEM_DESIGN.md
    system_design = generate_system_design(findings, scenarios)
    (out_path / "SYSTEM_DESIGN.md").write_text(system_design, encoding="utf-8")
    
    # 2. Generate SCENARIOS.md (summary)
    scenarios_md = generate_scenarios_summary(findings, scenarios)
    (out_path / "SCENARIOS.md").write_text(scenarios_md, encoding="utf-8")
    
    # 3. Generate individual scenario reports
    scenario_groups = _group_findings_by_scenario(findings)
    
    scenario_index = []
    for i, sc in enumerate(scenarios, 1):
        sc_id = _generate_scenario_id(sc.get("category", "gen"), i)
        
        # Get findings for this scenario
        key = f"{sc.get('category', '')}:{sc.get('target_url', '')}"
        sc_findings = scenario_groups.get(key, [])
        
        # Find matching video and screenshots
        video_path = sc.get("video_path", "")
        screenshots = sc.get("screenshots", [])
        
        # Generate report
        report = generate_scenario_report(
            sc_findings, sc.get("name", f"Scenario {i}"), sc_id,
            sc.get("trigger", ""), sc.get("expected", ""), sc.get("mutation", ""),
            video_path, screenshots
        )
        
        # Save scenario report
        scenario_file = out_path / "scenarios" / f"{sc_id}.md"
        scenario_file.write_text(report, encoding="utf-8")
        
        # Add to index
        verdicts = [f.get("verdict") for f in sc_findings]
        has_bug = "bug" in verdicts
        has_security = "security_violation" in verdicts
        
        scenario_index.append({
            "id": sc_id,
            "name": sc.get("name", f"Scenario {i}"),
            "category": sc.get("category", "general"),
            "trigger": sc.get("trigger", ""),
            "mutation": sc.get("mutation", ""),
            "findings_count": len(sc_findings),
            "has_bug": has_bug,
            "has_security_violation": has_security,
            "report": f"scenarios/{sc_id}.md",
            "video": video_path,
            "screenshots": screenshots
        })
    
    # 4. Generate findings.json (machine-readable)
    findings_json = {
        "generated_at": _utcnow(),
        "total_findings": len(findings),
        "summary": {
            "bug": sum(1 for f in findings if f.get("verdict") == "bug"),
            "security_violation": sum(1 for f in findings if f.get("verdict") == "security_violation"),
            "needs_review": sum(1 for f in findings if f.get("verdict") == "needs_review")
        },
        "findings": findings
    }
    (out_path / "findings.json").write_text(json.dumps(findings_json, indent=2), encoding="utf-8")
    
    # 5. Generate scenario_index.json
    (out_path / "scenario_index.json").write_text(json.dumps(scenario_index, indent=2), encoding="utf-8")
    
    # 6. Copy videos and screenshots to evidence folder
    for sc in scenarios:
        video_path = sc.get("video_path", "")
        if video_path and os.path.exists(video_path):
            dest = out_path / "evidence" / os.path.basename(video_path)
            shutil.copy2(video_path, dest)
        
        for sc_path in sc.get("screenshots", []):
            if sc_path and os.path.exists(sc_path):
                dest = out_path / "evidence" / os.path.basename(sc_path)
                shutil.copy2(sc_path, dest)
    
    # 7. Generate README for submission
    readme = generate_submission_readme(scenario_index, findings)
    (out_path / "README.md").write_text(readme, encoding="utf-8")
    
    return str(out_path)


def generate_scenarios_summary(findings: List[Dict[str, Any]], 
                                scenarios: List[Dict[str, Any]]) -> str:
    """Generate SCENARIOS.md - numbered list for evaluation"""
    
    lines = [
        "# Scenario Submissions",
        "",
        f"**Total Scenarios:** {len(scenarios)}",
        f"**Total Findings:** {len(findings)}",
        f"**Generated:** {_utcnow()}",
        "",
        "---",
        ""
    ]
    
    scenario_groups = _group_findings_by_scenario(findings)
    
    for i, sc in enumerate(scenarios, 1):
        sc_id = _generate_scenario_id(sc.get("category", "gen"), i)
        key = f"{sc.get('category', '')}:{sc.get('target_url', '')}"
        sc_findings = scenario_groups.get(key, [])
        
        verdicts = [f.get("verdict") for f in sc_findings]
        has_bug = "bug" in verdicts
        has_security = "security_violation" in verdicts
        
        status = "🔴 FAIL" if has_bug or has_security else ("🟡 REVIEW" if verdicts else "🟢 PASS")
        
        lines.append(f"## {i}. {sc.get('name', f'Scenario {i}')} — {status}")
        lines.append("")
        lines.append(f"- **Scenario ID:** {sc_id}")
        lines.append(f"- **Category:** {CATEGORY_LABELS.get(sc.get('category', ''), sc.get('category', ''))}")
        lines.append(f"- **Target URL:** {sc.get('target_url', 'N/A')}")
        lines.append(f"- **Trigger:** {sc.get('trigger', 'N/A')}")
        lines.append(f"- **Expected:** {sc.get('expected', 'N/A')}")
        lines.append(f"- **Mutation:** {sc.get('mutation', 'N/A')}")
        lines.append(f"- **Findings:** {len(sc_findings)}")
        lines.append(f"- **Video:** {sc.get('video_path', 'Not recorded')}")
        lines.append("")
        
        if sc_findings:
            lines.append("**Findings:**")
            for f in sc_findings:
                verdict = f.get("verdict", "unknown")
                desc = f.get("description", "")[:120]
                lines.append(f"  - {VERDICT_EMOJI.get(verdict, '⚪')} [{VERDICT_LABELS.get(verdict, verdict)}] {desc}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def generate_submission_readme(scenario_index: List[Dict[str, Any]], 
                                findings: List[Dict[str, Any]]) -> str:
    """Generate submission README.md"""
    
    total = len(findings)
    bugs = sum(1 for f in findings if f.get("verdict") == "bug")
    security = sum(1 for f in findings if f.get("verdict") == "security_violation")
    review = sum(1 for f in findings if f.get("verdict") == "needs_review")
    
    lines = [
        "# MIRA-FlytBase Hackathon Submission",
        "",
        f"**Generated:** {_utcnow()}",
        "",
        "## Package Contents",
        "",
        "- `SYSTEM_DESIGN.md` — System architecture and design document",
        "- `SCENARIOS.md` — Numbered scenario list (evaluation format)",
        "- `scenarios/` — Individual scenario reports with evidence",
        "- `evidence/` — Video recordings (.webm) and screenshots (.png)",
        "- `findings.json` — Machine-readable all findings",
        "- `scenario_index.json` — Scenario metadata index",
        "",
        "## Summary",
        "",
        f"- **Total Findings:** {total} ({bugs} bugs, {security} security violations, {review} needs review)",
        f"- **Scenarios:** {len(scenario_index)}",
        f"- **Categories Covered:** {len(set(s['category'] for s in scenario_index))}",
        "",
        "## Scenario Index",
        "",
    ]
    
    for sc in scenario_index:
        status = "🔴" if sc["has_bug"] or sc["has_security_violation"] else "🟡"
        lines.append(f"- {status} **{sc['id']}**: {sc['name']} ({sc['category']}) — {sc['findings_count']} findings")
    
    lines.extend([
        "",
        "## Evaluation Instructions",
        "",
        "1. Start with `SYSTEM_DESIGN.md` for architecture overview",
        "2. Review `SCENARIOS.md` for numbered scenario list",
        "3. Watch videos in `evidence/` (Playwright recordings, .webm format)",
        "4. Deep-dive individual scenarios in `scenarios/*.md`",
        "5. Machine-readable data in `findings.json` and `scenario_index.json`",
        "",
        "---",
        "",
        "*MIRA-FlytBase Agentic Testing System — FlytBase AHC SWE Hackathon*"
    ])
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test
    mock_findings = [
        {
            "finding_id": "MIRA-STALENESS-abc123",
            "category": "staleness",
            "verdict": "bug",
            "confidence": 0.9,
            "description": "Telemetry field 'Battery' displays stale placeholder value ('—')",
            "target_url": "http://localhost:4010",
            "element_id": "el_battery",
            "evidence": {"reasoning": "Element shows dash pattern"},
            "reproduction_steps": ["Navigate", "Observe dash"],
            "discovered_at": _utcnow()
        },
        {
            "finding_id": "MIRA-RESPONSIVE_REACHABILITY-def456",
            "category": "responsive_reachability",
            "verdict": "bug",
            "confidence": 0.95,
            "description": "Critical action 'Takeoff' completely outside 375x667 viewport",
            "target_url": "http://localhost:4010",
            "element_id": "btn_takeoff",
            "evidence": {"reasoning": "bbox x=350 > 375"},
            "reproduction_steps": ["Set mobile viewport", "Observe button offscreen"],
            "discovered_at": _utcnow()
        }
    ]
    
    mock_scenarios = [
        {
            "name": "Telemetry Shows Dashes Under Socket Drop",
            "category": "staleness",
            "target_url": "http://localhost:4010",
            "trigger": "POST /api/control/fault {kind: \"socket-drop\", value: 100}",
            "expected": "Telemetry shows live numeric values",
            "mutation": "All telemetry fields show — dashes",
            "video_path": "evidence/videos/scenario_1.webm",
            "screenshots": ["evidence/screenshots/scenario_1_before.png", "evidence/screenshots/scenario_1_after.png"]
        },
        {
            "name": "Mobile Takeoff Button Clipped",
            "category": "responsive_reachability",
            "target_url": "http://localhost:4010",
            "trigger": "Resize viewport to 375x667",
            "expected": "Takeoff button fully visible and tappable",
            "mutation": "Button positioned at x=350 (outside 375px viewport)",
            "video_path": "evidence/videos/scenario_2.webm",
            "screenshots": ["evidence/screenshots/scenario_2_mobile.png"]
        }
    ]
    
    out = generate_submission(mock_findings, mock_scenarios, "test_submission")
    print(f"Generated submission at: {out}")