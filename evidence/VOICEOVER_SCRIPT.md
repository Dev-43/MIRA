# Level 1 (L1) Demonstration: 2-Minute Voiceover Script

> **Video Title:** MIRA-Web: Autonomous Visual Bug Detection, Test Synthesis & Self-Healing Loop  
> **Duration:** Exactly 2:00 Minutes (Word count: ~270 words)  
> **Dashboard to Record:** `http://127.0.0.1:5050` (Tab 1: L1 Closed Loop)  
> **Live Speaker Notes Window:** `http://127.0.0.1:5050/presenter`  

---

### [00:00 - 00:20] • Introduction & The Automation Blindspot
* **Dashboard Action:** Show Tab 1 (*"L1 Self-Healing Closed Loop"*) with the **"Baseline"** button active.
* **Voiceover:**
> *"Welcome. Standard automated tests pass as long as an element exists in the DOM. But human users interact with what is visually rendered on screen.  
> Today we demonstrate MIRA: an autonomous agent that detects visual collisions, authors new regression tests dynamically, and verifies self-healed fixes with zero repeated crawl overhead."*

---

### [00:20 - 00:45] • Injected Bug & Vanilla Test Blindness
* **Dashboard Action:** Click **"Injected Bug"** button (shows the red emergency banner covering Drone 1).
* **Voiceover:**
> *"Here, we inject a common frontend bug: a floating alert banner with z-index 9999 drops directly over our Drone 1 control row.  
> In traditional Playwright or Cypress, calling `.is_visible()` or `.click()` passes green in CI. But for a human operator, their mouse physically clicks the red banner—preventing them from arming the drone. Traditional automation is completely blind to this."*

---

### [00:45 - 01:15] • Physical Hit-Testing Detection
* **Dashboard Action:** Click **"Phase 3 • Bug Caught"** on the left stepper. Point cursor to coordinate `(149, 117)`.
* **Voiceover:**
> *"Now MIRA takes over. Instead of checking DOM presence, MIRA performs physical coordinate hit-testing using `document.elementFromPoint` at the exact center of every interactive control.  
> It immediately discovers that coordinate (149, 117) does not hit Drone 1—it is physically intercepted by the alert banner. MIRA diagnoses a 65-pixel vertical collision with zero human intervention."*

---

### [01:15 - 01:40] • Autonomous Test Synthesis
* **Dashboard Action:** Scroll down slightly to highlight the **Synthesized Code Box** below the preview.
* **Voiceover:**
> *"Next is the agentic loop. Instead of waiting for a human QA engineer to manually write a test, MIRA dynamically synthesizes a brand-new Playwright regression test script into `tests/generated/`.  
> This script asserts physical hit-test coordinate integrity so this exact layout collision can never slip past CI again."*

---

### [01:40 - 02:00] • Self-Healing, Verification & Repetition Avoidance
* **Dashboard Action:** Click **"Healed & Verified"** button. Point cursor to top KPI card *"14 probes skipped"*.
* **Voiceover:**
> *"MIRA now applies an autonomous layout patch, repositioning the banner into a non-colliding floating pill at the top. All four drones and satellite terrain are completely unblocked.  
> To verify, MIRA does not re-crawl the whole app—it runs only the targeted probe, skipping 14 redundant tests and cutting verification from 45 seconds down to 1.2 seconds. Verified, healed, and closed in 2 iterations."*
