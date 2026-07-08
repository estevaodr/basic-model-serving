# Phase 2: Containerization - Research

**Researched:** 2026-07-08
**Domain:** Docker multi-stage builds for FastAPI + CPU-only PyTorch inference
**Confidence:** HIGH

## Summary

Phase 2 packages the existing Phase 1 FastAPI + ResNet-50 API into a production-style Docker image. All major decisions are locked in `02-CONTEXT.md`: `python:3.12-slim` base, CPU-only PyTorch via the dedicated wheel index, multi-stage build, non-root `appuser` (uid 1000), ResNet-50 weights baked at build time into `TORCH_HOME=/app/.cache/torch`, four env vars only, hardcoded Uvicorn CMD, and a full E2E smoke path (`build → run → /health/ready → POST /predict`) verified as non-root.

The highest-leverage technical risks are already documented in project research: accidentally pulling CUDA wheels (Pitfall 3, 5–8GB images) and non-root cache permission failures (Pitfall 4). The locked decision to bake weights at build time directly mitigates Pitfall 4. The Dockerfile must preserve the Phase 1 two-step CPU torch install pattern from `requirements.txt` and use `app.main:app` (not `main:app` as in the outdated STACK.md example).

For developer workflow, `uv run docker-build|docker-run|docker-smoke` maps to `[project.scripts]` entry points in a new `pyproject.toml` — Python callables that invoke `docker`/`curl` via `subprocess`, because uv has no native shell-script table [VERIFIED: Context7 `/astral-sh/uv`]. The smoke script must assert image size <2GB, container user is non-root, readiness before predict, and five top-k predictions in the response.

Estimated final image size: ~600–900MB (base ~150MB + CPU torch ~250MB + deps ~50MB + ResNet-50 weights ~100MB), comfortably under the 2GB cap [CITED: `.planning/research/STACK.md` CPU-wheel guidance; size breakdown ASSUMED pending first build].

**Primary recommendation:** Use a two-stage `Dockerfile` at repo root with a builder stage that (1) installs CPU torch/torchvision from `--index-url https://download.pytorch.org/whl/cpu`, (2) installs remaining requirements, (3) triggers `ResNetClassifier()` to download/cache weights, then a runtime stage that copies site-packages + baked cache, sets `TORCH_HOME`, chowns to `appuser`, and runs `uvicorn app.main:app` with a `urllib`-based HEALTHCHECK on `/health/ready`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Model Weights & Cache
- **D-01:** Bake ResNet-50 IMAGENET1K_V2 weights into the image at **build time** (download in builder stage as root, copy into runtime stage). No runtime network dependency for weights; aligns with "model loaded at startup, no cold start" and prevents non-root cache permission failures (PITFALLS.md Pitfall 4).
- **D-02:** Set `TORCH_HOME=/app/.cache/torch`; create the directory and `chown` to the non-root user before the `USER` switch. Use this path whether weights are pre-copied or torchvision resolves cache lookups.
- **D-03:** Accept ~100–200MB extra image size from baked weights — reliability over minimal image size; total image must still stay under 2GB with CPU-only torch.
- **D-04:** Phase 2 acceptance includes a **full smoke test as the non-root user**: build image → run container → verify `/health/ready` → `POST /predict` with a sample image returns 200 with predictions. Not build-only verification.

#### Configurable Environment Variables
- **D-05:** Keep the existing four settings only — no new env vars in Phase 2 unless strictly required by the Dockerfile: `TORCH_NUM_THREADS`, `MAX_UPLOAD_BYTES`, `URL_TIMEOUT`, `LOG_LEVEL` (already in `app/core/config.py` via pydantic-settings).
- **D-06:** Retain pydantic-settings auto-mapping convention (`torch_num_threads` → `TORCH_NUM_THREADS`, etc.) — no explicit `Field(validation_alias=...)` unless a naming conflict appears.
- **D-07:** Add `.env.example` at repo root documenting all configurable vars with defaults. Cross-reference from README Docker section.
- **D-08:** Uvicorn bind settings stay **hardcoded in Dockerfile CMD**: `--host 0.0.0.0 --port 8000`, single worker (Phase 1 D-02). Do not expose `UVICORN_HOST`, `UVICORN_PORT`, or `UVICORN_WORKERS` as env vars in Phase 2.

