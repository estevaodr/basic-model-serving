# Phase 1: Core Inference API - Pattern Map

**Mapped:** 2026-07-07
**Files analyzed:** 18
**Analogs found:** 0 / 18 (greenfield — no application code in repo)

## Greenfield Status

This repository contains **no existing application code** to copy from. Verified repo contents:

- `LICENSE`, stub `README.md`, `.gitignore`
- `.planning/` research and phase artifacts
- `.cursor/rules/gsd.mdc`

**All Phase 1 files are net-new.** The planner and executor MUST treat `.planning/research/ARCHITECTURE.md` and `.planning/phases/01-core-inference-api/01-RESEARCH.md` as the authoritative pattern sources. Where they diverge on Prometheus instrumentation, follow **RESEARCH.md** (custom `prometheus_client` with MON-01 exact metric names — not `prometheus-fastapi-instrumentator` defaults).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app/main.py` | provider | request-response | — (greenfield) | none |
| `app/core/config.py` | config | transform | — (greenfield) | none |
| `app/core/logging.py` | utility | event-driven | — (greenfield) | none |
| `app/api/dependencies.py` | hook | request-response | — (greenfield) | none |
| `app/api/routes/predict.py` | route | request-response, file-I/O | — (greenfield) | none |
| `app/api/routes/health.py` | route | request-response | — (greenfield) | none |
| `app/schemas/prediction.py` | model | transform | — (greenfield) | none |
| `app/services/inference.py` | service | transform, batch | — (greenfield) | none |
| `app/services/url_fetch.py` | service | file-I/O | — (greenfield) | none |
| `app/models/resnet.py` | model | transform | — (greenfield) | none |
| `app/metrics/prometheus.py` | middleware | request-response | — (greenfield) | none |
| `tests/conftest.py` | test | — | — (greenfield) | none |
| `tests/test_predict.py` | test | request-response | — (greenfield) | none |
| `tests/test_health.py` | test | request-response | — (greenfield) | none |
| `tests/test_metrics.py` | test | request-response | — (greenfield) | none |
| `requirements.txt` | config | — | — (greenfield) | none |
| `requirements-dev.txt` | config | — | — (greenfield) | none |
| `app/__init__.py` (+ package `__init__.py` files) | config | — | — (greenfield) | none |

## Pattern Assignments

Patterns below are extracted from **ARCHITECTURE.md** and **01-RESEARCH.md**. Line references point to planning docs, not repo source files.

---

### `app/main.py` (provider, request-response)

**Reference:** ARCHITECTURE.md Pattern 1; RESEARCH.md Pattern 1 + build order step 1

**Responsibilities:**
- Instantiate `FastAPI(lifespan=lifespan)`
- Call `torch.set_num_threads(settings.torch_num_threads)` inside lifespan (D-04)
- Set `app.state.ready = False` until model load completes (HLTH-02)
- Attach `app.state.classifier` from `ResNetClassifier()`
- Register routers (`predict`, `health`), metrics route, middleware (request ID, Prometheus)
- No auth (locked from PROJECT.md)

**Lifespan pattern** (RESEARCH.md lines 238–256):

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import torch
from app.core.config import settings
from app.models.resnet import ResNetClassifier

@asynccontextmanager
async def lifespan(app: FastAPI):
    torch.set_num_threads(settings.torch_num_threads)
    app.state.ready = False
    app.state.classifier = ResNetClassifier()
    app.state.ready = True
    yield
    app.state.ready = False
    del app.state.classifier

app = FastAPI(lifespan=lifespan)
```

**Layering rule** (ARCHITECTURE.md lines 115–116): `main.py` wires routers and middleware only — no inference logic in this file.

---

### `app/core/config.py` (config, transform)

**Reference:** ARCHITECTURE.md lines 69, 116–117; RESEARCH.md Standard Stack

