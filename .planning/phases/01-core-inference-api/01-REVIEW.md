---
phase: 01-core-inference-api
reviewed: 2026-07-07T20:30:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - app/main.py
  - app/core/config.py
  - app/core/logging.py
  - app/models/resnet.py
  - app/schemas/prediction.py
  - app/api/dependencies.py
  - app/api/routes/predict.py
  - app/api/routes/health.py
  - app/services/inference.py
  - app/services/url_fetch.py
  - app/metrics/prometheus.py
  - tests/conftest.py
  - tests/test_predict.py
  - tests/test_health.py
  - tests/test_metrics.py
  - tests/test_logging.py
  - requirements.txt
  - requirements-dev.txt
findings:
  critical: 1
  warning: 5
  info: 2
  total: 8
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-07T20:30:00Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 01 delivers a coherent FastAPI inference API with SSRF guards, structured 4xx errors, health probes, logging, and Prometheus metrics. The walking skeleton is well-structured and tests cover the primary happy paths and several failure modes.

One **BLOCKER** remains: multipart uploads are fully buffered into memory before `max_upload_bytes` is enforced, leaving a memory-exhaustion DoS vector despite the post-read size check in `predict_from_bytes`. Several **WARNING**-level gaps affect SSRF residual risk (DNS rebinding TOCTOU), inconsistent 503 error shapes, and incomplete image-decode error handling that can still surface as 500 responses.

## Critical Issues

### CR-01: Multipart upload buffered before size limit

**File:** `app/api/routes/predict.py:164`, `app/services/inference.py:18-22`
**Issue:** The multipart path calls `anyio.from_thread.run(file.read)`, loading the entire uploaded part into memory before `predict_from_bytes` checks `len(data) > settings.max_upload_bytes`. An attacker can send a multi-gigabyte upload and exhaust pod memory even though the handler would eventually reject the payload. Plan 01-02 noted this gap; plan 03 added a post-read check only, which does not prevent the DoS.
**Fix:**
```python
# app/api/routes/predict.py — stream-read with early cutoff
def _read_upload_limited(read_fn, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = read_fn(65536)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise _client_error(
                "payload_too_large",
                f"Upload exceeds maximum allowed size of {max_bytes} bytes",
            )
        chunks.append(chunk)
    return b"".join(chunks)

# In multipart branch:
data = _read_upload_limited(
    lambda n: anyio.from_thread.run(file.read, n),
    settings.max_upload_bytes,
)
```

## Warnings

### WR-01: DNS rebinding TOCTOU in URL fetch

**File:** `app/services/url_fetch.py:47-51`
**Issue:** `validate_url()` resolves and blocklists IPs at validation time, but `httpx.Client.stream("GET", url)` performs a separate DNS lookup at connection time. An attacker controlling DNS can return a public IP during validation and a private/metadata IP at connect time, bypassing SSRF checks. Phase docs accept this residual risk, but it remains an exploitable SSRF class in anything reachable beyond a local demo.
**Fix:** Resolve once, connect to the resolved address directly, and pass the original hostname in the `Host` header (or pin the connection via a custom transport). Example pattern:

```python
import socket
import httpx

def fetch_url_bytes(url: str, timeout: float, max_bytes: int) -> bytes:
    validate_url(url)
    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addrinfos = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    # pick first non-blocked sockaddr from validate_url's logic
    host, port = addrinfos[0][4][0], addrinfos[0][4][1]
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        with client.stream(
            "GET",
            f"{parsed.scheme}://{host}:{port}{parsed.path or '/'}",
            headers={"Host": parsed.hostname},
        ) as response:
            ...
```

### WR-02: 503 `not_ready` responses use non-ErrorDetail shape

**File:** `app/api/dependencies.py:6-7`, `app/main.py:52-58`
**Issue:** `get_classifier()` raises `HTTPException(detail={"status": "not_ready"})`. The global handler only passes through dicts containing an `"error"` key; otherwise it wraps the response as `{"error": "http_error", "message": "{'status': 'not_ready'}"}`. Clients expecting the documented `{error, message, request_id}` contract get an inconsistent 503 during startup/shutdown races.
**Fix:**
```python
# app/api/dependencies.py
raise HTTPException(
    status_code=503,
    detail=ErrorDetail(
        error="not_ready",
        message="Model is not loaded yet",
        request_id=_request_id(),
    ).model_dump(),
)
```

Apply the same `ErrorDetail` shape to `app/api/routes/health.py:15` for consistency.

### WR-03: Image decode errors beyond `UnidentifiedImageError` return 500

**File:** `app/services/inference.py:24-28`
**Issue:** Only `UnidentifiedImageError` is mapped to `InferenceError("invalid_image", ...)`. Other common Pillow failures—`DecompressionBombError`, `OSError` from truncated/corrupt files, and failures during `image.convert("RGB")`—propagate as unhandled exceptions and become 500 responses. Project pitfall docs explicitly call for treating decompression-bomb conditions as client errors, not server errors.
**Fix:**
```python
from PIL import Image, UnidentifiedImageError, DecompressionBombError

try:
    image = Image.open(io.BytesIO(data))
    image.verify()
    image = Image.open(io.BytesIO(data)).convert("RGB")
except (UnidentifiedImageError, DecompressionBombError, OSError) as exc:
    raise InferenceError("invalid_image", "Could not decode image") from exc
```

(Use `DecompressionBombError`; re-open after `verify()` as Pillow recommends.)

### WR-04: JSON request body read without size cap

**File:** `app/api/routes/predict.py:130`
**Issue:** `anyio.from_thread.run(request.body)` loads the entire request body before parsing. A client can send a very large `application/json` body (e.g., megabyte-scale `image_url` string) to consume memory even though URL fetch enforces response size separately.
**Fix:** Check `Content-Length` against a small JSON budget (e.g., 8–16 KiB) before reading, or stream-read with an early cutoff similar to CR-01.

### WR-05: Broad `ValueError` handler masks unexpected failures

**File:** `app/services/url_fetch.py:76-77`
**Issue:** The outer `except ValueError` converts any `ValueError` into `UrlFetchError("invalid_url", str(exc))`, including unexpected internal errors raised during fetch/parse. That can mislabel server-side bugs as client `invalid_url` 400s and hide root causes in logs.
**Fix:** Remove the catch-all `ValueError` handler, or narrow it to known validation paths (e.g., `ipaddress.AddressValueError`) and re-raise unknown `ValueError` instances.

## Info

### IN-01: Misleading torch install comment in requirements.txt

**File:** `requirements.txt:1-2`
**Issue:** The header comment instructs `pip install -r requirements.txt --index-url https://download.pytorch.org/whl/cpu`, but phase 01 documented that this single-step install fails because `--index-url` replaces PyPI and breaks FastAPI resolution. The comment contradicts the established two-step install procedure.
**Fix:** Update the comment to document the two-step install used in phase summaries (torch/torchvision from CPU index first, then remaining packages from PyPI).

### IN-02: Health probe 503 body differs from API error contract

**File:** `app/api/routes/health.py:15`
**Issue:** `/health/ready` returns `{"status": "not_ready"}` on 503 instead of the `ErrorDetail` schema used elsewhere. Functionally acceptable for probes, but inconsistent with the structured error pattern established for `/predict`.
**Fix:** Either document probe responses as intentionally distinct, or align with `ErrorDetail` for uniform client parsing.

---

_Reviewed: 2026-07-07T20:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
