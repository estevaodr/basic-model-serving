# Walking Skeleton — Basic Model Serving

**Phase:** 1
**Generated:** 2026-07-07

## Capability Proven End-to-End

A developer can install dependencies, start the FastAPI app, confirm `/health/ready` returns 200 after ResNet-50 loads, `POST /predict` with a JPEG upload returns exactly five ImageNet predictions with confidence scores, and `pytest` passes — proving the inference stack works locally without Docker or Kubernetes.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Framework | FastAPI 0.139.0 `[standard]` + Uvicorn | Lifespan hooks, OpenAPI, Pydantic v2 validation; single-worker dev per D-02 |
| Inference runtime | PyTorch 2.12.1 CPU + torchvision 0.27.1 | ResNet-50 ImageNet weights; CPU-only for future <2GB container |
| Model lifecycle | FastAPI `lifespan` → `app.state.classifier` + `app.state.ready` | API-06: load once at startup, no per-request cold start |
| Concurrency | Plain `def` `/predict` handlers (D-01); `torch.set_num_threads()` via `TORCH_NUM_THREADS` env (D-04) | Thread-pool offload keeps event loop free for health/metrics |
| Request contract | Dual content-type on `/predict`: multipart upload + JSON `image_url` (converge to bytes pipeline) | API-01 + API-02 per ARCHITECTURE.md Pattern 2 |
| Metrics | Custom `prometheus_client` with exact names `request_count`, `request_duration`, `prediction_count` | MON-01; instrumentator defaults use wrong names |
| URL safety | Stdlib `ipaddress` + `socket.getaddrinfo` + sync `httpx.Client(follow_redirects=False)` | API-05 SSRF checklist without extra dependency |
| Directory layout | Layered `app/{api,services,models,schemas,core,metrics}/` + `tests/` | ARCHITECTURE.md separation of HTTP, orchestration, ML |
| Deployment target (Phase 1) | Local `uvicorn app.main:app` — no container yet | Walking skeleton proves runnable slice; Phase 2 containerizes |

## Stack Touched in Phase 1

- [x] Project scaffold (Python 3.12, requirements pins, pytest, ruff dev deps)
- [x] Routing — `POST /predict` (upload path in skeleton; URL path in plan 02), `GET /health/live`, `GET /health/ready`
- [x] Model — ResNet-50 loaded once in lifespan, held in process memory (no DB)
- [x] Inference — real CPU forward pass returning top-5 predictions (no stub model)
- [x] Tests — `TestClient` integration tests exercising lifespan + predict + health
- [x] Local run — `uvicorn app.main:app --host 0.0.0.0 --port 8000` documented in plan verification

## Out of Scope (Deferred to Later Slices)

- Docker / multi-stage Dockerfile (Phase 2)
- docker-compose Prometheus + Grafana stack (Phase 3)
- GitHub Actions CI pipeline (Phase 4)
- Kubernetes manifests and `werf converge` (Phase 5)
- Load-test proof of <100ms p95 (Phase 6 — API-03 wired now, validated under load later)
- Authentication / authorization
- IP pinning transport for DNS-rebinding (defense-in-depth optional; stdlib SSRF checks are Phase 1 minimum)

## Subsequent Slice Plan

Each later phase adds capability on top of this skeleton without renegotiating its architectural decisions:

- Phase 2: Package the API into a multi-stage, non-root Docker image <2GB
- Phase 3: `docker-compose up` with Prometheus scraping `/metrics` and Grafana dashboards
- Phase 4: GitHub Actions lint/test/build/push to GHCR
- Phase 5: werf deploy to minikube with probes wired to `/health/live` and `/health/ready`
- Phase 6: Load tests, README polish, SLO alert demo
