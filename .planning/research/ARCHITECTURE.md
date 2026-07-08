# Architecture Research

**Domain:** ML model-serving portfolio system (FastAPI + PyTorch + Docker + Kubernetes/werf + Prometheus/Grafana + GitHub Actions)
**Researched:** 2026-07-06
**Confidence:** HIGH (FastAPI structure, Docker multi-stage, werf chart layout, GitHub Actions patterns — cross-checked against official docs/repos) / MEDIUM (specific monitoring-stack topology and werf-vs-CI build split — these are opinionated integration decisions for this project's scope, not single verifiable facts)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DEV / CI TIME (build-time)                        │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌────────────┐   ┌───────────────┐   ┌────────────────┐                 │
│  │ FastAPI app │→ │ Dockerfile     │→ │ GitHub Actions  │                 │
│  │ + tests     │   │ (multi-stage)  │   │ lint/test/build │→ GHCR         │
│  └────────────┘   └───────────────┘   │ /push           │                 │
│                                        └────────────────┘                 │
└──────────────────────────────────────────────────────────────────────────┘
                                    │  (manual: werf converge, image tag/ref)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     RUNTIME — minikube cluster (or docker-compose)        │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────┐      ┌─────────────────────────────┐    │
│  │      model-serving ns        │      │        monitoring ns         │   │
│  │  ┌───────────────────────┐  │      │  ┌────────────┐ ┌─────────┐  │   │
│  │  │ Deployment (app pods)  │  │scrape│  │ Prometheus │ │ Grafana │  │   │
│  │  │  FastAPI + ResNet-50   │◄─┼──────┼──┤ Deployment │◄┤Deployment│ │   │
│  │  │  /predict /health /metrics│      │  │ ConfigMap  │ │ConfigMap│  │   │
│  │  └──────────┬────────────┘  │      │  └────────────┘ └────┬────┘  │   │
│  │             │ Service (ClusterIP)   │  Service (ClusterIP)│Service│   │
│  │             │                │      │                     │(NodePort)│ │
│  │  ┌──────────┴────────────┐  │      │                     │        │   │
│  │  │ ConfigMap (app config) │  │      │                     ▼        │   │
│  │  └───────────────────────┘  │      │              browser :3000    │   │
│  └─────────────────────────────┘      └─────────────────────────────┘    │
│                    ▲                                                      │
│                    │ liveness/readiness/startup probes (kubelet)          │
└──────────────────────────────────────────────────────────────────────────┘
                                    ▲
                              werf converge
                    (.helm chart + werf.yaml, run locally)
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| FastAPI app | HTTP layer: routing, request validation, response shaping, OpenAPI docs | `main.py` + `api/routes/*` using `APIRouter`, Pydantic schemas |
| Inference service | Orchestrates image acquisition → preprocessing → model call → response formatting | `services/inference.py`, plain Python, no HTTP knowledge |
| Model wrapper | Owns the PyTorch model lifecycle: load once, hold in memory, run inference | `models/resnet.py`, a class loaded once in FastAPI `lifespan` and stored on `app.state` |
| Metrics exporter | Counts requests, measures latency, exposes `/metrics` in Prometheus text format | `prometheus-fastapi-instrumentator` + custom `Counter`/`Histogram` for `prediction_count` |
| Docker image | Packages app + model weights + runtime deps into a portable, minimal, non-root container | Multi-stage `Dockerfile` (builder installs deps, final stage copies artifacts only) |
| docker-compose | Fast local inner loop: app + Prometheus + Grafana wired together without K8s | `docker-compose.yml` at repo root, bind-mounts for iterative dev |
| K8s manifests (app) | Declares desired runtime state: replicas, resource limits, probes, config, network identity | `Deployment`, `Service`, `ConfigMap` templated as Helm chart under `.helm/templates/` |
| K8s manifests (monitoring) | Runs Prometheus + Grafana inside the same cluster, scraping the app | Separate `Deployment`/`Service`/`ConfigMap` set, same chart or a dedicated one |
| werf | Binds build instructions (Dockerfile) and deploy instructions (Helm chart) into one `werf converge` command | `werf.yaml` (project root) + `.helm/` (Helm-compatible chart, Nelm-rendered) |
| GitHub Actions | Lints, tests, builds, and publishes the image on every push to `main` — stops short of deploying | `.github/workflows/ci.yml`, jobs: `quality-gate` → `build-and-push` |

## Recommended Project Structure

```
.
├── app/
│   ├── main.py                    # FastAPI() instance, lifespan (model load), router includes, instrumentator wiring
│   ├── core/
│   │   ├── config.py               # Pydantic Settings — env-driven config (host, port, log level, max upload size)
│   │   └── logging.py              # structured logging setup
│   ├── api/
│   │   └── routes/
│   │       ├── predict.py          # POST /predict — thin, calls services/inference.py
│   │       └── health.py           # GET /health/live, /health/ready
│   ├── schemas/
│   │   └── prediction.py           # PredictRequest (url variant), PredictionItem, PredictResponse
│   ├── services/
│   │   └── inference.py            # fetch (upload|url) → decode → preprocess → model.predict() → format
│   └── models/
│       └── resnet.py               # ResNetClassifier: loads torchvision resnet50 + weights once, exposes .predict(img)
├── tests/
│   ├── test_predict.py
│   └── test_health.py
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml          # scrape config (compose variant: static target "app:8000")
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/datasource.yml
│       │   └── dashboards/dashboard.yml
│       └── dashboards/model-serving.json
├── .helm/                          # werf's default chart location (repo root, Helm-compatible)
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── _helpers.tpl
│       ├── app-deployment.yaml
│       ├── app-service.yaml
│       ├── app-configmap.yaml
│       ├── prometheus-deployment.yaml
│       ├── prometheus-configmap.yaml     # k8s variant scrape config (Service DNS, not "app:8000")
│       ├── prometheus-service.yaml
│       ├── grafana-deployment.yaml
│       ├── grafana-configmap.yaml
│       └── grafana-service.yaml
├── werf.yaml                       # binds Dockerfile build + .helm deploy instructions
├── Dockerfile                      # multi-stage build
├── docker-compose.yml              # app + prometheus + grafana for local dev
├── requirements.txt / requirements-dev.txt
└── .github/workflows/ci.yml        # lint → test → build → push (GHCR)
```

### Structure Rationale

- **`app/api/` vs `app/services/` vs `app/models/`:** separates HTTP concerns (validation, status codes) from business logic (image pipeline orchestration) from ML concerns (tensor math, weights). This means the model can be swapped (e.g., ResNet-50 → a different architecture) without touching route code, and routes can be tested by mocking the service layer without loading PyTorch at all.
- **`app/core/config.py`:** centralizes env-var-driven configuration so the same image runs unmodified in docker-compose, minikube, and CI — a hard requirement from the project's "config via env vars" constraint.
- **`monitoring/` at repo root, not under `app/`:** Prometheus and Grafana configuration is infrastructure, not application code — keeping it separate makes it obvious these files ship to the monitoring stack, not into the app's Docker image.
- **`.helm/` at repo root:** this is werf's (and Helm's) default chart discovery location; deviating from it means adding an explicit `deploy.helmChartDir` override in `werf.yaml` for no benefit.
- **Two separate Prometheus scrape configs (compose vs. k8s):** in compose, services address each other by container name (`app:8000`); in Kubernetes, they use Service DNS (`model-serving.default.svc.cluster.local:8000`). Trying to share one `prometheus.yml` across both environments adds templating complexity for a single-cluster portfolio project — simpler to keep two small static files than to introduce a templating layer for local Prometheus config.

