---
phase: 02
slug: containerization
status: verified
threats_open: 0
asvs_level: 1
created: 2026-07-08
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Containerization: multi-stage Dockerfile, non-root runtime, env-based config, host smoke scripts.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Host → docker build | Build context copied into image layers | Source tree; must exclude secrets via `.dockerignore` |
| Builder stage → network | One-time PyTorch weight download during `docker build` | Model weights from PyTorch CDN |
| Container runtime → client | Same API surface as Phase 1 inside container | HTTP requests/responses (upload, health, metrics) |
| Host smoke script → Docker daemon | `scripts/docker.py` invokes `docker` CLI | Fixed image name, localhost HTTP probes |
| `.env.example` → developer | Template for local/container env tuning | Placeholder config values (no secrets) |
| `docker run -e` → container | Runtime env overrides app settings | TORCH_NUM_THREADS, MAX_UPLOAD_BYTES, URL_TIMEOUT, LOG_LEVEL |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-02-01 | Information Disclosure | Dockerfile / image layers | mitigate | `.dockerignore` excludes `.env`; Dockerfile copies only `requirements.txt` and `app/`; config via runtime env (CONT-03) | closed |
| T-02-02 | Elevation of Privilege | Container process | mitigate | `useradd --uid 1000 appuser`; `chown -R appuser:appuser /app` before `USER appuser` | closed |
| T-02-03 | Denial of Service | Image size | mitigate | CPU-only torch install via `--index-url`; `docker-smoke` asserts image size &lt; 2 GB | closed |
| T-02-04 | Tampering | Model cache at runtime | mitigate | Weights baked in builder stage; `TORCH_HOME=/app/.cache/torch` copied to runtime; owned by appuser | closed |
| T-02-SC | Tampering | pip install in Dockerfile | mitigate | Reuses Phase 1 pinned `requirements.txt`; no new pip packages introduced | closed |
| T-02-05 | Information Disclosure | `.env.example` | mitigate | Placeholder defaults only; `.gitignore` excludes `.env`; README documents copy pattern | closed |
| T-02-06 | Tampering | smoke script subprocess | mitigate | All `subprocess.run`/`check_output` calls use argv lists; no `shell=True`; fixed `IMAGE` constant | closed |
| T-02-07 | Denial of Service | smoke poll loop | mitigate | `_wait_ready()` 120 s timeout; container stopped in `finally` block | closed |
| T-02-08 | Spoofing | smoke HTTP client | accept | Smoke targets `127.0.0.1` only; no external URLs in smoke path | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Mitigation Evidence

| Threat ID | Evidence |
|-----------|----------|
| T-02-01 | `.dockerignore:6` — `.env` excluded; `Dockerfile:5,14,29` — only `requirements.txt` and `app/` copied |
| T-02-02 | `Dockerfile:24,35,37` — uid 1000 user, chown, then `USER appuser` |
| T-02-03 | `Dockerfile:7-10` — CPU torch index; `scripts/docker.py:102-110` — `_assert_image_size()` |
| T-02-04 | `Dockerfile:16-18,28,31` — bake weights in builder, copy cache to runtime |
| T-02-SC | `Dockerfile:12` — `pip install -r requirements.txt` (Phase 1 pins unchanged) |
| T-02-05 | `.env.example:2-5` — placeholder values; `.gitignore:151` — `.env` excluded; `README.md:38` — copy guidance |
| T-02-06 | `scripts/docker.py:24,28-48,104,114,123,132` — list-form subprocess calls, no `shell=True` |
| T-02-07 | `scripts/docker.py:63-74` — `_wait_ready(timeout=120)`; `:139-156` — `finally: _stop_container()` |
| T-02-08 | `scripts/docker.py:17-19` — `HOST = "127.0.0.1"`; all smoke HTTP to localhost |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-08 | Smoke script only probes localhost container under test; no external URL fetch in smoke path — acceptable for dev E2E harness | security audit | 2026-07-08 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-08 | 9 | 9 | 0 | gsd-security-auditor (orchestrator inline) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-08
