# BUILD_SOLO.md — Devesh (Solo, Task-Ordered, Not Time-Ordered)
> ⚠️ AGENT INSTRUCTIONS: Build tasks IN ORDER. Do not start task N+1 until task N's acceptance
> test passes. If time runs out, stop at the last fully-passing task — a shorter chain of
> working tasks beats a longer chain of half-built ones, since every task here maps directly
> to something the submission doc or demo video needs.

---

## Priority Rule If Time Runs Out
Tasks 1–7 are the minimum viable submission (2 scenario primitives fully working end-to-end
with video + a hand-written doc). Tasks 8–11 add the remaining 3 primitives and automation.
Task 12 (Neo4j memory) is the first thing to cut — the detection pipeline must work with it
disabled; it never gates a finding.

---

## TASK 0 — Environment
**Build:** Confirm Docker starter kit running (`docker compose up --build` already done),
Neo4j Desktop running, `.env` filled, `pip install playwright neo4j python-dotenv google-genai openai`,
`playwright install chromium`.
**Acceptance:** Cockpit loads at `:4010` (socket connected, 4 drones visible), control panel
loads at `:4000/dashboard`, `python -c "from neo4j import GraphDatabase; print('ok')"` prints ok,
one successful Gemini test call.

---

## TASK 1 — graph.py (generic schema)
**Build:** `mira/graph.py` implementing the Neo4j schema from BUILD.md exactly — `Site`,
`Page`, `Element`, `LiveField` nodes, no app-specific fields anywhere.
Functions: `get_driver()`, `upsert_site()`, `upsert_page()`, `upsert_element()`,
`upsert_livefield()`, `get_elements_for_page()`, `get_livefields_for_page()`, `is_site_known(site_id)`.
**Acceptance:** Round-trip test — write one fake Page+Element+LiveField, read them back, values match.

---