## Architectural Patterns

### Pattern 1: Load model once via FastAPI lifespan, store on `app.state`

**What:** The model is loaded exactly once when the process starts (inside the `lifespan` async context manager), not per-request and not via a global mutable variable. It's attached to `app.state.model` so route handlers (via `Request.app.state`) and the readiness probe can both check whether it's loaded.
**When to use:** Any model-serving API where model load is expensive (ResNet-50 weight load + `eval()` + moving to device take real time) and must happen before traffic is accepted.
**Trade-offs:** Slightly more ceremony than a bare global, but it makes startup failure explicit (the process won't accept connections if loading throws), supports clean shutdown, and is the FastAPI-endorsed replacement for the deprecated `@app.on_event("startup")` decorator.

**Example:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.models.resnet import ResNetClassifier

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.classifier = ResNetClassifier()  # loads weights, .eval(), warms up
    app.state.ready = True
    yield
    app.state.ready = False
    del app.state.classifier

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Converging upload and URL input to one preprocessing path

**What:** `POST /predict` accepts either a multipart file upload or a JSON body with an image URL. Both are normalized to raw bytes as early as possible, then flow through one shared `decode → preprocess → predict` function so validation and error handling isn't duplicated.
**When to use:** Any endpoint accepting the same logical input (an image) via multiple transport mechanisms.
**Trade-offs:** URL fetch introduces a network call the file-upload path doesn't have (latency, timeout handling, SSRF risk if the URL isn't constrained) — needs an explicit timeout and, ideally, a size cap on the downloaded response before decoding.

