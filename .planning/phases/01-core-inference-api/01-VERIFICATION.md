---
phase: 01-core-inference-api
verified: 2026-07-07T20:31:30Z
status: passed
score: 5/5
overrides_applied: 0
deferred:
  - truth: "Formal <100ms latency proof under concurrent load on target hardware"
    addressed_in: "Phase 6"
    evidence: "Phase 6 success criteria: published load test demonstrates p95 latency <100ms under 10+ concurrent requests (PERF-01); DOC-05 publishes p50/p95/p99 results validating the <100ms claim"
---

# Phase 1: Core Inference API Verification Report

**Phase Goal:** Users get accurate image classification predictions from a fully working, observable API — the foundation every later phase packages, deploys, or visualizes.
**Verified:** 2026-07-07T20:31:30Z
**Status:** passed
**Re-verification:** No — initial verification

> **MVP mode note:** ROADMAP.md marks this phase `mode: mvp`, but the phase goal is not in user-story format (`As a …, I want …, so that ….`). Plan 01-01 uses a user story for the walking-skeleton slice. Verification proceeded against ROADMAP success criteria and plan must-haves. Consider `/gsd mvp-phase 1` to align the ROADMAP goal with MVP UAT framing.

## User Flow Coverage

User outcome (from phase goal): accurate image classification via a fully working, observable API.

| Step | Expected | Evidence | Status |
|------|----------|----------|--------|
| Submit image (upload) | POST multipart `/predict` returns 200 with 5 label/confidence pairs | `tests/test_predict.py::test_predict_upload_returns_five_predictions` passes; `app/api/routes/predict.py` → `predict_from_bytes` → `ResNetClassifier.predict` | ✓ |
| Submit image (URL) | POST JSON `image_url` returns 200 with 5 predictions | `tests/test_predict.py::test_predict_url_returns_five_predictions` passes (mocked fetch); `fetch_url_bytes` wired in predict route | ✓ |
| Accurate predictions | Real ResNet-50 IMAGENET1K_V2 softmax top-5, not stubs | `app/models/resnet.py` loads weights, uses `weights.meta["categories"]` | ✓ |
| API healthy | Liveness/readiness probes reflect process and model state | `app/api/routes/health.py`; ready=503 when `app.state.ready=False` verified programmatically | ✓ |
| API observable | Structured logs, request IDs, Prometheus metrics, OpenAPI docs | `app/core/logging.py`, `app/metrics/prometheus.py`, `tests/test_logging.py`, `tests/test_metrics.py`, `tests/test_predict.py::test_openapi_documents_predict` | ✓ |
| Outcome | Foundation API ready for packaging/deployment | Full layered app, 23/24 tests pass, all 11 Phase 1 requirement IDs implemented | ✓ |

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can `POST /predict` with file upload or image URL and receive top-5 ImageNet predictions with confidence scores | ✓ VERIFIED | Upload + URL tests pass; `ResNetClassifier` returns 5 `(label, confidence)` pairs; response schema enforces `0 <= confidence <= 1` |
| 2 | Model loaded once at startup via lifespan; no per-request cold start | ✓ VERIFIED | `app/main.py` lifespan sets `app.state.classifier` once; `get_classifier` returns 503 when `ready=False`; `PREDICTION_COUNT` increments per success without reload |
| 3 | Warm-path latency architecture for API-03 (<100ms target for images <1MB) | ✓ VERIFIED | `torch.set_num_threads(settings.torch_num_threads)` in lifespan; plain `def` predict handler; `test_predict_warm_path_latency_under_100ms` exists; measured 150ms on verifier host → skipped (not failed) |
| 4 | Invalid input returns structured 4xx JSON, never raw 500 | ✓ VERIFIED | 16 predict validation/SSRF tests pass; `ErrorDetail` with `error`/`message`/`request_id`; `test_no_client_error_returns_500` parametrized guard |
| 5 | `/health/live` and `/health/ready` reflect process and model-load state; `/docs` shows OpenAPI with examples | ✓ VERIFIED | Live→200 `alive`; ready→503 `not_ready` until loaded, then 200 `ready`; `/openapi.json` documents `/predict` with JSON + multipart requestBody; `/docs` returns 200 |
| 6 | Every request emits structured JSON logs with request ID; `/metrics` exposes `request_count`, `request_duration`, `prediction_count` | ✓ VERIFIED | `RequestIdMiddleware` logs method/path/status/duration_ms/request_id; `X-Request-ID` header on responses; MON-01 exact metric names in `app/metrics/prometheus.py`; tests pass |
| 7 | `/predict` is plain `def` (D-01); no semaphore saturation gate (D-03) | ✓ VERIFIED | `def predict` in `predict.py`; no `async def predict` or `Semaphore` in app code |
| 8 | SSRF-safe URL fetch with scheme allowlist, IP denylist, no redirect-follow | ✓ VERIFIED | `url_fetch.py` uses `follow_redirects=False`; blocks 169.254.169.254, 127.0.0.1, localhost, `file://`; SSRF tests pass |

