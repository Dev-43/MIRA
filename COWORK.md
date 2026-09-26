# COWORK.md — Antigravity & OpenCode Dual-Agent Collaboration Protocol

> **Purpose:** This file is the **Single Source of Truth (SSOT)** and real-time coordination protocol for **Antigravity** and **OpenCode** working collaboratively on the **MIRA-Web** autonomous QA platform for the FlytBase AHC SWE Hackathon.
> 
> **Zero Merge Conflicts Guarantee:** By adhering to strict module boundaries, exclusive file ownership, and centralized git custody, neither agent will overwrite or conflict with the other.

---

## 1. Division of Responsibilities

| Responsibility | Antigravity (IDE Lead & Custodian) | OpenCode (Feature Agent) |
|---|---|---|
| **Git Operations** | **EXCLUSIVE OWNER**: `git add`, `git commit`, `git revert`, `git branch` | **READ-ONLY**: Never runs `git commit` or `git push` |
| **Acceptance Testing** | Runs acceptance test scripts on real services (Neo4j, Cockpit :4010, Gemini API) | Writes unit/acceptance test alongside the code |
| **Core Infrastructure** | `mira/graph.py`, `mira/explorer.py`, `mira/runner.py` | — |
| **Vision & Reasoning** | `mira/vision_judge.py`, `mira/primitives/status_reality.py`, `mira/primitives/action_efficacy.py` | — |
| **Deterministic Primitives** | — | `mira/primitives/auth_gate.py`, `mira/primitives/staleness.py`, `mira/primitives/responsive_reachability.py` |
| **Reporting & Demo Tooling**| Verification & Final Packaging | `mira/reporter.py`, `demo/control_client.py` |

---

## 2. Strict Collaboration Rules

