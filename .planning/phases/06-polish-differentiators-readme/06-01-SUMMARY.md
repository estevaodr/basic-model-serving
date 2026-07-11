---
phase: 06-polish-differentiators-readme
plan: 01
subsystem: testing
tags: [hey, docker-compose, load-test, bash, pytest]

requires:
  - phase: 03-local-dev-stack-dashboards
    provides: compose stack with app/prometheus/grafana on localhost:8000
  - phase: 01-core-api
    provides: POST /predict multipart endpoint and health/ready probes
provides:
  - scripts/load-test.sh compose hey benchmark wrapper (D-01–D-05, D-07)
  - tests/test_load_test_script.py static script contract tests
  - benchmark evidence metrics for 06-03 README Performance Results table (DOC-05)
affects: [06-03-readme-polish, DOC-05]

tech-stack:
  added: [hey (external Go binary from github.com/rakyll/hey)]
  patterns:
    - "Pre-built multipart body file for hey -D (no native -F)"
    - "Background docker stats sampling during timed hey run"

key-files:
  created:
    - scripts/load-test.sh
    - tests/test_load_test_script.py
  modified: []

key-decisions:
  - "Literal hey -c 10 -z 60s flags in script body to satisfy static contract tests"
  - "Peak CPU reported as raw docker stats CPUPerc (can exceed 100% on multi-core hosts)"

patterns-established:
  - "Load-test script mirrors rollout-zero-downtime.sh bash conventions (set -euo pipefail, stderr errors)"
  - "Multipart boundary + sample.jpg body matches scripts/docker.py field name file"

requirements-completed: [PERF-01, PERF-02, PERF-03]

duration: 18min
completed: 2026-07-10
---

# Phase 6 Plan 01: Load-Test Script & Benchmark Summary

**Compose hey benchmark wrapper with contract tests; measured p50/p95/p99, RPS, 0% errors, and peak CPU on 8-core host (p95 exceeds 100ms SLO — flagged for honest README note in 06-03).**

## Performance

- **Duration:** 18 min
- **Started:** 2026-07-11T00:12:00Z
- **Completed:** 2026-07-11T00:30:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `scripts/load-test.sh`: validates hey + compose readiness, warm-up curl, multipart body from `sample.jpg`, 60s hey at 10 workers, peak CPU via docker stats
- Added `tests/test_load_test_script.py` static contract (hey flags, multipart, warm-up, stats, prerequisites)
- Ran end-to-end benchmark against healthy compose stack; captured raw hey output below for 06-03 README table

## Task Commits

Each task was committed atomically:

1. **Task 1: Load-test script contract tests and implementation** — `e486e1b` (test), `0b8541e` (feat)
2. **Task 2: Execute compose benchmark and capture evidence metrics** — no code changes (benchmark run only)

**Plan metadata:** pending (docs commit with this SUMMARY)

## Benchmark Run Log

**Run date (UTC):** 2026-07-11T00:29:34Z

**Host specs:**

| Spec | Value |
|------|-------|
| CPU cores | 8 (`nproc`) |
| Memory | 31 Gi total, 23 Gi available |
| OS | Linux 6.17.0-35-generic (Ubuntu 24.04 kernel) x86_64 |
| Docker | 29.6.1 |
| Machine | t480 |

**Command:** `./scripts/load-test.sh` (hey `-m POST -c 10 -z 60s`, compose stack)

### Parsed Metrics

| Metric | Value | SLO / Target | Status |
|--------|------:|:-------------|:-------|
| p50 latency | 671 ms | — | recorded |
| p95 latency | 798 ms | <100 ms (PERF-01) | **exceeds SLO** — publish honestly in 06-03 (D-09); suggest `TORCH_NUM_THREADS` tuning |
| p99 latency | 860 ms | — | recorded |
| RPS | 14.83 | — | recorded |
| Error rate | 0.0% (895/895 HTTP 200) | — | PERF-02 satisfied |
| Peak CPU (app container) | 740.17% raw docker stats | <70% (PERF-03) | **exceeds on normalized basis** (~93% of 8 cores); document in README |

### Raw hey Output (excerpt)

```
Summary:
  Total:	60.3667 secs
  Requests/sec:	14.8261

Latency distribution:
  50% in 0.6706 secs
  95% in 0.7981 secs
  99% in 0.8604 secs

Status code distribution:
  [200]	895 responses

Peak CPU (app container): 740.17%
```

**PERF-02 verification:** hey used `-c 10` (10 concurrent workers); 100% of responses were HTTP 200.

**PERF-01 / D-09 flag:** p95 = 798 ms on this host under 10-worker load. Do not omit from README — include tuning note (`TORCH_NUM_THREADS`, CPU limits).

**PERF-03 note:** docker stats `CPUPerc` is per-container and can exceed 100% on multi-core hosts (740% ≈ 7.4 cores fully busy on 8-core machine). Peak indicates heavy CPU use during concurrent inference; interpret alongside host core count in 06-03.

## Files Created/Modified

- `scripts/load-test.sh` — Compose hey benchmark wrapper (PERF-01–03 tooling)
- `tests/test_load_test_script.py` — Static contract tests for load-test script

## Decisions Made

- Used literal `-c 10 -z 60s` in hey invocation (not variables) so contract tests and grep acceptance checks pass
- Installed hey via `go install github.com/rakyll/hey@latest` (official GitHub source per T-06-01 / user_setup)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Contract test required literal `-c 10` in script**
- **Found during:** Task 1 (pytest contract)
- **Issue:** Initial script used `-c "${HEY_CONCURRENCY}"`; test asserts literal `-c 10` substring
- **Fix:** Changed hey command to use literal `-c 10 -z 60s`
- **Files modified:** `scripts/load-test.sh`
- **Committed in:** `0b8541e`

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** Cosmetic contract alignment; behavior unchanged.

## Issues Encountered

- `hey` was not pre-installed on host; installed from official GitHub source before Task 2 benchmark
- Worktree HEAD check expected `worktree-agent-*` branch but executor ran on `estevaodr/phase06` feature branch (not a Cursor worktree); execution proceeded with correct base commit

## User Setup Required

**hey** must be installed before first benchmark:

```bash
go install github.com/rakyll/hey@latest
export PATH="$HOME/go/bin:$PATH"
hey -h
```

Install only from `github.com/rakyll/hey` (T-06-01).

## Next Phase Readiness

- Benchmark evidence ready for 06-03 README Performance Results table (DOC-05)
- p95 and CPU exceed portfolio SLO on this host — 06-03 should include honest D-09 note and tuning pointers
- Load-test script and contract tests ready for CI inclusion if desired later

## Self-Check: PASSED

- FOUND: scripts/load-test.sh
- FOUND: tests/test_load_test_script.py
- FOUND: .planning/phases/06-polish-differentiators-readme/06-01-SUMMARY.md
- FOUND: e486e1b
- FOUND: 0b8541e

---
*Phase: 06-polish-differentiators-readme*
*Completed: 2026-07-10*