**Example:**
```python
async def load_image_bytes(file: UploadFile | None, image_url: str | None) -> bytes:
    if file is not None:
        return await file.read()
    if image_url is not None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            return resp.content
    raise HTTPException(422, "Provide either a file or an image_url")
```

### Pattern 3: Three-tier health endpoints matching Kubernetes probe types

**What:** Expose `/health/live` (process is up — always 200 once the server is running), `/health/ready` (dependencies ready — 503 until the model is loaded), and rely on the same readiness endpoint for the `startupProbe` with a longer grace window. This maps directly onto Kubernetes' three probe types instead of one generic `/health`.
**When to use:** Any service with a non-trivial startup cost (model loading) that must not receive traffic — or be killed by a liveness probe — before it's ready.
**Trade-offs:** Slightly more code than a single `/health`, but prevents two real failure modes: (a) Kubernetes routing traffic to a pod whose model isn't loaded yet, and (b) Kubernetes killing a pod that's still legitimately loading a large model, mistaking slow startup for a hung process.

## Data Flow

### Request Flow (prediction)

```
Client (multipart file OR {"image_url": "..."})
    ↓
FastAPI router (api/routes/predict.py) — Pydantic validates shape
    ↓
services/inference.py: load_image_bytes() → PIL.Image.open() → RGB convert
    ↓ (raises HTTPException 400 on invalid/corrupt image, 422 on missing input, 504 on URL fetch timeout)
torchvision transform pipeline (resize/crop/normalize to 224×224 tensor)
    ↓
models/resnet.py: ResNetClassifier.predict() — torch.inference_mode(), forward pass, softmax
    ↓
top-5 (label, confidence) pairs → schemas/prediction.py PredictResponse
    ↓
JSON response ← FastAPI
```

Concurrently, the Instrumentator middleware observes every request (method, path, status, duration) and increments a custom `prediction_count` counter inside the service layer after a successful inference.

### Metrics Flow

```
FastAPI request lifecycle
    ↓ (middleware, every request)
prometheus_client in-process registry (Counter: http_requests_total, prediction_count;
                                        Histogram: http_request_duration_seconds)
    ↓ (exposed at GET /metrics, text/plain)
Prometheus server (in-cluster Deployment) — scrapes app Service every N seconds (scrape_interval in prometheus.yml)
    ↓ (stored in local TSDB, retained per --storage.tsdb.retention.time)
Grafana (in-cluster Deployment) — Prometheus configured as a provisioned datasource
    ↓ (PromQL queries on dashboard load / refresh)
Dashboard panels (request rate, p95 latency, error rate, prediction throughput, pod uptime)
```

### Build/Deploy Flow

```
Developer writes code
    ↓
docker-compose up (app + prometheus + grafana) — fast inner loop, no K8s needed
    ↓
git push to main
    ↓
GitHub Actions: lint (ruff) → test (pytest) → docker build (multi-stage) → docker push to GHCR (tag: sha + latest)
    ↓ (CI stops here — hosted runners cannot reach local minikube)
Developer, locally: minikube start → werf converge (reads werf.yaml + .helm chart,
                                                     deploys app + monitoring stack,
                                                     image ref/tag passed via values or --set)
    ↓
Pods scheduled → readiness probes pass → Service routes traffic → app reachable via minikube service/tunnel
```

