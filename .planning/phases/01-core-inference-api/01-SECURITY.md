---
phase: 01
slug: core-inference-api
status: verified
threats_open: 0
asvs_level: 1
created: 2026-07-07
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Retroactive STRIDE audit of implemented FastAPI inference API (multipart/URL predict, SSRF guards, health probes, metrics, logging).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Client → POST /predict (upload) | Untrusted multipart file bytes enter server process | Raw image bytes (≤1 MB cap) |
| Client → POST /predict (JSON image_url) | Untrusted URL triggers outbound HTTP | URL string → fetched bytes |
| Server → external URL | Outbound GET crosses network trust boundary | HTTP(S) response body |
| PIL decode | Untrusted bytes expanded in memory for inference | Decompressed raster |
| Client → GET /health/* | Low-risk HTTP probes, no body | Status metadata |
| Client → GET /metrics | Unauthenticated metric scrape | Aggregated counters/histograms |
| Logs (stdout) | Request metadata persisted per request | method, path, status, duration_ms, request_id |
| pip install | Third-party packages from PyPI / PyTorch index | Build-time dependency supply chain |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-01-01 | Tampering | POST /predict upload | mitigate | Pillow-only decode; `verify()` + re-open; `UnidentifiedImageError`/`OSError` → `InferenceError` | closed |
| T-01-02 | Denial of Service | upload path | mitigate | `_read_upload_limited()` stream-read with early cutoff; `predict_from_bytes` size check | closed |
| T-01-03 | Information Disclosure | error responses | mitigate | `ErrorDetail` schema; HTTPException handler returns flat JSON; no traceback in route code | closed |
| T-01-04 | Tampering | requirements.txt | mitigate | Exact version pins in `requirements.txt` (torch, fastapi, httpx, pillow, etc.) | closed |
| T-01-SC | Tampering | pip package installs | mitigate | Pins from official PyPI/PyTorch CPU index; two-step install documented | closed |
| T-01-05 | Spoofing | url_fetch.py (SSRF) | mitigate | Scheme allowlist (`http`/`https`); resolved-IP denylist; `follow_redirects=False`; timeout; streaming size cap; DNS pinning | closed |
| T-01-06 | Tampering | DNS rebinding TOCTOU | mitigate | `validate_url()` resolves once; `fetch_url_bytes()` connects to pinned IP with `Host` header and SNI | closed |
| T-01-07 | Denial of Service | url_fetch.py | mitigate | `max_bytes` stream cap; `url_timeout` on httpx.Client; reject before decode | closed |
| T-01-08 | Information Disclosure | predict error handler | mitigate | `UrlFetchError`/`InferenceError` → safe `ErrorDetail` messages; server-side exceptions mapped, not raw tracebacks | closed |
| T-01-09 | Tampering | upload path | mitigate | In-memory only (no disk write); Pillow decode verification; size cap before inference | closed |
| T-01-10 | Information Disclosure | JSON logs | mitigate | `RequestIdMiddleware` logs method/path/status/duration only — no image bytes or image_url | closed |
| T-01-11 | Denial of Service | metric labels | mitigate | Labels limited to method/path/status; `prediction_count` unlabeled; route template path used | closed |
| T-01-12 | Information Disclosure | GET /metrics | accept | Public scrape endpoint by design; no secrets in metric labels | closed |
| T-01-13 | Repudiation | request logs | mitigate | `request_id` ContextVar + `X-Request-ID` header on every response; included in ErrorDetail | closed |
| T-01-14 | Spoofing | API endpoints | accept | No authentication/authorization — out of scope per PROJECT.md | closed |
| T-01-15 | Denial of Service | image decompression | mitigate | Pillow default `MAX_IMAGE_PIXELS`; `DecompressionBombError` caught as `invalid_image` 400 | closed |
| T-01-16 | Denial of Service | JSON request body | mitigate | `_read_json_body_limited()` with `MAX_JSON_BODY_BYTES=16384` streaming cap | closed |
| T-01-17 | Denial of Service | concurrent /predict | accept | No semaphore/rate cap per D-03; relies on Uvicorn thread pool for portfolio demo scale | closed |
| T-01-18 | Denial of Service | abuse/rate limiting | accept | No rate limiting or API gateway — out of scope per REQUIREMENTS.md | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Mitigation Evidence

| Threat ID | Evidence |
|-----------|----------|
| T-01-01, T-01-09, T-01-15 | `app/services/inference.py:25-30` — PIL open/verify/convert; catches `UnidentifiedImageError`, `DecompressionBombError`, `OSError` |
| T-01-02 | `app/api/routes/predict.py:39-53,208-211` — `_read_upload_limited()`; `app/services/inference.py:19-23` — post-read guard |
| T-01-03, T-01-08 | `app/main.py:51-58` — HTTPException handler; `app/api/routes/predict.py:24-36` — `_client_error()` with ErrorDetail |
| T-01-04, T-01-SC | `requirements.txt:4-11` — pinned versions |
| T-01-05, T-01-06, T-01-07 | `app/services/url_fetch.py:28-53` — validate_url scheme/IP checks + pinned URL; `:56-77` — httpx stream with `follow_redirects=False`, size cap, timeout |
| T-01-10 | `app/core/logging.py:70-78` — logs method, path, status, duration_ms only |
| T-01-11 | `app/metrics/prometheus.py:8-19,35-43` — low-cardinality labels; route template path |
| T-01-13 | `app/core/logging.py:59-68,70-78` — request_id generation/propagation |
| T-01-16 | `app/api/routes/predict.py:16,56-78,174` — JSON body streaming cap |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-01-12 | `/metrics` is intentionally unauthenticated for Prometheus scrape in local/portfolio demo; no sensitive data in metric series | PROJECT.md scope | 2026-07-07 |
| AR-02 | T-01-14 | No authentication/authorization on API — no real users/tenants for local demo; adds security surface with no portfolio benefit | PROJECT.md, REQUIREMENTS.md Out of Scope | 2026-07-07 |
| AR-03 | T-01-17 | No explicit concurrency cap on `/predict` (D-03) — sufficient for 10+ concurrent demo requests; formal load proof deferred to Phase 6 | 01-CONTEXT.md D-03 | 2026-07-07 |
| AR-04 | T-01-18 | Rate limiting and API gateway excluded from scope — no external abuse vector for local minikube demo | REQUIREMENTS.md Out of Scope | 2026-07-07 |

---

## Unregistered Flags

No `## Threat Flags` sections found in phase SUMMARY files. No unregistered implementation attack surface flagged by executor.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-07 | 18 | 18 | 0 | gsd-security-auditor (retroactive-STRIDE) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-07
