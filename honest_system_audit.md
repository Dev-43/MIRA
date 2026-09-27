# MIRA System: Honest Critical Audit

> **Date:** 2026-09-26  
> **Auditor:** Antigravity (self-assessment)  
> **Goal:** No sugarcoating. What actually works, what doesn't, and what would a judge see.

---

## What Works Well ✅

### 1. The `elementFromPoint` Hit-Testing Technique is Genuinely Novel
The physical coordinate probe (`document.elementFromPoint(cx, cy)`) is a real, defensible technique that catches a class of bugs standard Playwright/Cypress cannot. This is not a gimmick — it directly addresses the mentor's feedback about "Playwright can click it but the user can't."

**Evidence:** `l1_step2_bug_injected.png` clearly shows the red banner covering Drone 1. The hit-test correctly returned `div.global-alert-banner` instead of `li.device-row`. This is a true positive.

### 2. Responsive Reachability Findings are Legitimate
The two `responsive_reachability` findings are **real bugs in the actual Cockpit code**:
- "Control panel →" at `x=1333px` is genuinely unreachable on a 375px phone — `visible_ratio: 0.0%`
- 3 elements overflow horizontally — the Cockpit has no mobile breakpoints

These are not injected mutations. These are real issues in the shipped SUT.

### 3. Neo4j Graph Schema is Live and Populated
The knowledge graph has real data: 1 Site, 1 Page, 7 Elements, 6 LiveFields with bbox coordinates and value hashes. The warm-run path is structurally sound.

### 4. The Synthesized Test Script Runs and Passes
`test_visual_unoccluded_controls.py` was dynamically authored by the system and independently executed against the live Cockpit. Output: `TEST PASSED`. This proves the test generation loop closes.

---

## What Has Problems ⚠️

### 1. The "Healed" Screenshot (`l1_step5_healed.png`) Has New Issues
Look carefully at the healed state:
- **White rectangle** in the top-left map area (Cesium rendering artifact / broken canvas)
- **FPV Video says "reconnecting"** (was showing live feed in baseline)
- The banner pill is repositioned correctly, but the **page has degraded** during the test

**Impact:** If a reviewer compares baseline vs "healed," the healed state looks *worse* in some ways. The system solved the occlusion bug but didn't notice it introduced visual degradation elsewhere. A human reviewer would flag this.

### 2. The L1 Demo is Circular (Self-Injected → Self-Detected → Self-Fixed)
- We inject the bug ourselves via `page.evaluate(js_inject_bug)`
- We detect it ourselves via `elementFromPoint`
- We fix it ourselves via `page.evaluate(js_apply_fix)`

This proves the **mechanism works**, but it's not a real-world scenario where the system discovers an organic bug in production code. A judge may ask: "Can it find bugs that weren't planted by the same system?"

**Mitigation:** The responsive_reachability findings ARE organic — they're real bugs in the untouched Cockpit. Lead with those.

### 3. Two Primitives Produced Zero Findings
- **`staleness`**: 0 findings. The Cockpit has live telemetry updating (Battery 100%, Wind NW 3.8 m/s) and an FPV video feed marked "live." The staleness detector should have at least sampled these and logged a "healthy" baseline, but it appears to have found nothing noteworthy.
- **`status_reality`**: 0 findings. The Vision Judge was invoked but produced no contradictions. This could mean the system is correctly healthy, OR the primitive isn't sensitive enough.

**Impact:** 2 out of 5 primitives are effectively silent. Only `auth_gate`, `responsive_reachability`, and now `visual_occlusion` produced actionable output.

### 4. The Auth Gate Finding is Arguably Expected Behavior
`MIRA-AUTH_GATE-243991` flags "Full cockpit UI accessible without authentication." But the hackathon starter kit **doesn't implement auth by default** — there's no login page in the codebase. This is "by design" for the demo, not a discovered regression.

