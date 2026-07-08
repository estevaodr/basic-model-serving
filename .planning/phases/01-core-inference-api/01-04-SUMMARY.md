---
phase: 01-core-inference-api
plan: 04
subsystem: api
tags: [fastapi, prometheus, structured-logging, openapi, request-id, metrics]

requires:
  - phase: 01-03
    provides: Dual-input /predict, ErrorDetail schema, structured 4xx errors
provides:
  - RequestIdMiddleware with X-Request-ID on every response
  - Structured JSON per-request logs with method, path, status, duration_ms, request_id
  - MON-01 custom Prometheus metrics at GET /metrics
  - OpenAPI docs with golden retriever examples for upload and URL input modes
affects: [02-containerization, 03-local-dev-stack]

tech-stack:
  added: [prometheus_client custom Counter/Histogram, stdlib JSON logging formatter]
  patterns: [RequestIdMiddleware outermost over PrometheusMiddleware, route-path metric labels]

key-files:
  created:
    - app/core/logging.py
    - app/metrics/prometheus.py
    - tests/test_logging.py
    - tests/test_metrics.py
  modified:
    - app/main.py
    - app/api/routes/predict.py
    - app/schemas/prediction.py
    - app/services/inference.py
    - tests/test_predict.py

key-decisions:
  - "PrometheusMiddleware inner, RequestIdMiddleware outer so logs include final status after metrics timing"
  - "Metric labels use route template path (e.g. /predict) not raw URLs for cardinality safety"
  - "OpenAPI requestBody documents both application/json and multipart/form-data on single /predict handler"

patterns-established:
  - "Per-request JSON logs via app.request logger with JsonFormatter and contextvar request_id"
  - "MON-01 exact metric names via prometheus_client; prediction_count incremented in inference service on success"

requirements-completed: [API-07, API-08, MON-01]

duration: 3min
completed: 2026-07-07
---

# Phase 1 Plan 04: Observability and OpenAPI Summary

**Structured JSON logging with request IDs, MON-01 Prometheus metrics on /metrics, and reviewer-friendly OpenAPI docs for dual predict input modes**

## Performance

- **Duration:** 3 min
- **Started:** 2026-07-07T20:22:00Z
- **Completed:** 2026-07-07T20:25:34Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- RequestIdMiddleware generates or propagates X-Request-ID and emits structured JSON logs per request
- Custom request_count, request_duration, and prediction_count metrics exposed at GET /metrics with route-path labels
- OpenAPI schema documents both JSON image_url and multipart file upload with golden retriever examples and invalid_image error sample
- Full test suite passes (23 passed, 1 skipped latency smoke)

## Task Commits

Each task was committed atomically:

1. **Task 1: Request ID middleware and structured JSON logging** - `ecb4ac8` (feat)
2. **Task 2: Custom Prometheus metrics and /metrics endpoint** - `0add068` (test), `6e66b16` (feat)
3. **Task 3: OpenAPI docs with examples for both input modes** - `ad3bcd9` (feat)

**Plan metadata:** pending (docs commit follows)

## Files Created/Modified

- `app/core/logging.py` - RequestIdMiddleware, JsonFormatter, request_id contextvar
- `app/metrics/prometheus.py` - MON-01 counters/histogram, PrometheusMiddleware, /metrics route
- `app/main.py` - Middleware wiring, app description, metrics router
- `app/api/routes/predict.py` - request_id in ErrorDetail; OpenAPI requestBody and 400 example
- `app/schemas/prediction.py` - Golden retriever 5-prediction examples on schemas
- `app/services/inference.py` - PREDICTION_COUNT.inc() on successful predict
- `tests/test_logging.py` - JSON log and X-Request-ID header tests
- `tests/test_metrics.py` - Metric names, increment, and naming guard tests
- `tests/test_predict.py` - OpenAPI /predict documentation test

## Decisions Made

- Middleware order: Prometheus inner, RequestId outer so per-request logs capture final status code
- Prometheus Counter exports as `{name}_total` per client library convention; grep/substring checks use MON-01 base names
- Single /predict handler OpenAPI uses openapi_extra requestBody with both content types rather than dual route decorators

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Metrics test parser for prometheus_client _total suffix**
- **Found during:** Task 2 (test_prediction_count_increments)
- **Issue:** prometheus_client Counter exports as `prediction_count_total`; exact-name regex returned 0 after increment
- **Fix:** Updated `_metric_value` to match both `name` and `{name}_total` export lines
- **Files modified:** tests/test_metrics.py
- **Verification:** test_prediction_count_increments passes
- **Committed in:** 6e66b16

---

**Total deviations:** 1 auto-fixed (test parser for library naming convention)
**Impact on plan:** No scope change. MON-01 substring grep requirements still satisfied.

## Issues Encountered

None beyond the metrics test parser deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 1 complete: observable API with logging, metrics, docs, dual predict input, health probes, and structured errors
- `/metrics` ready for Prometheus scrape in Phase 3 docker-compose and Phase 5 kube-prometheus-stack
- Phase 2 can containerize with HEALTHCHECK on /health/live and env-driven log_level

## Self-Check: PASSED

- FOUND: app/core/logging.py
- FOUND: app/metrics/prometheus.py
- FOUND: tests/test_logging.py
- FOUND: tests/test_metrics.py
- FOUND: commit ecb4ac8
- FOUND: commit 0add068
- FOUND: commit 6e66b16
- FOUND: commit ad3bcd9

---
*Phase: 01-core-inference-api*
*Completed: 2026-07-07*