1. **Exclusive File Ownership**: No agent may edit a file owned by the other agent. Each primitive lives in its own standalone file inside `mira/primitives/`.
2. **Contract-First Rigor**: All primitives must accept the exact data shape from `mira/explorer.py` and output the standardized Finding schema (defined below and in [`BUILD.md`](file:///d:/MIRA/BUILD.md)).
3. **Task Claiming Protocol**:
   - An agent claims a task by changing its status in the **Live Task Board** below from `TODO` to `IN_PROGRESS: <AgentName>`.
   - Once implementation and self-testing are complete, set status to `READY_FOR_REVIEW`.
   - Antigravity runs the live verification suite. If passing, Antigravity commits the code and marks status `COMMITTED: <hash>`.
   - If acceptance fails, Antigravity logs the failure in `COWORK.md` and requests a fix or reverts.
4. **Git Commit Strategy (Rollback & Bisect Ready)**:
   - Every commit is atomic: `feat(<module>): <summary>` or `test(<module>): <summary>`.
   - Commits only happen after acceptance tests pass.
   - If a breaking change occurs, Antigravity can cleanly execute `git revert <hash>` without damaging other working modules.

---

## 3. Standard Interface Contracts

### Primitive Input (Produced by `mira/explorer.py`)
```python
elements: list[dict] = [
    {
        "id": str,          # unique element id e.g. "el_p1_btn_0"
        "role": str,        # "button", "link", "textbox", "heading", "checkbox", "tab"
        "name": str,        # accessible name/text
        "page_url": str,    # URL where element was found
        "bbox": {"x": float, "y": float, "width": float, "height": float}
    }
]

livefields: list[dict] = [
    {
        "id": str,          # unique field id e.g. "lf_p1_0"
        "page_url": str,
        "region_bbox": {"x": float, "y": float, "width": float, "height": float},
        "label_text": str,  # nearby text or badge label
        "last_value_hash": str, # MD5 hash of sampled pixel block
        "last_changed_ts": float,
        "freshness_claim": bool # True if label contains 'live', 'real-time', 'online', 'fps', etc.
    }
]
```

### Primitive Output / Finding Schema (Consumed by `mira/runner.py` & `mira/reporter.py`)
```json
{
  "finding_id": "MIRA-001",
  "category": "auth_gate | staleness | responsive_reachability | status_reality | action_efficacy",
  "verdict": "bug | security_violation | needs_review",
  "confidence": 0.95,
  "description": "Clear explanation of discrepancy between expected and observed state",
  "target_url": "http://localhost:4010/...",
  "element_id": "optional element id",
  "evidence": {
    "screenshot_path": "evidence/MIRA-001_screenshot.png",
    "video_path": "evidence/MIRA-001_video.webm",
    "reasoning": "Vision judge reasoning or rule match details",
    "telemetry_diff": null
  },
  "reproduction_steps": [
    "Navigate to URL",
    "Perform step..."
  ],
  "discovered_at": "2026-09-26T13:00:00Z"
}
```

---

## 4. Live Task Board & Progress Tracker

| Task ID | Module / Deliverable | Target File | Assigned Owner | Status | Commit Hash |
|---|---|---|---|---|---|
| **Task 0** | Dev Environment & SUT Verification | `.env`, `:4010`, `:4000` | Antigravity | `COMPLETED` | Baseline ready |
| **Task 1** | Graph Engine (Neo4j Schema) | `mira/graph.py` | Antigravity | `COMPLETED` | `1b6b5c3` |
| **Task 2** | Generic Web Explorer (Playwright) | `mira/explorer.py` | Antigravity | `COMPLETED` | `7b1969d` |
| **Task 3** | Auth-Gate Primitive | `mira/primitives/auth_gate.py` | **OpenCode** | `COMPLETED` | `8574bd1` |
| **Task 4** | Staleness & Freeze Primitive | `mira/primitives/staleness.py` | **OpenCode** | `COMPLETED` | `2b73a96` |
| **Task 5** | Responsive Reachability (375px) | `mira/primitives/responsive_reachability.py` | **OpenCode** | `COMPLETED` | `2abdefc` |
| **Task 6** | Multimodal Vision Judge | `mira/vision_judge.py` | Antigravity | `COMPLETED` | `5ed4109` |
| **Task 7** | Status Reality Primitive | `mira/primitives/status_reality.py` | Antigravity | `COMPLETED` | `7bd862a` |
| **Task 8** | Action Efficacy Primitive | `mira/primitives/action_efficacy.py` | Antigravity | `COMPLETED` | `e61e900` |
| **Task 9** | Runner & Orchestration Pipeline | `mira/runner.py` | Antigravity | `COMPLETED` | `8460842` |
| **Task 10** | Hackathon Report Generator | `mira/reporter.py` | **OpenCode** | `COMPLETED` | `7214ff7` |
| **Task 11** | Fault Injection Control Client | `demo/control_client.py` | **OpenCode** | `COMPLETED` | `f9ded7c` |
| **Task 12** | Graph Memory Path (Warm runs) | `mira/graph.py` | Antigravity | `COMPLETED` | `8b67c6e` |
| **Task 13** | Video Recording & Submission Assembly| `SUBMISSION_DRAFT.md` | Joint | `READY_FOR_RECORDING` | — |

---

## 5. Instructions for OpenCode

Copy and paste the prompt in the section below into OpenCode when you are ready for OpenCode to start its assigned modules.

### Prompt to Send to OpenCode:
```markdown
You are OpenCode, working as the Feature Agent in parallel with Antigravity on MIRA-Web.
Read and adhere strictly to `COWORK.md` and `BUILD.md` in the workspace root.

Your Rules of Engagement:
1. You DO NOT perform git commits or pushes. Antigravity is the Git Custodian and will run automated tests and commit your work cleanly.
2. You only write/edit files assigned to you in `COWORK.md`:
   - `mira/primitives/auth_gate.py` (Task 3)
   - `mira/primitives/staleness.py` (Task 4)
   - `mira/primitives/responsive_reachability.py` (Task 5)
   - `mira/reporter.py` (Task 10)
   - `demo/control_client.py` (Task 11)
3. You must never touch `mira/graph.py`, `mira/explorer.py`, `mira/vision_judge.py`, or `mira/runner.py`.
4. Follow the exact input/output contracts defined in Section 3 of `COWORK.md`.
5. When you finish a task, update `COWORK.md` to set that task's status to `READY_FOR_REVIEW`.
```

---

## 6. Git Commit Protocol & Rollback Checklist

For Antigravity:
1. **Verification Gate**:
   - Run acceptance command: e.g. `python -m unittest tests/test_<module>.py` or standalone test script.
   - Ensure zero false positives on baseline cockpit (`http://localhost:4010`).
2. **Atomic Stage**:
   - `git add <exact_modified_files>` (never blindly `git add .`).
3. **Commit Convention**:
   - `feat(<module>): <concise explanation>`
   - Include notes on acceptance test results in commit body.
4. **Update `COWORK.md`**:
   - Record the commit hash in the Live Task Board.
5. **Rollback Plan**:
   - If an issue is discovered later: `git revert <commit-hash> --no-edit` or checkout previous state for that specific module.
