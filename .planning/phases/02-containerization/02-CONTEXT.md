# Phase 2: Containerization - Context

**Gathered:** 2026-07-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Package the working Phase 1 FastAPI + ResNet-50 API into a portable, secure Docker image: multi-stage build, CPU-only PyTorch wheel, image under 2GB, non-root runtime user, all application configuration via environment variables. The image must be ready for local `docker run` and later consumption by docker-compose (Phase 3), CI build/push (Phase 4), and werf/Kubernetes (Phase 5).

**Out of scope for this phase:** docker-compose stack (CONT-04 → Phase 3), GitHub Actions CI (Phase 4), Kubernetes manifests or werf deploy (Phase 5), Grafana dashboards, new API features, authentication.

</domain>

<decisions>
## Implementation Decisions

### Model Weights & Cache
- **D-01:** Bake ResNet-50 IMAGENET1K_V2 weights into the image at **build time** (download in builder stage as root, copy into runtime stage). No runtime network dependency for weights; aligns with "model loaded at startup, no cold start" and prevents non-root cache permission failures (PITFALLS.md Pitfall 4).
- **D-02:** Set `TORCH_HOME=/app/.cache/torch`; create the directory and `chown` to the non-root user before the `USER` switch. Use this path whether weights are pre-copied or torchvision resolves cache lookups.
- **D-03:** Accept ~100–200MB extra image size from baked weights — reliability over minimal image size; total image must still stay under 2GB with CPU-only torch.
- **D-04:** Phase 2 acceptance includes a **full smoke test as the non-root user**: build image → run container → verify `/health/ready` → `POST /predict` with a sample image returns 200 with predictions. Not build-only verification.

### Configurable Environment Variables
- **D-05:** Keep the existing four settings only — no new env vars in Phase 2 unless strictly required by the Dockerfile: `TORCH_NUM_THREADS`, `MAX_UPLOAD_BYTES`, `URL_TIMEOUT`, `LOG_LEVEL` (already in `app/core/config.py` via pydantic-settings).
- **D-06:** Retain pydantic-settings auto-mapping convention (`torch_num_threads` → `TORCH_NUM_THREADS`, etc.) — no explicit `Field(validation_alias=...)` unless a naming conflict appears.
- **D-07:** Add `.env.example` at repo root documenting all configurable vars with defaults. Cross-reference from README Docker section.
- **D-08:** Uvicorn bind settings stay **hardcoded in Dockerfile CMD**: `--host 0.0.0.0 --port 8000`, single worker (Phase 1 D-02). Do not expose `UVICORN_HOST`, `UVICORN_PORT`, or `UVICORN_WORKERS` as env vars in Phase 2.

### Local Container Workflow
- **D-09:** Developer workflow uses **`uv run` scripts** defined in `pyproject.toml` (net-new file) — not a Makefile. Intended commands wrap docker build/run/smoke (e.g., `uv run docker-build`, `uv run docker-run`, `uv run docker-smoke`). Reviewers with `uv` installed get a one-command inner loop.
- **D-10:** Smoke workflow is **full E2E**: `docker build` → `docker run` → curl `/health/ready` → curl `POST /predict` with sample image. Include image size verification (<2GB) and non-root user confirmation in the smoke path.
- **D-11:** Standard `.dockerignore`: exclude `.git`, `.venv`, `__pycache__`, `.planning/`, `.env`, and other dev artifacts; **keep `tests/`** in build context (may be useful for in-container validation; not excluded aggressively).
- **D-12:** Local image tag convention: fixed tag `basic-model-serving:local`. GHCR/SHA tagging deferred to Phase 4 CI.

### Carried Forward (not re-discussed — locked from Phase 1, research, PROJECT.md)
- Base image: `python:3.12-slim` (Debian glibc) — **not Alpine** (PyTorch has no musl wheels; STACK.md, PITFALLS.md)
- CPU-only torch install via `--index-url https://download.pytorch.org/whl/cpu` — already pinned in `requirements.txt` two-step pattern
- Multi-stage Dockerfile: builder installs wheels, runtime copies artifacts only (CONT-01)
- Non-root user `appuser` uid 1000 (CONT-02)
- Split health probes from Phase 1: `/health/live` (process) and `/health/ready` (model loaded)
- `torch.set_num_threads(settings.torch_num_threads)` at startup (Phase 1 D-04) — container must respect `TORCH_NUM_THREADS` env

