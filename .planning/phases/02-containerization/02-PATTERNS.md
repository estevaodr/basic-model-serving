# Phase 2: Containerization - Pattern Map

**Mapped:** 2026-07-08
**Files analyzed:** 8 (new/modified) + 5 (integration references)
**Analogs found:** 6 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `Dockerfile` | config | batch | `requirements.txt` + `app/main.py` + `app/models/resnet.py` | partial (compose 3 files) |
| `.dockerignore` | config | file-I/O | `.gitignore` | role-match |
| `.env.example` | config | transform | `app/core/config.py` | exact |
| `pyproject.toml` | config | — | — (net-new) | none |
| `scripts/docker.py` | utility | batch | `tests/conftest.py` + `tests/test_health.py` + `tests/test_predict.py` | partial |
| `scripts/__init__.py` | config | — | `app/__init__.py` | role-match |
| `README.md` | config | — | `README.md` (stub) | partial |
| `requirements.txt` | config | — | `requirements.txt` (self) | exact (unchanged) |

**Integration references (unchanged, consumed by Dockerfile/smoke):**

| File | Role | Data Flow | Used By |
|------|------|-----------|---------|
| `app/main.py` | provider | request-response | Dockerfile CMD, smoke readiness |
| `app/core/config.py` | config | transform | `.env.example`, `docker run -e` |
| `app/models/resnet.py` | model | transform | Dockerfile builder weight bake |
| `app/api/routes/health.py` | route | request-response | HEALTHCHECK, smoke `/health/ready` |
| `tests/conftest.py` | test | — | smoke JPEG generation pattern |

## Pattern Assignments

### `Dockerfile` (config, batch)

**Analogs:** `requirements.txt` (CPU install), `app/main.py` (Uvicorn entry), `app/models/resnet.py` (weight download trigger)

**Do NOT copy verbatim from** `.planning/research/STACK.md` lines 269–287 — it uses outdated `main:app` and `/health`. Use `app.main:app` and `/health/ready` per Phase 1 implementation.

---

**CPU two-step install pattern** (`requirements.txt` lines 1–11):

```1:11:requirements.txt
# CPU-only torch — two-step install:
# 1. pip install torch==2.12.1 torchvision==0.27.1 --index-url https://download.pytorch.org/whl/cpu
# 2. pip install -r requirements.txt
torch==2.12.1
torchvision==0.27.1
fastapi[standard]==0.139.0
pillow==12.3.0
python-multipart==0.0.32
httpx==0.28.1
pydantic-settings==2.14.2
prometheus-client==0.25.0
```

**Dockerfile translation:** Two separate `RUN` layers — first with `--index-url https://download.pytorch.org/whl/cpu` for torch/torchvision only, then `pip install -r requirements.txt`. Never combine into one step; never use `--extra-index-url`.

---

**Uvicorn entry point** (`app/main.py` lines 1–9, 37–46):

```1:9:app/main.py
"""Basic Model Serving API.

Run as a single Uvicorn worker (one process, one model copy in memory):

    uvicorn app.main:app --host 0.0.0.0 --port 8000

Do not pass ``--workers`` — concurrent requests are handled via FastAPI's
thread pool within a single process.
"""
```

**Dockerfile CMD (D-08 — hardcoded, no env vars):**

```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

**Build-time weight download trigger** (`app/models/resnet.py` lines 5–11):

```5:11:app/models/resnet.py
class ResNetClassifier:
    def __init__(self) -> None:
        self.weights = ResNet50_Weights.IMAGENET1K_V2
        self.model = resnet50(weights=self.weights)
        self.model.eval()
        self.preprocess = self.weights.transforms()
        self.categories = self.weights.meta["categories"]
```

**Builder stage pattern (D-01/D-02):**

```dockerfile
ENV TORCH_HOME=/app/.cache/torch
COPY app/ ./app/
RUN python -c "from app.models.resnet import ResNetClassifier; ResNetClassifier()"
```

---

**Lifespan semantics affecting HEALTHCHECK** (`app/main.py` lines 26–34):

```26:34:app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    torch.set_num_threads(settings.torch_num_threads)
    app.state.ready = False
    app.state.classifier = ResNetClassifier()
    app.state.ready = True
    yield
    app.state.ready = False
    del app.state.classifier
```

Weights are baked at build time but model still loads into memory at startup — `/health/ready` returns 503 until `app.state.ready=True`. HEALTHCHECK needs `--start-period=45s` (tune 30–60s).

---

**Runtime stage non-root pattern** (from `02-RESEARCH.md` Pattern 1, validated against Phase 1 paths):

```dockerfile
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
```

**Order constraint:** `chown` before `USER appuser` (PITFALLS.md Pitfall 4).

---

**HEALTHCHECK pattern** (analog: `app/api/routes/health.py` readiness contract):

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3); exit(0 if r.status==200 else 1)"
```

Use stdlib `urllib` — `python:3.12-slim` has no `curl`. Probe `/health/ready`, not `/health/live`.

---

### `.dockerignore` (config, file-I/O)

