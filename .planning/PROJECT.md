# Basic Model Serving

## What This Is

A portfolio-grade ML model serving system that deploys a pre-trained ResNet-50 image classification model as a REST API. The system is containerized with Docker, deployed to a local Kubernetes cluster (minikube) via werf, monitored with Prometheus and Grafana, and built/tested/pushed automatically via GitHub Actions CI. It demonstrates the full lifecycle of shipping an ML model as a production-style service: inference API, containerization, orchestration, observability, and CI/CD.

## Core Value

A single `POST /predict` request returns accurate top-5 ImageNet predictions in under 100ms, running as a properly containerized, orchestrated, observable service — end to end, not just a notebook demo.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] REST API: `POST /predict` accepts image upload (multipart) or image URL, returns top-5 predictions with confidence scores
- [ ] REST API: response time <100ms for images <1MB; proper error handling for invalid inputs
- [ ] REST API: auto-generated docs at `/docs` (FastAPI)
- [ ] Containerization: multi-stage Dockerfile, image <2GB, runs as non-root user, config via env vars, `/health` endpoint
- [ ] Local dev: docker-compose stack running API + Prometheus + Grafana together for fast inner-loop iteration
- [ ] Kubernetes: Deployment (resource requests/limits), Service, ConfigMap, liveness/readiness probes, zero-downtime rolling updates, running on local minikube
- [ ] Kubernetes deploys via werf (manual `werf converge`, not automated in CI — see Key Decisions)
- [ ] Monitoring: Prometheus scrapes custom app metrics (`request_count`, `request_duration`, `prediction_count`)
- [ ] Monitoring: Grafana dashboard with 5-7 key metrics; alert on service downtime; 7+ day metric retention
- [ ] CI/CD: GitHub Actions runs on every push to `main` — lint, test, build Docker image, push to GHCR; pipeline completes in <10 minutes
- [ ] Performance (should-have): p95 latency <100ms, handles 10+ concurrent requests, model loaded in memory (no cold start), CPU <70% under normal load

### Out of Scope

- Automated CI→K8s deployment — GitHub-hosted runners can't reach a local minikube cluster; deployment stays a manual `werf converge` step (documented in README). Revisit if migrating to cloud K8s or a self-hosted runner.
- Cloud Kubernetes (EKS/GKE/AKS) — local minikube only for this milestone; cloud deployment would introduce cost and infra not needed to demonstrate the skill set
- Model training/fine-tuning — uses a pre-trained torchvision ResNet-50 (ImageNet weights) as-is; training pipeline is a different project
- Multi-model serving / model registry — single fixed model for v1
- Authentication/authorization on the API — out of scope for a local/portfolio demo
- Horizontal autoscaling (HPA) — resource requests/limits and probes are in scope, but autoscaling policy is deferred

## Context

- Solo project intended as a portfolio piece to demonstrate MLOps/ML-serving skills for job applications — favors clarity, documented decisions, and a clean README/demo over maximal production hardening.
- Repo is currently a blank scaffold (LICENSE + stub README only) — this is a greenfield build.
- Target reviewer is likely a hiring manager or interviewer skimming the repo and possibly running it locally, so the local dev experience (docker-compose, README instructions, minikube setup) matters as much as the "real" K8s deployment.
- werf is the chosen deploy tool (build+deploy via Helm-compatible chart definitions); the user explicitly chose it over vanilla `kubectl apply`/Helm.

## Constraints

- **Tech stack**: Python 3.9+, PyTorch, FastAPI, Uvicorn, Docker, Kubernetes (minikube), Prometheus, Grafana, GitHub Actions, werf — fixed per project spec
- **Registry**: GitHub Container Registry (GHCR) — free, integrates natively with GitHub Actions
- **Model**: torchvision pre-trained ResNet-50 (ImageNet weights) — fixed choice, no training involved
- **Deployment environment**: Local Kubernetes only (minikube) — no cloud spend
- **CI/CD reachability**: GitHub Actions (cloud-hosted runners) cannot reach the local minikube cluster, so CI stops at build+push; deploy is a separate manual/local step via werf

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| ResNet-50 over ResNet-18 | Better accuracy/standard ImageNet baseline while still fast enough for <100ms target | — Pending |
| Local minikube over cloud K8s | Zero cost, sufficient to demonstrate orchestration skills for a portfolio piece | — Pending |
| werf for deployment | User's explicit tool choice for build+deploy over Helm-compatible charts | — Pending |
| CI/CD does not auto-deploy to K8s | GitHub-hosted runners can't reach a local minikube cluster; self-hosted runner deemed unnecessary complexity for now | — Pending |
| GHCR as container registry | Free, native GitHub Actions integration, no extra account setup | — Pending |
| docker-compose for local dev | Faster inner loop than minikube while iterating on API + monitoring stack | — Pending |
| Accept both file upload and URL for `/predict` | Matches spec's "image upload or URL"; broadens usability for demoing | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-07-06 after initialization*