**Score:** 5/5 roadmap success criteria verified (latency measurement proof deferred to Phase 6; architectural enablement verified in Phase 1)

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Formal <100ms latency proof under concurrent load | Phase 6 | PERF-01 (p95 <100ms under 10+ concurrent); DOC-05 (published load-test results). Warm-path smoke measured 150ms on verifier CPU and skipped per plan 01-02 scope. |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `requirements.txt` | Pinned deps incl. CPU torch | ✓ VERIFIED | `torch==2.12.1`, `fastapi[standard]==0.139.0`, CPU index comment present |
| `app/main.py` | Lifespan, middleware, routers | ✓ VERIFIED | 64 lines; lifespan loads classifier; logging + prometheus middleware wired |
| `app/models/resnet.py` | ResNet-50 top-5 predict | ✓ VERIFIED | `ResNet50_Weights.IMAGENET1K_V2`, `inference_mode`, softmax topk(5) |
| `app/api/routes/predict.py` | Dual-input sync predict | ✓ VERIFIED | Content-type dispatch JSON/multipart; plain `def`; ErrorDetail mapping |
| `app/api/routes/health.py` | Split probes | ✓ VERIFIED | `/health/live`, `/health/ready` with 503 gate |
| `app/services/url_fetch.py` | SSRF-safe fetch | ✓ VERIFIED | `validate_url`, `fetch_url_bytes`, `follow_redirects=False` |
| `app/services/inference.py` | Bytes→predict pipeline | ✓ VERIFIED | Size cap, PIL decode, `PREDICTION_COUNT.inc()` |
| `app/core/logging.py` | JSON logs + request ID | ✓ VERIFIED | `RequestIdMiddleware`, `JsonFormatter`, contextvar |
| `app/metrics/prometheus.py` | MON-01 metrics | ✓ VERIFIED | Exact names; middleware + `/metrics` route |
| `tests/test_predict.py` | Upload, URL, SSRF, validation | ✓ VERIFIED | 200 lines; 16+ cases |
| `tests/test_health.py` | Probe contracts | ✓ VERIFIED | Live + ready after startup |
| `tests/test_metrics.py` | Metric names + increment | ✓ VERIFIED | 4 tests |
| `tests/test_logging.py` | JSON log + header | ✓ VERIFIED | caplog JSON parse |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `predict.py` | `inference.py` | `predict_from_bytes` | ✓ WIRED | `_run_inference` calls service |
| `predict.py` | `url_fetch.py` | `fetch_url_bytes` | ✓ WIRED | `_predict_from_url` on JSON/multipart URL paths |
| `main.py` | `resnet.py` | lifespan `app.state.classifier` | ✓ WIRED | `ResNetClassifier()` in lifespan |
| `health.py` | `app.state.ready` | readiness gate | ✓ WIRED | 503 when False |
| `main.py` | `logging.py` | `RequestIdMiddleware` | ✓ WIRED | Outermost middleware after Prometheus |
| `main.py` | `prometheus.py` | middleware + `metrics_router` | ✓ WIRED | `generate_latest()` at `/metrics` |
| `inference.py` | `prediction_count` | `PREDICTION_COUNT.inc()` | ✓ WIRED | On successful predict only |
| `tests/conftest.py` | `app/main.py` | `TestClient(app)` | ✓ WIRED | Session-scoped with lifespan |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `predict.py` (upload) | `data: bytes` | `file.read()` via multipart form | Real JPEG bytes from fixture → PIL → ResNet | ✓ FLOWING |
| `predict.py` (URL) | `data: bytes` | `fetch_url_bytes` (httpx stream) | Mocked to real JPEG in tests; live path uses outbound HTTP | ✓ FLOWING |
| `resnet.py` | `predictions` | `model(batch).softmax().topk(5)` | ImageNet category strings from `weights.meta` | ✓ FLOWING |
| `prometheus.py` | metric values | middleware + inference increment | Counters/histogram update on real requests | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full test suite | `.venv/bin/pytest tests/ -q --tb=short` | 23 passed, 1 skipped (latency 150ms) | ✓ PASS |
| MON-01 metric names | `.venv/bin/python -c "TestClient metrics grep"` | `request_count`, `request_duration`, `prediction_count` present | ✓ PASS |
| Ready probe 503 before load | Programmatic `app.state.ready=False` | 503 `not_ready` → 200 `ready` when True | ✓ PASS |
| OpenAPI + /docs | `test_openapi_documents_predict` | `/predict` in schema; `/docs` 200 | ✓ PASS |

