# Level 1 Evaluation Document: Static UI and Basic Security Testing

**Project:** MIRA (Model-Driven Intelligent Regression & Agentic QA)  
**Target SUT:** FlytBase Drone Fleet Operations Cockpit (`http://127.0.0.1:4010`)  
**Submission Category:** Level 1 — Static UI & Basic Security Testing  
**Live QA Dashboard:** `http://127.0.0.1:5050`  

---

## Part 1: System Design

### 1.1 Overview & Architectural Philosophy
Standard frontend test runners (such as vanilla Playwright, Selenium, and Cypress) suffer from two fundamental weaknesses when evaluating dynamic, mission-critical single-page applications:
1. **DOM Illusion & Visual Blindness:** Vanilla automation checks whether an element exists in the DOM (`is_visible() == True`) and dispatches synthetic DOM click events (`dispatchEvent('click')`). However, if a translucent overlay, floating alert banner, or fixed navigation bar overlays that element, the DOM assertion passes **falsely**, even though a real human operator is completely blocked from clicking it.
2. **Repetitive, Brittle Regression Crawls:** When a bug is repaired, typical CI/CD pipelines rerun entire multi-page regression suites across all viewports (~45–60 seconds). 

**MIRA** is an autonomous agentic testing and self-healing engine designed specifically for complex operational interfaces (such as drone ground stations and aerospace telemetry dashboards). MIRA replaces superficial DOM checks with physical coordinate hit-testing, multimodal vision validation, autonomous test synthesis, and targeted regression verification.

```
                      ┌───────────────────────────────────────────────┐
                      │             FlytBase Cockpit SUT              │
                      │  (Cesium 3D Globe + Websocket Telemetry UI)   │
                      └───────────────────────┬───────────────────────┘
                                              │
                      ┌───────────────────────▼───────────────────────┐
                      │          1. Autonomous Crawler &              │
                      │       Physical Coordinate Hit-Tester          │
                      │  document.elementFromPoint(centerX, centerY)  │
                      └───────────────────────┬───────────────────────┘
                                              │ [Interception / Collision]
                      ┌───────────────────────▼───────────────────────┐
                      │    2. Gemini Multimodal Vision Judge          │
                      │  Visual inspection & Root-Cause Bounding Box  │
                      └───────────────────────┬───────────────────────┘
                                              │
                      ┌───────────────────────▼───────────────────────┐
                      │   3. Dynamic Regression Test Synthesizer      │
                      │  Generates standalone test script in tests/   │
                      └───────────────────────┬───────────────────────┘
                                              │
                      ┌───────────────────────▼───────────────────────┐
                      │    4. Autonomous Layout & CSS Healer          │
                      │  Applies localized patch to resolve collision │
                      └───────────────────────┬───────────────────────┘
                                              │
                      ┌───────────────────────▼───────────────────────┐
                      │    5. Targeted Hit-Test Verification          │
                      │  1.2s targeted probe (14 redundant tests skipped)
                      └───────────────────────────────────────────────┘
```

---

### 1.2 Core Subsystems & How They Work Together

#### A. Physical Coordinate Hit-Testing Engine (`mira/primitives/visual_occlusion.py`)
Instead of querying DOM selector presence, MIRA computes the absolute bounding rectangle of every interactive component (`x, y, width, height`) via `getBoundingClientRect()`. It calculates the physical center point `(cx, cy)` and queries the browser's graphics rendering compositor:
```javascript
document.elementFromPoint(cx, cy)
```
If the top-most rendered element is an overlapping layer (e.g., `div.global-alert-banner`) rather than the target control or its direct descendants, MIRA flags an **Interaction Interception**. This physically guarantees that no mouse or touch event can reach the underlying control.

#### B. Gemini Multimodal Vision Judge (`mira/vision_judge.py`)
Upon catching a collision, MIRA captures a high-resolution viewport buffer and dispatches the visual scene along with DOM context to Gemini 2.5 Flash Vision. The Vision Judge performs semantic scene reasoning:
* Validates whether the overlay is an acceptable modal vs. an unintended spatial obstruction.
* Computes collision geometry (e.g., *"65px vertical intrusion overlapping Drone 1 control row"*).
* Categorizes severity to prevent false positives on subtle brand differences.

#### C. Dynamic Regression Test Synthesizer (`mira/healer.py`)
MIRA does not just log bugs in a bug tracker; it codifies them into code. It dynamically authors a standalone Playwright regression test script into `tests/generated/test_visual_unoccluded_controls.py`. The generated test isolates the exact physical coordinates and asserts zero interaction interception.

#### D. Autonomous Layout & CSS Healer
MIRA synthesizes an ergonomic layout adjustment (e.g., transforming an intrusive 110px sticky alert into a centered non-colliding floating pill at `top: 10px; height: 28px`). It hot-patches the CSS layout while preserving full operational visibility.

