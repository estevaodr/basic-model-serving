---
phase: 01-core-inference-api
plan: 03
subsystem: api
tags: [fastapi, httpx, ssrf, structured-errors, url-fetch, predict]

requires:
  - phase: 01-02
    provides: Sync upload /predict, predict_from_bytes pipeline, ErrorDetail/PredictUrlRequest stubs
provides:
  - SSRF-safe sync url_fetch.py with scheme/IP validation and no redirect-follow
  - JSON and multipart /predict via content-type dispatch on one plain def handler
  - Structured 4xx ErrorDetail responses for invalid images, oversize payloads, and URL failures
  - Expanded test_predict.py SSRF and invalid-input coverage
affects: [01-04-PLAN.md]

tech-stack:
  added: [anyio.from_thread for sync Request body/form reads in plain def handler]
  patterns: [UrlFetchError/InferenceError domain errors mapped to ErrorDetail, HTTPException flat JSON handler]

key-files:
  created:
    - app/services/url_fetch.py
  modified:
    - app/api/routes/predict.py
    - app/services/inference.py
    - app/schemas/prediction.py
    - app/main.py
    - tests/test_predict.py

key-decisions:
  - "Single Request-based /predict handler dispatches JSON vs multipart after dual-route OpenAPI collision"
  - "PredictUrlRequest.image_url uses str (not HttpUrl) so file:// and SSRF checks run before pydantic scheme rejection"
  - "HTTPException handler returns flat {error, message} JSON for API-04 consistency"

patterns-established:
  - "URL path: validate_url → fetch_url_bytes (sync httpx, follow_redirects=False) → predict_from_bytes"
  - "Client errors: domain exceptions → HTTPException with ErrorDetail.model_dump()"

requirements-completed: [API-02, API-04, API-05]

duration: 4min
completed: 2026-07-07
---

# Phase 1 Plan 03: URL Input and Structured Errors Summary

**SSRF-safe JSON URL predict path with sync httpx fetch, content-type dispatch on `/predict`, and flat ErrorDetail 4xx responses for all invalid inputs**

## Performance

- **Duration:** 4 min
- **Started:** 2026-07-07T20:13:00Z
- **Completed:** 2026-07-07T20:16:44Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `url_fetch.py` with scheme allowlist, resolved-IP denylist, streaming size cap, and `follow_redirects=False`
- Extended `/predict` to accept JSON `image_url` alongside multipart upload via content-type dispatch in one plain `def` handler
- Mapped inference, upload size, and URL fetch failures to structured `{error, message}` JSON; no invalid-input test returns 500
- Full predict test suite passes (16 passed, 1 skipped latency smoke)

## Task Commits

Each task was committed atomically:

1. **Task 1: SSRF-safe URL fetch and JSON /predict path** - `dd6ad04` (feat)
2. **Task 2: Structured 4xx errors for all invalid inputs** - `05fffa9` (feat)

**Plan metadata:** pending (docs commit follows)

## Files Created/Modified

- `app/services/url_fetch.py` - SSRF validation and sync httpx streaming download
- `app/api/routes/predict.py` - Content-type dispatch, ErrorDetail mapping, plain def handler
- `app/services/inference.py` - max_upload_bytes enforcement and InferenceError for decode failures
- `app/schemas/prediction.py` - PredictUrlRequest with OpenAPI example; ErrorDetail finalized
- `app/main.py` - HTTPException handler returning flat ErrorDetail JSON
- `tests/test_predict.py` - URL success (mocked fetch), SSRF, invalid image, oversize, unreachable URL, empty input tests

## Decisions Made

- Used single Request-based handler instead of dual `@router.post("/predict")` decorators after FastAPI route collision caused JSON requests to 422 against the upload schema
- Kept `image_url` as `str` so non-http schemes reach `validate_url` and return `unsafe_url` instead of unhandled pydantic ValidationError
- Registered global HTTPException handler so clients receive top-level `{error, message}` objects per API-04

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] FastAPI dual-route collision on `/predict`**
- **Found during:** Task 1 (test_predict_url_returns_five_predictions)
- **Issue:** Two `@router.post("/predict")` handlers caused JSON POST to validate against multipart `File(...)` schema → 422
- **Fix:** Single plain `def` handler dispatching on `Content-Type` via `anyio.from_thread.run(request.body|form)` per RESEARCH fallback pattern
- **Files modified:** app/api/routes/predict.py
- **Verification:** URL and upload tests pass
- **Committed in:** dd6ad04

**2. [Rule 2 - Missing Critical] HttpUrl rejected file:// before SSRF module**
- **Found during:** Task 1 (test_ssrf_file_scheme_rejected)
- **Issue:** Pydantic `HttpUrl` raised ValidationError (potential 500) before `validate_url` could reject `file://`
- **Fix:** Changed `PredictUrlRequest.image_url` to `str`; scheme enforcement in `validate_url`
- **Files modified:** app/schemas/prediction.py, app/api/routes/predict.py
- **Verification:** test_ssrf_file_scheme_rejected returns 400 with structured body
- **Committed in:** dd6ad04

---

**Total deviations:** 2 auto-fixed (1 blocking route collision, 1 security validation order)
**Impact on plan:** No scope change. Dual-input contract preserved; fallback dispatch pattern documented for plan 01-04.

## Issues Encountered

None beyond deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Dual-input `/predict` with SSRF guards and structured 4xx errors ready for plan 01-04 (logging, metrics, OpenAPI polish)
- DNS-rebinding residual risk accepted per RESEARCH Assumption A3; IP pinning deferred

## Self-Check: PASSED

- FOUND: app/services/url_fetch.py
- FOUND: app/api/routes/predict.py
- FOUND: app/services/inference.py
- FOUND: app/main.py
- FOUND: tests/test_predict.py
- FOUND: commit dd6ad04
- FOUND: commit 05fffa9

---
*Phase: 01-core-inference-api*
*Completed: 2026-07-07*
