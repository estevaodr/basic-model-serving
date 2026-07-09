---
phase: 04-ci-cd-pipeline
plan: 01
subsystem: infra
tags: [github-actions, ghcr, ruff, pytest, docker-buildx, uv, ci]

# Dependency graph
requires:
  - phase: 02-containerization
    provides: Multi-stage Dockerfile with CPU torch and baked weights for CI build
  - phase: 01-core-inference-api
    provides: Unit/API pytest suite and ruff lint targets
provides:
  - Single-job GitHub Actions CI workflow (lint → test → build → conditional GHCR push)
  - Static contract tests locking D-01..D-14 workflow decisions
  - Local quality gate aligned with CI ruff + marker-filtered pytest
affects: [04-ci-cd-pipeline, 05-kubernetes-deployment, 06-polish-readme]

# Tech tracking
tech-stack:
  added: [GitHub Actions, docker/build-push-action@v7, astral-sh/setup-uv@v8, GHA Docker cache]
  patterns: [Single-job CI, TDD contract tests on workflow YAML, CPU torch two-step install in CI]

key-files:
  created:
    - .github/workflows/ci.yml
    - tests/test_ci_workflow.py
  modified:
    - app/api/routes/predict.py
    - app/models/resnet.py
    - app/schemas/prediction.py
    - app/services/url_fetch.py
    - scripts/docker.py
    - tests/test_compose_stack.py
    - tests/test_grafana_alerting.py
    - tests/test_grafana_dashboard.py
    - tests/test_metrics.py

key-decisions:
  - "Single job `ci` with sequential lint → test → build → push (D-11)"
  - "GHCR push gated to main push events only; PRs build without push (D-02, D-12)"
  - "Tags: short SHA, latest, bare semver from pyproject.toml on main (D-08, D-09)"
  - "Docker layer cache type=gha mode=max plus uv enable-cache (D-13, D-14)"

patterns-established:
  - "Contract tests assert workflow YAML strings for D-01..D-14 without PyYAML dependency"
  - "CI pytest excludes docker and compose markers matching local dev E2E split"

requirements-completed: [CI-01, CI-02, CI-03, CI-04]

# Metrics
duration: 2min
completed: 2026-07-09
---

# Phase 4 Plan 01: CI Workflow Summary

**Single-job GitHub Actions pipeline with ruff/pytest quality gate, Buildx build, GHA cache, and conditional GHCR publish with SHA/latest/semver tags**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-09T18:50:42Z
- **Completed:** 2026-07-09T18:52:50Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments

- Added 14 static contract tests covering D-01..D-14 before workflow implementation (TDD RED)
- Implemented `.github/workflows/ci.yml` as a single `ci` job with uv+ruff+pytest, Buildx, and gated GHCR push
- Aligned local tree with CI quality gate: ruff check/format clean, 46 tests pass with 3 docker/compose deselected

## Task Commits

Each task was committed atomically:

1. **Task 1: Failing static CI workflow contract tests** - `bb566a7` (test)
2. **Task 2: Implement single-job ci.yml and green the contract** - `32bf60f` (feat)
3. **Task 3: Make local lint/test match CI quality gate** - `671ccc2` (fix)

## Files Created/Modified

- `.github/workflows/ci.yml` - Single-job CI: triggers, concurrency, uv install, ruff, pytest, Buildx, GHCR metadata/push
- `tests/test_ci_workflow.py` - Static contract suite for D-01..D-14
- `app/api/routes/predict.py`, `app/models/resnet.py`, `app/schemas/prediction.py`, `app/services/url_fetch.py` - ruff format only
- `scripts/docker.py` - Removed unused import + format
- `tests/test_*.py` (4 files) - ruff format only

## Decisions Made

- Followed RESEARCH canonical skeleton exactly for single-job layout (D-11)
- Contract test job-name regex scoped to `jobs:` section to avoid false matches on `on.push`/`on.pull_request`
- Warm-run timing proof for CI-04 deferred to 04-02 per plan scope

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed job-name regex false positives in contract test**
- **Found during:** Task 2 (Implement ci.yml)
- **Issue:** `test_d11_single_ci_job` matched `push` and `pull_request` under `on:` as job names
- **Fix:** Scoped regex to YAML content after `jobs:` split
- **Files modified:** tests/test_ci_workflow.py
- **Committed in:** 32bf60f

**2. [Rule 3 - Blocking] Pre-existing ruff violations blocked CI quality gate**
- **Found during:** Task 3 (Local lint/test alignment)
- **Issue:** 2 lint errors and 10 files failing `ruff format --check`
- **Fix:** `ruff check --fix` + `ruff format .` across reported files
- **Files modified:** 10 source/test files
- **Committed in:** 671ccc2

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Required for contract tests and CI-02 correctness. No scope creep.

## Issues Encountered

None beyond auto-fixed items above.

## User Setup Required

None for workflow merge. Plan 04-02 includes human GHCR visibility verification after first main push (D-10).

## Next Phase Readiness

- CI workflow encoded and locally verified; ready for 04-02 (GHCR visibility + warm-run timing proof)
- Phase 5 can consume `ghcr.io/estevaodr/basic-model-serving` tags once first main push succeeds

---
*Phase: 04-ci-cd-pipeline*
*Completed: 2026-07-09*

## Self-Check: PASSED

- FOUND: .github/workflows/ci.yml
- FOUND: tests/test_ci_workflow.py
- FOUND: .planning/phases/04-ci-cd-pipeline/04-01-SUMMARY.md
- FOUND: bb566a7
- FOUND: 32bf60f
- FOUND: 671ccc2
