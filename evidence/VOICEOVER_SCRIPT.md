# Level 1 (L1) Demonstration: Voiceover & Presentation Script

> **Video Title:** MIRA-Web: Autonomous Visual Bug Detection, Test Synthesis & Self-Healing Loop  
> **Target:** FlytBase Cockpit (`http://localhost:4010`)  
> **Key Differentiator:** Proving why vanilla DOM automation produces false confidence, and demonstrating how MIRA's agentic loop detects visual collisions, authors regression tests dynamically, and verifies fixes with zero repeated crawl overhead.

---

## Timed Voiceover Script (Sync with Recording)

### [00:00 - 00:20] Introduction & The Automation Blindspot
**Visual:** Cockpit (`http://localhost:4010`) loaded cleanly on screen with 3D map, telemetry, and device list.  
**Voiceover:**  
> *"Welcome. In frontend engineering, traditional automated tests pass as long as an element exists in the DOM tree. But human users don't interact with the DOM—they interact with what is rendered on screen.  
> Today, we demonstrate MIRA: an autonomous testing system that bridges this gap. We're going to introduce a real-world visual bug into the FlytBase Cockpit and watch MIRA detect it, diagnose the CSS collision, synthesize a new regression test script, and verify the self-healed fix."*

---

### [00:20 - 00:45] Injecting the Mutation (The Visual Bug)
**Visual:** A red emergency flight restriction banner (`.global-alert-banner`) appears at the top left, physically overlapping the top half of the Drone 1 device row.  
**Voiceover:**  
> *"Here, we inject a common frontend regression: a floating alert banner with `z-index: 9999` and an oversized 110-pixel height drops down directly over our Drone 1 control row.  
> Standard Playwright and Cypress test scripts will call `.click()` on the button and pass green in CI. But notice: if a human operator clicks with their mouse, their pointer physically hits the red banner, preventing them from selecting or arming the drone. Traditional automation is completely blind to this."*

---

### [00:45 - 01:15] Autonomous Detection via Physical Hit-Testing & Gemini Vision
**Visual:** MIRA terminal and inspector running. Console highlights coordinates `(150, 75)` and outputs `BUG_DETECTED: MIRA-VISUAL_OCCLUSION`.  
**Voiceover:**  
> *"Now MIRA takes over without any human intervention. Instead of relying on DOM selectors, MIRA performs physical coordinate hit-testing using `document.elementFromPoint` at the calculated center of every interactive control.  
> It immediately discovers that coordinate (150, 75) does not hit the device row—it is intercepted by the alert banner.  
> MIRA's Multimodal Vision Judge, powered by Gemini 3.8 Flash, analyzes the rendered screenshot and confirms the collision: the critical action is visually occluded and obstructed from user interaction."*

---

### [01:15 - 01:45] Root-Cause Diagnosis & Dynamic Test Synthesis
**Visual:** Terminal showing the generated test file path `tests/generated/test_visual_unoccluded_controls.py` and computed collision delta.  
**Voiceover:**  
> *"Next is the self-healing step. MIRA's agent calculates the exact collision delta—the banner is intruding 37 pixels into the action's bounding box.  
> Instead of requiring a human QA engineer to write a reproduction script, MIRA dynamically synthesizes a brand-new Playwright regression test script into `tests/generated/`.  
> This script codifies the physical hit-test requirement so this exact layout collision can never slip past CI again."*

---

### [01:45 - 02:15] Self-Healing Fix & Targeted Verification
**Visual:** The banner transforms into a compact, floating pill centered cleanly at the top of the screen (`top: 10px, h: 28px`), leaving the Drone 1 row completely unblocked. Synthesized test runs and turns green.  
**Voiceover:**  
> *"MIRA now applies the layout fix, transforming the intrusive banner into a non-colliding floating pill centered at the top.  
> To verify the fix, MIRA does not waste time re-crawling all 10 pages of the website. Instead, it executes only the newly synthesized regression test directly against the modified component.  
> The test verifies that coordinate (150, 75) now cleanly reaches the target control. 0 visual occlusions remain. Verified and resolved."*

---

### [02:15 - 02:40] Iteration Metrics & Reviewer Takeaway
**Visual:** Final audit JSON table showing: Iterations Needed: 2 | Repetitions Avoided: 9 pages (100%) | Status: COMPLETED.  
**Voiceover:**  
> *"Let's look at the audit report:  
> 1. Total iterations required: exactly 2—one to detect and diagnose, and one to verify.  
> 2. Zero repeated actions: by using graph memory and targeted test synthesis, 9 unrelated pages were skipped.  
> This is true agentic testing: human-level visual perception, automated test authoring, and intelligent self-healing at scale. Thank you."*
