# MIRA Pivot Plan: FlytBase Agentic Software Testing Hackathon

> **Date:** September 26, 2026  
> **Target Application:** FlytBase Drone Cockpit (`flytbase-ahc-swe-qa-hackathon`)  
> **Source Brief:** `AHC SWE Hackathon - Agentic Software Testing.docx`

---

## 1. Executive Summary & The Core Pivot

### What We Planned Before (Old MIRA)
- **Target App:** A local static 3-page toy app (`mock-app/`: Login, Dashboard, Settings).
- **Core Strategy:** DOM accessibility role+name diffing stored in Neo4j Desktop, passing text diffs to Gemini to detect element renames or missing buttons.
- **Why It's Insufficient for the Hackathon:**
  1. The hackathon does **not** evaluate against a toy HTML form. The challenge is testing a **Live Incident Response Drone Cockpit** with 3D Cesium maps, high-frequency Socket.io telemetry, and live WebRTC aerial video streams.
  2. The hackathon explicitly states: *"Operating the browser is the easy part. The hard part is knowing what correct behaviour means to the user... judge behaviour by meaning, not by exact text, pixels or element selectors."*
  3. Neo4j graph diffs of DOM nodes cannot verify if a drone on a 3D map is in the right location, whether a WebRTC video tile is frozen/black, whether telemetry values are stale dashes, or whether layout collapses on a mobile viewport.
  4. The evaluation requires **real-time video recordings of every test scenario**. A test without a video is disqualified.

### What the Hackathon Demands (The Real Challenge)
- **Domain:** Live Incident Response (fires, security breaches, search & rescue).
- **System Under Test:**
  - **Frontend (`:4010`):** React 18, Vite 5, Cesium map, telemetry cards, WebRTC video tile (MediaMTX).
  - **Backend (`:4000`):** Express + Socket.io, retained topic telemetry, Control REST API.
  - **Control Dashboard (`:4000/dashboard`):** Allows programmatic fault injection (`socket-kick`, `sim-offline`, `video-freeze`, `socket-delay`, etc.) and drone operations (`takeoff`, `land`).
  - **Simulator:** Flight state machine generating simulated telemetry.
- **Evaluation Focus (Level 1 Mutations):**
  - **Visual & Semantic:** Offline drone displayed as online; status badge mismatch.
  - **Responsive Layout:** Main action pushed off screen at mobile viewport (e.g. 375px).
  - **Functional & Security:** Unauthenticated access allowed; missing action buttons.
  - **Data & Telemetry:** Stale dashes (`—`) vs live values; telemetry out of sync with map/video.
  - **Media:** Video feed frozen/degraded while badge falsely claims "live".
- **Deliverables:**
  1. **System Design Document:** Architecture of the autonomous testing agent.
  2. **Scenario Submissions:** Numbered list of test scenarios with **mandatory screen recording videos**, reproducibility steps, and semantic verdict evidence.

---

## 2. Status of OpenCode in the Active Terminal

- **Process:** PID 17772 (`opencode`) running in `d:\MIRA`.
- **Model:** `nvidia/nemotron-3-ultra-550b-a55b` via NVIDIA provider.
- **What Happened:**
  - OpenCode analyzed the docx and starter kit codebase.
  - The user asked: `can you make an md file of you finding and all you gave right now?`
  - OpenCode switched into `plan` mode (which enforces read-only access) and was blocked from writing files to `d:\MIRA`, causing it to stall while attempting to resolve file permissions.
- **Resolution:** This document (`HACKATHON_PLAN_PIVOT.md`) consolidates all findings, architecture decisions, and roadmap so development can proceed without losing context.

---

## 3. Detailed Gap Analysis: Old Plan vs. Hackathon Brief