**Analog:** `.gitignore`

**Exclusion patterns to mirror** (`.gitignore` lines 1–4, 51, 151–153, 207):

```1:4:.gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[codz]
*$py.class
```

```151:153:.gitignore
.env
.envrc
.venv
```

```51:51:.gitignore
.pytest_cache/
```

```207:207:.gitignore
.ruff_cache/
```

**Phase 2 additions beyond `.gitignore`:**

```dockerignore
.git
.planning/
```

**Intentionally NOT excluded (D-11):** `tests/` — keep in build context.

---

### `.env.example` (config, transform)

**Analog:** `app/core/config.py` — field-for-field mapping

**Source of truth** (`app/core/config.py` lines 1–13):

```1:13:app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    torch_num_threads: int = 2
    max_upload_bytes: int = 1048576
    url_timeout: float = 5.0
    log_level: str = "INFO"


settings = Settings()
```

**`.env.example` pattern (D-06 auto-mapping — uppercase env names):**

```bash
# pydantic-settings maps field names to env vars automatically
TORCH_NUM_THREADS=2
MAX_UPLOAD_BYTES=1048576
URL_TIMEOUT=5.0
LOG_LEVEL=INFO
```

No `Field(validation_alias=...)` needed. Do not add `UVICORN_*` vars (D-08).

---

### `pyproject.toml` (config)

**Analog:** none — net-new file for host-side `uv run` workflow (D-09)

**Pattern from `02-RESEARCH.md` Pattern 2:**