**Responsibilities:**
- `pydantic-settings` `BaseSettings` with typed fields
- Required env vars: `TORCH_NUM_THREADS` (default `2`), `MAX_UPLOAD_BYTES`, `URL_TIMEOUT`, optional log level
- Single import point for settings — no scattered `os.environ.get()`

**Pattern:** Use Pydantic v2 `model_config = SettingsConfigDict(env_file=...)` per FastAPI 0.139 / pydantic-settings 2.14.2 stack pins in RESEARCH.md.

---

### `app/core/logging.py` (utility, event-driven)

**Reference:** RESEARCH.md Code Examples — Request ID Middleware (lines 497–512); API-08

**Request ID + JSON logging pattern** (RESEARCH.md lines 499–512):

```python
import uuid, logging, contextvars
from starlette.middleware.base import BaseHTTPMiddleware

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id")

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response
```

**Apply:** Wire middleware in `main.py`; use `logging.Formatter` emitting JSON with `request_id` from contextvar on every log line.

---

### `app/api/dependencies.py` (hook, request-response)

**Reference:** ARCHITECTURE.md Pattern 1 (`app.state.classifier`); RESEARCH.md Architectural Responsibility Map

**Core pattern:**

```python
from fastapi import Request, HTTPException

def get_classifier(request: Request):
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(status_code=503, detail={"status": "not_ready"})
    return request.app.state.classifier
```

**Apply to:** All `/predict` handlers via `Depends(get_classifier)`.

---

### `app/api/routes/predict.py` (route, request-response + file-I/O)

**Reference:** RESEARCH.md Pattern 2 + Pattern 3; ARCHITECTURE.md Pattern 2; PITFALLS.md Pitfall 1

**Critical locked constraint (D-01):** Plain `def` handlers only — never `async def` for `/predict`.

**Dual content-type pattern** (RESEARCH.md lines 270–286):

```python
from fastapi import APIRouter, Depends, File, UploadFile
from app.schemas.prediction import PredictUrlRequest, PredictResponse

router = APIRouter()

@router.post("/predict", response_model=PredictResponse)
def predict_from_upload(file: UploadFile = File(...), classifier=Depends(get_classifier)):
    data = file.file.read()  # sync read — required in plain def
    return run_inference(data, classifier)

@router.post("/predict", response_model=PredictResponse)
def predict_from_url(payload: PredictUrlRequest, classifier=Depends(get_classifier)):
    data = fetch_image_url(payload.image_url)  # sync httpx.Client inside
    return run_inference(data, classifier)
```

**Sync I/O rules** (RESEARCH.md Pattern 3):
- `file.file.read()` not `await file.read()`
- `httpx.Client()` not `AsyncClient`
- Delegate orchestration to `services/inference.py` — routes stay thin (ARCHITECTURE.md lines 51–52, 177–178)

**Fallback if OpenAPI collision (Assumption A1):** Single multipart endpoint with optional `file` and `image_url` Form fields — one required, not both.

---

### `app/api/routes/health.py` (route, request-response)

**Reference:** ARCHITECTURE.md Pattern 3; RESEARCH.md phase requirements HLTH-01/HLTH-02

**Split probe pattern** (ARCHITECTURE.md lines 166–169):

| Endpoint | Status | Body | When |
|----------|--------|------|------|
| `GET /health/live` | 200 | `{"status": "alive"}` | Always once Uvicorn accepts connections |
| `GET /health/ready` | 503 → 200 | `{"status": "not_ready"}` / ready variant | 503 until `app.state.ready` is True |

**Implementation note:** Health routes may use lightweight `async def` or `def` — they must never call the model (RESEARCH.md line 11).

---

### `app/schemas/prediction.py` (model, transform)

**Reference:** RESEARCH.md Code Examples — Response Schema + Structured Error Response (lines 464–495)

**Response schema** (RESEARCH.md lines 470–479):