### Key Data Flows

1. **Prediction request:** client → validation → image decode (two possible sources converge to one path) → preprocessing → inference → formatted response. Fully synchronous within one request; no queue or async worker needed at this scale (single model, CPU inference, <100ms target).
2. **Metrics:** app → in-process registry → pull-based scrape by Prometheus → Grafana query-time read. Entirely pull-based; the app never pushes metrics anywhere, which keeps it stateless and simplifies both the compose and K8s topologies.
3. **Config:** environment variables (docker-compose `environment:` / K8s `ConfigMap` mounted as env) → `core/config.py` `Settings` object → consumed by app startup and model loader. The same image is never rebuilt for different environments — only its config injection differs.
4. **Image/deploy artifact:** one Docker image, built once in CI, tagged with the Git SHA, pushed to GHCR, and referenced identically by docker-compose (local, optional) and the werf chart's `values.yaml` (minikube) — "build once, deploy everywhere."

## Build Order & Dependencies

This is the sensible sequencing given what each component depends on:

1. **Model wrapper + FastAPI app (predict, health endpoints), tested locally with `pytest`.** No containers, no cluster — this is the foundation everything else packages or observes. Nothing else can start until `/predict` and `/health/ready` exist and work.
2. **Metrics instrumentation** (`prometheus-fastapi-instrumentator` + custom counters, `/metrics` endpoint). Added directly to the app from step 1 — trivial to bolt on, and every downstream monitoring component (compose Prometheus, K8s Prometheus, Grafana dashboards) depends on `/metrics` existing and emitting real data.
3. **Dockerfile (multi-stage) + `.dockerignore`.** Requires a working app (step 1) and a stable `requirements.txt`. Cannot be meaningfully written/tested before the app runs locally.
4. **docker-compose stack (app + Prometheus + Grafana).** Requires the Docker image (step 3) and a first-pass Prometheus scrape config + Grafana datasource/dashboard provisioning pointing at `/metrics` (step 2). This is the fastest environment to validate the whole monitoring loop before touching Kubernetes.
5. **Kubernetes manifests for the app** (Deployment, Service, ConfigMap, probes) as plain YAML first. Depends on the image existing (step 3, can be loaded into minikube via `minikube image load` before any registry push exists) and on the health endpoints (step 1) to write meaningful probe paths.
6. **Kubernetes manifests for Prometheus + Grafana** (their own Deployment/Service/ConfigMap). Can be built in parallel with step 5 once `/metrics` works (step 2) — only needs the app's Service name to configure the scrape target, so it's a soft dependency on step 5's Service manifest existing (even in draft).
7. **werf.yaml + `.helm/` chart** templating the manifests from steps 5–6 and wiring in the Dockerfile from step 3. This is a wrapping/packaging step — it cannot start meaningfully until the raw manifests it templates have been hand-validated with plain `kubectl apply` at least once, to avoid debugging both templating and K8s correctness simultaneously.
8. **GitHub Actions CI** (lint/test/build/push). Depends only on tests existing (step 1) and the Dockerfile existing (step 3) — it does **not** depend on Kubernetes/werf work at all, so it can be built in parallel with steps 5–7 once steps 1 and 3 are done.
9. **README tying it together** (compose quick-start, minikube + werf converge instructions, architecture diagram). Last, once every piece has been run at least once.

**Parallelizable once their prerequisites are met:** step 2 (metrics) and step 3 (Dockerfile) can overlap; steps 5/6 (app vs. monitoring K8s manifests) can overlap; step 8 (CI) can proceed independently of steps 5–7 (K8s/werf) as soon as steps 1 and 3 exist.

## Scaling Considerations