```toml
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

**Constraints:**
- Use `[project.scripts]`, not `[tool.uv.scripts]` (uv has no shell-script table)
- Image tag: `basic-model-serving:local` (D-12)
- Scripts are host-side only — no new pip deps in container

---

### `scripts/docker.py` (utility, batch)

**Analogs:** `tests/conftest.py` (JPEG bytes), `tests/test_health.py` (health assertions), `tests/test_predict.py` (predict assertions)

**Constants (D-12):**

```python
IMAGE = "basic-model-serving:local"
PORT = 8000
MAX_IMAGE_BYTES = 2_000_000_000  # CONT-01
```

---

**JPEG generation pattern** (`tests/conftest.py` lines 16–21):

```16:21:tests/conftest.py
@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    image = Image.new("RGB", (64, 64), color=(128, 64, 32))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()
```

**Smoke reuse:** Extract same PIL pattern into `scripts/docker.py` helper — write temp file for multipart POST or use `httpx`/`urllib` multipart on host. Avoid depending on pytest fixtures.

---

**Health readiness assertion** (`tests/test_health.py` lines 8–12):

```8:12:tests/test_health.py
def test_health_ready_after_startup(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
```

**Smoke translation:** Poll `GET http://localhost:8000/health/ready` until 200 (with timeout), assert `status == "ready"`. Smoke must wait for ready before predict (D-04/D-10).

---

**Predict assertion** (`tests/test_predict.py` lines 139–147):

```139:147:tests/test_predict.py
def test_predict_upload_returns_five_predictions(client, sample_jpeg_bytes):
    response = client.post(
        "/predict",
        files={"file": ("test.jpg", sample_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    payload = response.json()
    predictions = payload["predictions"]
```

**Smoke must verify:** status 200, `len(predictions) == 5`.

---

**Core subprocess pattern** (stdlib only — no new deps):

```python
import subprocess

def build() -> None:
    subprocess.run(["docker", "build", "-t", IMAGE, "."], check=True)

def run() -> None:
    subprocess.run(
        ["docker", "run", "--rm", "-d", "-p", f"{PORT}:{PORT}", "--name", "bms-smoke", IMAGE],
        check=True,
    )

def smoke() -> None:
    build()
    # 1. assert image size < 2GB via docker image inspect
    # 2. run detached container
    # 3. poll /health/ready
    # 4. POST /predict with sample JPEG → 200, 5 predictions
    # 5. docker exec id -u → expect 1000 (non-root, D-04)
    # 6. cleanup container
```

Use `subprocess.check_output` + `json.loads` for image size assertion per `02-RESEARCH.md` Code Examples.

---

### `scripts/__init__.py` (config)

**Analog:** `app/__init__.py` (empty package marker)

Create empty `scripts/__init__.py` so hatchling can package `scripts` for `[project.scripts]` entry points.

---

### `README.md` (config)

**Analog:** `README.md` (stub — line 1 only)

**Current state:**

```1:1:README.md
# basic-model-serving
```

**D-07 requirement:** Add minimal Docker section cross-referencing `.env.example` and `uv run docker-smoke`. Phase 6 expands full quickstart.

---

### `requirements.txt` (config, unchanged)

**Analog:** self — Dockerfile must preserve, not modify

The two-step CPU install comment block is the authoritative install contract. Dockerfile builder replicates it; file itself stays unchanged in Phase 2.

---

## Shared Patterns

### Health Probe Contract

**Source:** `app/api/routes/health.py`
**Apply to:** Dockerfile HEALTHCHECK, `scripts/docker.py` smoke polling

```15:31:app/api/routes/health.py
@router.get("/health/live")
def health_live():
    return {"status": "alive"}


@router.get("/health/ready")
def health_ready(request: Request):
    if not getattr(request.app.state, "ready", False):
        return JSONResponse(
            status_code=503,
            content=ErrorDetail(
                error="not_ready",
                message="Model is not loaded yet",
                request_id=_request_id(),
            ).model_dump(),
        )
    return {"status": "ready"}
```

| Probe | Docker use | Status when model loading |
|-------|-------------|---------------------------|
| `/health/live` | Liveness only (K8s Phase 5) | Always 200 once Uvicorn accepts |
| `/health/ready` | HEALTHCHECK + smoke gate (Phase 2) | 503 until model in memory |

### Environment Configuration (CONT-03)

**Source:** `app/core/config.py`
**Apply to:** `.env.example`, `docker run -e`, future ConfigMap

- Four vars only: `TORCH_NUM_THREADS`, `MAX_UPLOAD_BYTES`, `URL_TIMEOUT`, `LOG_LEVEL`
- pydantic-settings auto-maps snake_case fields → UPPER_SNAKE env names
- `.dockerignore` excludes `.env`; secrets never baked into image
- `torch.set_num_threads(settings.torch_num_threads)` already wired in lifespan (`app/main.py` line 28)

### Non-Root Runtime (CONT-02)

**Apply to:** Dockerfile runtime stage, smoke `docker exec` check

| Step | Pattern |
|------|---------|
| User creation | `useradd --create-home --uid 1000 appuser` |
| Cache path | `ENV TORCH_HOME=/app/.cache/torch` |
| Ownership | `chown -R appuser:appuser /app` before `USER` |
| Verification | `docker exec <cid> id -u` → `1000` |

### CPU-Only Image Size (CONT-01)

**Source:** `requirements.txt` comment + PITFALLS.md Pitfall 3
**Apply to:** Dockerfile builder, smoke size assertion

- Separate `RUN` with `--index-url https://download.pytorch.org/whl/cpu`
- Smoke: `docker image inspect basic-model-serving:local --format '{{.Size}}'` < 2_000_000_000
- Warning sign: `pip show torch` without `+cpu` suffix

### Dev Workflow (D-09/D-10)

**Apply to:** `pyproject.toml` + `scripts/docker.py`

```
uv run docker-build   → docker build -t basic-model-serving:local .
uv run docker-run     → docker run --rm -p 8000:8000 basic-model-serving:local
uv run docker-smoke   → full E2E: build + size + run + ready + predict + non-root
```

No Makefile. Host needs `uv` and `docker` only.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `pyproject.toml` | config | — | Net-new; no existing uv project config in repo. Use `02-RESEARCH.md` Pattern 2. |

## Metadata

**Analog search scope:** Repo root (`Dockerfile`, `.dockerignore`, `pyproject.toml`, `scripts/`), `app/`, `tests/`, `.gitignore`, `.planning/research/STACK.md`, `.planning/phases/02-containerization/02-RESEARCH.md`
**Files scanned:** 62
**Pattern extraction date:** 2026-07-08
**Primary references:** Phase 1 implemented code (`app/`, `tests/`, `requirements.txt`), `02-RESEARCH.md`, `02-CONTEXT.md`
**Outdated reference warning:** STACK.md Dockerfile example uses `main:app` and `/health` — override with Phase 1 paths

## PATTERN MAPPING COMPLETE

**Phase:** 2 - Containerization
**Files classified:** 8 new/modified + 5 integration references
**Analogs found:** 6 / 8

### Coverage
- Files with exact analog: 2 (`requirements.txt`, `.env.example` ← `config.py`)
- Files with partial/compose analog: 4 (`Dockerfile`, `scripts/docker.py`, `README.md`, `scripts/__init__.py`)
- Files with role-match analog: 1 (`.dockerignore` ← `.gitignore`)
- Files with no analog: 1 (`pyproject.toml`)

### Key Patterns Identified
- **CPU torch two-step install:** Separate Dockerfile `RUN` with `--index-url` before `requirements.txt` — mirrors `requirements.txt` header comment
- **Build-time weight bake:** `ResNetClassifier()` in builder with `TORCH_HOME=/app/.cache/torch`; copy cache + `chown` before `USER appuser`
- **Uvicorn entry:** `app.main:app` hardcoded in CMD — matches `app/main.py` docstring; single worker, no `--workers`
- **Readiness probe:** HEALTHCHECK and smoke use `/health/ready` (503 until lifespan completes), not `/health/live`
- **Env-only config:** Four vars from `Settings` → `.env.example`; no new env vars, no Uvicorn env exposure
- **uv run workflow:** `[project.scripts]` → `scripts.docker:build|run|smoke`; smoke reuses test assertion patterns from `tests/`

### File Created
`.planning/phases/02-containerization/02-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner should reference concrete excerpts above when writing PLAN.md task actions — especially Dockerfile layer sequencing and smoke E2E assertions copied from Phase 1 tests.