```python
from pydantic import BaseModel, Field

class PredictionItem(BaseModel):
    label: str = Field(examples=["golden retriever"])
    confidence: float = Field(ge=0, le=1, examples=[0.82])

class PredictResponse(BaseModel):
    predictions: list[PredictionItem]
    model_config = {"json_schema_extra": {"examples": [{"predictions": [
        {"label": "golden retriever", "confidence": 0.82},
        {"label": "Labrador retriever", "confidence": 0.09},
    ]}]}}
```

**Error schema** (RESEARCH.md lines 487–494):

```python
class ErrorDetail(BaseModel):
    error: str
    message: str
    request_id: str | None = None
```

**Also define:** `PredictUrlRequest` with `image_url: HttpUrl` or validated `str` + OpenAPI examples for API-07.

---

### `app/services/inference.py` (service, transform + batch)

**Reference:** ARCHITECTURE.md Data Flow (lines 173–189); RESEARCH.md Architectural Responsibility Map

**Pipeline (single entry point):**

```
bytes → PIL.Image.open() → RGB convert → torchvision transforms → classifier.predict() → PredictResponse
```

**Rules:**
- No HTTP knowledge (status codes raised via exceptions caught in routes, or raise domain errors mapped in routes)
- Catch `PIL.UnidentifiedImageError` → structured 400 (PITFALLS.md Pitfall 8 / RESEARCH.md Pitfall 8)
- Keep Pillow `MAX_IMAGE_PIXELS` default — do not set to `None`
- Increment `prediction_count` metric on successful inference (MON-01)
- Use `@torch.inference_mode()` inside model wrapper, not here

**Convergence pattern** (ARCHITECTURE.md lines 146–150): Both upload and URL paths call one `predict_from_bytes(data: bytes, classifier) -> PredictResponse`.

---

### `app/services/url_fetch.py` (service, file-I/O)

**Reference:** RESEARCH.md Pattern 5; PITFALLS.md Pitfall 8; API-05

**SSRF-safe sync fetch** (RESEARCH.md lines 327–359):

```python
import ipaddress, socket
from urllib.parse import urlparse
import httpx

BLOCKED = lambda ip: (
    ip.is_private or ip.is_loopback or ip.is_link_local
    or ip.is_reserved or ip.is_multicast
)

def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http/https allowed")
    if not parsed.hostname:
        raise ValueError("Missing hostname")
    for family, _, _, _, addr in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)):
        if BLOCKED(ipaddress.ip_address(addr[0])):
            raise ValueError("URL resolves to blocked address")

def fetch_url_bytes(url: str, timeout: float, max_bytes: int) -> bytes:
    validate_url(url)
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            chunks, size = [], 0
            for chunk in resp.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError("Response too large")
                chunks.append(chunk)
    return b"".join(chunks)
```

**Enhancement (optional):** IP pinning transport for DNS-rebinding defense — document if not implemented (RESEARCH.md Assumption A3).

---

### `app/models/resnet.py` (model, transform)

**Reference:** RESEARCH.md Code Examples — ResNet-50 Load and Top-5 Predict (lines 440–461); ARCHITECTURE.md lines 53, 79–80

**Model wrapper pattern** (RESEARCH.md lines 445–461):

```python
import torch
from torchvision.models import resnet50, ResNet50_Weights

class ResNetClassifier:
    def __init__(self):
        self.weights = ResNet50_Weights.IMAGENET1K_V2
        self.model = resnet50(weights=self.weights)
        self.model.eval()
        self.preprocess = self.weights.transforms()
        self.categories = self.weights.meta["categories"]

    @torch.inference_mode()
    def predict(self, image) -> list[tuple[str, float]]:
        batch = self.preprocess(image).unsqueeze(0)
        probs = self.model(batch).squeeze(0).softmax(0)
        top5 = probs.topk(5)
        return [
            (self.categories[idx], float(probs[idx]))
            for idx in top5.indices.tolist()
        ]
```

**Anti-pattern:** Never load weights per request (ARCHITECTURE.md Anti-Pattern 1, lines 266–270).

---

### `app/metrics/prometheus.py` (middleware, request-response)

