---
phase: 03-local-dev-stack-dashboards
plan: 03
subsystem: infra
tags: [grafana, alerting, docker-compose, observability, readme, tdd]

requires:
  - phase: 03-local-dev-stack-dashboards
    plan: 02
    provides: Grafana datasource uid prometheus and Model Serving Overview dashboard
provides:
  - Service Down unified alerting rule provisioned from git
  - README local observability stack quickstart with curl traffic and alert demo
  - Static alert provisioning contract tests
  - Human-verified alert Firing/Resolved demo workflow
affects: []

tech-stack:
  added: []
  patterns: [Grafana unified alerting file provisioning, UI-only alerts without contact points, README compose quickstart]

key-files:
  created:
    - monitoring/grafana/provisioning/alerting/downtime.yml
    - tests/test_grafana_alerting.py
  modified:
    - README.md
    - .env.example

key-decisions:
  - "Use 10s alert evaluation interval because Grafana scheduler base interval is 10s and 15s is not an exact multiple"
  - "Use threshold lt 1 on up{job=\"app\"} instead of up{job=\"app\"} == 0 with classic_conditions chain for reliable Firing transitions"

patterns-established:
  - "Pattern: Grafana alert provisioning in monitoring/grafana/provisioning/alerting/ with no contact points"
  - "Pattern: README Local observability stack section documents plain docker compose up workflow"

requirements-completed: [MON-03, MON-05, CONT-04]

duration: 16min
completed: 2026-07-08
---

# Phase 03 Plan 03: Downtime Alert and Observability Quickstart Summary

**Service Down Grafana unified alert provisioned as code with README compose quickstart and human-verified Firing/Resolved demo**

## Performance

- **Duration:** 16 min
- **Started:** 2026-07-08T20:40:00Z
- **Completed:** 2026-07-08T20:56:00Z
- **Tasks:** 3/3
- **Files modified:** 4

## Accomplishments

- TDD alert contract tests (RED) then Service Down provisioning YAML (GREEN)
- Grafana loads Service Down rule on compose startup without contact points
- README documents full reviewer workflow: docker-build → compose up → curl → dashboards → alert demo
- Human-verified alert demo: Firing after sustained API stop, Normal after restart, no false firing on healthy boot

## Task Commits

Each task was committed atomically:

1. **Task 1: Alert provisioning and static validation tests** - `32e163c` (test), `3b6f1d1` (feat), `aca9fb8` (fix)
2. **Task 2: README observability quickstart and reviewer workflow** - `dcfc5dd` (docs)
3. **Task 3: Alert Firing/Resolved demo verification** - verified (human checkpoint; no code commit)

**Plan metadata:** `6e10dd9` (docs: initial summary), updated in completion commit

## Files Created/Modified

- `monitoring/grafana/provisioning/alerting/downtime.yml` - Service Down unified alert (threshold lt 1 on up{job="app"}, for 1m)
- `tests/test_grafana_alerting.py` - Static provisioning contract validation
- `README.md` - Local observability stack section with ports, curl, alert demo, troubleshooting
- `.env.example` - Commented Grafana admin credentials section

## Decisions Made

- Alert evaluation interval set to 10s (not 15s) because Grafana 11.6 scheduler base interval is 10s and rule intervals must be exact multiples
- Alert condition uses threshold `lt 1` on `up{job="app"}` rather than `up{job="app"} == 0` with classic_conditions — the latter caused expression errors and did not transition to Firing

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Grafana rejected 15s rule group interval**
- **Found during:** Task 1 verification (Grafana restart)
- **Issue:** `interval (15s) should be non-zero and divided exactly by scheduler interval: 10` — provisioning failed, Grafana crashed loop
- **Fix:** Changed rule group interval to 10s; updated test assertion accordingly
- **Files modified:** monitoring/grafana/provisioning/alerting/downtime.yml, tests/test_grafana_alerting.py
- **Verification:** Grafana starts cleanly; alert rule visible via provisioning API
- **Committed in:** 3b6f1d1

**2. [Rule 1 - Bug] Alert rule had expression error and did not fire**
- **Found during:** Task 1 runtime verification before checkpoint
- **Issue:** classic_conditions on Expression refId B caused `only data source queries may be inputs to a classic condition`; `up{job="app"} == 0` with gt 0 threshold never reached Firing
- **Fix:** Simplified to condition B with threshold `lt 1` on `up{job="app"}`; removed classic_conditions refId C
- **Files modified:** monitoring/grafana/provisioning/alerting/downtime.yml
- **Verification:** `docker compose stop app` → state Firing after ~75s; `docker compose start app` → state inactive/Normal after ~75s
- **Committed in:** aca9fb8

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes required for MON-03 runtime behavior. Query semantics equivalent to UI-SPEC downtime detection intent.

## Issues Encountered

None — Task 3 human checkpoint cleared after operator verified Grafana Alerting UI and API/Prometheus behavior.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 observability vertical slice complete: compose stack, dashboards, alert, README quickstart
- MON-05 fully satisfied (datasource + dashboard + alert provisioned as code)
- Ready for Phase 4 CI/CD pipeline

## Self-Check: PASSED

- FOUND: monitoring/grafana/provisioning/alerting/downtime.yml
- FOUND: tests/test_grafana_alerting.py
- FOUND: .planning/phases/03-local-dev-stack-dashboards/03-03-SUMMARY.md
- FOUND: 32e163c
- FOUND: 3b6f1d1
- FOUND: dcfc5dd
- FOUND: aca9fb8
- FOUND: 6e10dd9

---
*Phase: 03-local-dev-stack-dashboards*
*Completed: 2026-07-08*
