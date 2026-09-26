# INTEGRATION.md — Module Contracts & Demo Path (MIRA-Web)

> Solo build — "integration" means the order modules are wired, and the exact data each
> module hands to the next. Build and acceptance-test each module standalone before wiring.

---

## Module Dependency Order

```
graph.py                    ← no dependencies. Build and test FIRST (Task 1).
     ↓
explorer.py                 ← depends on graph.py + Playwright (Task 2)
     ↓
auth_gate.py                ← depends on explorer.py output only (Task 3)
staleness.py                ← depends on explorer.py LiveField output only (Task 4)
responsive_reachability.py  ← depends on explorer.py Element output only (Task 5)
     ↓
vision_judge.py              ← no dependency on graph/explorer, pure function (Task 6)
     ↓
status_reality.py           ← depends on explorer.py + vision_judge.py (Task 7)
action_efficacy.py          ← depends on explorer.py + vision_judge.py (Task 8)
     ↓
runner.py                   ← wires graph + explorer + all 5 primitives + video capture (Task 9)
     ↓
reporter.py                  ← depends on runner.py's findings.json only (Task 10)
     ↓
demo/control_client.py       ← standalone, used manually/scripted to manufacture faults
                                for recording — never imported by the pipeline above
```

---

## Interface Contracts (exact data shapes)

### explorer.py → primitives (all 5)
Every primitive receives the same two lists, regardless of which site was explored:
```python
elements: list[dict]    # {id, role, name, page_url, bbox: {x,y,w,h}}
livefields: list[dict]  # {id, page_url, region_bbox, label_text, last_value_hash,
                         #  last_changed_ts, freshness_claim: bool}
```
No primitive receives or expects any field beyond this shape — this is what makes them
site-agnostic. If a primitive needs something not in this shape, that's a sign the shape
is missing something generic, not a reason to special-case one app.

### primitives → vision_judge.py (only status_reality, action_efficacy call this)
```python
context = {
    "region_description": str,   # e.g. "a status badge reading 'Connected'"
    "claimed_state": str,        # e.g. "connected"
    "observed_change": str,      # e.g. "no visual change across 3 samples over 9s"
}
judge(screenshot_bytes: bytes, context: dict) -> {"verdict": str, "reasoning": str}
```

### all primitives → runner.py
Every primitive returns the same finding shape (see BUILD.md's Finding Schema) — this is the
single contract runner.py depends on, regardless of which primitive produced it.

### runner.py → reporter.py
`findings.json` as specified in BUILD.md. reporter.py must not read anything else.

---

## What Each Module Must NOT Touch
| Module | Must NOT modify / import |
|---|---|
| explorer.py | vision_judge.py, primitives/, reporter.py |
| Any file in primitives/ | Each other's files, graph.py directly (read via explorer output only) |
| vision_judge.py | Neo4j, Playwright, filesystem, anything site-specific |
| runner.py | demo/control_client.py |
| reporter.py | Neo4j, Playwright, vision_judge.py |
| demo/control_client.py | Nothing under mira/ may import this — it is demo-only |

---

## Demo Path (once code passes Tasks 1–9)

1. `python run_mira.py --target http://localhost:4010 --cold` — cold run, builds graph,
   runs all primitives against the current (unfaulted) cockpit. Expect zero or near-zero
   findings here — this is your "baseline is clean" proof.
2. Manually trigger auth-gate check by opening a fresh incognito context to a cockpit URL
   without joining — Task 3's finding, if the app is vulnerable, or a clean pass if not.
   Either result is submittable evidence.
3. Use `demo/control_client.py` to trigger `sim-offline` or `socket-kick` on one drone.
4. `python run_mira.py --target http://localhost:4010` (warm run — Task 12's memory path) —
   should now surface the `status_reality` finding for that drone, faster than the cold run.
5. Use `demo/control_client.py` to trigger `video-freeze`.
6. Re-run — should surface the `staleness` finding on the video tile's LiveField.
7. Resize to 375px in a fresh run (or a dedicated responsive pass) — surfaces or clears
   Task 5's finding.
8. `python reporter.py` — produces `SUBMISSION_DRAFT.md` with one scenario block per finding
   from steps 2–7, ready for video links to be pasted in per Task 13.

---

## Known Integration Risks

| Risk | Mitigation |
|---|---|
| Cesium 3D canvas / WebRTC video tile aren't standard DOM — explorer's accessibility snapshot may under-discover them | LiveField's pixel-diff sampling (Task 2) is deliberately DOM-agnostic — it catches canvas/video regions by visual change, not by accessibility tree, specifically because of this |
| Vision judge (Gemini) rate-limited mid-demo | Task 6's NIM fallback; if both fail, `needs_review` never crashes the pipeline — a `needs_review` finding is still evidence of correct detection behavior, just weaker verdict confidence |
| Neo4j not running at demo time | Task 12 explicitly requires the pipeline to work with Neo4j down — memory is a speed/cost bonus, never a hard dependency |
| Time runs out before Task 9 (orchestration) | Tasks 3, 4, 5 can each be demoed standalone with a manual script — you don't strictly need runner.py wired to have submittable findings + videos for 3 of 5 primitives |
| A primitive fires a false positive on the untouched cockpit during the cold run | Each task's acceptance test explicitly requires a no-false-positive check on the baseline app before moving on — don't skip this even under time pressure, since false positives cost you on the Precision judging criterion directly |
