# Stack Research

**Domain:** ML model serving (REST API) — containerized, Kubernetes-deployed, observable, CI-built
**Researched:** 2026-07-06
**Confidence:** HIGH (core libraries, verified via PyPI/GitHub release metadata) / MEDIUM (minikube sizing, pod resource sizing — community consensus, not benchmarked for this specific model)

## Executive Take

Every fixed-constraint technology in the project spec (PyTorch, FastAPI, Uvicorn, Docker, minikube, Prometheus, Grafana, GitHub Actions, GHCR, werf) is still the correct, current choice in mid-2026 — nothing here needed replacing. The research below fills in the *exact versions* and the *glue* around those fixed choices: which supporting libraries, which container/CI action versions, and — most importantly — a hard version-compatibility conflict in the stated constraints that must be resolved before coding starts (see "Critical Compatibility Issue" below).

## Critical Compatibility Issue — Resolve Before Coding

**The stated constraint "Python 3.9+" is incompatible with the rest of the current stack.** Python 3.9 reached official end-of-life on 2025-10-31 (no more security patches, confirmed via python.org devguide and multiple sources). More importantly, as of mid-2026 the *current* releases of nearly every library this project needs have already dropped 3.9 support:

| Package | Current version | Minimum Python |
|---|---|---|
| torch | 2.12.1 | >=3.10 |
| torchvision | 0.27.1 | >=3.10 (paired with torch 2.12) |
| Pillow | 12.3.0 | >=3.10 |
| requests | 2.34.2 | >=3.10 |
| pydantic-settings | 2.14.2 | >=3.10 |
| python-multipart | 0.0.32 | >=3.10 |
| prometheus-fastapi-instrumentator | 8.0.2 | >=3.10 |

**Recommendation (HIGH confidence):** Read "3.9+" as a floor, not a target, and build on **Python 3.12**. It's the sweet spot in 2026 — fully supported until Oct 2028, supported by every dependency above, and one step behind bleeding-edge 3.13/3.14 (avoids first-mover wheel-availability issues, e.g. some ML wheels lag on brand-new Python releases). Do not attempt Python 3.9 or 3.10; 3.9 cannot install current torch/Pillow/etc. at all, and 3.10 works but is one EOL cycle closer to end of support (Oct 2026).

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12 | Runtime | Current supported release compatible with every dependency below; see compatibility note above. Pin via `.python-version` / Docker base tag, not a range. |
| PyTorch | 2.12.1 (CPU build) | Model inference engine | Latest stable (released 2026-06-17). Install the **CPU-only wheel** (`--index-url https://download.pytorch.org/whl/cpu`) — this project has no GPU in scope, and the default PyPI wheel silently drags in ~6GB of unused CUDA/cuDNN/Triton dependencies, blowing the "<2GB image" requirement. |
| torchvision | 0.27.1 | Pre-trained ResNet-50 weights + image transforms | Must match torch's major.minor exactly (0.27.x pairs with torch 2.12.x only — mismatches raise import errors or silently give wrong results). Provides `torchvision.models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)` and the modern `transforms.v2` preprocessing API. |
| FastAPI | 0.139.0 | REST API framework | Still the standard for Python ML-serving APIs: async-native, auto-generated OpenAPI docs at `/docs` (a project requirement), Pydantic-based validation. Install as `fastapi[standard]`, which pulls in the recommended Uvicorn extras and CLI automatically. |
| Uvicorn | latest via `uvicorn[standard]` (bundled by `fastapi[standard]`) | ASGI server | FastAPI's own recommended server; the `[standard]` extra adds `uvloop` for a meaningful throughput/latency improvement — relevant given the project's <100ms p95 target. |
| Pydantic | >=2.9 (installed transitively by FastAPI; use latest 2.x) | Request/response validation, settings | FastAPI 0.139 requires Pydantic v2 (>=2.9.0) — Pydantic v1 is not an option with a current FastAPI. v2's Rust-backed validation is also 5–50x faster than v1, which matters for a latency-sensitive endpoint. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | 12.3.0 | Decode uploaded images (JPEG/PNG/WebP) into arrays torchvision can transform | Always — needed to turn raw upload bytes / downloaded URL bytes into a `PIL.Image` before running `transforms.v2`. |
| python-multipart | 0.0.32 | Enables FastAPI's `UploadFile` / multipart form parsing | Required as soon as `/predict` accepts a file upload (per project requirement); FastAPI raises a runtime error at startup if this isn't installed and multipart routes exist. Already listed as a FastAPI optional dependency — pin it explicitly anyway for reproducible builds. |
| requests | 2.34.2 | Fetch an image from a user-supplied URL for the "image URL" input mode | Only needed for the URL-based `/predict` path. Set an explicit timeout and a max-content-length guard (e.g. stream + size check) to avoid the endpoint hanging or being used as a fetch-arbitrary-URL vector. |
| prometheus-fastapi-instrumentator | 8.0.2 | Auto-instruments FastAPI with standard HTTP metrics + exposes `/metrics` | The de facto standard FastAPI+Prometheus integration (1k+ GitHub stars, actively maintained, latest release 2026-06-23). Use it for request_count/request_duration; add custom `prometheus_client` `Counter`/`Histogram` objects alongside it for the domain-specific `prediction_count` metric the project requires. |
| prometheus-client | latest 0.2x (pulled in transitively by the instrumentator, or add directly) | Custom app metrics (`prediction_count`, per-class counters, etc.) | Use directly wherever you need a metric the instrumentator doesn't auto-generate — e.g. `prediction_count` labeled by predicted class or confidence bucket. |
| pydantic-settings | 2.14.2 | Typed env-var configuration (`BaseSettings`) | Matches the project's "config via env vars" containerization requirement; avoids hand-rolled `os.environ.get()` scattered through the app. |
| python-json-logger or stdlib `logging` + `json` formatter | n/a | Structured logs readable by `kubectl logs` / log aggregation | Recommended so logs are parseable; not a hard requirement for this scope, but cheap to add and pairs well with the observability goal. |

