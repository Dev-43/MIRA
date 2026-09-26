# BUILD.md — MIRA-Web (Generic Agentic UI Testing System)
> ⚠️ AGENT INSTRUCTIONS: Build ONLY what is listed here. Do not add features, do not infer
> requirements, do not improve on the spec. If unclear, output `// UNCLEAR: [question]` and stop.
> Do not proceed past unclear points. Do not hardcode any string, selector, field name, or concept
> that only makes sense for one specific website. Every module must be testable against a site
> MIRA has never seen before, with zero code changes.

---

## Project Overview

MIRA-Web is an autonomous frontend testing agent that works on **any web application**,
not a specific one. On first contact with a site it explores generically (crawls same-origin
links, inventories interactive elements, samples anything that appears to update live),
writes what it found to a Neo4j memory graph, then applies five **generic detection
primitives** to what it discovered. None of the primitives contain app-specific vocabulary —
they operate on roles, labels, timestamps, and visual regions, never on words like "drone" or
"telemetry." The system is demoed against the FlytBase drone cockpit, but the cockpit is a
**test target**, never a dependency.

Differentiators for judging: (1) genuinely site-agnostic — same code catches the same bug
classes on any app; (2) memory-backed — a second run against the same site is faster/cheaper
because it diffs against what it already knows; (3) every finding auto-produces a video +
a draft scenario write-up in the exact format the submission requires.

---

## Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| Browser automation | Playwright (Python, sync API) | `record_video_dir` per context — mandatory video output |
| Graph memory | Neo4j Desktop | bolt://localhost:7687, local only |
| Vision/semantic judge | Gemini 2.5-flash (primary) | Free tier, accepts images directly |
| Vision judge fallback | NVIDIA NIM `meta/llama-3.2-90b-vision-instruct` | Used only if Gemini rate-limits mid-run |
| Language | Python 3.11+ | |
| Target under test | Any URL passed as `--target` | Never hardcoded; cockpit used only for demo runs |

---

## Shared Contracts (must be honored by every module)

### Neo4j Graph Schema
```
(:Site {id, base_url, last_explored})
(:Page {id, url, title, last_seen})
(:Element {id, role, name, page_id, last_seen, status})
(:LiveField {id, page_id, region_bbox, label_text, last_value_hash, last_changed_ts, freshness_claim})

(:Site)-[:HAS_PAGE]->(:Page)
(:Page)-[:HAS_ELEMENT]->(:Element)
(:Page)-[:HAS_LIVEFIELD]->(:LiveField)
(:Element)-[:CHANGED_TO {run_id, old_name, new_name, verdict}]->(:Element)
```
`Site.id` = domain, so memory is naturally scoped per target app without any app-specific code.

### Element Identity Contract
Identical to prior MIRA: `(role, name)` tuple, Playwright accessibility role + accessible name.
Never CSS selector or XPath. This was already generic — kept unchanged.

### LiveField Discovery Contract (NEW — replaces hardcoded "telemetry" concept)
A LiveField is *any* DOM region whose rendered text or pixel content changes across two
snapshots taken `LIVEFIELD_SAMPLE_INTERVAL_S` (default 3s) apart, during passive observation
with no user action. `freshness_claim` = any nearby badge/label matching a fixed generic
wordlist (`live, connected, online, active, current, streaming`) via case-insensitive text
match — never a hardcoded field name.

### Finding Schema (findings.json — replaces mira_report.json)
```json
{
  "run_id": "run_003",
  "target": "http://localhost:4010",
  "findings": [
    {
      "primitive": "status_reality | responsive_reachability | action_efficacy | staleness | auth_gate",
      "element_or_field": {"role": "...", "name": "...", "page_url": "..."},
      "observed": "plain-English description of what was seen",
      "expected": "plain-English description of what should happen",
      "verdict": "bug | intentional_redesign | needs_review | security_violation",
      "reasoning": "one paragraph, references the specific evidence",
      "evidence_video": "path/to/scenario_NNN.webm",
      "evidence_screenshots": ["before.png", "after.png"]
    }
  ]
}
```
This schema's fields map 1:1 to the submission doc's Title/Description/Approach/Video —
reporter.py generates the write-up directly from this, not as a separate manual step.

### Environment Variables (.env)
```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<set by dev>
GEMINI_API_KEY=<Google AI Studio key>
NVIDIA_API_KEY=<fallback vision key>
TARGET_URL=http://localhost:4010
```

### File Structure
```
mira_web/
├── BUILD.md
├── BUILD_SOLO.md
├── INTEGRATION.md
├── .env
├── requirements.txt
├── mira/
│   ├── __init__.py
│   ├── graph.py                  ← Neo4j read/write, generic schema above
│   ├── explorer.py               ← generic crawler + LiveField sampler, no hardcoded pages
│   ├── primitives/
│   │   ├── __init__.py
│   │   ├── status_reality.py     ← vision-assisted
│   │   ├── responsive_reachability.py   ← rule-based, no vision needed
│   │   ├── action_efficacy.py    ← vision-assisted
│   │   ├── staleness.py          ← rule-based, no vision needed
│   │   └── auth_gate.py          ← rule-based, no vision needed
│   ├── vision_judge.py           ← Gemini primary, NIM fallback, generic prompt templates
│   ├── runner.py                 ← orchestrates explore → primitives → judge → video
│   └── reporter.py               ← findings.json + scenario markdown generator
├── run_mira.py                   ← CLI entry point, takes --target URL
└── demo/
    └── control_client.py         ← FlytBase-specific fault injection, DEMO USE ONLY
                                     never imported by anything under mira/
```

---

## DO NOT Section
- Do not hardcode any page URL, field name, button label, or app concept anywhere under `mira/`
- Do not import `demo/control_client.py` from any file under `mira/` — it is a demo harness only
- Do not call the vision judge for `responsive_reachability`, `staleness`, or `auth_gate` — these
  are deterministic rule checks and calling vision on them wastes quota and adds flakiness
- Do not proceed to the next task in BUILD_SOLO.md before the current task's acceptance test passes
- Do not use async Playwright — sync API only
- Do not add a frontend/dashboard — JSON + generated markdown + video files only
- Do not skip video recording on any primitive run — a finding without video is not submittable
