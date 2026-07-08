---
phase: 01-core-inference-api
plan: 01
subsystem: testing
tags: [fastapi, pytest, pytorch, tdd, walking-skeleton]

requires: []
provides:
  - Layered app/ package skeleton with pinned dependencies
  - TestClient fixtures and failing predict/health integration tests (TDD red phase)
affects: [01-02-PLAN.md]

tech-stack:
  added: [torch==2.12.1, torchvision==0.27.1, fastapi==0.139.0, pytest==9.1.1, pillow==12.3.0]
  patterns: [layered FastAPI package layout, session-scoped TestClient fixture, CPU torch index install]

key-files:
  created:
    - requirements.txt
    - requirements-dev.txt
    - app/main.py
    - tests/conftest.py
    - tests/test_predict.py
    - tests/test_health.py
  modified: []

key-decisions:
  - "Two-step pip install: torch/torchvision from CPU index, remaining packages from PyPI (single --index-url replaces PyPI entirely)"
  - "Stub FastAPI app without routes so tests fail with 404, not ImportError"

patterns-established:
  - "TDD red phase: integration tests define /predict and /health contract before implementation"
  - "sample_jpeg_bytes fixture generates in-memory JPEG via Pillow under 50KB"

requirements-completed: [API-01, HLTH-01, HLTH-02]

duration: 3min
completed: 2026-07-07
---

# Phase 1 Plan 01: Project Scaffold Summary

**Pinned dependency layout, layered app/ skeleton, and failing predict/health integration tests defining the walking-skeleton contract**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-07T20:03:00Z
- **Completed:** 2026-07-07T20:06:00Z
- **Tasks:** 1
- **Files modified:** 14

## Accomplishments

- Created production and dev requirement pins with CPU torch install comment
- Established layered `app/{core,api/routes,schemas,services,models}/` package layout
- Added `sample_jpeg_bytes` and session-scoped `TestClient` fixtures in conftest
- Wrote three failing integration tests asserting `/predict` (5 predictions) and `/health/live`, `/health/ready` contracts

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold project and failing upload E2E test** - `3195699` (test)

**Plan metadata:** pending (docs commit follows)

## Files Created/Modified

- `requirements.txt` - Pinned production deps with CPU torch index install comment
- `requirements-dev.txt` - pytest and ruff dev pins
- `app/main.py` - Minimal FastAPI stub exportable as `app`
- `tests/conftest.py` - `sample_jpeg_bytes` and session `client` fixtures
- `tests/test_predict.py` - Upload E2E test expecting 5 predictions
- `tests/test_health.py` - Live and ready health probe tests
- `app/**/__init__.py` - Package skeleton init files

## Decisions Made

- Used two-step pip install (torch CPU index, then PyPI packages) because `--index-url` on the full requirements file excludes PyPI and breaks FastAPI resolution
- Kept stub `app/main.py` route-free so pytest fails with 404 Not Found (correct red-phase signal)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Two-step pip install instead of single requirements.txt --index-url**
- **Found during:** Task 1 (dependency install verification)
- **Issue:** `pip install -r requirements.txt --index-url https://download.pytorch.org/whl/cpu` fails — CPU index replaces PyPI, so fastapi and other packages are not found
- **Fix:** Install `torch` and `torchvision` from CPU index first, then install remaining packages from PyPI
- **Files modified:** none (requirements.txt comment already documents CPU index; install procedure adjusted at verification time)
- **Verification:** All packages install; pytest runs and fails with 404 on `/predict`
- **Committed in:** 3195699 (verification only; no requirements.txt change needed)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Install procedure clarified; no scope change. Plan 01-02 should use the same two-step install pattern.

## Issues Encountered

None beyond the pip index-url behavior documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Red-phase tests and scaffold ready for plan 01-02 (lifespan model load, health routes, `/predict` upload path)
- First `ResNetClassifier()` construction in 01-02 will trigger ~100MB torchvision weight download to `~/.cache/torch`

## Self-Check: PASSED

- FOUND: requirements.txt
- FOUND: requirements-dev.txt
- FOUND: app/main.py
- FOUND: tests/conftest.py
- FOUND: tests/test_predict.py
- FOUND: tests/test_health.py
- FOUND: commit 3195699

---
*Phase: 01-core-inference-api*
*Completed: 2026-07-07*
