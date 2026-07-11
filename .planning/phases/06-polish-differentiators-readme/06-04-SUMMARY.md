---
phase: 06-polish-differentiators-readme
plan: 04
subsystem: testing
tags: [hey, docker-compose, load-test, perf, bash]

requires:
  - phase: 06-polish-differentiators-readme
    provides: baseline load-test script and benchmark metrics from 06-01
provides:
  - Fixed hey status-line parsing for non-200 majority guard
  - Dual raw and host-normalized peak CPU reporting
  - Compose app benchmark tuning (TORCH_NUM_THREADS=2, 2-core CPU limit)
affects:
  - 06-05 re-benchmark and README evidence table

tech-stack:
  added: []
  patterns:
    - "Status distribution line sum for total request count (not Total: duration)"
    - "Peak CPU normalized by nproc for PERF-03 host-core interpretation"

key-files:
  created: []
  modified:
    - scripts/load-test.sh
    - tests/test_load_test_script.py
    - docker-compose.yml

key-decisions:
  - "Sum indented [CODE] N responses lines for TOTAL_REQUESTS instead of parsing Total: duration field"
  - "Report both raw docker stats CPUPerc and peak/nproc normalized % for honest PERF-03 evaluation"
  - "Align compose app cpus: 2.0 and TORCH_NUM_THREADS default 2 with K8s PERF-04 pattern"

patterns-established:
  - "load-test.sh contract tests use inline hey fixtures plus script source assertions"

requirements-completed: [PERF-01, PERF-03]

duration: 5min
completed: 2026-07-11
---

# Phase 6 Plan 04: Load-Test Parsing & Compose Tuning Summary

**Fixed hey output parsing bug, added host-normalized CPU reporting, and tuned compose app resources for reproducible re-benchmark in 06-05**

## Performance

- **Duration:** 5 min
- **Started:** 2026-07-11T00:57:00Z
- **Completed:** 2026-07-11T01:02:07Z
- **Tasks:** 2 completed
- **Files modified:** 3

## Accomplishments

- load-test.sh non-200 majority guard now sums status distribution counts instead of mis-reading `Total:` duration as request count
- Peak CPU reporting prints raw docker stats % and host-normalized % (`peak / nproc`) for PERF-03 gap closure
- docker-compose app service tuned with `TORCH_NUM_THREADS=${TORCH_NUM_THREADS:-2}`, `cpus: "2.0"`, and `mem_limit: 2g` matching K8s limits

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix hey output parsing and add normalized CPU reporting** - `e4165d6` (test RED), `889041c` (feat GREEN)
2. **Task 2: Apply compose benchmark tuning** - `5518457` (feat)

**Plan metadata:** pending (docs commit)

## Files Created/Modified

- `scripts/load-test.sh` — Status-line sum parsing; dual raw/normalized peak CPU output
- `tests/test_load_test_script.py` — Fixture parsing tests and normalized CPU contract assertions
- `docker-compose.yml` — App benchmark tuning env and resource limits

## Decisions Made

- Sum all `[CODE] N responses` lines for total request count; keep non-200 guard threshold at majority of that sum
- Use `nproc` with fallback to 1 for normalized CPU; one decimal place via awk
- Mirror K8s deployment limits (2 CPU, 2Gi memory) in compose for fair compose-vs-K8s comparison

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 06-05 can restart compose stack and re-run `./scripts/load-test.sh` with corrected parsing and tuned resources
- README evidence table (06-05) should cite both raw and normalized CPU columns

## Verification Results

- `uv run pytest tests/test_load_test_script.py -x` — 7 passed
- `docker compose config -q` — valid
- `grep -v '^#' scripts/load-test.sh | grep -c 'nproc'` — 1
- No `grep -E '^Total:' ... awk '{print $2}'` pattern in script

## Self-Check: PASSED

- FOUND: scripts/load-test.sh
- FOUND: tests/test_load_test_script.py
- FOUND: docker-compose.yml
- FOUND: e4165d6
- FOUND: 889041c
- FOUND: 5518457

---
*Phase: 06-polish-differentiators-readme*
*Completed: 2026-07-11*