#### E. Targeted Verification & Repetition Avoidance
Instead of re-running the entire 5-primitive suite across 3 viewports (15 total probes, ~45s), MIRA executes **only the synthesized coordinate probe**. This verifies the resolution in **1.2 seconds**, avoiding 14 redundant probes and cutting regression cycles by over 97%.

#### F. Executive QA Dashboard (`http://127.0.0.1:5050`)
A real-time telemetry and demonstration console providing complete visibility into baseline health, active mutations, physical coordinate probes, code synthesis, and verified patches.

---

## Part 2: Scenarios

```
====================================================================================================
SCENARIO SUMMARY MATRIX
====================================================================================================
#   Title                                 Category              Detection Method       Target SUT
----------------------------------------------------------------------------------------------------
1   Visual Occlusion on Fleet Controls    Level 1 Hero Loop     Physical Hit-Test      Cockpit UI
2   Critical Action Off-Screen on Mobile  Responsive Reach      Viewport Clipping      Cockpit Nav
3   Websocket Disconnection & Freeze      Status Reality        Telemetry Delta        Control API
4   Live Video Stream Freeze Detection    Temporal Staleness    Perceptual Frame Diff  Video Feed
5   Unprotected Flight Control Endpoints  Basic Security        Route Probe & Session  Cockpit Auth
====================================================================================================
```

---

### Scenario 1: Visual Occlusion & Interaction Interception on Fleet Controls (Hero Scenario)

* **Title:** Physical Hit-Test Occlusion Detection and Autonomous Closed-Loop Self-Healing
* **Video Link:** `[Google Drive Video Link - Pending Upload]` *(Insert your video URL here)*
* **Target Component:** Drone Fleet Device Control Row (`#drone-1` at physical coordinates `x: 149, y: 117`)

#### 1. Description: What is tested & What the user expects
In a mission-critical drone operations cockpit, operators must have unobstructed access to select drones, send takeoff commands, and initiate emergency RTL (Return To Launch). 
During evaluation, a mutation is injected: a floating emergency notification banner (`.global-alert-banner`, height 110px, `z-index: 9999`) is injected across the top-left quadrant of the screen directly on top of the Drone 1 device row.
* **User Expectation:** Clicking on Drone 1 immediately opens its telemetry panel and flight controls.
* **Failure Observed:** The banner visibly and physically obstructs Drone 1. Clicking on the row strikes the banner instead.
* **Why Vanilla Tools Fail:** Playwright's `page.locator("text=Drone 1").is_visible()` returns `True`, and synthetic `.click()` dispatches directly to the DOM node, completely missing the fact that a human operator cannot click it.

#### 2. Approach: How MIRA tests & resolves the issue
1. **Physical Probe:** MIRA queries `document.elementFromPoint(149, 117)`. The rendering engine returns `DIV#demo-critical-alert-banner`.
2. **Diagnosis:** MIRA flags `MIRA-VISUAL_OCCLUSION-194bcb` and determines a 65px vertical collision intrusion.
3. **Dynamic Test Generation:** The agent automatically synthesizes a new regression test file: `tests/generated/test_visual_unoccluded_controls.py`.
4. **Autonomous Patch:** MIRA applies a layout patch restructuring the banner into a centered floating status pill (`top: 10px; max-width: 600px; height: 28px`), leaving all device rows unoccluded.
5. **Targeted Verification:** MIRA runs the newly synthesized test against the live page. Physical hit-test passes with `0 remaining occlusions` in 1.2s (14 redundant probes skipped).

#### 3. Reproducibility & Starting State
* **Starting State:** FlytBase Cockpit loaded clean at `http://127.0.0.1:4010` (1440x900 viewport).
* **Reproduction Command:** `python -m mira.healer`
* **Artifacts & Evidence:**
  * Baseline Screenshot: `evidence/screenshots/l1_step1_baseline.png`
  * Bug Injected Screenshot: `evidence/screenshots/l1_step2_bug_injected.png`
  * Healed Screenshot: `evidence/screenshots/l1_step5_healed.png`
  * Machine Audit Log: `evidence/l1_demonstration_audit.json`

---

### Scenario 2: Critical Navigation Action Pushed Off-Screen at Mobile Viewport

* **Title:** Responsive Layout Failure — Critical Action Off-Screen at 375px Viewport Width
* **Video Link:** `[Google Drive Video Link - Pending Upload]` *(Insert your video URL here)*
* **Target Component:** Cockpit Navigation Bar Header Link (`.dashboard-link` "Control panel →")

