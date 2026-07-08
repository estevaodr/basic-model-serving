# Requirements: Basic Model Serving

**Defined:** 2026-07-06
**Core Value:** A single `POST /predict` request returns accurate top-5 ImageNet predictions in under 100ms, running as a properly containerized, orchestrated, observable service — end to end, not just a notebook demo.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### API

- [x] **API-01**: User can `POST /predict` with an image file upload and receive top-5 predictions with confidence scores
- [x] **API-02**: User can `POST /predict` with an image URL and receive top-5 predictions with confidence scores
- [x] **API-03**: API responds in <100ms for images <1MB
- [x] **API-04**: API returns structured, typed 4xx JSON errors for invalid input (bad file type, corrupt image, oversized upload, non-image/unreachable URL) instead of raw 500s
- [x] **API-05**: API rejects unsafe image URLs (private/loopback/link-local IPs, non-http(s) schemes, no auto-redirect-follow) to prevent SSRF
- [x] **API-06**: Model is loaded exactly once at startup (via FastAPI `lifespan`) and held in memory — no per-request cold start
- [x] **API-07**: Auto-generated OpenAPI docs available at `/docs`, including example request/response payloads
- [x] **API-08**: API emits structured JSON logs with a request ID per request

### Health

- [x] **HLTH-01**: `GET /health/live` reports process liveness
- [x] **HLTH-02**: `GET /health/ready` reports readiness, returning 503 until the model is fully loaded into memory

### Containerization

- [ ] **CONT-01**: Multi-stage Dockerfile produces an image <2GB (CPU-only PyTorch build, no CUDA)
- [ ] **CONT-02**: Container runs as a non-root user
- [ ] **CONT-03**: Application configuration is provided via environment variables
- [x] **CONT-04**: `docker-compose.yml` runs the API, Prometheus, and Grafana together for local development

### Kubernetes

- [ ] **K8S-01**: Deployment manifest specifies CPU/memory resource requests and limits
- [ ] **K8S-02**: Service exposes the API within the local minikube cluster
- [ ] **K8S-03**: ConfigMap supplies application configuration in-cluster
- [ ] **K8S-04**: Liveness, readiness, and startup probes are configured and correctly reflect real model-load state (no premature kills)
- [ ] **K8S-05**: Rolling updates achieve zero downtime
- [ ] **K8S-06**: Deployment to minikube is performed via `werf converge` (manual/local step, not automated in CI)

### Monitoring

- [x] **MON-01**: Prometheus scrapes application metrics: `request_count`, `request_duration` (histogram), `prediction_count`
- [ ] **MON-02**: Grafana dashboard displays 5-7 key metrics with real data
- [ ] **MON-03**: Alert is configured for service downtime
- [x] **MON-04**: Metrics are retained for 7+ days
- [ ] **MON-05**: Grafana datasource and dashboard are provisioned as code (not manual clicking)

### CI/CD

- [ ] **CI-01**: GitHub Actions pipeline runs on every push to `main`
- [ ] **CI-02**: Pipeline runs automated linting and tests
- [ ] **CI-03**: Pipeline builds the Docker image and pushes it to GHCR
- [ ] **CI-04**: Pipeline completes in <10 minutes

### Performance

- [ ] **PERF-01**: p95 API latency is <100ms
- [ ] **PERF-02**: API handles 10+ concurrent requests
- [ ] **PERF-03**: CPU utilization stays <70% under normal load
- [ ] **PERF-04**: PyTorch thread count is explicitly set to match the pod's CPU limit (avoids cgroup throttling)

### Documentation

- [ ] **DOC-01**: README includes an architecture diagram
- [ ] **DOC-02**: README includes a quickstart that gets the local stack running in <5 minutes
- [ ] **DOC-03**: README documents key design decisions and rationale (including the werf choice and the manual-deploy CI/CD boundary)
- [ ] **DOC-04**: README includes a limitations / "what I'd improve" section
- [ ] **DOC-05**: README publishes load-test results (p50/p95/p99 latency, RPS) validating the <100ms claim
- [ ] **DOC-06**: Grafana dashboard has an SLO alerting rule (e.g. latency or downtime threshold) demonstrated firing/resolving

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Observability Extras