The second auth finding (`MIRA-AUTH_GATE-89a26b`, verdict: `needs_review`, confidence: 0.6) is essentially a duplicate with weaker language. Together they look like padding — 2 findings from 1 observation.

### 5. The `root_desktop.png` Screenshot Shows No Video Feed
The main pipeline's desktop screenshot shows the FPV tile as a blank black box with just "FPV · Drone 1" and "live" text — the actual WebRTC video stream wasn't captured by Playwright's screenshot engine. A reviewer comparing this against the live app (which shows an aerial video clip) may wonder why our evidence doesn't show what the user actually sees.

### 6. "9 Pages Avoided" Metric is Inflated
The audit claims "9 pages avoided via targeted probe." But the Cockpit is a **single-page application** — BFS exploration only discovered 1 page (`http://localhost:4010`). There aren't 10 pages to skip. The metric overstates the efficiency gain.

---

## What's Missing ❌

### 1. No Fault Injection Demonstration
`demo/control_client.py` exists but was never exercised in the evidence:
- No `inject_socket_kick` → no status_reality contradiction detected
- No `inject_video_freeze` → no staleness finding on the video tile
- No drone `takeoff`/`land` → no action_efficacy click-response verification

These were listed as Task 13 in the build plan and never completed.

### 2. No Multi-Page Crawl Evidence
The explorer only found 1 page. The BFS crawler's depth-3 traversal didn't discover additional routes. This is partly the SUT's fault (single-route React SPA), but it means we can't demonstrate the Neo4j warm-run graph diff value.

### 3. No "Before vs After Mutation" Scenario from the Brief
The hackathon brief explicitly says: *"During evaluation we will introduce deliberate changes (mutations) into the app, and your testing system has to catch them."* Our evidence should show catching mutations the evaluators introduce, but we only show catching our own self-injected one.

### 4. Voiceover Script Exists but No Actual Video with Audio
`VOICEOVER_SCRIPT.md` is a text script. It hasn't been recorded as an actual video with narration yet.

---

## Honest Scoring (If I Were a Judge)

| Criterion | Score | Notes |
|---|:---:|---|
| **Detection Mechanism** (does it find real bugs?) | **7/10** | Responsive findings are genuine. Hit-testing is novel. But 2/5 primitives are silent. |
| **Evidence Quality** (screenshots, video, JSON) | **5/10** | Screenshots exist but have artifacts. Videos are `.webm` captures without commentary. No diff comparisons. |
| **Autonomy** (zero human intervention?) | **6/10** | The pipeline runs end-to-end with `python run_l1_demo.py`. But the L1 demo is self-contained/circular. |
| **Test Synthesis** (dynamic test generation) | **8/10** | The synthesized script is clean, runs independently, and makes a real assertion. This is strong. |
| **Graph Memory / Efficiency** | **4/10** | Neo4j is live and populated. But warm-run diff hasn't been demonstrated. "9 pages avoided" is inflated. |
| **Submission Readiness** | **5/10** | SYSTEM_DESIGN.md and SCENARIOS.md exist but are auto-generated boilerplate. No fault injection demo. No voiceover recording. |

**Overall: 5.8/10 — The core mechanism is sound but the demonstration needs more depth.**

---

## What to Fix Before Submission (Priority Order)

1. **Run fault injection** (`inject_socket_kick`, `inject_video_freeze`) and capture staleness + status_reality findings with screenshots. This fills the empty primitive gap.
2. **Fix the "healed" screenshot** — either remove the Cesium white artifact or take the screenshot before the canvas degrades.
3. **Remove the inflated "9 pages avoided" metric** — be honest that it's a 1-page SPA and frame the efficiency as "targeted component re-test vs full-page re-scan."
4. **Record an actual screen recording with voiceover** using the script in `VOICEOVER_SCRIPT.md`.
5. **Add a real mutation test** — modify the frontend CSS (e.g., add `display: none` to the device list) and show MIRA catching it via graph diff.