| Dimension | Previous Plan (Old MIRA) | Hackathon Brief Requirement | Gap & Required Adjustment |
|---|---|---|---|
| **Target App** | Toy `mock-app` (Login/Dashboard/Settings HTML) | Live Incident Drone Cockpit (`flytbase-ahc-swe-qa-hackathon`) | Complete shift to Cockpit UI (React + Cesium + WebRTC + Sockets) |
| **Fault Injection** | Static mutated HTML files (`index_v2.html`) | Dynamic backend control API (`/api/control/fault`, `/api/control/command`) | Build automated Python client for backend control API |
| **Verification Method** | DOM accessibility tree diffing + Neo4j | Multimodal Vision reasoning + state cross-validation | Add Vision LLM (NVIDIA NIM Llama-3.2-Vision or Gemini 2.0 Flash) to evaluate screenshots |
| **Map & Video Testing** | None | Cesium 3D canvas + WebRTC video player | Visual inspection of canvas rendering + stream status indicators |
| **Responsive Testing** | Fixed desktop viewport | Mobile (375px), Tablet (768px), Desktop (1440px) | Playwright multi-viewport automated matrix |
| **Evidence & Output** | `mira_report.json` + terminal logs | **Playwright screen recording videos (MANDATORY)** + before/after screenshots + structured scenario reports | Enable Playwright `recordVideo` in browser contexts and export per scenario |

---

## 4. Target Problem Categories from Hackathon Brief

The evaluation judges scenarios across these official categories:
1. **Visual UI:** Required action missing, clipped content, conflicting status badges.
2. **Responsive UI:** Workflow works on desktop but primary action unusable on phone.
3. **Functional UI:** Action claims success but fails to execute.
4. **API & Data:** Changes lost on refresh, API contract mismatch breaking UI.
5. **Map & Geospatial:** Drone in wrong position, stale coordinates looking active.
6. **Video & Media:** Source switched but stream unchanged; dropped feed still says "live".
7. **Telemetry:** Mismatched source, out of order telemetry, dashes shown during active connection.
8. **Network & Recovery:** Recovery after socket disconnect or reconnect failure.
9. **Security & Permissions:** Unauthenticated access allowed to restricted views.

---

## 5. Revised Architecture: MIRA-FlytBase Testing System

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      MIRA-FlytBase Testing Agent                         │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ Playwright Runner│       │  Control Client  │       │   Vision Judge   │
│ (Multi-Viewport) │       │ (Backend API)    │       │ (NIM / Gemini)   │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│ • Desktop 1440px │       │ • POST /fault    │       │ • Screenshot OCR │
│ • Mobile 375px   │       │ • POST /command  │       │ • Semantic check │
│ • Video recorder │       │ • POST /sim reset│       │ • Layout audit   │
│ • Canvas snapshot│       │ • GET /health    │       │ • Verdict JSON   │
└────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       Scenario Runner & Evidence Engine                  │
├──────────────────────────────────────────────────────────────────────────┤
│ 1. Reset Sim & Verify Initial Baseline                                   │
│ 2. Trigger Action / Inject Fault via Control API or UI                   │
│ 3. Capture Live Screenshots & Inspect DOM / Telemetry                    │
│ 4. Vision Judge Evaluates Semantic Validity                              │
│ 5. Compile Video (.webm/.mp4) + Findings JSON + Submission Markdown      │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Priority Scenarios for Evaluation (Level 1 + Core Quality)

### Scenario 1: Offline Drone Displayed as Online (Visual / Telemetry Conflict)
- **Mutation / Trigger:** Inject `sim-offline` or disconnect socket via Control API.
- **Expected Behavior:** UI immediately reflects disconnect/stale state, alerts user.
- **Bug Detected:** UI badge still says "Connected" or drone marker remains bright green with stale altitude/speed.
- **Evidence:** Before/after screenshots, video showing fault injection and UI lag/failure.

### Scenario 2: Main Flight Action Collapsed on Mobile Viewport (Responsive UI)
- **Mutation / Trigger:** Set browser viewport to 375x667 (iPhone SE).
- **Expected Behavior:** Takeoff/Land controls, device drawer, and telemetry remain accessible and tap-target compliant.
- **Bug Detected:** Action buttons pushed off screen, overlapping Cesium canvas, or non-scrollable.
- **Evidence:** Full-page mobile screenshot + video demonstrating clipped interactive elements.

### Scenario 3: Video Stream Dropped While Status Shows "Live" (Media / Video)
- **Mutation / Trigger:** Inject `video-freeze` or stop MediaMTX stream via `/api/control/fault`.
- **Expected Behavior:** Video tile indicates "Reconnecting" or "Stream Lost".
- **Bug Detected:** Video tile label continues showing green "LIVE" badge despite black/frozen feed.
- **Evidence:** Video recording showing frozen frames alongside active live indicator.