- **OBS-01**: Prediction-confidence histogram / class-distribution panel
- **OBS-02**: `/model/info` endpoint (model name, framework version, git SHA)
- **OBS-03**: Zero-downtime rollout demo capture (screenshot/GIF)
- **OBS-04**: Adversarial-input integration tests in CI

### Demo

- **DEMO-01**: Minimal demo web page (static HTML or Streamlit) for drag-and-drop image upload

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Automated CI → K8s deployment (GitOps, self-hosted runner) | GitHub-hosted runners can't reach local minikube; manual `werf converge` is the deliberate boundary |
| Cloud Kubernetes (EKS/GKE/AKS) | No cloud spend for a portfolio project; minikube demonstrates the same mechanics |
| Model training/fine-tuning pipeline | Project scope is serving, not training; conflates two different skill stories |
| Multi-model serving / model registry | Single fixed model by design; registry infra solves a problem that doesn't exist here |
| Authentication/authorization | No real users/tenants for a local demo; adds security surface with no benefit |
| Horizontal Pod Autoscaler (HPA) | Minikube is single-node; nothing meaningful to scale against |
| Request batching | CPU-only, low-concurrency scope; adds queuing/timeout complexity with no demonstrable payoff |
| A/B testing / canary traffic-splitting | Requires a second model version, which doesn't exist |
| Distributed tracing (Jaeger/Tempo) | Single-container, single-hop service; structured logs already give debuggability |
| GPU inference optimization | Local minikube target is CPU-only by design; GPU code path would be dead code |
| Custom Kubernetes Operator/CRDs | Infrastructure for managing many model deployments; this project has exactly one |
| Rate limiting / API gateway | No real external traffic/abuse vector for a local demo |
| Message-queue-based async inference | ResNet-50 inference is sub-second/synchronous; no corresponding scale requirement |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| API-01 | Phase 1 | Complete |
| API-02 | Phase 1 | Complete |
| API-03 | Phase 1 | Complete |
| API-04 | Phase 1 | Complete |
| API-05 | Phase 1 | Complete |
| API-06 | Phase 1 | Complete |
| API-07 | Phase 1 | Complete |
| API-08 | Phase 1 | Complete |
| HLTH-01 | Phase 1 | Complete |
| HLTH-02 | Phase 1 | Complete |
| CONT-01 | Phase 2 | Pending |
| CONT-02 | Phase 2 | Pending |
| CONT-03 | Phase 2 | Pending |
| CONT-04 | Phase 3 | Complete |
| K8S-01 | Phase 5 | Pending |
| K8S-02 | Phase 5 | Pending |
| K8S-03 | Phase 5 | Pending |
| K8S-04 | Phase 5 | Pending |
| K8S-05 | Phase 5 | Pending |
| K8S-06 | Phase 5 | Pending |
| MON-01 | Phase 1 | Complete |
| MON-02 | Phase 3 | Pending |
| MON-03 | Phase 3 | Pending |
| MON-04 | Phase 3 | Complete |
| MON-05 | Phase 3 | Pending |
| CI-01 | Phase 4 | Pending |
| CI-02 | Phase 4 | Pending |
| CI-03 | Phase 4 | Pending |
| CI-04 | Phase 4 | Pending |
| PERF-01 | Phase 6 | Pending |
| PERF-02 | Phase 6 | Pending |
| PERF-03 | Phase 6 | Pending |
| PERF-04 | Phase 5 | Pending |
| DOC-01 | Phase 6 | Pending |
| DOC-02 | Phase 6 | Pending |
| DOC-03 | Phase 6 | Pending |
| DOC-04 | Phase 6 | Pending |
| DOC-05 | Phase 6 | Pending |
| DOC-06 | Phase 6 | Pending |

**Coverage:**

- v1 requirements: 39 total (corrected from 38 — actual count of listed REQ-IDs)
- Mapped to phases: 39
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-06*
*Last updated: 2026-07-06 after initial definition*