## TASK 2 — explorer.py (generic crawler, no hardcoded pages)
**Build:** Given `--target URL`, same-origin BFS crawl up to depth 3 or 15 pages (whichever
first), following `<a href>` and same-origin `fetch`-triggering nav only if reachable via a
click (no manual URL guessing beyond what's linked). For each page: accessibility snapshot →
flatten to elements (role in button/textbox/link/heading/checkbox/tab, non-empty name) →
`upsert_element`. LiveField discovery: take two full-page screenshots 3s apart with no
interaction, diff regions (simple pixel-block diff, e.g. 32x32 grid), any region that changed
becomes a candidate LiveField; grab nearby text for `label_text`, check against the freshness
wordlist for `freshness_claim`.
**Acceptance:** Run against the cockpit — must discover the cockpit page(s), at least one
LiveField (e.g. a telemetry number or the video tile region) with `freshness_claim` populated,
and write all of it to Neo4j without any code path that names "drone" or "telemetry" explicitly.
Re-run against any second, completely different site (e.g. a public news homepage) with zero
code changes and confirm it also discovers pages/elements there.

---

## TASK 3 — auth_gate.py (rule-based, no vision, judge-bait priority #1)
**Build:** After exploration, for each discovered Page URL, open a **fresh unauthenticated
browser context** (no cookies/join-flow completed) and navigate directly to that URL. Compare
the resulting page's discovered elements/title against the authenticated version. If the
unauth version exposes the same or materially similar interactive content (not a login/join
redirect), emit a finding with `verdict: security_violation`.
**Acceptance:** Run against the cockpit both with and without completing the join flow first;
confirm it correctly distinguishes a properly-gated route from an exposed one. If the cockpit
gates everything correctly, this task's acceptance is "produces zero false positives on a
correctly-gated app" — verify by intentionally testing against a route you know is public
(e.g. a marketing/login page) to confirm it does NOT flag that.

---

## TASK 4 — staleness.py (rule-based, no vision)
**Build:** For each `LiveField` with `freshness_claim` set, poll the region again after a
configurable wait (default 8s). If the underlying value/pixel-hash has NOT changed but the
freshness_claim label is still present and unchanged, emit a finding with `verdict: bug`
(or `needs_review` if the field plausibly updates on a longer natural interval — flag both
paths, let vision judge disambiguate only if this task's simple threshold is ambiguous, per
BUILD.md's DO NOT section, but the default threshold check should not need it).
**Acceptance:** Run against the cockpit with no fault injected — must NOT flag telemetry that
is actually updating normally (no false positive). Then use `demo/control_client.py` to
inject a video/telemetry freeze and confirm the same code — unmodified — now flags it.

---

## TASK 5 — responsive_reachability.py (rule-based, no vision)
**Build:** For each Element classified as a primary action (heuristic: `role=button`, and
either it's the only enabled button on the page, or its bounding box was in the top 30% of
page height at desktop width), re-check its bounding box at 375px viewport width. Flag if
box.x + box.width > viewport.width, or box is fully outside the visible scroll region, or
box.height/width falls under a minimum tap-target threshold (44x44px, standard mobile a11y
guideline).
**Acceptance:** Run at both 1440px and 375px against the cockpit; confirm it reports the
actual state of the primary action controls at mobile width, correctly, with no manual
per-app coordinates hardcoded.

---

## TASK 6 — vision_judge.py (Gemini primary, NIM fallback, generic prompts)
**Build:** Single function `judge(screenshot_bytes, context: dict) -> dict` where `context`
contains only generic fields (`region_description`, `claimed_state`, `observed_change`) —
never app-specific text. Prompt template:
```
You are inspecting a UI region. A status/label claims: "{claimed_state}".
Independent observation of the same region over time shows: "{observed_change}".
Does the visible evidence support the claimed state? Answer with one of:
bug | intentional_redesign | needs_review, plus one sentence of reasoning.
Return ONLY valid JSON: {{"verdict": str, "reasoning": str}}
```
Try Gemini 2.5-flash first; on any exception or 429, retry once, then fall back to NIM
vision model; if both fail, return `{"verdict": "needs_review", "reasoning": "vision judge unavailable"}`
— never crash the pipeline.
**Acceptance:** Pass one clearly-mismatched fake case and one clearly-fine fake case; confirm
correct verdicts. Force an exception (bad API key) and confirm graceful `needs_review` fallback,
no crash.

---

## TASK 7 — status_reality.py (vision-assisted, judge-bait priority #2)
**Build:** For each discovered status-style Element/LiveField (badge/label matching words like
`online, offline, connected, disconnected, live, active`), independently verify: for connection-type
badges, cross-check against actual socket/network activity if observable (e.g. no new WebSocket
frames for N seconds); for anything ambiguous, take before/after screenshots around a state
change and call `vision_judge.judge()`.
**Acceptance:** With no fault injected, confirm no false positive on the cockpit's normal
"connected"/drone-online badges. Trigger a fault via `control_client.py` (drone offline /
socket kick) and confirm this task — unmodified — detects the mismatch and calls it a bug.

---

## TASK 8 — action_efficacy.py (vision-assisted)
**Build:** For any button click performed during exploration or a scripted flow, capture
before/after DOM+screenshot; if a success indicator appears (toast, checkmark, state text)
but no other observable value changed, call vision judge with generic context; flag if it
confirms no real effect occurred.
**Acceptance:** Run one real action on the cockpit (e.g. select a drone) and confirm no false
positive; construct one deliberately broken case if possible (or note as `needs_review` if
the cockpit gives no easy way to fake this without the fault API) and confirm correct handling.

---

## TASK 9 — runner.py (orchestration)
**Build:** `run_mira.py --target URL [--cold]`. Logic: load .env → connect Neo4j → if
`is_site_known()` is false or `--cold`, run explorer fully; else run explorer's LiveField
sampling only (skip full re-crawl) → run all 5 primitives → for each finding, open a fresh
Playwright context with `record_video_dir` set, replay the minimal repro steps for that
finding, save the video → write `findings.json`.
**Acceptance:** `python run_mira.py --target http://localhost:4010 --cold` completes without
error and produces at least one `.webm` file per finding.

---

## TASK 10 — reporter.py (submission doc generator)
**Build:** Read `findings.json`, for each finding emit a markdown block:
```
### Scenario N: [primitive name, humanized] — [element_or_field.name]
**Description:** [observed] vs [expected]
**Approach:** [reasoning]
**Video:** [evidence_video path — replace with your upload link before submitting]
```
Concatenate into `SUBMISSION_DRAFT.md`, plus a short "System Design" section templated from
BUILD.md's Project Overview.
**Acceptance:** `SUBMISSION_DRAFT.md` exists, has one numbered scenario block per finding in
`findings.json`, in the exact field order the hackathon brief's table requires.

---

## TASK 11 — Demo control client (outside core, cockpit-specific, OK to hardcode here)
**Build:** `demo/control_client.py` — thin wrapper around `POST http://localhost:4000/api/control/*`
for `sim-offline`, `socket-kick`, `video-freeze`, `socket-delay`, `takeoff`, `land`. Used only
to manufacture fault conditions for recording Tasks 4/7's demo videos. Never imported by
anything under `mira/`.
**Acceptance:** Each function returns 200 and the cockpit visibly reflects the fault within
a few seconds when watched manually.

---

## TASK 12 — Neo4j memory pass (cut first under time pressure)
**Build:** Confirm a second `run_mira.py --target http://localhost:4010` (no `--cold`) is
measurably faster (skips full re-crawl, only re-samples LiveFields and re-runs primitives)
and produces the same findings as the cold run when no fault is active.
**Acceptance:** Second run completes faster than the first; `findings.json` matches for the
no-fault case; explicitly confirm the pipeline still fully produces findings.json + videos
even with Neo4j stopped (temporarily kill the Neo4j service and re-run to prove this).

---

## TASK 13 — Video + submission finishing (use once code is done)
Once Tasks 1–10 pass: for each finding, review its auto-recorded `.webm`, trim to a clean
scenario clip, upload each somewhere linkable (not embedded in the doc), paste links into
`SUBMISSION_DRAFT.md` replacing the local paths, finalize as the one evaluation document.
This is a separate pass — do not start it until the detection pipeline (Tasks 1–9) is done,
since a polished video of a broken finding is wasted effort.
