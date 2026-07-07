# Project Research Summary

**Project:** Basic Model Serving
**Domain:** ML model-serving REST API (ResNet-50 image classification) — containerized, Kubernetes-deployed via werf, observable with Prometheus/Grafana, CI-built via GitHub Actions. Portfolio/MLOps demonstration project.
**Researched:** 2026-07-06
**Confidence:** HIGH

## Executive Summary

This is a single-model ML serving portfolio project, and every fixed technology choice in the spec (PyTorch, FastAPI, Docker, minikube, werf, Prometheus/Grafana, GitHub Actions) remains the correct, current choice in mid-2026 — nothing needed replacing. The one hard finding that must be resolved before coding starts: the stated "Python 3.9+" constraint is incompatible with the current release of nearly every required dependency (torch 2.12, Pillow 12, prometheus-fastapi-instrumentator 8.0, etc. all require Python >=3.10), so build on **Python 3.12** and treat "3.9+" as a floor, not a target. Beyond that, the architecture is a straightforward layered FastAPI app (routes → inference service → model wrapper) with the model loaded once at startup via `lifespan`, wrapped in a multi-stage Docker build, deployed identically to docker-compose (fast inner loop) and minikube via werf (deploy checkpoint).

The research converges on a clear MVP scope that matches PROJECT.md's Active requirements almost exactly, with two precision fixes: split the single `/health` endpoint into `/health/live` + `/health/ready` (gated on a real "model loaded" flag) to make the required K8s probes actually correct, and treat structured JSON logging as a near-mandatory (not optional) baseline. A short list of cheap, high-leverage differentiators (load-test results in the README, an SLO alert, a confidence-histogram panel, a `/model/info` endpoint) can follow once the P1 scope is stable — none of them are required to look "done," but each buys credibility disproportionate to its cost. Equally important is a long list of well-documented anti-features (multi-model registry, auth, HPA, GitOps auto-deploy, batching, GPU optimization, distributed tracing) that the project has already correctly excluded — the research confirms these exclusions are the right call for this scope, not omissions to second-guess later.

The dominant risk category is not "which library to use" but a cluster of well-documented operational footguns that only surface once real constraints (Kubernetes CPU limits, a non-root user, a public internet-facing URL-fetch feature) are applied: synchronous PyTorch inference blocking the async event loop, PyTorch's thread count ignoring cgroup CPU quotas, the default PyPI torch wheel silently bloating the image 3-4x past the 2GB budget, non-root cache-permission failures on cold start, liveness probes killing pods mid-model-load, and SSRF via the image-URL `/predict` path. Every one of these has a specific, cheap prevention documented in PITFALLS.md and should be built in from the start (not retrofitted) — most map directly onto the API and Docker phases, before Kubernetes work begins. One open tension worth flagging explicitly for planning: STACK.md recommends the full `kube-prometheus-stack` Helm chart for monitoring, while ARCHITECTURE.md's own anti-pattern analysis argues for hand-rolled Prometheus/Grafana manifests instead, given minikube's single-node resource constraints and the operator's ServiceMonitor label-matching footgun (Pitfall 6/Anti-Pattern 2) — this should be decided explicitly during the Kubernetes/Monitoring phase, not left ambiguous.

## Key Findings

### Recommended Stack

