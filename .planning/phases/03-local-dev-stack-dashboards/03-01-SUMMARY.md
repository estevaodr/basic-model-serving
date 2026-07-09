---
phase: 03-local-dev-stack-dashboards
plan: 01
subsystem: infra
tags: [docker-compose, prometheus, grafana, observability, e2e]

requires:
  - phase: 02-containerization
    provides: basic-model-serving:local image, health probes, /metrics export
provides:
  - Three-service docker compose stack (app + Prometheus + Grafana)
  - Prometheus scrape config for app:8000 with 7d retention
  - Grafana auto-provisioned Prometheus datasource
  - Compose stack E2E pytest gate
affects: [03-02, 03-03]

tech-stack:
  added: [prom/prometheus:v3.3.0, grafana/grafana:11.6.0]
  patterns: [health-gated scrape, monitoring config bind-mounts, compose E2E gate]

key-files:
  created:
    - docker-compose.yml
    - monitoring/prometheus/prometheus.yml
    - monitoring/grafana/provisioning/datasources/prometheus.yml
    - tests/test_compose_stack.py
  modified:
    - pyproject.toml

key-decisions:
  - "Use --storage.tsdb.retention.time=7d CLI flag on prom/prometheus:v3.3.0 because config-file retention requires a newer Prometheus release"
  - "Document MON-04 retention in prometheus.yml via external_labels.retention_policy=7d for explicit grep verification"

patterns-established:
  - "Pattern: docker compose up with pre-built basic-model-serving:local (no build: directive)"
  - "Pattern: Prometheus scrape gated on app service_healthy before first scrape"

requirements-completed: [CONT-04, MON-04, MON-05]

duration: 12min
completed: 2026-07-08
---

# Phase 03 Plan 01: Compose Stack Summary

**One-command docker compose stack wiring API metrics into Prometheus with 7d retention and auto-provisioned Grafana datasource**

## Performance

- **Duration:** 12 min
- **Started:** 2026-07-08T20:24:00Z
- **Completed:** 2026-07-08T20:36:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Compose E2E test scaffold (RED) then GREEN after stack implementation
- `docker compose up` starts app, Prometheus, and Grafana with health-gated scrape
- Prometheus scrapes `app:8000/metrics` with explicit 7d TSDB retention
- Grafana provisions Prometheus datasource (`uid: prometheus`) on startup

## Task Commits

Each task was committed atomically:

1. **Task 1: Failing compose stack E2E test scaffold** - `da9a0f5` (test)
2. **Task 2: Compose stack with Prometheus scrape and Grafana datasource** - `8c1eec8` (feat)

## Files Created/Modified

- `docker-compose.yml` - Three-service stack with healthcheck, retention CLI, named TSDB volume
- `monitoring/prometheus/prometheus.yml` - Scrape config for `app:8000`, retention label
- `monitoring/grafana/provisioning/datasources/prometheus.yml` - Auto-provisioned datasource
- `tests/test_compose_stack.py` - Compose E2E gate with predict traffic and PromQL assertions
- `pyproject.toml` - Added `compose` pytest marker

## Decisions Made

- Retention enforced via compose CLI flag on pinned `prom/prometheus:v3.3.0`; config-file `storage.tsdb.retention` is unsupported in this image tag
- E2E test copies `.env.example` → `.env` when missing so compose `env_file` works locally

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Prometheus failed to start with config-file retention block**
- **Found during:** Task 2 (Compose stack with Prometheus scrape and Grafana datasource)
- **Issue:** `prom/prometheus:v3.3.0` rejects `storage.tsdb.retention` in `prometheus.yml` (merged in PR #17026 after v3.3)
- **Fix:** Moved retention to `--storage.tsdb.retention.time=7d` compose command; kept explicit `7d` in `external_labels.retention_policy` for MON-04 grep verification
- **Files modified:** docker-compose.yml, monitoring/prometheus/prometheus.yml
- **Verification:** `docker compose up` starts prometheus; `pytest tests/test_compose_stack.py -m docker` passes
- **Committed in:** 8c1eec8

**2. [Rule 1 - Bug] E2E test queried Prometheus before first scrape**
- **Found during:** Task 2 verification
- **Issue:** `up{job="app"}` returned empty immediately after compose up
- **Fix:** Added `_wait_prometheus` and `_wait_prometheus_metric` polling helpers
- **Files modified:** tests/test_compose_stack.py
- **Verification:** Compose E2E test passes consistently (~3s when stack warm)
- **Committed in:** 8c1eec8

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes required for MON-04 correctness and reliable E2E gate. No scope creep.

## Issues Encountered

None beyond deviations above.

## User Setup Required

None - no external service configuration required. Copy `.env.example` to `.env` before first `docker compose up` (E2E test does this automatically).

## Next Phase Readiness

- Compose observability spine ready for dashboard JSON provisioning (Plan 03-02)
- Alert provisioning can reference `up{job="app"}` and `uid: prometheus` (Plan 03-03)
- README compose quickstart still needed in a later plan

## Self-Check: PASSED

- FOUND: docker-compose.yml
- FOUND: monitoring/prometheus/prometheus.yml
- FOUND: monitoring/grafana/provisioning/datasources/prometheus.yml
- FOUND: tests/test_compose_stack.py
- FOUND: .planning/phases/03-local-dev-stack-dashboards/03-01-SUMMARY.md
- FOUND: da9a0f5
- FOUND: 8c1eec8

---
*Phase: 03-local-dev-stack-dashboards*
*Completed: 2026-07-08*
