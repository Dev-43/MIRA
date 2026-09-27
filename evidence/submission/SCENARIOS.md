# MIRA Scenario Submissions & Evidence Log

**Total Verified Scenarios:** 5  
**Active Testing Primitives:** 5 / 5 Operational  
**Last Updated:** 2026-09-26  

---

## 1. Autonomous Closed-Loop Self-Healing: Visual Occlusion (Level 1 Track) — 🟢 HEALED & VERIFIED

- **Scenario ID:** SCN-VISUAL-001 (Level 1 Closed Loop)
- **Category:** Visual Occlusion & Interaction Interception
- **Target URL:** http://127.0.0.1:4010
- **Trigger:** Autonomous visual crawler injecting sticky alert banner over Drone 1 control row
- **Problem Detected:** Visual occlusion where bounding box is `is_visible() == True` in vanilla Playwright, but `document.elementFromPoint(149, 117)` resolves to `<div.global-alert-banner>` (z-index: 9999).
- **Autonomous Root Cause:** Banner overlays vertically into Drone 1 action item, blocking user clicks.
- **Synthesis:** Agent autonomously wrote regression test `tests/generated/test_visual_unoccluded_controls.py`.
- **Self-Healing Action:** Restructured layout to non-colliding floating pill centered at `top: 10px, h: 28px`.
- **Targeted Verification:** Probe verified 0 occlusions remaining.
- **Repetition Avoidance:** Avoided rerunning full 5-primitive suite across 3 viewports (14 probes skipped), reducing regression turnaround from ~45s to 1.2s.
- **Evidence Artifacts:**
  - Baseline: `evidence/screenshots/l1_step1_baseline.png`
  - Mutated: `evidence/screenshots/l1_step2_bug_injected.png`
  - Healed: `evidence/screenshots/l1_step5_healed.png`
  - Audit Log: `evidence/l1_demonstration_audit.json`
  - Synthesized Test: `tests/generated/test_visual_unoccluded_controls.py`

---

## 2. Autonomous Detection: Responsive Layout / Mobile Reachability — 🔴 DISCOVERED BUG (Cockpit Baseline)

- **Scenario ID:** SCN-RESP-002
- **Category:** Responsive Layout / Mobile Reachability
- **Target URL:** http://127.0.0.1:4010
- **Trigger:** Viewport resize probe at 375x667 (Mobile Portrait)
- **Expected:** Critical controls remain accessible within touch target bounds
- **Findings:**
  - 🔴 [BUG] Critical action `Control panel →` is completely off-screen at x=1333px in 375px viewport (0% visible).
  - 🔴 [BUG] Horizontal overflow detected: 3 elements extend beyond 375px viewport width without responsive wrapping.
- **Evidence Artifacts:**
  - Screenshot: `evidence/screenshots/root_desktop.png`
  - Findings JSON: `evidence/findings.json` (ID: `MIRA-RESPONSIVE_REACHABILITY-8b6f90`)

---

## 3. Autonomous Detection: Status Reality Mismatch — 🟡 FAULT INJECTION (Live API)

- **Scenario ID:** SCN-STATUS-003
- **Category:** Status Reality / Socket State Verification
- **Target URL:** http://127.0.0.1:4010
- **Trigger:** Live Control API Fault Injection (`POST /api/control/fault` with `kind: "socket-refuse"`)
- **Observed Behavior:** Backend rejects websocket handshake; Cockpit status badge transitions from `socket connected` → `socket connecting`. Telemetry values freeze while UI attempts reconnect.
- **Evidence Artifacts:**
  - Screenshot: `evidence/fault_screenshots/B_socket_refused.png`
  - Finding ID: `MIRA-STATUS_REALITY-FAULT-14231`
  - Demo Audit: `evidence/fault_demo_audit.json`

---

## 4. Autonomous Detection: Telemetry & Video Staleness — 🟡 FAULT INJECTION (Live API)

- **Scenario ID:** SCN-STALE-004
- **Category:** Staleness Detection / FPV Stream Freeze
- **Target URL:** http://127.0.0.1:4010
- **Trigger:** Live Control API Fault Injection (`POST /api/control/fault` with `kind: "video-freeze", deviceId: "drone-1"`)
- **Observed Behavior:** Video stream freezes on Drone 1 tile while telemetry claims active state.
- **Evidence Artifacts:**
  - Screenshots: `evidence/fault_screenshots/C1_before_freeze.png`, `evidence/fault_screenshots/C2_during_freeze.png`
  - Finding ID: `MIRA-STALENESS-FAULT-14244`
  - Demo Audit: `evidence/fault_demo_audit.json`

---

## 5. Autonomous Detection: Authentication & Session Gate — 🔴 SECURITY AUDIT

- **Scenario ID:** SCN-AUTH-005
- **Category:** Authentication / Entry Flow Inspection
- **Target URL:** http://127.0.0.1:4010
- **Trigger:** Direct unauthenticated page navigation
- **Observed Behavior:** Full mission-critical drone cockpit UI and live controls accessible without prior login, join prompt, or org token challenge.
- **Evidence Artifacts:**
  - Finding ID: `MIRA-AUTH_GATE-243991`
  - Screenshot: `evidence/screenshots/root_desktop.png`