**Reference:** RESEARCH.md Pattern 4; MON-01 requirement

**Do NOT use** `prometheus-fastapi-instrumentator` default metric names (`http_requests_total`, `http_request_duration_seconds`) — they fail MON-01.

**Custom metrics pattern** (RESEARCH.md lines 308–318):

```python
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUEST_COUNT = Counter("request_count", "Total HTTP requests", ["method", "path", "status"])
REQUEST_DURATION = Histogram(
    "request_duration", "Request duration seconds",
    ["method", "path"],
    buckets=(0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0),
)
PREDICTION_COUNT = Counter("prediction_count", "Successful predictions")
```

**Expose:** `GET /metrics` returning `generate_latest()` with `CONTENT_TYPE_LATEST`. Starlette middleware records count + duration per request; `PREDICTION_COUNT.inc()` in inference service on success.

**Cardinality rule** (RESEARCH.md Security Domain): Never label metrics with raw `image_url` or class names.

---

### `tests/conftest.py` (test)

**Reference:** RESEARCH.md TestClient Smoke Test setup (lines 516–521)

**Fixtures to provide:**
- `TestClient(app)` — triggers lifespan, loads model once per session (slow; acceptable for integration tests)
- `sample_jpeg_bytes` — small valid JPEG for upload tests
- Optional: mock classifier for unit tests that skip torch load

---

### `tests/test_predict.py` (test, request-response)

**Reference:** RESEARCH.md lines 527–531; API-01, API-02, API-04, API-05

**Required test cases:**
- Upload path returns 200 with exactly 5 predictions
- URL path returns 200 with 5 predictions
- Invalid/corrupt image → structured 4xx (not 500)
- SSRF URLs rejected: `http://169.254.169.254/`, `http://localhost/`, private IPs (PITFALLS.md checklist)

**Smoke test pattern** (RESEARCH.md lines 527–531):

```python
def test_predict_upload(sample_jpeg_bytes):
    r = client.post("/predict", files={"file": ("test.jpg", sample_jpeg_bytes, "image/jpeg")})
    assert r.status_code == 200
    assert len(r.json()["predictions"]) == 5
```

---

### `tests/test_health.py` (test, request-response)

**Reference:** RESEARCH.md lines 523–525; HLTH-01, HLTH-02

**Required assertions:**
- `/health/live` → 200 after startup
- `/health/ready` → 200 only when model loaded (503 during lifespan if testable, or assert post-startup 200)

---

### `tests/test_metrics.py` (test, request-response)

**Reference:** MON-01; RESEARCH.md Pitfall 5

**Required assertions:**
- `GET /metrics` returns 200
- Response body contains exact strings: `request_count`, `request_duration`, `prediction_count`
- After successful predict, `prediction_count` increments

---

### `requirements.txt` / `requirements-dev.txt` (config)

**Reference:** RESEARCH.md Installation block (lines 126–135); STACK.md pins

**requirements.txt pattern:**

```bash
# CPU-only torch (pin index-url in pip.conf or comment in file)
torch==2.12.1
torchvision==0.27.1
fastapi[standard]==0.139.0
pillow==12.3.0
python-multipart==0.0.32
httpx==0.28.1
pydantic-settings==2.14.2
prometheus-client==0.25.0
```

**requirements-dev.txt:** `pytest==9.1.1`, `ruff==0.15.20`

**Note:** RESEARCH.md chose `httpx` over `requests` for URL fetch; STACK.md mentions `requests` — follow RESEARCH.md for Phase 1.

---

## Shared Patterns

### Concurrency (D-01 through D-04)

**Source:** 01-CONTEXT.md Decisions; PITFALLS.md Pitfalls 1 & 2

**Apply to:** `predict.py`, `main.py` lifespan, `config.py`

| Decision | Pattern |
|----------|---------|
| D-01 | Plain `def` on `/predict` — FastAPI thread pool offload |
| D-02 | Single Uvicorn worker — one model copy |
| D-03 | No semaphore/503 saturation gate |
| D-04 | `torch.set_num_threads(settings.torch_num_threads)` in lifespan, default `2` |