#### Local Container Workflow
- **D-09:** Developer workflow uses **`uv run` scripts** defined in `pyproject.toml` (net-new file) — not a Makefile. Intended commands wrap docker build/run/smoke (e.g., `uv run docker-build`, `uv run docker-run`, `uv run docker-smoke`). Reviewers with `uv` installed get a one-command inner loop.
- **D-10:** Smoke workflow is **full E2E**: `docker build` → `docker run` → curl `/health/ready` → curl `POST /predict` with sample image. Include image size verification (<2GB) and non-root user confirmation in the smoke path.
- **D-11:** Standard `.dockerignore`: exclude `.git`, `.venv`, `__pycache__`, `.planning/`, `.env`, and other dev artifacts; **keep `tests/`** in build context (may be useful for in-container validation; not excluded aggressively).
- **D-12:** Local image tag convention: fixed tag `basic-model-serving:local`. GHCR/SHA tagging deferred to Phase 4 CI.

#### Carried Forward (not re-discussed — locked from Phase 1, research, PROJECT.md)
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

### Deferred Ideas (OUT OF SCOPE)

- **Docker HEALTHCHECK endpoint choice** — deferred to Claude's discretion (see decisions); user did not select this gray area for discussion
- **docker-compose stack** — Phase 3 (CONT-04, MON-02–05)
- **CI build/push to GHCR** — Phase 4; image tagging with git SHA happens there, not Phase 2 local tag
- **Kubernetes probes and resource limits** — Phase 5; startupProbe tuning builds on Phase 2 HEALTHCHECK learnings
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONT-01 | Multi-stage Dockerfile produces an image <2GB (CPU-only PyTorch build, no CUDA) | Two-stage pattern with CPU `--index-url`; separate torch install RUN layer; `pip show torch` must show `+cpu`; smoke asserts `docker image inspect` size < 2e9 bytes |
| CONT-02 | Container runs as a non-root user | `useradd --uid 1000 appuser`; `COPY --chown`; `chown` on `TORCH_HOME`; `USER appuser` before CMD; smoke runs `docker exec` id check |
| CONT-03 | Application configuration is provided via environment variables | Existing `Settings` in `app/core/config.py` (4 vars); `.env.example`; `docker run -e` overrides; no code changes per environment |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Multi-stage image build | Build-time (Dockerfile) | — | CONT-01; packages app + deps + weights into portable artifact |
| CPU-only PyTorch install | Build-time (Dockerfile builder) | — | Wrong index at build time permanently bloats image; not fixable at runtime |
| ResNet-50 weight caching | Build-time (Dockerfile builder) | Runtime read-only (`TORCH_HOME`) | D-01/D-02; weights downloaded as root, consumed by non-root at runtime |
| Non-root process identity | Container runtime (Dockerfile USER) | — | CONT-02; enforced by image, not app code |
| App configuration (4 env vars) | Container runtime (env injection) | API / Backend (`pydantic-settings`) | CONT-03; same image, different env per environment |
| Health/readiness signaling | API / Backend (`/health/*`) | Container runtime (HEALTHCHECK) | App owns readiness semantics; Docker/K8s consume HTTP probes |
| Local build/run/smoke workflow | Developer host (`uv run` scripts) | — | D-09/D-10; orchestrates Docker CLI on host, not in-container |
| Inference execution | API / Backend (existing Phase 1) | — | Out of scope for Phase 2 changes; container wraps unchanged app |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `python` (base image) | 3.12-slim | Container runtime | Locked D-01; glibc Debian base; PyTorch has no musl wheels [CITED: `.planning/research/PITFALLS.md` Pitfall 3] |
| `torch` | 2.12.1 (+cpu) | Inference engine | Pinned in `requirements.txt`; CPU wheel via PyTorch index [CITED: pytorch.org get-started] |
| `torchvision` | 0.27.1 | ResNet-50 weights + transforms | Must match torch 2.12.x major.minor [CITED: `.planning/research/STACK.md`] |
| `uvicorn` | via `fastapi[standard]` | ASGI server | Phase 1 single-worker pattern; hardcoded in CMD (D-08) |
| `pydantic-settings` | 2.14.2 | Env-var config | CONT-03; already wired in `app/core/config.py` |
| `uv` | 0.8.3 (host) | Script runner for docker workflow | D-09; available on dev host [VERIFIED: local `uv --version`] |
| `docker` | 29.6.1 (host) | Image build/run | Required for all Phase 2 deliverables [VERIFIED: local `docker --version`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fastapi[standard]` | 0.139.0 | HTTP API (unchanged) | Already in image via requirements.txt |
| `pillow` | 12.3.0 | Image decode for /predict smoke | POST /predict multipart in smoke test |
| `prometheus-client` | 0.25.0 | Metrics (unchanged) | Carried in image; scraped in Phase 3 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pip` + `requirements.txt` in Dockerfile | `uv sync` + `uv.lock` (astral-sh/uv-docker-example) | uv-docker-example is best practice for uv-native projects; this project uses `requirements.txt` from Phase 1 — switching adds scope. Keep pip in Dockerfile; use uv only for host scripts (D-09). |
| `curl` in HEALTHCHECK | `python -c "import urllib.request; ..."` | `python:3.12-slim` has no curl [CITED: Docker slim image practice, Context7 `/docker/docs`]; stdlib urllib adds zero image size |
| Runtime weight download | Build-time bake (locked D-01) | Runtime download fails for non-root without careful chown; adds network dependency |
| `[tool.uv.scripts]` shell aliases | `[project.scripts]` Python entry points | uv has no native shell-script table [VERIFIED: Context7 `/astral-sh/uv`]; `[project.scripts]` is the supported `uv run <name>` mechanism |

**Version verification (2026-07-08):**
```bash
pip index versions torch      # latest 2.13.0; project pins 2.12.1
pip index versions torchvision  # latest 0.28.0; project pins 0.27.1
pip index versions fastapi    # 0.139.0 matches pin
```

**Installation (in Dockerfile builder — not new packages on host):**
```bash
# Step 1: CPU torch (MUST be separate RUN with --index-url)
pip install --no-cache-dir torch==2.12.1 torchvision==0.27.1 \
  --index-url https://download.pytorch.org/whl/cpu

# Step 2: remaining deps (torch already satisfied)
pip install --no-cache-dir -r requirements.txt
```

## Package Legitimacy Audit

> Phase 2 does not introduce new pip dependencies beyond what Phase 1 already installed. The container reuses `requirements.txt`. The new `pyproject.toml` is for host-side `uv run` scripts only (stdlib `subprocess`, no additional pip deps required for scripts).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| torch==2.12.1 | PyPI | ~1 yr | High (est.) | github.com/pytorch/pytorch | OK* | Approved — Phase 1 pin, CPU index install |
| torchvision==0.27.1 | PyPI | ~1 yr | High (est.) | github.com/pytorch/vision | OK* | Approved — paired with torch 2.12.1 |
| fastapi==0.139.0 | PyPI | Current | High (est.) | github.com/fastapi/fastapi | OK* | Approved — Phase 1 pin |
| pillow==12.3.0 | PyPI | Current | High (est.) | github.com/python-pillow/Pillow | OK* | Approved — Phase 1 pin |
| pydantic-settings==2.14.2 | PyPI | Current | High (est.) | github.com/pydantic/pydantic-settings | OK* | Approved — Phase 1 pin |

\*Seam returned `SUS` for all packages due to missing download telemetry in the checker — these are established packages already vetted in Phase 1 `requirements.txt`. No new installs in Phase 2.

**Packages removed due to [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** none actionable (existing Phase 1 pins only)

## Project Constraints (from .cursor/rules/)

- **GSD workflow:** Phase work should flow through `/gsd-execute-phase`; direct edits outside GSD only when user explicitly requests bypass.
- **Fixed tech stack:** Python, PyTorch, FastAPI, Uvicorn, Docker — no substitutions.
- **Python target:** Build on **Python 3.12** (not 3.9/3.10) per STACK.md compatibility resolution.
- **CPU-only inference:** No GPU/CUDA code paths.
- **Registry/deployment context:** GHCR + werf are downstream (Phases 4–5); Phase 2 delivers local `basic-model-serving:local` tag only.
- **CI/CD boundary:** No GitHub Actions or werf in Phase 2.

## Architecture Patterns

### System Architecture Diagram

```
Developer host                         Docker build context                Container runtime (non-root)
┌──────────────────┐                ┌─────────────────────┐            ┌────────────────────────────┐
│ uv run           │  docker build  │ STAGE: builder      │   COPY     │ STAGE: runtime             │
│  docker-build ───┼───────────────►│ python:3.12-slim    ├───────────►│ python:3.12-slim           │
│  docker-run      │                │  1. pip CPU torch   │ site-pkgs  │  ENV TORCH_HOME=/app/.cache│
│  docker-smoke    │                │  2. pip requirements│ + weights  │  COPY app/ + baked cache   │
└────────┬─────────┘                │  3. ResNetClassifier│            │  USER appuser (uid 1000)   │
         │ docker run               │     (download wt.)  │            │  CMD uvicorn app.main:app  │
         ▼                          └─────────────────────┘            │  HEALTHCHECK → /health/ready│
┌──────────────────┐                                                   └─────────────┬──────────────┘
│ curl /health/ready│◄──────────────────────────────────────────────────────────────┘
│ curl POST /predict│        pydantic-settings ← env vars (TORCH_NUM_THREADS, etc.)
└──────────────────┘
```

### Recommended Project Structure

```
.
├── Dockerfile                  # Multi-stage build (new)
├── .dockerignore               # Standard exclusions (new)
├── .env.example                # 4 env vars documented (new)
├── pyproject.toml              # [project.scripts] for uv run (new)
├── scripts/
│   └── docker.py               # build / run / smoke entry points (new)
├── requirements.txt            # Unchanged CPU two-step pattern
├── app/                        # Unchanged Phase 1 application
│   ├── main.py                 # lifespan + uvicorn entry (app.main:app)
│   ├── core/config.py          # 4 env vars
│   └── models/resnet.py        # Build-time weight download trigger
└── tests/                      # Kept in build context per D-11
    └── conftest.py             # sample_jpeg_bytes fixture pattern for smoke
```

### Pattern 1: Two-Stage Dockerfile with CPU Torch Isolation

**What:** Builder stage installs dependencies and downloads model weights; runtime stage copies only installed packages, app code, and weight cache — no pip/gcc in final image.

**When to use:** Always for CONT-01.

**Example:**
```dockerfile
# Source: Context7 /docker/docs + .planning/research/STACK.md
FROM python:3.12-slim AS builder
WORKDIR /app

COPY requirements.txt .
# CRITICAL: separate RUN — --index-url must not be --extra-index-url
RUN pip install --no-cache-dir torch==2.12.1 torchvision==0.27.1 \
    --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
ENV TORCH_HOME=/app/.cache/torch
RUN python -c "from app.models.resnet import ResNetClassifier; ResNetClassifier()"

FROM python:3.12-slim AS runtime
WORKDIR /app

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app/.cache/torch /app/.cache/torch
COPY app/ ./app/

ENV TORCH_HOME=/app/.cache/torch \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN mkdir -p /app/.cache/torch && chown -R appuser:appuser /app

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Pattern 2: uv `[project.scripts]` for Docker Workflow

**What:** Define `docker-build`, `docker-run`, `docker-smoke` as Python entry points; `uv run docker-smoke` orchestrates the full acceptance path.

**When to use:** D-09/D-10 local developer workflow.

**Example:**
```toml
# Source: Context7 /astral-sh/uv docs/concepts/projects/config.md
[project]
name = "basic-model-serving"
version = "0.1.0"
requires-python = ">=3.12"

[project.scripts]
docker-build = "scripts.docker:build"
docker-run = "scripts.docker:run"
docker-smoke = "scripts.docker:smoke"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["scripts"]
```

```python
# scripts/docker.py — smoke must verify: size <2GB, non-root, ready, predict 200
IMAGE = "basic-model-serving:local"

def build() -> None:
    subprocess.run(["docker", "build", "-t", IMAGE, "."], check=True)

def smoke() -> None:
    build()
    # assert image size, run detached, poll /health/ready, POST /predict, verify uid
```

### Pattern 3: Env-Only Configuration (No Image Rebuild)

**What:** Runtime tuning via the four existing env vars; Uvicorn bind stays in CMD.

**When to use:** CONT-03; validating with `docker run -e TORCH_NUM_THREADS=4`.

**Example:**
```bash
docker run --rm -p 8000:8000 \
  -e TORCH_NUM_THREADS=2 \
  -e LOG_LEVEL=DEBUG \
  -e MAX_UPLOAD_BYTES=1048576 \
  -e URL_TIMEOUT=5.0 \
  basic-model-serving:local
```

### Anti-Patterns to Avoid

- **Single-stage Dockerfile with build tools in runtime:** Adds ~300MB+ and violates CONT-01 spirit.
- **`pip install -r requirements.txt` without prior CPU torch step:** Silently pulls CUDA wheels from PyPI default [CITED: PITFALLS.md Pitfall 3].
- **`--extra-index-url` for CPU torch:** Pip resolver may still prefer CUDA wheel from PyPI.
- **`USER appuser` before `chown` on `TORCH_HOME`:** PermissionError at model load [CITED: PITFALLS.md Pitfall 4].
- **`HEALTHCHECK` on `/health/live` only:** Reports healthy before model loaded; use `/health/ready` per discretion guidance.
- **`curl` in HEALTHCHECK without installing it:** Fails on slim image; use stdlib urllib [CITED: Docker docs HEALTHCHECK reference].
- **Exposing Uvicorn host/port/workers as env vars:** Violates D-08.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CPU vs CUDA wheel selection | Custom pip wrapper / manual wheel URLs | `--index-url https://download.pytorch.org/whl/cpu` in dedicated RUN | Documented PyTorch install path; wrong index is the #1 image bloat cause |
| Env-var configuration | `os.environ.get()` scattered in Dockerfile/app | Existing `pydantic-settings` `Settings` | CONT-03 already implemented in Phase 1 |
| Health probe HTTP client | Install curl/wget just for HEALTHCHECK | `python -c "import urllib.request; ..."` | Zero extra packages; python guaranteed in base image |
| Docker task runner | Makefile (user rejected) or third-party uvtask | `[project.scripts]` + stdlib subprocess | Matches D-09; no extra dependencies |
| Model weight download at runtime | Entrypoint script downloading on first start | Builder-stage `ResNetClassifier()` + COPY cache | Locked D-01; avoids non-root cache bugs |
| Image size verification | Manual `docker images` only in docs | Assert in `docker-smoke` script | D-10 hard acceptance criterion |

**Key insight:** Every pitfall in this phase is a well-documented Docker+PyTorch footgun (CUDA wheels, non-root cache, slim-image probe tools). The locked decisions already point at the standard mitigations — the planner's job is sequencing Dockerfile layers correctly, not inventing new abstractions.

## Common Pitfalls

### Pitfall 1: CUDA Wheel Accidentally Installed (Image >2GB)

**What goes wrong:** `docker build` succeeds but image is 4–8GB; `pip show torch` lacks `+cpu` suffix.

**Why it happens:** Default PyPI torch is CUDA build; single combined `pip install -r requirements.txt` without CPU index first.

**How to avoid:** Separate `RUN` with `--index-url https://download.pytorch.org/whl/cpu` before other requirements [CITED: PITFALLS.md Pitfall 3, pytorch.org].

**Warning signs:** `docker images` shows >2GB; `pip show torch` shows `+cu124` or similar.

### Pitfall 2: Non-Root Permission Denied on Model Cache

**What goes wrong:** Container starts, `/health/ready` stays 503 or crashes with `PermissionError` on `/.cache/torch`.

**Why it happens:** Weights downloaded as root in builder but cache dir not chowned; or `TORCH_HOME` unset so torchvision writes to `~/.cache` owned by root.

**How to avoid:** D-01 bake at build time + D-02 `TORCH_HOME=/app/.cache/torch` with `chown -R appuser:appuser /app` before `USER` [CITED: PITFALLS.md Pitfall 4].

**Warning signs:** Works with `docker run -u root`, fails with default USER.

### Pitfall 3: HEALTHCHECK Marks Unhealthy During Model Load

**What goes wrong:** Docker reports `unhealthy` while app is still loading model into memory.

**Why it happens:** Default `--start-period=0s`; `/health/ready` returns 503 until `app.state.ready=True`.

**How to avoid:** `--start-period=45s` (tune 30–60s); probe `/health/ready` not `/health/live` [CITED: docs.docker.com/reference/dockerfile/#healthcheck].

**Warning signs:** `docker inspect` shows `Health.Status: unhealthy` in first 30s then recovers.

### Pitfall 4: Wrong Uvicorn Module Path

**What goes wrong:** Container crashes immediately: `Error loading ASGI app. Could not import module "main"`.

**Why it happens:** STACK.md example uses `main:app`; this project uses package layout `app/main.py`.

**How to avoid:** CMD must be `uvicorn app.main:app` [VERIFIED: `app/main.py` exists].

**Warning signs:** ImportError in container logs on startup.

### Pitfall 5: Smoke Test Passes Build-Only (Not Runtime Non-Root)

**What goes wrong:** Image builds but predict fails at runtime as non-root user.

**Why it happens:** Acceptance checks `docker build` exit code only, never runs container.

**How to avoid:** D-04/D-10 mandate full E2E; smoke script runs `docker exec <cid> id -u` expecting `1000` and POST /predict [locked in CONTEXT.md].

**Warning signs:** No `docker run` step in verification tasks.

### Pitfall 6: uv Scripts Expect Shell Aliases

**What goes wrong:** Planner adds `[tool.uv.scripts]` table that uv does not recognize.

**Why it happens:** npm-style `tool.*.scripts` is not a uv feature [VERIFIED: Context7 `/astral-sh/uv`].

**How to avoid:** Use `[project.scripts]` mapping to `scripts.docker:build` etc.

**Warning signs:** `uv run docker-build` fails with "command not found".

## Code Examples

### Build-Time Weight Download (D-01)

```python
# Source: app/models/resnet.py (existing) — run in builder after pip install + COPY app/
# Dockerfile RUN line:
ENV TORCH_HOME=/app/.cache/torch
RUN python -c "from app.models.resnet import ResNetClassifier; ResNetClassifier()"
```

### HEALTHCHECK with Readiness Semantics

```dockerfile
# Source: docs.docker.com/reference/dockerfile/#healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3); exit(0 if r.status==200 else 1)"
```

### .dockerignore (D-11)

```dockerignore
# Source: .planning/phases/02-containerization/02-CONTEXT.md D-11
.git
.venv
__pycache__
*.pyc
.planning/
.env
.pytest_cache
.ruff_cache
# tests/ intentionally NOT excluded
```

### .env.example (D-07)

```bash
# Source: app/core/config.py defaults
TORCH_NUM_THREADS=2
MAX_UPLOAD_BYTES=1048576
URL_TIMEOUT=5.0
LOG_LEVEL=INFO
```

### Smoke Test Predict Payload

```bash
# Source: tests/conftest.py sample_jpeg_bytes pattern — generate or reuse minimal JPEG
curl -sf -X POST http://localhost:8000/predict \
  -F "file=@/tmp/smoke-test.jpg;type=image/jpeg" | jq '.predictions | length == 5'
```

### Image Size Assertion

```bash
# Source: CONT-01 acceptance
python -c "
import json, subprocess
size = int(json.loads(subprocess.check_output(
    ['docker','image','inspect','basic-model-serving:local','--format','{{.Size}}'],
    text=True))
assert size < 2_000_000_000, f'Image {size} bytes exceeds 2GB cap'
"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single-stage `pip install` in runtime image | Multi-stage: builder installs, runtime copies | Standard since Docker 17.05 | Smaller, more secure images |
| `pip install torch` from PyPI default | `--index-url https://download.pytorch.org/whl/cpu` | PyTorch split CPU index years ago | Required for <2GB CPU images |
| `@app.on_event("startup")` for model load | FastAPI `lifespan` | FastAPI 0.93+ | Already used in Phase 1 |
| Generic `/health` endpoint | Split `/health/live` + `/health/ready` | K8s probe best practice | Phase 1 done; Phase 2 wires HEALTHCHECK to ready |
| Makefile for docker tasks | `uv run` + `[project.scripts]` | uv 2024–2026 ecosystem | Locked D-09 for this project |

**Deprecated/outdated:**
- STACK.md Dockerfile example: uses `main:app` and `/health` — **do not copy verbatim**; use `app.main:app` and `/health/ready`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Final image size ~600–900MB with CPU torch + baked weights | Summary | Still likely under 2GB even if ~1.2GB; smoke script is the gate |
| A2 | `--start-period=45s` sufficient for ResNet-50 load with baked weights | Pattern 1 | HEALTHCHECK may flap unhealthy; increase to 60s |
| A3 | `pip install` to `/usr/local` in builder copies cleanly to runtime | Pattern 1 | May need `pip install --target` or venv copy pattern if paths differ |
| A4 | `[project.scripts]` hyphenated names (`docker-build`) work with `uv run docker-build` | Pattern 2 | May need underscore names; test during implementation |
| A5 | README Docker section exists or will be created in Phase 2 for D-07 cross-reference | User Constraints | `.env.example` alone still satisfies CONT-03; README link deferred |

## Open Questions (RESOLVED)

1. **Builder artifact copy strategy: site-packages vs pip wheel** — RESOLVED: Use builder `pip install` + `COPY --from=builder /usr/local/lib/python3.12/site-packages` and `/usr/local/bin` into runtime (Plan 02-01). Smoke gate validates the image works; `pip wheel` pattern is acceptable future optimization if site-packages copy fails smoke.

2. **Smoke JPEG source** — RESOLVED: Generate minimal 64×64 RGB JPEG in-memory in `scripts/docker.py` using the same PIL pattern as `tests/conftest.py` `sample_jpeg_bytes`. Write to temp file only for multipart POST if urllib cannot stream bytes directly.

3. **README update scope** — RESOLVED: Add minimal Docker section to README in Plan 02-02 (build, run, config via `.env.example`, `uv run docker-smoke`). Phase 6 expands full reviewer quickstart.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Engine | CONT-01/02, Dockerfile build, smoke | ✓ | 29.6.1 | None — blocking |
| Docker daemon | `docker build/run` | ✓ | Ubuntu 24.04.4 LTS host | None — blocking |
| uv | D-09 `uv run` scripts | ✓ | 0.8.3 | Direct `python -m scripts.docker` (worse DX) |
| Python 3.12 | Builder base image + host scripts | ✓ | 3.12.3 (host) | — |
| curl | Smoke HTTP checks (host-side) | ✓ [ASSUMED] | — | Python `urllib` in smoke script |
| Network (build) | Builder weight download | ✓ [ASSUMED] | — | Build fails without; weights cannot bake |

**Missing dependencies with no fallback:**
- Docker Engine + running daemon

**Missing dependencies with fallback:**
- curl on host → use Python httpx/urllib in smoke script

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Out of scope — no auth in portfolio demo |
| V3 Session Management | no | Stateless API |
| V4 Access Control | no | No multi-tenant access |
| V5 Input Validation | yes (carried from Phase 1) | pydantic + Pillow decode + SSRF checks — unchanged in container |
| V6 Cryptography | no | No crypto operations in containerization phase |

### Known Threat Patterns for Docker + FastAPI ML Serving

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secrets baked into image layers | Information Disclosure | Config via env vars only (CONT-03); `.dockerignore` excludes `.env` (D-11) |
| Running as root in container | Elevation of Privilege | `USER appuser` uid 1000 (CONT-02) |
| CUDA dependency supply-chain bloat | Denial of Service (disk) | CPU index only; size gate in smoke |
| Writable model cache by non-root | Tampering / DoS | Baked weights + read-only cache path with correct ownership |
| SSRF via /predict URL mode | Spoofing | Phase 1 SSRF guards unchanged; container does not alter |

## Sources

### Primary (HIGH confidence)
- Context7 `/docker/docs` — multi-stage Python Dockerfile patterns, layer caching
- Context7 `/astral-sh/uv` — `[project.scripts]` + `uv run` entry points
- Context7 `/astral-sh/uv-docker-example` — non-root user, multi-stage, `.dockerignore` for `.venv`
- Context7 `/websites/pytorch_2_12` — `torch.hub.get_dir()`, TORCH_HOME behavior
- [CITED: pytorch.org/get-started/locally] — CPU install via `--index-url https://download.pytorch.org/whl/cpu`
- [CITED: docs.docker.com/reference/dockerfile/#healthcheck] — HEALTHCHECK options (`--start-period`, etc.)
- `.planning/phases/02-containerization/02-CONTEXT.md` — locked decisions
- `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md` — project-specific patterns and pitfalls
- `app/core/config.py`, `app/main.py`, `app/models/resnet.py`, `requirements.txt` — existing implementation

### Secondary (MEDIUM confidence)
- WebSearch — urllib HEALTHCHECK on slim images (corroborates Context7/Docker docs)
- Local environment probe — Docker 29.6.1, uv 0.8.3, Python 3.12.3 available

### Tertiary (LOW confidence)
- Image size estimate breakdown — pending first `docker build` measurement

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — locked decisions + Phase 1 pins + official PyTorch/Docker docs
- Architecture: HIGH — well-established multi-stage + bake-weights pattern from project research
- Pitfalls: HIGH — PITFALLS.md Pitfalls 3–4 directly map to this phase; mitigations locked in CONTEXT.md

**Research date:** 2026-07-08
**Valid until:** 2026-08-08 (stable Docker/PyTorch patterns; 30-day validity)