### Claude's Discretion
- **Docker HEALTHCHECK endpoint:** User did not discuss. Use `GET /health/ready` with a generous `--start-period` (covering in-process model load at container start). Weights are baked so load is faster than runtime download, but ResNet-50 init still takes seconds. Alternative `/health/live` is acceptable only if start-period is insufficient — prefer readiness semantics so Docker reports healthy when the API can actually serve predictions.
- **`pyproject.toml` structure:** Script entry points, optional `[project]` metadata, and whether smoke logic lives inline in scripts or a small `scripts/` module — planner decides; must support `uv run docker-build|docker-run|docker-smoke` ergonomics.
- **Builder-stage weight download mechanism:** Exact `python -c` or small build script to trigger `ResNetClassifier` / `torchvision.models.resnet50(weights=...)` download during build — implementation detail for planner.
- **HEALTHCHECK probe implementation:** `curl` vs `python -c urllib` vs `wget` — depend on what's available in `python:3.12-slim` with minimal extra packages.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope & requirements
- `.planning/PROJECT.md` — Containerization active requirements, <2GB image target, non-root, env-var config, GHCR/werf context
- `.planning/REQUIREMENTS.md` — CONT-01, CONT-02, CONT-03 acceptance criteria
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, dependency on Phase 1

### Phase 1 context (upstream decisions)
- `.planning/phases/01-core-inference-api/01-CONTEXT.md` — D-01 plain `def` predict, D-02 single Uvicorn worker, D-04 `TORCH_NUM_THREADS`, health probe split
- `app/core/config.py` — Existing pydantic-settings surface (4 env vars)
- `app/main.py` — Lifespan model load, Uvicorn single-worker comment
- `app/api/routes/health.py` — `/health/live` and `/health/ready` contracts
- `requirements.txt` — CPU-only torch two-step install pattern

### Research (stack, architecture, pitfalls)
- `.planning/research/STACK.md` — § Docker / Multi-Stage Build: `python:3.12-slim`, CPU index, non-root user, multi-stage pattern (note: example uses outdated `/health` path and wrong `main:app` module path — use `app.main:app`)
- `.planning/research/ARCHITECTURE.md` — Dockerfile + `.dockerignore` build order (step 3), config injection pattern, "build once deploy everywhere"
- `.planning/research/PITFALLS.md` — Pitfall 3 (CUDA wheel bloat), Pitfall 4 (non-root cache permissions — bake weights), Pitfall 2 (torch thread count in cgroup)
- `.planning/research/SUMMARY.md` — Phase 2 deliverables summary, pitfall-to-phase mapping

### State
- `.planning/STATE.md` — Current project position after Phase 1 ship

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/core/config.py` — `Settings` with `TORCH_NUM_THREADS`, `MAX_UPLOAD_BYTES`, `URL_TIMEOUT`, `LOG_LEVEL`; extend only if Dockerfile truly needs a new var (user locked to 4)
- `app/models/resnet.py` — `ResNetClassifier` loads `ResNet50_Weights.IMAGENET1K_V2`; use as build-time weight download trigger
- `app/api/routes/health.py` — Ready-made probes for Docker HEALTHCHECK and smoke tests
- `requirements.txt` + `requirements-dev.txt` — Pinned deps; Dockerfile must preserve two-step CPU torch install

### Established Patterns
- pydantic-settings for all runtime config — container injects env vars, no code changes per environment (CONT-03)
- Lifespan loads model once; `app.state.ready` gates `/health/ready` — smoke test should wait for ready before predict
- Phase 1 comment in `app/main.py`: single Uvicorn worker, no `--workers` flag

### Integration Points
- `/health/ready` and `/health/live` — consumed by Docker HEALTHCHECK (Phase 2) and later K8s probes (Phase 5)
- `/metrics` — not scraped in Phase 2; Prometheus wiring is Phase 3 docker-compose
- `TORCH_NUM_THREADS` — wired in Phase 1, passed unchanged via container env / later ConfigMap
- Image tag `basic-model-serving:local` — referenced by Phase 3 docker-compose before GHCR tags exist

</code_context>

<specifics>
## Specific Ideas

- User prefers **uv run scripts in pyproject.toml** over Makefile for the container dev workflow — aligns with project's existing `uv` usage for local dev
- User explicitly chose baking weights and accepting larger image for reliability over runtime download complexity
- Full E2E smoke (health + predict) as non-root user is a hard acceptance criterion, not optional

</specifics>

<deferred>
## Deferred Ideas

- **Docker HEALTHCHECK endpoint choice** — deferred to Claude's discretion (see decisions); user did not select this gray area for discussion
- **docker-compose stack** — Phase 3 (CONT-04, MON-02–05)
- **CI build/push to GHCR** — Phase 4; image tagging with git SHA happens there, not Phase 2 local tag
- **Kubernetes probes and resource limits** — Phase 5; startupProbe tuning builds on Phase 2 HEALTHCHECK learnings

</deferred>

---

*Phase: 2-Containerization*
*Context gathered: 2026-07-08*