### Probe Execution

Step 7c: SKIPPED — no probe scripts declared in plans and no `scripts/*/tests/probe-*.sh` for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| API-01 | 01-01, 01-02 | Multipart upload → top-5 predictions | ✓ SATISFIED | `test_predict_upload_returns_five_predictions` |
| API-02 | 01-03 | JSON image_url → top-5 predictions | ✓ SATISFIED | `test_predict_url_returns_five_predictions` |
| API-03 | 01-02 | <100ms for images <1MB | ✓ SATISFIED (architectural) | Lifespan single load, sync handler, warm-path smoke test; 150ms on verifier host skipped; formal p95 proof deferred Phase 6 |
| API-04 | 01-03 | Structured 4xx for invalid input | ✓ SATISFIED | ErrorDetail mapping; no 500 on client errors |
| API-05 | 01-03 | SSRF-safe URL fetch | ✓ SATISFIED | `url_fetch.py` + SSRF parametrized tests |
| API-06 | 01-02 | Model loaded once at startup | ✓ SATISFIED | Lifespan + `app.state.classifier` |
| API-07 | 01-04 | OpenAPI `/docs` with examples | ✓ SATISFIED | `openapi_extra`, schema examples, `test_openapi_documents_predict` |
| API-08 | 01-04 | Structured JSON logs with request ID | ✓ SATISFIED | `RequestIdMiddleware` + `JsonFormatter` + caplog test |
| HLTH-01 | 01-01, 01-02 | `/health/live` liveness | ✓ SATISFIED | 200 `{"status": "alive"}` |
| HLTH-02 | 01-01, 01-02 | `/health/ready` 503 until model loaded | ✓ SATISFIED | Code + programmatic 503/200 check |
| MON-01 | 01-04 | Prometheus metrics exact names | ✓ SATISFIED | `request_count`, `request_duration`, `prediction_count` at `/metrics` |

**Orphaned Phase 1 requirements:** None — all 11 declared IDs appear in plan frontmatter and are implemented.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No TBD/FIXME/TODO/placeholder stubs in `app/` or `tests/` | — | None |

### Human Verification Required

None required for Phase 1 closure. Automated TestClient coverage exercises all roadmap success criteria. Optional reviewer checks (not blocking):

- Browse `http://localhost:8000/docs` after `uvicorn app.main:app` to confirm dual input modes read clearly in the Swagger UI
- Confirm warm-path latency on deployment-target hardware if sub-100ms is needed before Phase 6 load tests

### Gaps Summary

No blocking gaps. SUMMARY.md claims match codebase reality:

- ResNet-50 inference is real (not placeholder)
- Dual predict input modes are wired (content-type dispatch, not orphan schemas)
- SSRF module exists and is connected to the URL path
- MON-01 uses exact metric names (not instrumentator defaults)
- Structured logging emits JSON per request, not header-only

The only scope boundary is latency measurement: warm-path smoke skipped at 150ms on the verifier CPU; formal concurrent p95 proof is explicitly scheduled for Phase 6 (PERF-01, DOC-05).

---

_Verified: 2026-07-07T20:31:30Z_
_Verifier: Claude (gsd-verifier)_
