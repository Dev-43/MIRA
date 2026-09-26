# Live Application Inspection Report: FlytBase Drone Cockpit & Control Panel

> **Generated:** September 26, 2026  
> **Inspection Engine:** Playwright Chromium (Headless) + Network Probes  
> **Target Environment:** Docker Local Stack (Ports 4010, 4000, 8889)

---

## 1. System Health & Endpoint Status

| Service | Endpoint | HTTP Status | Backend State / Uptime |
|---|---|---|---|
| **Cockpit Frontend** | `http://localhost:4010` | `200 OK` | React 18 + Vite + Cesium Map + WebRTC Video |
| **Control Dashboard** | `http://localhost:4000/dashboard` | `200 OK` | Simulator controls, drone fleet, fault injection |
| **Backend API Health** | `http://localhost:4000/api/health` | `200 OK` | `{"status": "ok", "simulator": "connected", "video": "up"}` |
| **Video Stream (WHEP)** | `http://localhost:8889` | `200 OK` | MediaMTX WebRTC Stream Engine |

Visual artifacts captured during inspection:
* Desktop Cockpit: [`evidence/cockpit_desktop.png`](file:///d:/MIRA/evidence/cockpit_desktop.png)
* Mobile Cockpit (375×667): [`evidence/cockpit_mobile.png`](file:///d:/MIRA/evidence/cockpit_mobile.png)
* Control Dashboard: [`evidence/control_dashboard.png`](file:///d:/MIRA/evidence/control_dashboard.png)
* Raw JSON Snapshot: [`evidence/live_check_raw.json`](file:///d:/MIRA/evidence/live_check_raw.json)

---

## 2. Cockpit Architecture (`http://localhost:4010`)

### 2.1 Layout Breakdown

The live Cockpit consists of three main regions:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Top Banner: "FlytBase Cockpit" | Badge: "socket connected" | "Control panel →" │
├─────────────────────────┬──────────────────────────────────────────────┤
│ SIDEBAR (Complementary) │ MAIN VIEW                                    │
│                         │                                              │
│ • DEVICES (4 drones)    │ • Map Controls: [ 2D ] [ 3D (active) ]       │
│   - Drone 1 · Dock 1    │ • Cesium 3D Globe with Drone/Dock Entities   │
│   - Drone 2 · Dock 2    │                                              │
│   - Drone 3 · Dock 3    │ • Floating Video Tile (bottom right):        │
│   - Drone 4 · Dock 4    │   "FPV · Drone 1" | Badge: "live"            │
│                         │   (MediaMTX WebRTC aerial loop)              │
│ • DRONE TELEMETRY       │                                              │
│   (Selected: Drone 1)   │                                              │
│   - Battery: 100%       │                                              │
│   - Altitude RLT: 0.0m  │                                              │
│   - Altitude AGL: 0.0m  │                                              │
│   - Altitude ASL: 560m  │                                              │
│   - H-Speed: 0.0 m/s    │                                              │
│   - V-Speed: 0.0 m/s    │                                              │
│   - Heading: 47°        │                                              │
│   - Wind: NW 2.4 m/s    │                                              │
│   - Dist home: 0m       │                                              │
└─────────────────────────┴──────────────────────────────────────────────┘
```

### 2.2 Semantic Accessibility Snapshot (ARIA Tree)

* **Banner:**
  * Text: `FlytBase Cockpit`
  * Status Badge: `socket connected`
  * Navigation Link: `Control panel →` (`http://localhost:4000/dashboard`)
* **Complementary Sidebar:**
  * Heading: `Devices` [level 2]
  * List:
    * `Drone 1` (`dock-1`, `dock closed`, `standby`)
    * `Drone 2` (`dock-2`, `dock closed`, `standby`)
    * `Drone 3` (`dock-3`, `dock closed`, `standby`)
    * `Drone 4` (`dock-4`, `dock closed`, `standby`)
  * Heading: `Drone Telemetry · Drone 1 standby` [level 2]
    * Term/Definition pairs for: Battery, Altitude (RLT/AGL/ASL), H-Speed, V-Speed, Heading, Wind, Distance from home.
* **Main Container:**
  * Group `Map view`: Toggle buttons `2D` and `3D [pressed]`
  * Text / Video Tile: `FPV · Drone 1 live`

---

## 3. Responsive Analysis: Desktop vs. Mobile (375×667)

When inspected under phone viewport constraints (iPhone SE: 375×667):
* **Sidebar Overlap:** The `Devices` list and `Drone Telemetry` cards consume the entire initial viewport height.
* **Map Obscurity:** The Cesium 3D canvas is forced below or behind the telemetry cards.
* **Action Vulnerability:** On small devices, interactions require heavy scrolling, and high-priority action alerts or video tiles are pushed off-screen.
* **Key Test Scenario:** Verifying that critical actions remain visible and actionable without horizontal clipping or overlapping interactive buttons.

---

## 4. Control Panel Architecture (`http://localhost:4000/dashboard`)

The Control Panel provides complete programmatic command and fault injection controls:

### 4.1 Simulator & Fleet Controls
* **Simulator State:** `Start`, `Stop`, `Reset`, Speed multiplier (`1x`, `2x`, `5x`).
* **Add Drone:** Name, Latitude, Longitude, `Add drone + dock`.
* **Global Video:** `Start all video`, `Stop all video`.
* **Per-Drone Actions (Drones 1–4):**
  * `Take off` (triggers flight state machine from `standby` → `taking_off` → `in_flight`)
  * `Land` (disabled in standby, active during flight)
  * `Stop video`
  * `Remove`

### 4.2 Built-in Fault Injection Suite
The control panel exposes 10 distinct fault triggers under `/api/control/fault`:

| Category | Trigger Button | Backend Endpoint / Payload | Testing Purpose |
|---|---|---|---|
| **Socket** | `Kick all clients` | `POST /api/control/fault` `{"kind": "socket-kick"}` | Test client auto-reconnection & stale toast handling |
| **Socket** | `Refuse connections` | `POST /api/control/fault` `{"kind": "socket-refuse"}` | Test UI degradation when server rejects handshake |
| **Simulator** | `Simulator offline` | `POST /api/control/fault` `{"kind": "sim-offline"}` | Test if UI detects simulator death vs showing fake live |
| **Telemetry** | `Delay telemetry` | `POST /api/control/fault` `{"kind": "socket-delay"}` | Test lag handling, timestamp freshness, and out-of-order data |
| **Telemetry** | `Drop telemetry` | `POST /api/control/fault` `{"kind": "socket-drop"}` | Test packet loss tolerance and missing attribute warnings |
| **Video** | `Freeze` | `POST /api/control/fault` `{"kind": "video-freeze"}` | Test if video tile detects frozen frames vs showing "live" |
| **Video** | `Stutter (3 fps)` | `POST /api/control/fault` `{"kind": "video-stutter"}` | Test low frame rate degradation detection |
| **Video** | `Degrade (320x180)` | `POST /api/control/fault` `{"kind": "video-degrade"}` | Test visual resolution degradation detection |
| **Video** | `Flicker` | `POST /api/control/fault` `{"kind": "video-flicker"}` | Test video glitch / frame loss detection |
| **Reset** | `Clear all faults` | `POST /api/control/fault` `{"kind": "clear"}` | Clean state restoration between test cases |

---

## 5. Direct Test Assertions for Level 1 Mutations

With the live UI and fault endpoints fully cataloged, here are the exact automated assertions our agent will run:

1. **Simulator Disconnection vs. UI Badge:**
   * Action: `POST /api/control/fault {"kind": "sim-offline"}`
   * UI Assertion: The Cockpit badge MUST transition from `socket connected` / `live` to an error/offline state. If it stays green or keeps displaying live telemetry, **FLAG AS MUTATION/BUG**.
2. **Flight Telemetry Progression:**
   * Action: `POST /api/control/command {"deviceId": "drone-1", "action": "takeoff"}`
   * UI Assertion: Telemetry header must update from `standby` to `taking_off` and `Altitude RLT` must rise from `0.0 m` to `30.0 m`.
3. **WebRTC Video Freeze Detection:**
   * Action: `POST /api/control/fault {"kind": "video-freeze"}`
   * UI Assertion: If video frames stall, the FPV tile badge must NOT claim `live` without an alert.
4. **Mobile Viewport Action Availability (375×667):**
   * Action: Resize to 375×667.
   * UI Assertion: Control panel link, device selection, and telemetry cards must remain within viewport bounds with no clipped text or obscured controls.