### Layered Architecture

**Source:** ARCHITECTURE.md lines 64–80, 115–116

```
api/routes/     → HTTP validation, status codes, thin delegation
services/       → orchestration, no HTTP types
models/         → PyTorch lifecycle + forward pass
schemas/        → Pydantic request/response contracts
core/           → config + logging cross-cutting
metrics/        → Prometheus registry + middleware
```

**Rule:** Routes ↔ services communicate via in-process function calls only (ARCHITECTURE.md Internal Boundaries, line 297).

### Error Handling

**Source:** RESEARCH.md Structured Error Response; API-04

**Apply to:** All routes and services

- Pydantic validation → 422 with structured body
- Domain errors (bad image, SSRF, oversize) → 400 with `ErrorDetail` shape
- Never expose stack traces to clients
- Include `request_id` in error JSON when available
- Log full exception server-side only

```python
# Raise pattern from RESEARCH.md lines 492–494:
# HTTPException(status_code=400, detail=ErrorDetail(
#   error="invalid_image", message="Could not decode image", request_id=rid
# ).model_dump())
```

### Validation

**Source:** RESEARCH.md Security Domain V5; Don't Hand-Roll table

| Input | Validation |
|-------|------------|
| Upload | Size cap before read; decode via Pillow, not filename extension |
| URL | SSRF module before any outbound HTTP |
| Response | Pydantic `Field(ge=0, le=1)` on confidence |

### Testing

**Source:** RESEARCH.md Code Examples — TestClient; ARCHITECTURE.md build order step 1

- Use `fastapi.testclient.TestClient` — no live server
- Validate with pytest before any container work
- Test SSRF rejection manually against metadata IP (PITFALLS.md reviewer checklist)

## No Analog Found

All 18 Phase 1 files fall into this category — the codebase has no application modules to mirror.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| All files in classification table | various | various | Greenfield repo — LICENSE + stub README only; patterns sourced from ARCHITECTURE.md and 01-RESEARCH.md |

## Metadata

**Analog search scope:** Entire repository (`app/`, `tests/`, `src/`, root Python files)
**Files scanned:** 55 (including `.git`, `.planning`; zero Python application modules)
**Pattern extraction date:** 2026-07-07
**Primary references:** `.planning/research/ARCHITECTURE.md`, `.planning/phases/01-core-inference-api/01-RESEARCH.md`, `.planning/research/PITFALLS.md`

## PATTERN MAPPING COMPLETE

**Phase:** 1 - Core Inference API
**Files classified:** 18
**Analogs found:** 0 / 18

### Coverage
- Files with exact analog: 0
- Files with role-match analog: 0
- Files with no analog: 18 (all — greenfield)

### Key Patterns Identified
- **Layered FastAPI layout:** `api/` (thin routes) → `services/` (orchestration) → `models/` (PyTorch) with `schemas/` and `core/` cross-cutting
- **Lifespan model load:** `app.state.classifier` + `app.state.ready` flag; `torch.set_num_threads()` at startup
- **Sync `/predict`:** Plain `def` handlers with sync I/O (`file.file.read()`, `httpx.Client`) for thread-pool offload per D-01
- **Dual input convergence:** Upload and URL normalize to bytes → single `predict_from_bytes()` pipeline
- **Custom Prometheus metrics:** Exact names `request_count`, `request_duration`, `prediction_count` — not instrumentator defaults
- **SSRF-safe URL fetch:** Stdlib `ipaddress` + `socket.getaddrinfo` + sync httpx, no redirect-follow
- **Structured errors + request ID:** Pydantic `ErrorDetail`, JSON logging middleware, never raw 500s on bad input

### File Created
`.planning/phases/01-core-inference-api/01-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner should reference ARCHITECTURE.md and 01-RESEARCH.md excerpts above when writing PLAN.md task actions — no existing repo files to copy from.