### Scenario 4: Telemetry Data Dropout / Stale Dashes (Data Integrity)
- **Mutation / Trigger:** Inject `socket-delay` or `socket-drop`.
- **Expected Behavior:** Telemetry cards gracefully handle dropped packets without crashing or displaying meaningless defaults.
- **Bug Detected:** Telemetry displays unhandled `NaN` or raw dashes without warning badges.

### Scenario 5: Unauthorized Route / Cockpit State Access (Security)
- **Mutation / Trigger:** Direct URL navigation to protected views without active incident session.
- **Expected Behavior:** Redirect to join/entry flow.
- **Bug Detected:** Direct cockpit exposure without session context.

---

## 7. Implementation Roadmap & Next Steps

1. **Step 1: Test Infrastructure Setup**
   - Ensure Docker starter kit runs (`docker compose up -d` or node mode).
   - Verify Cockpit (`http://localhost:4010`) and Control API (`http://localhost:4000/api`).

2. **Step 2: Core Python Agent Modules (`mira_flytbase/`)**
   - `api/control_client.py`: Python client for all `/api/control/*` commands and fault injections.
   - `runner/browser_runner.py`: Playwright runner configured with video recording and viewport switching.
   - `judge/vision_judge.py`: Multimodal evaluation using NVIDIA NIM / Gemini 2.0 Flash.

3. **Step 3: Automated Scenarios & Evidence Packager**
   - Script 5 reproducible mutation scenarios.
   - Auto-generate the final evaluation document with embedded scenario links, descriptions, and video files.

---

## 8. Open-Source (OS) Resources & Accelerated Stack Integration

The hackathon brief curates 7 open-source tools, 6 SOTA research papers, and 6 keynote sessions. Integrating these patterns eliminates ~80% of testing boilerplate:

### Curated OS Tools & Frameworks from the Brief

| Tool | Source | Role in Our System |
|---|---|---|
| **[Midscene](https://github.com/web-infra-dev/midscene)** | ByteDance (`web-infra-dev/midscene`) | **Visual Semantic Assertion Engine**: Instead of fragile DOM selectors for 3D Cesium canvas and WebRTC video tiles, assert UI state via multimodal vision (`assert_visual("Is drone altitude live and visible?")`). |
| **[Stagehand](https://www.stagehand.dev/)** | Browserbase | **AI Browser Automation SDK**: Natural language browser actions and self-healing locators on Playwright. |
| **[agent-browser](https://github.com/vercel-labs/agent-browser)** | Vercel Labs | Ultra-fast CLI browser runner for AI coding agents. |
| **[Playwright Test Agents](https://playwright.dev/docs/test-agents)** | Microsoft Playwright Team | Native test planner, generator, and self-healing agent suite. |
| **[Bug0 Passmark](https://github.com/bug0inc/qa-agent)** | `bug0inc/qa-agent` | Plain-English regression test execution with memory caching. |
| **[Agentic QE](https://github.com/proffesor-for-testing/agentic-qe)** | `proffesor-for-testing/agentic-qe` | Autonomous QA agent fleet designed to work alongside coding agents. |
| **[Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp)** | Chrome DevTools Team | Deep inspection of browser network requests, WebSocket frames, DOM trees, and console errors. |

### Theoretical Blueprint & Mutation Strategy

* **Meta's Just-in-Time & Mutation-Guided Testing:**
  * *Papers:* [Arxiv 2601.22832](https://arxiv.org/pdf/2601.22832) & [Arxiv 2602.11724](https://arxiv.org/pdf/2602.11724)
  * *Application:* We use FlytBase's `/api/control/fault` as an automated mutation generator to verify our agent catches real-time regressions deterministically.
* **Cognition (Devin) & Shopify Architecture:**
  * Verifier-centric agent architectures and handling asynchronous real-time frontend states without flakiness.

### How the Integrated Stack Accelerates Delivery

1. **Zero Manual Video Overhead:** Playwright context natively records `.webm` videos per scenario (`record_video_dir`), satisfying the mandatory hackathon submission criteria automatically.
2. **Robust Visual Assertions on Canvas/Video:** Midscene-style prompt-based assertions with Gemini 2.0 Flash / NVIDIA NIM (`meta/llama-3.2-90b-vision-instruct`) verify the 3D map and video feeds without relying on brittle DOM trees.
3. **Automated Submission Output:** Directly writes scenario videos, before/after screenshot comparisons, and verdict JSON into an evaluation package.

