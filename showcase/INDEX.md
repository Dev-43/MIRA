# MIRA Executive Showcase Bundle Index

Welcome to the **MIRA Showcase Bundle**. Everything needed to present, demonstrate, and verify MIRA's autonomous quality engineering and self-healing engine is organized here.

---

## 📁 Directory Structure

```
d:\MIRA\showcase\
├── documentation/          # Submission markdown, technical deep dive, and recording scripts
│   ├── MIRA_TECHNICAL_DEEP_DIVE.md      # Full architecture, Playwright code, LLM prompts, Neo4j queries
│   ├── EVALUATION_DOCUMENT_LEVEL_2.md   # Level 2 formal evaluation document
│   ├── SUBMISSION.md                    # Official hackathon submission overview
│   └── l2_1min_script.txt               # Clean ElevenLabs 1-minute voiceover script
│
├── screenshots/            # Playwright visual evidence PNGs
│   ├── l1_step1_baseline.png            # L1 clean baseline cockpit
│   ├── l1_step2_bug_injected.png        # L1 visual occlusion defect injected
│   ├── l1_step5_healed.png              # L1 autonomous CSS layout healed
│   ├── l2_step1_baseline.png            # L2 baseline swarm takeoff (30m altitude)
│   ├── l2_step2_bug_injected.png        # L2 "Ghost on Land" desync bug injected
│   ├── l2_step5_healed.png              # L2 restored canonical selector & synced flight
│   ├── l2_state_desync_detected.png     # Full screen UI capture of anomaly
│   ├── l2_swarm_synchronized.png        # Full screen 3D Cesium synchronized flight
│   └── dashboard_level2_tab_updated.png # Dashboard Level 2 interface
│
├── synthesized_tests/      # Standalone Playwright tests generated dynamically by MIRA
│   ├── test_visual_unoccluded_controls.py # Targeted probe for visual occlusion
│   └── test_swarm_state_sync.py           # Targeted probe for multi-drone state reconciliation
│
└── audit_logs/             # Machine-readable audit trails and telemetry benchmarks
    ├── l1_demonstration_audit.json        # Level 1 closed loop audit metrics
    ├── l2_closed_loop_audit.json          # Level 2 closed loop audit metrics (5.37s probe)
    ├── l2_multidrone_audit.json           # Swarm performance and telemetry benchmarks
    └── findings.json                      # All evaluated primitives and defect findings
```

---

## ⚡ Instant Demo Commands

1. **Open Executive Dashboard:**
   Open browser at: `http://127.0.0.1:5050`
   Navigate to the **Level 2: Multi-Drone Swarm & Performance Sync** tab.

2. **Run the Synthesized Swarm Test:**
   ```powershell
   python showcase\synthesized_tests\test_swarm_state_sync.py
   ```
   *Result:* `TEST PASSED: Drone 1 operational state is 100% synchronized with flight controller.`

3. **Run Full Test Suite:**
   ```powershell
   python -m unittest discover tests
   ```
   *Result:* `Ran 8 tests ... OK`

4. **Run Live Autonomous Closed-Loop Engine:**
   ```powershell
   python -m mira.l2_healer
   ```
   *Result:* Runs all 6 phases and verifies targeted probe in ~5.3s (skipping 14 redundant tests).
