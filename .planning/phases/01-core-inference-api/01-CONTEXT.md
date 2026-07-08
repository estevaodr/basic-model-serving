# Phase 1: Core Inference API - Context

**Gathered:** 2026-07-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a working, observable FastAPI service that loads ResNet-50 once at startup and serves top-5 ImageNet predictions via `POST /predict` (file upload or image URL), with split health probes (`/health/live`, `/health/ready`), structured JSON logging, auto-generated OpenAPI docs, and Prometheus metrics (`request_count`, `request_duration`, `prediction_count`). This is the foundation every later phase packages, deploys, or visualizes — no Docker, Kubernetes, CI, or Grafana work in this phase.

</domain>

<decisions>
## Implementation Decisions

### Concurrent Inference
- **D-01:** `/predict` is implemented as a plain `def` handler (not `async def`). FastAPI offloads synchronous CPU-bound PyTorch inference to its internal thread pool, keeping the asyncio event loop free for `/health/*` and `/metrics`.
- **D-02:** Single Uvicorn worker for Phase 1 — one process, one model copy in memory. Concurrent requests are handled via the thread pool within that process, not via multiple worker processes.
- **D-03:** No explicit concurrency cap (no semaphore/503 saturation gate). Rely on FastAPI/Uvicorn default thread pool behavior; sufficient for the portfolio demo target of 10+ concurrent requests.
- **D-04:** Configure `torch.set_num_threads()` at startup via env var (e.g. `TORCH_NUM_THREADS`, default sensible value like 2) through `pydantic-settings`. Avoids PyTorch defaulting to host CPU count, which causes cgroup throttling once deployed to Kubernetes in Phase 5.

### Carried Forward (not re-discussed — locked from PROJECT.md / REQUIREMENTS.md / research)
- Both file upload (multipart) and image URL input on `/predict`
- ResNet-50 with ImageNet weights; top-5 predictions with confidence scores
- Model loaded exactly once at startup via FastAPI `lifespan`, stored on `app.state`
- Split `/health/live` (process alive) and `/health/ready` (503 until model loaded)
- Structured JSON logs with request ID per request
- Structured 4xx JSON errors for invalid input (never raw 500s)
- SSRF protection on URL fetch (private/loopback/link-local IP block, scheme allowlist, no redirect-follow, timeout + size cap) — per REQUIREMENTS.md API-05; implementation specifics left to planner/researcher
- Python 3.12 target runtime (not 3.9 — current torch/Pillow deps require >=3.10)
- No authentication/authorization

### Claude's Discretion
- Request contract shape (single multipart endpoint vs dual content-types vs separate routes) — user did not discuss; follow ARCHITECTURE.md Pattern 2 (converge upload + URL to one preprocessing path)
- Response JSON shape (ImageNet label strings vs synset IDs, confidence as 0–1 float) — user did not discuss; use human-readable ImageNet class names and 0–1 confidence floats unless research suggests otherwise
- Validation error message verbosity — user did not discuss; structured 4xx with clear, reviewer-friendly messages per API-04
- URL guardrail strictness beyond API-05 minimum — user did not discuss; implement full SSRF checklist from PITFALLS.md Pitfall 8
- Layered project structure (`app/api/`, `app/services/`, `app/models/`) — follow ARCHITECTURE.md recommended layout
- Metrics histogram bucket boundaries around the 100ms SLO — tune during instrumentation, not left at Prometheus defaults

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope & requirements
- `.planning/PROJECT.md` — Core value, active requirements, out-of-scope boundaries, key decisions (ResNet-50, no auth, upload+URL input)
- `.planning/REQUIREMENTS.md` — API-01 through API-08, HLTH-01, HLTH-02, MON-01 with acceptance-level detail
- `.planning/ROADMAP.md` — Phase 1 goal, success criteria, requirement mapping

### Research (stack, architecture, pitfalls)
- `.planning/research/STACK.md` — Python 3.12, torch 2.12.1 CPU wheel, FastAPI 0.139, dependency pins, CPU-only install pattern
- `.planning/research/ARCHITECTURE.md` — Layered app structure, lifespan model loading, health probe split, upload/URL convergence pattern, build order
- `.planning/research/PITFALLS.md` — Pitfall 1 (event-loop blocking), Pitfall 2 (thread/CPU mismatch), Pitfall 8 (SSRF); phase-to-pitfall mapping
- `.planning/research/SUMMARY.md` — Consolidated findings, open decisions flagged for later phases

### State
- `.planning/STATE.md` — Current project position and accumulated context

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield repo (LICENSE + stub README only). All application code is net-new.

### Established Patterns
- ARCHITECTURE.md prescribes: `app/main.py` with lifespan → `app.state.classifier`; thin routes in `app/api/routes/`; inference orchestration in `app/services/inference.py`; model wrapper in `app/models/resnet.py`; config via `app/core/config.py` (pydantic-settings)
- PITFALLS.md mandates plain `def` for CPU-bound inference (now locked in D-01)

### Integration Points
- `/metrics` endpoint must expose `request_count`, `request_duration`, `prediction_count` (MON-01) — consumed by Prometheus in Phase 3 docker-compose and Phase 5 K8s
- `/health/live` and `/health/ready` probe paths consumed by Docker HEALTHCHECK (Phase 2) and K8s probes (Phase 5)
- `TORCH_NUM_THREADS` env var wired in Phase 1, consumed unchanged by container/K8s config in later phases

</code_context>

<specifics>
## Specific Ideas

- User explicitly chose the research-recommended path for concurrency: plain `def` handler, single worker, no cap, env-configurable torch threads — aligns with PITFALLS.md Pitfalls 1 and 2 prevention without over-engineering for Phase 1

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Undiscussed gray areas (request contract, response shape, error UX, URL guardrail strictness) deferred to Claude's discretion per decisions above, not to future phases.

</deferred>

---

*Phase: 1-Core Inference API*
*Context gathered: 2026-07-07*
