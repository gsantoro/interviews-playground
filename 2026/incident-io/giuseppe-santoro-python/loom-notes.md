# Loom Notes — On-Call Scheduling Take-Home

> ~5 minutes. Bullet points = talking cues, not a script.

---

## Intro (30s)

- Hi, I'm Giuseppe Santoro — senior platform engineer, applying for the platform engineering role at incident.io
- This is my Python take-home: given schedule entries + overrides, produce one flat list of who was *actually* on-call
- Coding done in **exactly one hour**; extra time = recording setup only
- Workflow: spoke thoughts aloud → **MacWhisper** transcribed → fed into **Claude Code**, which drafted implementation while I reviewed, directed, and refined
- Recording with **OBS** — Loom account setup failed, OBS is the alternative
- Notes attached to submission (`loom-notes.md`) for reference while reviewing

---

## Setup & tooling (15s)

- Personal conveniences I add to every project: `uv` (package manager), `ruff` (linter), `Taskfile` (task runner)
- Not required to review the code — the README's original instructions (`pip install`, `python3 main.py`, `pytest`) still work as-is

---

## Tests (15s)

- Unit tests for every method and all four requirements (overlaps, gaps, overrides, flatten)
- One functional test validates the full pipeline end-to-end: loads real `input.json`, runs `process_schedule`, verifies the output is gapless and spans the exact same window as the original schedule

---

## Overview (15s)

Three steps:
1. Validate schedule — no overlaps, no gaps
2. Validate overrides — no overlaps
3. Flatten schedule + overrides into one timeline

---

## Code structure (20s)

- The assignment already defined the contract: `input.json` in, `output.json` out, harness wired up
- I only filled in three methods: `process_schedule`, `_validate_entries`, `_flatten`
- Everything else — `load_data`, `write_output_json`, `ScheduleEntry`, `ScheduleData` — was already there and untouched
- The implementation fits exactly into the shape the README described; no extra abstractions, no scope creep

---

## `process_schedule` (30s)

- Orchestrates the full pipeline — the only public entry point
- **Order matters and is intentional:**
  1. Sort schedule by `start_at`
  2. Validate schedule (overlaps + gaps) — if broken, raise immediately
  3. Sort overrides by `start_at`
  4. Validate overrides (overlaps only)
  5. Pass both sorted lists to `_flatten`
- **Fail fast:** if the schedule is invalid there is no point sorting or validating overrides — we stop at the first error
- **Sort outside `_flatten`:** once both lists are sorted, `_flatten` reuses them as-is; sorting inside would either duplicate work or force a second pass

---

## `_validate_entries` (1m 30s)

**Algorithm**
- Classic interval problem
- Sort by `start_at`, then single pass comparing each entry to the previous one
- Two checks per pair:
  - `curr.start < prev.end` → **overlap** → raise immediately
  - `curr.start > prev.end` → **gap** → raise immediately (schedule only)
- Fail fast: stop at the first violation, no point continuing

**Design decisions**
- Single loop for both checks — half the iterations vs two separate passes; one traversal is enough
- `check_gaps=False` by default — overrides are allowed gaps (silence = original schedule applies)
- Sort lives in `process_schedule`, not inside this method — sorted lists reused by `_flatten`, no double sort
- Schedule validated first — if broken, raise before touching overrides

**Complexity**
- Sort: O(n log n)
- Loop: O(n), single pass
- Overall: O(n log n) — sort dominates

---

## `_flatten` (1m 30s)

**Algorithm**
- Two pointers: `s_idx` over schedule, `o_idx` over overrides
- `current_start` tracks how far into the current schedule entry we've consumed
- Each iteration: compare next override against current schedule entry

**Three cases per iteration**
1. No overrides left, or next override starts after this schedule entry ends
   → emit `(schedule_user, current_start, s.end_at)`, advance `s_idx`
2. Override starts after `current_start`
   → emit `(schedule_user, current_start, o.start_at)` — the prefix before the override
   → then fall through to case 3
3. Override overlaps
   → emit `(override_user, o.start_at, o.end_at)`
   → advance `current_start = o.end_at`, advance `o_idx`
   → inner `while` loop: advance `s_idx` past any schedule entries fully consumed by the override

**Concrete example**
- Schedule: User 1, 9am–5pm
- Override: User 2, 12pm–2pm
- Step 1: `current_start=9am`, overlap detected → emit User 1 9am–12pm
- Step 2: emit User 2 12pm–2pm, `current_start=2pm`
- Step 3: no more overrides → emit User 1 2pm–5pm
- Result: 3 entries ✓

**Edge case: override spanning multiple schedule entries**
- E.g. schedule has User 1 9am–12pm and User 2 12pm–5pm; override is 10am–3pm
- After emitting the override, inner `while` skips User 1 entirely (fully consumed)
- Picks up User 2 at `current_start=3pm`, emits User 2 3pm–5pm

**Complexity**
- Each pointer moves forward only — each entry visited at most once
- Merge: O(n + m)
- Overall (including upfront sort): O((n + m) log(n + m))
- This is optimal: must visit every entry at least once; comparison sort can't beat O(n log n)

---

## Wrap-up (10s)

- Sort, validate, flatten — ~60 lines of logic in one file
- Happy to answer questions