This is a single-node, single-replica portfolio deployment — "scale" here means "what breaks first if someone hits it harder than expected," not multi-region traffic.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Local demo / single reviewer | Current design as specified: 1 minikube node, low replica count, CPU-only inference — fine as-is |
| 10+ concurrent requests (project's stated should-have) | Ensure Uvicorn/Gunicorn worker count and pod `resources.requests/limits` are tuned so CPU-bound `model.forward()` calls don't serialize behind Python's GIL; `torch.set_num_threads()` tuned to container CPU limit, not host CPU count |
| Beyond a single pod | Add a second replica behind the existing Service (already stateless — no code change needed) once resource requests/limits are dialed in; HPA is explicitly out of scope per project constraints |

### Scaling Priorities

1. **First bottleneck:** CPU-bound PyTorch inference serializing under load on a single pod — mitigate with correct `torch.set_num_threads()` sizing relative to the pod's CPU limit, not by adding replicas first (replicas without correct thread sizing waste resources).
2. **Second bottleneck (out of scope but worth flagging):** Prometheus local storage growth past the 7-day retention target — irrelevant at portfolio scale but the retention flag (`--storage.tsdb.retention.time=7d` or similar) should be set explicitly rather than left at Prometheus's default, since the project requires "7+ day metric retention."

## Anti-Patterns

### Anti-Pattern 1: Loading the model inside the request handler

**What people do:** Call `torch.load(...)` or re-instantiate the classifier inside `/predict` "to keep things simple."
**Why it's wrong:** Every request pays multi-second model-load latency, blowing the <100ms target by orders of magnitude, and concurrent requests can race on loading the same weights into memory multiple times.
**Do this instead:** Load once in `lifespan`, store on `app.state`, reuse across all requests (Pattern 1 above).

### Anti-Pattern 2: Installing the full Prometheus Operator (kube-prometheus-stack) for a one-app, one-cluster portfolio project

**What people do:** `helm install kube-prometheus-stack` because it's the de-facto standard for production Kubernetes monitoring, then fight `ServiceMonitor`/`PodMonitor` CRD label-selector mismatches (a very common failure mode — Prometheus silently not scraping because `release:` labels don't match) inside a local single-node minikube cluster.
**Why it's wrong:** It's built for multi-team, multi-namespace production clusters — the CRDs, Alertmanager, node-exporter, and kube-state-metrics it bundles are overkill for scraping one app's `/metrics` endpoint, and the extra moving parts (Operator reconciliation, CRD installation, label-matching) add debugging surface without adding portfolio signal.
**Do this instead:** Hand-write a plain `Deployment` + `ConfigMap` (static `scrape_configs` targeting the app's Service DNS) + `Service` for Prometheus, and the same for Grafana (`ConfigMap`-provisioned datasource + dashboard JSON). This demonstrates raw manifest fluency — arguably a stronger signal in a portfolio context — and keeps the whole stack small enough to `kubectl apply` and reason about directly. If Grafana alerting is needed for "alert on service downtime," use Grafana's built-in unified alerting against the Prometheus datasource rather than standing up a separate Alertmanager.

### Anti-Pattern 3: Letting werf and CI both try to own the image build

**What people do:** Use `docker/build-push-action` in CI to build+push, then also let `werf converge` rebuild the image again from the same Dockerfile at deploy time (via werf's own BuildKit-based builder), resulting in two different build paths producing two different image digests for "the same" release.
**Why it's wrong:** Confuses which artifact is actually running, and duplicates registry credentials/logic in two places for no benefit — this project's CI already produces a fully tagged, pushed image.
**Do this instead:** Let GitHub Actions own the build+push (plain `docker build`/`docker/build-push-action`, tagged with the Git SHA) exactly as scoped. Let the werf chart's `values.yaml` reference that already-built image by repository + tag, and pass the tag at `werf converge` time (e.g. `--set image.tag=<sha>` or a values override) so `werf converge` is a pure deploy step, not a second build path. This matches the project's explicit constraint that CI stops at build+push and deploy stays manual.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| GitHub Container Registry (GHCR) | `docker/login-action` + `docker/build-push-action` with `secrets.GITHUB_TOKEN`; `werf converge` pulls the same tag at deploy time | Needs `packages: write` permission on the CI job; image visibility (public/private) must be set once in GHCR settings or the local `werf converge`/minikube pull will fail on auth |
| Arbitrary image URLs (for `/predict` URL input) | `httpx.AsyncClient` with an explicit timeout and response-size cap before decoding | Treat as untrusted input — cap download size, set a short timeout, and don't follow unlimited redirects, since this is effectively a server-side-request path |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| FastAPI routes ↔ inference service | Direct in-process function call | Deliberately not split into a separate microservice/network call — no benefit at this scale, adds latency and a new failure mode |
| App pod ↔ Prometheus | Pull over HTTP (`GET /metrics`), same-cluster Service DNS | App has zero awareness of Prometheus — no push client, no dependency; app functions identically with or without a scraper attached |
| Prometheus ↔ Grafana | Grafana queries Prometheus's HTTP API using a provisioned datasource (ConfigMap-mounted `datasource.yml`), same-cluster Service DNS | One-directional at query time; Grafana has no write access to Prometheus |
| docker-compose stack ↔ K8s deployment | Same Docker image, same app code; only the network addressing (container name vs. Service DNS) and config injection mechanism (`environment:` vs. `ConfigMap`) differ | Keeping these divergences confined to config/scrape-target files (not app code) is what makes "build once, deploy everywhere" hold |
| CI ↔ werf/minikube | None (deliberately) | GitHub-hosted runners cannot reach a local minikube API server; the only "integration" is the shared image tag in GHCR that a human references when running `werf converge` locally |

## Sources

- PyImageSearch — FastAPI for MLOps: Python Project Structure and API Best Practices — https://pyimagesearch.com/2026/04/13/fastapi-for-mlops-python-project-structure-and-api-best-practices/ (HIGH — recent, detailed, matches FastAPI official patterns)
- FastAPI official lifespan pattern (cross-checked via multiple secondary sources: llmbestpractices.com, theneuralbase.com) — model loading once at startup via `lifespan`, replacing deprecated `@app.on_event` (HIGH — consistent across sources, matches FastAPI's documented migration away from `on_event`)
- werf official docs — Project configuration overview — https://werf.io/docs/v2/usage/project_configuration/overview.html (HIGH — official docs)
- werf official docs — Charts and dependencies — https://werf.io/docs/v2/usage/deploy/charts.html (HIGH — official docs, confirms `.helm/` default chart location, Nelm-based rendering)
- Helm official docs — Charts — https://helm.sh/docs/topics/charts/ (HIGH — official docs)
- kube-prometheus-stack — Artifacthub package page — https://artifacthub.io/packages/helm/prometheus-community/kube-prometheus-stack (HIGH — official chart docs; used here to justify *avoiding* it for this project's scope, not to recommend adopting it)
- ServiceMonitor label-selector pitfalls — cross-checked across devopsdaily.eu, jorijn.com, Stack Overflow (MEDIUM — consistent community consensus on a well-known operational gotcha, informed the anti-pattern recommendation)
- `trallnag/prometheus-fastapi-instrumentator` — GitHub README — https://github.com/trallnag/prometheus-fastapi-instrumentator (HIGH — official library docs, confirms default metrics: `http_requests_total`, `http_request_duration_seconds`)
- Kubernetes probe patterns for FastAPI (startup/readiness/liveness split for slow-loading models) — cross-checked across codingeasypeasy.com, agentfactory.panaversity.org, learnixo.io (MEDIUM-HIGH — consistent pattern across multiple independent write-ups, aligns with documented Kubernetes probe semantics)
- Docker multi-stage build size optimization for Python/PyTorch — markaicode.com, Docker Hub `pytorchlab/pytorch` — https://markaicode.com/howto/docker-python-ml-image-optimization/ (MEDIUM-HIGH — practical, consistent with Docker's own multi-stage build documentation; specific size numbers are illustrative, not guaranteed)
- CPU-only PyTorch install via `--index-url https://download.pytorch.org/whl/cpu` to avoid pulling CUDA wheels — cross-checked across pushrealm.com and general PyTorch installation docs (HIGH — this is documented, standard PyTorch installation guidance)
- GitHub Actions FastAPI CI/CD pipeline structure (lint → test → build → push to GHCR, `docker/build-push-action`, `GITHUB_TOKEN` for GHCR auth) — cross-checked across masterlablearn.com, blog.greeden.me, dev.to write-up (HIGH — consistent pattern, matches GitHub's own documented GHCR authentication flow)

---
*Architecture research for: ML model-serving portfolio system (FastAPI/PyTorch/Docker/K8s-werf/Prometheus-Grafana/GitHub Actions)*
*Researched: 2026-07-06*