### Testing & Dev Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| pytest | 9.1.1 | Test runner | Current stable (2026-06-19). Use `fastapi.testclient.TestClient` (built on Starlette's TestClient) for API tests — no live server needed. |
| httpx | latest 0.2x (installed as FastAPI's own test-client dependency) | HTTP client backing `TestClient` / manual async client tests | FastAPI 0.139 itself still depends on `httpx` (not the newer `httpx2` package some Starlette-adjacent projects are migrating toward as of mid-2026). Stick with plain `httpx` for this project — it's what FastAPI's own dependency chain pins, it works without warnings-as-errors issues, and `httpx2` is a very recent (2026 H1), still-thin-adoption package not worth the churn for a portfolio project. Revisit only if FastAPI itself moves its dependency floor. |
| ruff | 0.15.20 | Lint + format (replaces flake8/black/isort) | Current stable (2026 releases). One tool, one config block, fast enough to run in CI in well under a second — helps hit the "<10 min pipeline" requirement. |
| mypy (optional) | latest 1.x | Static typing | Nice-to-have given Pydantic v2's strong typing story; not required to hit the project's stated scope — treat as a stretch goal, not a blocker. |

## Installation

```bash
# Core (CPU-only torch — critical for the <2GB image requirement)
pip install torch==2.12.1 torchvision==0.27.1 --index-url https://download.pytorch.org/whl/cpu

# Web framework + server
pip install "fastapi[standard]==0.139.0"

# Supporting libraries
pip install pillow==12.3.0 python-multipart==0.0.32 requests==2.34.2 \
            prometheus-fastapi-instrumentator==8.0.2 pydantic-settings==2.14.2

# Dev / test dependencies
pip install pytest==9.1.1 httpx ruff==0.15.20
```

Pin all of the above with `==` in `requirements.txt` (or a `pyproject.toml` + lockfile if you prefer Poetry/uv) — floating ranges like `torch>=2.0` are exactly what causes the torch/torchvision major.minor mismatch failures documented across the PyTorch ecosystem.

## werf Deployment Specifics

werf's current major version is **v2.0** (released 2026, Nelm deployment engine replacing the Helm engine internally — backward compatible with standard Helm charts, so nothing below changes because of it). `werf.yaml` still uses `configVersion: 1`.

### Project layout for a single-service app

```
.
├── werf.yaml              # build + project config
├── Dockerfile             # multi-stage build (see Docker section)
└── .helm/
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
        ├── deployment.yaml
        ├── service.yaml
        ├── configmap.yaml
        └── servicemonitor.yaml   # for Prometheus scraping (see Monitoring section)
```

`werf.yaml` for a single Dockerfile-based image is minimal:

```yaml
project: basic-model-serving
configVersion: 1
---
image: api
dockerfile: Dockerfile
context: .
```

The Helm templates in `.helm/templates/` are standard Kubernetes manifests (Nelm/Helm templating) — werf's role is purely to (1) build the image from the Dockerfile, (2) push it to `--repo`, and (3) render+apply the chart with the built image's tag auto-injected via `.Values.werf.image.api` in templates. This is the same pattern documented for years across werf's official guides, unaffected by the v1.2→v2.0 transition.

### Registry auth — two different contexts, two different credentials

This is the detail most likely to trip up a first-time werf user with this project's specific CI/CD split (build+push in CI, deploy manually from a laptop):

- **In GitHub Actions** (build/push only, no `werf converge` per the project's Out-of-Scope decision): you don't actually need `werf` in CI at all for this project, since CI never runs `werf build`/`werf converge` — plain `docker/build-push-action` authenticated with the ambient `GITHUB_TOKEN` (see CI/CD section) is sufficient and simpler.
- **Locally, running `werf converge` against minikube**: werf needs its own registry login, run once per machine/session:
  ```bash
  werf cr login ghcr.io -u <your-github-username> -p <personal-access-token-with-write:packages>
  ```
  This must be a GitHub **personal access token** (classic or fine-grained, `write:packages`/`read:packages` scope) — `GITHUB_TOKEN` only exists inside an Actions runner and isn't available to you locally. Then converge with:
  ```bash
  werf converge --repo ghcr.io/<github-username>/<repo-name> --env local --dev
  ```
  The `--dev` flag is important for local iteration: werf enforces "giterminism" (config must come from committed Git state) by default, and `--dev` relaxes that so you can `werf converge` against uncommitted local changes while iterating.

### If you later automate deploy from CI (documented as out-of-scope now)

Should this change, the pattern is: `werf/actions/install@v2` to install the CLI, then `. $(werf ci-env github --as-file)` before `werf converge`, which auto-configures GHCR auth from the ambient `GITHUB_TOKEN` when using GitHub's own registry — no explicit `werf cr login` needed in that specific case. This only works from an Actions runner reaching the cluster, which is exactly the constraint the project has already correctly ruled out for a local-only minikube cluster.

## Kubernetes / minikube Setup

### Driver and sizing

Use the **docker driver** (`minikube start --driver=docker`) — it's the Linux default, doesn't require nested virtualization (KVM2/VirtualBox), and integrates cleanly with `eval $(minikube docker-env)` if you ever want to load locally-built images without pushing to GHCR first.

Recommended sizing for this workload (API pod + kube-prometheus-stack + Grafana, all on one node):

```bash
minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=20g
```

Rationale (MEDIUM confidence — community consensus across several 2026 minikube guides, not a benchmark specific to ResNet-50): 2 CPU/2GB is minikube's bare default and is too tight once kube-prometheus-stack's Prometheus+Grafana+Alertmanager pods are added alongside the inference pod. 4 CPU/8GB leaves comfortable headroom; if the laptop has 16GB+ RAM, this is a safe default that avoids OOM-killed pods without starving the host OS.

### Resource requests/limits for the inference pod (starting point, LOW-MEDIUM confidence — tune after load testing)

ResNet-50 forward passes on CPU are single-threaded-friendly but benefit from 1-2 cores; the model itself is ~100MB of weights plus PyTorch's own baseline memory footprint (interpreter + torch libs, easily 300-500MB before any request arrives):

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "768Mi"
  limits:
    cpu: "2"
    memory: "1.5Gi"
```

Set `torch.set_num_threads()` explicitly at startup to match the container's CPU limit — PyTorch defaults to detecting the *host's* core count, which on a shared minikube node can cause oversubscription and unpredictable latency.

### Exposing Prometheus/Grafana alongside the app: use kube-prometheus-stack, don't hand-roll manifests

**Recommendation (HIGH confidence):** install the community **kube-prometheus-stack** Helm chart directly via `helm install` (not werf-managed) into its own `monitoring` namespace, as a one-time local setup step documented in the README — separate from the app's own werf-managed release:

```bash
kubectl create namespace monitoring
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus-stack prometheus-community/kube-prometheus-stack \
  -n monitoring \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
```

Why not hand-roll Prometheus/Grafana manifests: kube-prometheus-stack bundles the Prometheus Operator, pre-built Grafana dashboards, Alertmanager, and the CRDs (`ServiceMonitor`, `PrometheusRule`) that make scraping declarative — hand-writing a Prometheus `scrape_configs` block and a Grafana deployment from scratch is significantly more YAML for zero benefit in a project whose goal is demonstrating standard MLOps practice, not reinventing observability tooling. This chart is the de facto standard used across virtually every "FastAPI + Kubernetes + Prometheus" reference project found during research.

Then, in the app's own Helm chart (deployed via `werf converge`), add a `ServiceMonitor` that the already-running Prometheus Operator auto-discovers:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: basic-model-serving
  labels:
    release: prometheus-stack   # must match the operator's serviceMonitorSelector
spec:
  selector:
    matchLabels:
      app: basic-model-serving
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

The `release: prometheus-stack` label is the detail every one of the reference implementations found during research calls out explicitly — omit it and Prometheus silently never discovers your ServiceMonitor, which is a confusing "no error, just no data" failure mode.

Access both UIs the same way in a local minikube setup, no Ingress needed for a portfolio demo:

```bash
kubectl port-forward -n monitoring svc/prometheus-stack-grafana 3000:80    # http://localhost:3000, admin/prom-operator by default
kubectl port-forward -n monitoring prometheus-stack-kube-prom-prometheus-0 9090
```

## CI/CD (GitHub Actions)

Given the project's own decision to keep deploy manual, the CI pipeline is deliberately simple: checkout → lint/test → build → push to GHCR. No werf, no cluster access, from CI.

```yaml
name: CI
on:
  push:
    branches: [main]

permissions:
  contents: read
  packages: write        # required to push to ghcr.io

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check .
      - run: pytest

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: docker/setup-buildx-action@v4
      - uses: docker/login-action@v4
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v6
        id: meta
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha,prefix=
            type=raw,value=latest,enable={{is_default_branch}}
      - uses: docker/build-push-action@v7
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

Notes:
- `permissions: packages: write` at the job/workflow level is required — its omission is the single most common GHCR-push failure reported across current guides; `GITHUB_TOKEN` exists automatically but has read-only package scope unless this is set.
- `docker/metadata-action` for tagging (short SHA + `latest` on main) is the standard pattern rather than hand-rolling tag strings — it also keeps tag logic out of shell scripting.
- `cache-from/cache-to: type=gha` uses GitHub's own Actions cache for Docker layer caching, which meaningfully helps hit the "<10 minute pipeline" requirement given how large the PyTorch layer is.
- Actions versions above (`checkout@v7`, `setup-python@v6`, the `docker/*@v4`/`@v6`/`@v7` actions) are each the current major release as of research date (2026-07). `actions/checkout@v4`/`setup-python@v5` still work fine if preferred for stability — no functional requirement forces the newest majors, this is just "what's current."

## Docker / Multi-Stage Build

The single highest-leverage decision for hitting the "<2GB image" requirement is the CPU-only torch wheel — the default PyPI torch wheel installs the CUDA build, which alone is documented to add several GB (community reports of 6-8x image size increase from this exact mistake). Multi-stage build to keep build tooling out of the final image:

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels \
    --index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home --uid 1000 appuser
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY . .
USER appuser
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Notes:
- `--index-url` (not `--extra-index-url`) for the wheel-building stage ensures pip resolves *everything* torch-related (torch, torchvision) from the CPU index consistently; mixing index behavior is the most common cause of accidentally pulling a CUDA build anyway.
- `python:3.12-slim` (Debian-based) over `python:3.12-alpine`: PyTorch does not publish musl-libc wheels, so Alpine forces a from-source PyTorch build — extremely slow and fragile. This is a well-documented Alpine+PyTorch pitfall; slim (glibc-based) avoids it entirely.
- Non-root user (`appuser`, uid 1000) satisfies the project's own "runs as non-root" requirement directly.
- `/health` endpoint should be a plain liveness check with no model inference in the request path (just confirms the process + loaded model object are alive) — used by both Docker `HEALTHCHECK` and the Kubernetes liveness/readiness probes.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Model serving format | Plain PyTorch `nn.Module.eval()` inference in FastAPI | TorchServe / NVIDIA Triton / ONNX Runtime | Those add real value at scale (multi-model, dynamic batching, GPU sharing) but are pure overhead for a single fixed CPU model behind one `/predict` route — they'd obscure the "hand-built FastAPI serving layer" skill this portfolio project is meant to demonstrate. |
| Prometheus/Grafana deployment | kube-prometheus-stack Helm chart | Hand-rolled Prometheus/Grafana Deployment + ConfigMap manifests | Valid if the goal were to demonstrate raw manifest-writing skill, but it's much more YAML for the same outcome and loses the Operator's ServiceMonitor-based service discovery, which is itself a skill worth demonstrating (it's what real Prometheus deployments use). |
| Deploy tool | werf (already fixed by project spec) | Plain `helm install`/`kubectl apply`, or ArgoCD/Flux GitOps | werf was an explicit user choice; note for context: werf adds build+push orchestration on top of Helm/Nelm templating that plain Helm doesn't have, which is a reasonable value-add to highlight, not just "Helm with extra steps." GitOps tools (ArgoCD/Flux) assume a cluster that's reachable from a Git-watching controller — overkill/inapplicable for a local-only minikube cluster with a manual deploy step. |
| Local dev inner loop | docker-compose (already decided per project) | Skaffold / Tilt against minikube directly | Both are reasonable "fast inner loop on K8s" tools, but the project already chose docker-compose specifically to avoid the K8s reconcile-loop overhead while iterating — correct call for a solo portfolio project where the K8s deploy is a periodic checkpoint, not the primary dev loop. |
| Test HTTP client | `httpx` (matches FastAPI's own pin) | `httpx2` | `httpx2` is a genuine, real package (`pydantic/httpx2` on GitHub) that Starlette's `TestClient` is beginning to prefer as of mid-2026, but it's extremely new, not yet FastAPI's own declared dependency, and adopting bleeding-edge package renames early adds churn risk for no functional benefit here. Revisit if/when FastAPI itself moves to depend on it. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Default (non-CPU-indexed) `pip install torch` | Pulls the CUDA build and its bundled cuDNN/Triton/NCCL dependencies — routinely balloons image size by 5-6GB+ for a project with no GPU in scope, blowing the "<2GB image" requirement immediately. | `pip install torch --index-url https://download.pytorch.org/whl/cpu` |
| `python:3.x-alpine` as the base image for anything importing torch | PyTorch does not ship musl/Alpine wheels; pip falls back to compiling PyTorch from source, which can take 30-60+ minutes and frequently fails on missing build toolchain pieces. | `python:3.12-slim` (Debian glibc-based) |
| Python 3.9 (or 3.10) as the actual target despite the "3.9+" constraint | 3.9 is past EOL (Oct 2025) and can't even install current torch/Pillow/etc.; 3.10 works but is one cycle closer to its own Oct 2026 EOL. | Python 3.12 (see Critical Compatibility Issue above) |
| Hand-writing raw Prometheus scrape configs + a bare Grafana Deployment from scratch | Much more YAML, no Operator-based auto-discovery, reinvents a solved problem for zero portfolio benefit. | kube-prometheus-stack Helm chart + a `ServiceMonitor` |
| Running `werf converge` from a GitHub Actions runner in this project | The runner cannot reach a local minikube cluster — this is already correctly called out as Out of Scope in the project's own PROJECT.md; don't accidentally reintroduce it while wiring up CI. | Manual local `werf converge`, CI stops at build+push |
| Mixing arbitrary torch/torchvision version pins (e.g. latest torch with an older torchvision, or vice versa) | The two packages are released in lockstep by major.minor (torch 2.12 ↔ torchvision 0.27); mismatches cause import-time errors or, worse, silently wrong numerical output from transforms. | Always pin both together from the compatibility table (torch 2.12.1 + torchvision 0.27.1) |
| `httpx2` as a required dependency right now | Extremely recent (2026 H1) rename/successor package; FastAPI itself hasn't moved its own dependency floor to it yet. | Plain `httpx` (already a transitive FastAPI dependency) |

## Stack Patterns by Variant

**If you want to load-test the <100ms / 10+ concurrent requests requirement before deploying to K8s:**
- Use `locust` or a simple `hey`/`wrk` run against the docker-compose stack first.
- Because: catching CPU-thread-oversubscription issues (see `torch.set_num_threads`) locally is far faster to iterate on than round-tripping through `werf converge` each time.

**If image build time becomes painful in CI (torch wheel is large):**
- Add `cache-from`/`cache-to: type=gha` (already in the recommended workflow above) and consider splitting the wheel-building stage's `pip wheel` step from the final `pip install` step across cache-friendly layers.
- Because: torch's CPU wheel is still ~200-300MB to download; without layer caching, every CI run re-downloads it, eating into the <10 minute pipeline budget.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| torch==2.12.1 | torchvision==0.27.1 | Must match major.minor in lockstep; verify with `torch.__version__`/`torchvision.__version__` after install, not just visually check requirements.txt. |
| fastapi==0.139.0 | pydantic>=2.9.0,<3 | FastAPI's own PyPI metadata enforces this floor; do not attempt Pydantic v1. |
| fastapi[standard] | uvicorn[standard]>=0.12.0, python-multipart>=0.0.18, pydantic-settings>=2.0.0 | All pulled in automatically by the `[standard]` extra — the explicit pins in this doc are for reproducibility, not because FastAPI needs help finding them. |
| prometheus-fastapi-instrumentator==8.0.2 | Python >=3.10 | Confirms the Python 3.12 recommendation above; this library alone rules out Python 3.9. |
| werf v2.x | Existing Helm charts/templates | Nelm (v2's deployment engine) is backward-compatible with standard Helm chart syntax — no chart rewrite needed vs. what you'd write for werf v1.2 or plain Helm. |
| kube-prometheus-stack ServiceMonitor | Prometheus Operator's `serviceMonitorSelector` | Only discovered if the ServiceMonitor carries the `release: <helm-release-name>` label matching the installed chart's release name — a labeling mismatch is a silent failure (no scrape, no error). |

## Sources

- PyPI package pages for torch, torchvision, fastapi, pydantic-settings, python-multipart, pillow, requests, prometheus-fastapi-instrumentator, pytest, ruff — version numbers and `Python:` classifier requirements (HIGH confidence, checked 2026-07-06/07)
- `pytorch/vision` GitHub releases + torchvision PyPI compatibility table — torch/torchvision major.minor pairing (HIGH confidence)
- `pytorch/pytorch` `RELEASE.md` compatibility matrix and `pyproject.toml` — confirms `requires-python = ">=3.10"` for torch 2.10-2.12 (HIGH confidence)
- FastAPI GitHub repo + PyPI dependency metadata — Pydantic v2 floor, `fastapi[standard]` extras (HIGH confidence)
- werf official docs (`werf.io/docs/v2/...`) + werf blog "werf 2.0 is out with Nelm" + `werf/werf` GitHub discussion #6100 — current major version, Nelm backward compatibility, `configVersion: 1` (HIGH confidence)
- werf official CI/CD guide (`werf.io/guides/.../040_github_actions.html`) + `werf/actions` GitHub repo — GHCR auth via `werf ci-env github`, local `werf cr login` pattern (HIGH confidence for the documented CI pattern; MEDIUM-HIGH for the local-vs-CI auth distinction, which is synthesized from official docs rather than a single page stating this exact project's split)
- Multiple community reference repos (`dudeperf3ct/9-fastapi-kubernetes-monitoring`, `rishirk408/k8s-observability-lab`, `jeremyjordan/ml-monitoring`) — converging on the same kube-prometheus-stack + ServiceMonitor pattern independently (HIGH confidence via cross-referencing)
- minikube official docs (`minikube.sigs.k8s.io/docs/faq`, `/commands/start`) + community 2026 guides (thelinuxcode.com, markaicode.com) — driver choice and resource sizing (MEDIUM confidence — official docs give defaults/minimums, specific 4CPU/8GB recommendation is community consensus, not benchmarked against this project's actual workload)
- python.org devguide (`devguide.python.org/versions`) + endoflife.ai — Python 3.9 EOL date (HIGH confidence)
- Stack Overflow + `pytorch/pytorch` GitHub issue #146786 + community blog post — CPU-only wheel install pattern and image-size impact (HIGH confidence, corroborated across independent sources)
- GitHub Actions marketplace / release pages for `actions/checkout`, `actions/setup-python`, `docker/setup-buildx-action`, `docker/login-action`, `docker/metadata-action`, `docker/build-push-action` — current major versions as of 2026-07 (HIGH confidence)

---
*Stack research for: ML model serving (ResNet-50 REST API, Docker, minikube, werf, Prometheus/Grafana, GitHub Actions CI)*
*Researched: 2026-07-06*