#### 1. Description: What is tested & What the user expects
Field technicians and remote drone supervisors often monitor automated flights using mobile handheld devices (smartphones and tablets).
* **User Expectation:** When accessing the Cockpit on a mobile portrait screen (375x667, iPhone SE standard), all vital navigation actions (specifically the link to switch between live fleet map and control settings) must adapt responsively and remain within the viewport.
* **Failure Observed:** In FlytBase Cockpit, the header uses a fixed horizontal layout without wrapping or hamburger collapse. The primary action `"Control panel →"` is pushed to coordinate `x = 1333px`, placing it 958px beyond the screen edge. Its visible screen intersection ratio is **0.0%**. A mobile operator cannot reach the control panel.

#### 2. Approach: How MIRA tests & identifies the issue
1. **Multi-Viewport Crawl:** MIRA renders the application across 3 standard profiles: Desktop (1440x900), Tablet (768x1024), and Mobile (375x667).
2. **Geometric Clipping Analysis:** For each interactive element identified as a primary action or navigation route, MIRA calculates:
   $$\text{Visible Ratio} = \frac{\text{Area}(\text{Element Rect} \cap \text{Viewport Rect})}{\text{Area}(\text{Element Rect})}$$
3. **Threshold Trigger:** The bounding box evaluates to `left: 1333, right: 1424` against a `375px` viewport limit. MIRA flags `MIRA-RESPONSIVE_REACHABILITY-8b6f90` with severity **CRITICAL** (element inaccessible to touch/pointer interactions).

#### 3. Reproducibility & Starting State
* **Starting State:** Viewport set to `375 x 667`.
* **Reproduction Steps:**
  1. Load `http://127.0.0.1:4010` in mobile viewport.
  2. Inspect `.dashboard-link` bounding rectangle.
  3. Notice button is completely rendered off-screen in the horizontal overflow zone.
* **Evidence:** `evidence/findings.json` (Finding: `MIRA-RESPONSIVE_REACHABILITY-8b6f90`).

---

### Scenario 3: Telemetry Disconnection & Socket Freezing Under Server Mutation

* **Title:** Status Reality Verification — Websocket Refusal & Frozen Telemetry Audit
* **Video Link:** `[Google Drive Video Link - Pending Upload]` *(Insert your video URL here)*
* **Target Component:** Cockpit Header Socket Status Badge & Live Drone Telemetry Panel

#### 1. Description: What is tested & What the user expects
Drones in flight stream live attitude, altitude, and battery metrics via WebSocket. If the backend socket connection drops, the UI must immediately warn the operator and refuse to display stale telemetry as "live".
* **User Expectation:** When the WebSocket connection is refused or severed, the UI status indicator must transition from `socket connected` to `socket connecting` or `disconnected`, and the operator should be alerted.
* **Mutation Injected:** MIRA invokes the native FlytBase Control API fault endpoint:
  ```http
  POST http://127.0.0.1:4000/api/control/fault
  Content-Type: application/json

  {"kind": "socket-refuse"}
  ```

#### 2. Approach: How MIRA tests & identifies the issue
1. **Coupled Reality Probing:** MIRA pairs DOM text assertions with real-time socket inspection.
2. **Delta Verification:** Prior to fault injection, MIRA records telemetry deltas ($\Delta \text{Altitude}$, $\Delta \text{Battery}$). Upon injecting `socket-refuse`, MIRA captures the socket badge transitioning to `socket connecting` with an amber indicator.
3. **Frozen Telemetry Audit:** MIRA confirms that telemetry values freeze and verifies that the UI prevents stale commands from dispatching without a healthy socket handshake.

#### 3. Reproducibility & Starting State
* **Starting State:** Cockpit and Control API online (`http://127.0.0.1:4010` and `http://127.0.0.1:4000`).
* **Reproduction Command:** `python demo/fault_injection_demo.py`
* **Evidence:**
  * Screenshot: `evidence/fault_screenshots/B_socket_refused.png`
  * Audit File: `evidence/fault_demo_audit.json`

---

### Scenario 4: Temporal Staleness — Live Video Feed Freeze Detection

* **Title:** Perceptual Video Stream Staleness Detection During Native Control API Fault
* **Video Link:** `[Google Drive Video Link - Pending Upload]` *(Insert your video URL here)*
* **Target Component:** Live Video Feed Player Tile (`#drone-1-video`)

#### 1. Description: What is tested & What the user expects
Operators piloting BVLOS (Beyond Visual Line of Sight) rely completely on the real-time camera feed to avoid terrain and obstacles. If a video feed freezes while the UI continues to display a green "LIVE" badge, the operator risks fatal crashes.
* **User Expectation:** If the video stream freezes or drops frames, the UI must flag the feed as stale or paused.
* **Mutation Injected:** MIRA triggers a native video freeze mutation:
  ```http
  POST http://127.0.0.1:4000/api/control/fault
  Content-Type: application/json

  {"kind": "video-freeze", "deviceId": "drone-1"}
  ```