Core stack is Python 3.12, PyTorch 2.12.1 (CPU-only wheel via `--index-url https://download.pytorch.org/whl/cpu` — critical to avoid a 5-8GB CUDA-bloated image), torchvision 0.27.1 (must match torch's major.minor exactly), FastAPI 0.139.0 with `fastapi[standard]`, and Pydantic v2 (>=2.9). Supporting libraries: Pillow (image decode), python-multipart (upload parsing), requests/httpx (URL fetch), prometheus-fastapi-instrumentator + prometheus-client (metrics), pydantic-settings (env-var config). Testing via pytest + httpx's `TestClient`; linting via ruff. werf v2.0 (Nelm engine, Helm-compatible) is confirmed still correct for the deploy tooling, with a `.helm/` chart at repo root and `werf.yaml` binding the Dockerfile build to the chart deploy.

**Core technologies:**
- Python 3.12: runtime — every current dependency requires >=3.10; 3.9 is EOL and can't install torch/Pillow at all
- PyTorch 2.12.1 (CPU wheel) + torchvision 0.27.1: inference engine + ImageNet weights/transforms — CPU-only install is the single highest-leverage decision for the <2GB image budget
- FastAPI 0.139.0 (`[standard]` extra) + Uvicorn (`uvloop`): REST API framework — async-native, auto OpenAPI docs, pulls in the recommended server config automatically
- prometheus-fastapi-instrumentator + prometheus-client: auto HTTP metrics + custom `prediction_count`/confidence metrics
- werf v2.0 + Helm-compatible `.helm/` chart: binds Docker build + K8s deploy into one `werf converge` command, run manually/locally against minikube

### Expected Features

**Must have (table stakes):**
- `POST /predict` (upload + URL), top-5 predictions with confidence — not top-1
- Pydantic input validation with structured 4xx JSON errors (not raw 500s)
- Split `/health/live` + `/health/ready` (readiness gated on model-loaded flag) — PROJECT.md's single `/health` is in tension with its own liveness/readiness probe requirement
- Model loaded once at startup via FastAPI `lifespan`, never per-request
- Auto-generated `/docs` with example request/response payloads
- Structured JSON logging with request IDs
- Multi-stage Dockerfile: non-root user, <2GB, env-var config
- docker-compose stack (API + Prometheus + Grafana)
- K8s Deployment/Service/ConfigMap, resource requests/limits, probes, rolling updates, deployed via werf
- Prometheus metrics (request count, duration histogram, prediction count) + Grafana dashboard (5-7 panels, downtime alert, 7+ day retention)
- GitHub Actions CI: lint, test, build, push to GHCR, <10 min
- README: architecture diagram, <5 min quickstart, design rationale, limitations section

**Should have (competitive differentiators, add after P1 is stable):**
- Load-test results (locust/k6/hey) published in README next to the latency claim
- SLO alerting rules layered on the Grafana dashboard (e.g. "page if p95 > 200ms for 5m")
- Prediction-confidence histogram / class-distribution panel ("drift-lite" signal)
- `/model/info` endpoint (model name, framework version, git SHA)
- Zero-downtime rollout demo (screenshot/GIF of `kubectl rollout status`)
- Adversarial-input integration tests in CI

**Defer (v2+ or explicitly out of scope):**
- Minimal demo web page — nice-to-have, defer until API + docs are polished
- Request batching, multi-model registry — genuine anti-features for this CPU-only, single-model, low-concurrency scope
- Auth/authz, HPA, cloud K8s, GitOps auto-deploy, distributed tracing — all already correctly excluded in PROJECT.md; research confirms the exclusion reasoning holds against how the broader ecosystem treats these as flagship features

### Architecture Approach

A layered FastAPI app: HTTP routes stay thin and delegate to an in-process inference service, which owns the decode→preprocess→predict pipeline; the model itself is wrapped in its own class, loaded exactly once in `lifespan` and stored on `app.state`. This separation lets routes be tested without loading PyTorch, and keeps the model swappable without touching route code. The same Docker image runs unmodified across docker-compose (local dev) and minikube (via werf) — only config injection (env vars vs. ConfigMap) and network addressing (container name vs. Service DNS) differ. CI (GitHub Actions) deliberately stops at build+push to GHCR since hosted runners can't reach a local minikube cluster; `werf converge` is a manual, local, deploy-only step that references the already-built image by tag rather than rebuilding it.

**Major components:**
1. FastAPI app (`app/main.py`, `api/routes/`) — HTTP layer: routing, validation, OpenAPI docs
2. Inference service (`services/inference.py`) — orchestrates image acquisition (upload or URL) → decode → preprocess → model call → response formatting, converging both input paths into one shared pipeline
3. Model wrapper (`models/resnet.py`) — owns the PyTorch model lifecycle: load once at startup, hold in memory, run inference in `torch.inference_mode()`
4. Metrics exporter — `prometheus-fastapi-instrumentator` + custom `Counter`/`Histogram` exposed at `/metrics`
5. werf + `.helm/` chart — binds the Dockerfile build and Helm-compatible K8s manifests into one deploy command, run manually against minikube

### Critical Pitfalls

1. **Blocking the event loop with synchronous PyTorch inference** — declaring `/predict` as `async def` and calling the model directly freezes the single-threaded asyncio loop for the whole forward pass, serializing concurrent requests. Fix: use plain `def` (FastAPI auto-offloads to its thread pool) or explicitly `await asyncio.to_thread(...)` around the forward pass.
2. **PyTorch thread count ignoring Kubernetes CPU limits** — `torch.get_num_threads()` defaults to the host's core count, not the pod's cgroup CPU quota, causing CFS throttling and latency spikes once deployed to K8s. Fix: explicitly `torch.set_num_threads(N)` matching the pod's CPU limit at startup.
3. **Docker image bloats to 5-8GB from the default CUDA torch wheel** — `pip install torch` without `--index-url .../cpu` silently pulls full CUDA/cuDNN dependencies. Fix: install from the CPU-only index explicitly, verify `pip show torch` reports a `+cpu` suffix and `docker images` shows <2GB.
4. **Liveness probe kills the pod mid-model-load → CrashLoopBackOff** — a short `initialDelaySeconds` fires before ResNet-50 weights finish loading. Fix: add a `startupProbe` sized to comfortably exceed worst-case model-load time; make `/health/ready` reflect real model-loaded state, not just "process is up."
5. **SSRF via the "predict from image URL" feature** — an unvalidated server-side fetch of a user-supplied URL can probe cloud metadata endpoints or internal services. Fix: scheme allowlist, resolve-then-reject private/loopback/link-local IPs, disable auto-redirect-follow, enforce timeout + size cap.

## Implications for Roadmap

Based on combined research (especially ARCHITECTURE.md's "Build Order & Dependencies" section and PITFALLS.md's phase mapping), suggested phase structure:

### Phase 1: Core Inference API
**Rationale:** Nothing else (Docker, K8s, CI, monitoring) can be meaningfully built or tested until `/predict` and health endpoints exist and work — this is the foundation every later phase packages, observes, or ships.
**Delivers:** FastAPI app with model loaded once via `lifespan`; `POST /predict` accepting upload + URL, top-5 predictions; split `/health/live` + `/health/ready`; Pydantic validation with structured 4xx errors; structured JSON logging; SSRF protection on the URL-fetch path; `/docs` with example payloads. Tested with pytest + `TestClient`.
**Addresses:** All P1 features from FEATURES.md except containerization/K8s/CI/monitoring items.
**Avoids:** Pitfall 1 (event-loop blocking — use `def` not `async def`, or `asyncio.to_thread`), Pitfall 8 (SSRF), the liveness/readiness UX pitfall (health must reflect real model state), and the "generic 500 on bad input" UX pitfall.

### Phase 2: Observability Instrumentation
**Rationale:** Metrics must exist and emit real data before any dashboard (docker-compose or K8s) can be built against them — sequence instrument → scrape → visualize → alert.
**Delivers:** `/metrics` endpoint via `prometheus-fastapi-instrumentator`; custom `prediction_count` counter and confidence histogram; Prometheus histogram buckets tuned around the 100ms SLO boundary (not left at defaults).
**Uses:** prometheus-fastapi-instrumentator, prometheus-client (STACK.md).
**Implements:** Metrics exporter component (ARCHITECTURE.md).

### Phase 3: Containerization
**Rationale:** Requires a working, testable app (Phase 1) and a stable `requirements.txt`; can't be meaningfully validated before the app runs locally.
**Delivers:** Multi-stage Dockerfile (builder installs CPU-only torch wheels, final stage copies artifacts only), non-root user with correct `TORCH_HOME`/cache permissions, env-var config via `pydantic-settings`, port ≥1024, `HEALTHCHECK`.
**Addresses:** Containerization P1 requirements from PROJECT.md.
**Avoids:** Pitfall 3 (CUDA wheel bloat — verify `+cpu` suffix and <2GB image), Pitfall 4 (non-root cache/port permission failures — bake weights in at build time, run the built image through a real predict request as the declared non-root user, not just build it).

### Phase 4: Local Dev Stack (docker-compose)
**Rationale:** Requires the Docker image (Phase 3) and working metrics (Phase 2); this is the fastest environment to validate the whole monitoring loop before touching Kubernetes.
**Delivers:** `docker-compose.yml` (app + Prometheus + Grafana), Prometheus scrape config addressing the app by container name, Grafana datasource + dashboard provisioning-as-code (not manual clicking), 5-7 dashboard panels showing real data.
**Addresses:** docker-compose P1 requirement, Grafana dashboard P1 requirement.

### Phase 5: CI/CD Pipeline
**Rationale:** Depends only on tests existing (Phase 1) and the Dockerfile existing (Phase 3) — does not depend on Kubernetes/werf work at all, so it can run in parallel with Phase 6 once Phases 1 and 3 are done.
**Delivers:** GitHub Actions workflow — lint (ruff) → test (pytest) → build (multi-stage, `docker/build-push-action`) → push to GHCR with `permissions: packages: write`, `cache-from/cache-to: type=gha` for the large torch layer, <10 min budget.
**Addresses:** CI/CD P1 requirement.
**Avoids:** The GHCR `403 Forbidden` integration gotcha (missing `packages: write`), the "<10 min pipeline" performance trap (no layer caching on a cold run).

### Phase 6: Kubernetes Deployment (via werf)
**Rationale:** Requires the image (Phase 3, loadable into minikube even before any registry push) and health endpoints (Phase 1) to write meaningful probes; raw manifests should be hand-validated with plain `kubectl apply` before wrapping them in the werf/Helm chart, to avoid debugging templating and K8s correctness simultaneously.
**Delivers:** Deployment/Service/ConfigMap with resource requests/limits (CPU thread count pinned to match the limit), `startupProbe` + liveness + readiness probes, zero-downtime rolling updates; Prometheus + Grafana running in-cluster (monitoring namespace) scraping the app via Service DNS; `werf.yaml` + `.helm/` chart wrapping the Dockerfile build reference (image built in Phase 5's CI, not rebuilt by werf) and the validated manifests.
**Implements:** K8s manifests (app) and (monitoring) components, werf binding component (ARCHITECTURE.md).
**Avoids:** Pitfall 2 (thread/CPU-limit mismatch), Pitfall 5 (liveness kills mid-load), Pitfall 6 (minikube resource exhaustion — size the node generously up front), Pitfall 7 (werf giterminism confusion — document `--dev` vs. committed-state flow), Anti-Pattern 3 (don't let werf rebuild the image CI already built).

**Open decision to resolve during this phase's planning:** STACK.md recommends the full `kube-prometheus-stack` Helm chart (Operator, CRDs, pre-built dashboards); ARCHITECTURE.md's Anti-Pattern 2 argues for hand-rolled Prometheus/Grafana `Deployment`+`ConfigMap`+`Service` manifests instead, citing minikube resource constraints and the ServiceMonitor label-matching footgun. Both are internally coherent — pick explicitly rather than defaulting to whichever is easier to copy-paste, and size `minikube start --cpus/--memory` accordingly either way (Pitfall 6).

### Phase 7: Polish, Differentiators & README
**Rationale:** Load-test results require a running, stable deployment target; the README ties every prior phase together and should be written last, once each piece has actually been run at least once.
**Delivers:** Load-test results (locust/k6/hey) with p50/p95/p99 published in README; SLO alerting rule(s) on the Grafana dashboard with a demonstrable fire/resolve; `/model/info` endpoint; zero-downtime rollout demo capture; adversarial-input integration tests in CI; final README with architecture diagram, quickstart, design rationale, and a "what I'd improve" limitations section.
**Addresses:** All P2 differentiators from FEATURES.md.

### Phase Ordering Rationale

- API → Metrics → Docker → docker-compose → CI/Kubernetes (parallel) → Polish mirrors ARCHITECTURE.md's explicit "Build Order & Dependencies" section almost exactly; CI/CD (Phase 5) and Kubernetes (Phase 6) have no direct dependency on each other once Phases 1 and 3 are complete, so they can be worked in parallel if desired.
- Grouping metrics instrumentation as its own phase (rather than folding into either API or Docker) reflects FEATURES.md's explicit dependency note: "don't build dashboard panels for metrics that haven't been instrumented" — instrument-scrape-visualize-alert is a strict sequence.
- Pushing docker-compose before Kubernetes matches both ARCHITECTURE.md (fastest environment to validate the full monitoring loop) and PROJECT.md's own stated rationale (faster inner loop than minikube while iterating).
- Every pitfall with a "Phase to address" entry in PITFALLS.md has been mapped into the phase above where its prevention code must actually be written (mostly Phase 1 for API-level fixes, Phase 3 for Docker, Phase 6 for K8s-specific tuning) — several pitfalls (e.g. thread count) span two phases and are called out in both.

### Research Flags

Needs deeper research during planning:
- **Phase 6 (Kubernetes Deployment):** The kube-prometheus-stack vs. hand-rolled-manifests decision is a genuine, unresolved tradeoff between two research documents — worth a focused `/gsd-plan-phase --research-phase 6` pass to pick one and confirm minikube sizing against the choice. Also confirm werf's exact image-tag-passing mechanism (`--set`/values override) against whatever werf version is actually installed.
- **Phase 1 (Core Inference API):** SSRF prevention (IP/scheme validation before URL fetch) has clear guidance (OWASP cheat sheet, HIGH confidence) but no ready-made library was identified in STACK.md — implementation specifics (DNS-rebinding handling, redirect re-validation) may need a short research pass if not already familiar.

Phases with standard, well-documented patterns (skip research-phase):
- **Phase 2 (Observability Instrumentation):** `prometheus-fastapi-instrumentator` usage is a well-documented, single de facto standard library.
- **Phase 3 (Containerization):** Multi-stage Dockerfile + CPU-only torch install is thoroughly documented with an exact, copy-paste-ready pattern in STACK.md.
- **Phase 4 (docker-compose):** Standard compose patterns, no novel integration risk.
- **Phase 5 (CI/CD):** GitHub Actions → GHCR is a fully standard, extensively cross-checked pattern with a ready-to-use workflow file in STACK.md.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified via PyPI/GitHub release metadata for every core and supporting library; version-compatibility table cross-checked against official `pyproject.toml`/`RELEASE.md` sources. Minikube resource sizing is MEDIUM (community consensus, not benchmarked against this specific model). |
| Features | MEDIUM-HIGH | Cross-checked across 3+ independent sources per claim and calibrated against one directly comparable open-source portfolio repo, but Context7/gsd-tools was unavailable for this research pass, so no official vendor docs were consulted directly for the features research. |
| Architecture | HIGH for FastAPI structure, Docker multi-stage, werf chart layout, GitHub Actions patterns (official docs cross-checked); MEDIUM for the specific monitoring-stack topology and werf-vs-CI build split, which are opinionated integration decisions for this project's scope rather than single verifiable facts. |
| Pitfalls | HIGH for probe semantics, Prometheus storage, OWASP SSRF, Pillow security, werf giterminism (official docs); MEDIUM where only community/blog sources were available (e.g. specific thread-count/cgroup interaction numbers, minikube monitoring-stack sizing). |

**Overall confidence:** HIGH

### Gaps to Address

- **kube-prometheus-stack vs. hand-rolled monitoring manifests:** STACK.md and ARCHITECTURE.md give opposing recommendations for the same decision (see Phase 6 above). Resolve explicitly during Kubernetes phase planning rather than defaulting silently to one.
- **Minikube resource sizing (4 CPU/8GB vs. leaner budgets):** MEDIUM confidence, community consensus only — validate with `kubectl top nodes`/`kubectl get events` once the monitoring stack is actually deployed (Pitfall 6), and adjust the documented `minikube start` flags in the README if the chosen monitoring approach (kube-prometheus-stack vs. hand-rolled) changes the footprint significantly.
- **Exact CPU/memory requests/limits for the inference pod:** STACK.md's suggested `500m`/`768Mi` request and `2`/`1.5Gi` limit is explicitly flagged LOW-MEDIUM confidence, a starting point to tune after load testing (Phase 7), not a final answer.
- **SSRF prevention implementation specifics:** guidance is clear (OWASP cheat sheet) but no specific Python library/pattern was pinned down in research beyond `ipaddress` stdlib checks — treat as a Phase 1 implementation detail to get right, with DNS-rebinding documented as an accepted limitation for this portfolio scope.

## Sources

### Primary (HIGH confidence)
- PyPI package pages (torch, torchvision, fastapi, pydantic-settings, python-multipart, pillow, requests, prometheus-fastapi-instrumentator, pytest, ruff) — version numbers, Python version classifiers
- `pytorch/pytorch` and `pytorch/vision` GitHub repos — `RELEASE.md`/`pyproject.toml` compatibility matrices
- werf official docs (`werf.io/docs/v2/...`) — project configuration, charts and dependencies, giterminism, `werf converge` CLI reference
- Kubernetes official docs — Configure Liveness, Readiness and Startup Probes
- Prometheus official docs — Storage, Histograms and summaries
- OWASP — Server Side Request Forgery Prevention Cheat Sheet
- Pillow official docs — Security
- GitHub Docs — Publishing and installing a package with GitHub Actions
- `trallnag/prometheus-fastapi-instrumentator` GitHub README
- python.org devguide + endoflife.ai — Python 3.9 EOL date

### Secondary (MEDIUM confidence)
- minikube official docs (FAQ, commands/start) + multiple 2026 community guides — driver choice and resource sizing recommendations
- `flaviagaia/ml-model-serving-observability` — directly comparable open-source portfolio repo used as a scope calibration point
- Multiple "what hiring managers look for in an ML/MLOps portfolio" articles (theaimarketpulse.com, VeriiPro, InterviewKickstart, InterviewNode, MentorCruise)
- PyImageSearch, community FastAPI-for-MLOps writeups — project structure and lifespan patterns
- ServiceMonitor label-selector pitfalls — cross-checked across devopsdaily.eu, jorijn.com, Stack Overflow
- `vllm-project/vllm` PR #34462 — CFS-aware torch thread count in containers (first-party ML-serving project encountering the same cgroup/thread mismatch)

### Tertiary (LOW confidence)
- Specific minikube CPU/memory sizing numbers (4 CPU/8GB) and inference-pod resource requests/limits — community consensus, not benchmarked against this project's actual ResNet-50 workload; flagged for validation via load testing in Phase 7

---
*Research completed: 2026-07-06*
*Ready for roadmap: yes*
