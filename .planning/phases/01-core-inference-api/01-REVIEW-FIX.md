---
phase: 01-core-inference-api
fixed_at: 2026-07-07T20:37:00Z
review_path: .planning/phases/01-core-inference-api/01-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-07-07T20:37:00Z
**Source review:** `.planning/phases/01-core-inference-api/01-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 6
- Fixed: 6
- Skipped: 0
- Tests: 23 passed, 1 skipped (warm-path latency)

## Fixed Issues

### CR-01: Multipart upload buffered before size limit

**Files modified:** `app/api/routes/predict.py`
**Commit:** 157b92a
**Applied fix:** Added `_read_upload_limited()` to stream-read multipart uploads in 64 KiB chunks with early cutoff at `max_upload_bytes`, replacing unbounded `file.read()`.

### WR-01: DNS rebinding TOCTOU in URL fetch

**Files modified:** `app/services/url_fetch.py`
**Commit:** 9bf2b5f
**Applied fix:** `validate_url()` now returns a pinned URL using the resolved IP; `fetch_url_bytes()` connects to that address with the original hostname in the `Host` header and `sni_hostname` for HTTPS.

### WR-02: 503 `not_ready` responses use non-ErrorDetail shape

**Files modified:** `app/api/dependencies.py`, `app/api/routes/health.py`
**Commit:** 5d38cf9
**Applied fix:** Replaced `{"status": "not_ready"}` with `ErrorDetail(error="not_ready", message="Model is not loaded yet", request_id=...)` in both `get_classifier()` and `/health/ready`.

### WR-03: Image decode errors beyond `UnidentifiedImageError` return 500

**Files modified:** `app/services/inference.py`
**Commit:** 00641b4 (import path corrected in 84cc74c)
**Applied fix:** Added Pillow `verify()` + re-open pattern; catch `UnidentifiedImageError`, `DecompressionBombError`, and `OSError` as `invalid_image` client errors. Import uses `from PIL.Image import DecompressionBombError` for Pillow 12.x compatibility.

### WR-04: JSON request body read without size cap

**Files modified:** `app/api/routes/predict.py`
**Commit:** d3005b8
**Applied fix:** Added `MAX_JSON_BODY_BYTES` (16 KiB), `Content-Length` pre-check, and `_read_json_body_limited()` streaming reader before JSON parse.

### WR-05: Broad `ValueError` handler masks unexpected failures

**Files modified:** `app/services/url_fetch.py`
**Commit:** 84cc74c
**Applied fix:** Replaced catch-all `except ValueError` with `except ipaddress.AddressValueError` so unexpected internal errors propagate instead of being mislabeled as `invalid_url`.

---

_Fixed: 2026-07-07T20:37:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