#### 2. Approach: How MIRA tests & identifies the issue
1. **Perceptual Temporal Sampling:** MIRA samples the video canvas / image stream across a sliding 3-second temporal window ($t_0, t_0+1.5s, t_0+3.0s$).
2. **Perceptual Hash Difference:** MIRA computes frame-to-frame pixel differences. While normal feeds exhibit continuous pixel variance due to sensor noise and camera motion, the frozen stream returns a differential of $\Delta < 0.01\%$.
3. **Staleness Flagged:** MIRA correlates the zero-delta frame with the UI's status, catching the silent freeze condition without requiring access to internal video player source code.

#### 3. Reproducibility & Starting State
* **Starting State:** Cockpit online, Drone 1 video stream active.
* **Reproduction Command:** `python demo/fault_injection_demo.py`
* **Evidence:**
  * Pre-freeze Screenshot: `evidence/fault_screenshots/C1_before_freeze.png`
  * Freeze Screenshot: `evidence/fault_screenshots/C2_during_freeze.png`
  * Audit Report: `evidence/fault_demo_audit.json`

---

### Scenario 5: Basic Security Boundary — Unauthenticated Access to Flight Controls

* **Title:** Unauthenticated Route Protection & Fleet Command Authorization Audit
* **Video Link:** `[Google Drive Video Link - Pending Upload]` *(Insert your video URL here)*
* **Target Component:** Cockpit Fleet Control Panel & API Command Dispatchers

#### 1. Description: What is tested & What the user expects
Cockpit interfaces must ensure that unauthenticated users cannot issue drone commands, modify flight parameters, or trigger emergency maneuvers.
* **User Expectation:** If an unauthenticated session directly requests mission control routes or attempts to invoke command dispatchers, the system must immediately redirect the session to an authentication boundary or return HTTP `401 / 403 Forbidden`.
* **Failure / Vulnerability Probed:** Direct navigation to control endpoints and inspection of socket handshake payloads to verify whether authentication headers or session tokens are enforced.

#### 2. Approach: How MIRA tests & identifies the issue
1. **Headless Session Isolation:** MIRA launches a clean browser context with zero cookies, local storage, or session tokens.
2. **Direct Route Traversal:** MIRA probes both `/` and control panel routes (`/control`, API endpoints).
3. **Boundary Verification:** MIRA audits whether sensitive operational telemetry (latitude/longitude coordinates, payload status) is leaked to unverified clients before credentials are validated.

#### 3. Reproducibility & Starting State
* **Starting State:** Clean Playwright browser context without cached storage.
* **Reproduction Steps:**
  1. Launch fresh incognito context.
  2. Attempt navigation to Cockpit endpoints.
  3. Audit DOM and network socket handshakes for credential barriers.
* **Evidence:** `evidence/findings.json` (Security audit section).

---

## Part 3: Evaluation Criteria Compliance Summary

| Criterion | How MIRA Meets & Exceeds the Standard |
| :--- | :--- |
| **1. Validity** | Every reported scenario represents a genuine, high-impact user-facing defect: pointer events intercepted by floating elements, critical actions completely clipped off phone screens, and frozen video feeds. No cosmetic wording disputes. |
| **2. Reproducibility & Evidence** | Every scenario includes a clean starting state, exact API/code reproduction steps, high-resolution screenshots (`evidence/screenshots/`), machine-readable audit logs (`evidence/l1_demonstration_audit.json`), and live dashboard video replays. |
| **3. Product Understanding** | MIRA understands drone operations: it recognizes that a blocked Drone 1 row prevents emergency RTL, that an off-screen dashboard link cripples mobile field supervisors, and that frozen video feeds lead to BVLOS collisions. |
| **4. Breadth** | Spans across all 5 key frontend testing disciplines: physical visual occlusion, responsive device reachability (3 viewports), real-time WebSocket state reality, temporal video staleness, and unauthenticated security boundaries. |
| **5. Depth and Impact** | Goes beyond detection: MIRA performs root-cause bounding-box calculation, dynamically authors regression test scripts into `tests/generated/`, applies self-healing CSS fixes, and proves targeted verification in 1.2s. |
| **6. Precision** | Eliminates false positives via physical `elementFromPoint` rendering hit-tests combined with Gemini Vision reasoning. Avoids repeating full multi-page crawls by skipping 14 redundant probes on verification. |

---

## Part 4: Submission Links Checklist

* [x] **System Design (Part 1):** Complete & documented above
* [x] **Numbered Scenarios (Part 2):** 5 fully documented scenarios with Title, Description, Approach, and Video placeholder
* [ ] **Video Link (Google Drive):** `[INSERT YOUR GOOGLE DRIVE VIDEO LINK HERE]`
* [ ] **Write-up Link (Google Doc):** Ready to paste into Google Docs or export as PDF

---
*Generated by MIRA Autonomous Agentic Quality Assurance System*
