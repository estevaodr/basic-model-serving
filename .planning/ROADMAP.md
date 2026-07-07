# Roadmap: Basic Model Serving

## Overview

This project delivers one vertical capability — serving ResNet-50 image classification predictions — built out layer by layer across infrastructure: a working inference API first, then the container it ships in, the local dev stack that makes it observable, the CI pipeline that automates its build, the Kubernetes deployment that runs it for real, and finally the proof (load tests, docs) that it actually meets its own performance claims. Each phase is a hard dependency for the next: you can't containerize an API that doesn't work, can't build dashboards for metrics that don't exist yet, and can't credibly document performance you haven't measured.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Core Inference API** - Working `/predict` + health endpoints + metrics instrumentation, model loaded once in memory
- [ ] **Phase 2: Containerization** - Multi-stage, non-root, <2GB Docker image configured via env vars
- [ ] **Phase 3: Local Dev Stack & Dashboards** - `docker-compose` stack with live Grafana dashboards, provisioned as code
- [ ] **Phase 4: CI/CD Pipeline** - GitHub Actions lint/test/build/push to GHCR on every push to `main`
- [ ] **Phase 5: Kubernetes Deployment (via werf)** - Orchestrated, self-healing, zero-downtime deployment to minikube
- [ ] **Phase 6: Polish, Differentiators & README** - Load-test proof, SLO alert demo, and reviewer-ready documentation

## Phase Details

### Phase 1: Core Inference API
**Goal**: Users get accurate image classification predictions from a fully working, observable API — the foundation every later phase packages, deploys, or visualizes.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08, HLTH-01, HLTH-02, MON-01
**Success Criteria** (what must be TRUE):
  1. User can `POST /predict` with either an image file upload or an image URL and receive top-5 ImageNet predictions with confidence scores
  2. Requests complete in <100ms for images <1MB, served from a model loaded once at startup with no per-request cold start
  3. Invalid input (bad file type, corrupt/oversized image, unsafe or unreachable URL) returns a structured 4xx JSON error, never a raw 500
  4. `/health/live` and `/health/ready` accurately reflect process and model-load state, and `/docs` renders auto-generated OpenAPI docs with example payloads
  5. Every request is logged as structured JSON with a request ID, and `/metrics` exposes `request_count`, `request_duration`, and `prediction_count` ready to be scraped
**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Walking skeleton: scaffold, lifespan model load, health probes, sync upload /predict
- [ ] 01-02-PLAN.md — URL input path, structured 4xx validation, SSRF protection
- [ ] 01-03-PLAN.md — Structured JSON logging, MON-01 Prometheus metrics, OpenAPI docs

### Phase 2: Containerization
**Goal**: The API runs as a portable, secure container image ready for both local dev and Kubernetes.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: CONT-01, CONT-02, CONT-03
**Success Criteria** (what must be TRUE):
  1. `docker build` produces a working image under 2GB using a CPU-only PyTorch wheel
  2. The container runs as a non-root user with no permission errors on startup or during inference
  3. All application configuration is supplied via environment variables, with no code changes needed to reconfigure
**Plans**: TBD

### Phase 3: Local Dev Stack & Dashboards
**Goal**: A single `docker-compose up` gives a fully working inner loop — API plus live metrics dashboards — for fast local iteration.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: CONT-04, MON-02, MON-03, MON-04, MON-05
**Success Criteria** (what must be TRUE):
  1. `docker-compose up` starts the API, Prometheus, and Grafana together and the API is reachable and healthy
  2. Grafana displays a dashboard with 5-7 panels showing real, live metric data from actual `/predict` traffic
  3. The Grafana datasource and dashboard are provisioned automatically from code on startup, with no manual UI clicking required
  4. An alert fires when the service goes down, and Prometheus retains metric history for 7+ days
**Plans**: TBD
**UI hint**: yes

### Phase 4: CI/CD Pipeline
**Goal**: Every push to `main` is automatically linted, tested, built, and published — no manual release steps.
**Mode:** mvp
**Depends on**: Phase 1, Phase 2
**Requirements**: CI-01, CI-02, CI-03, CI-04
**Success Criteria** (what must be TRUE):
  1. Pushing to `main` automatically triggers a GitHub Actions run
  2. The pipeline runs linting and automated tests, failing the build on violations
  3. On success, a Docker image is built and pushed to GHCR with a usable tag
  4. The full pipeline (lint → test → build → push) completes in under 10 minutes
**Plans**: TBD

### Phase 5: Kubernetes Deployment (via werf)
**Goal**: The service runs in local Kubernetes exactly as it would in production — orchestrated, self-healing, configurable, and updatable with zero downtime.
**Mode:** mvp
**Depends on**: Phase 1, Phase 2
**Requirements**: K8S-01, K8S-02, K8S-03, K8S-04, K8S-05, K8S-06, PERF-04
**Success Criteria** (what must be TRUE):
  1. `werf converge` deploys the app to minikube, creating a Deployment (with CPU/memory requests/limits), a Service, and a ConfigMap for configuration
  2. Liveness, readiness, and startup probes correctly reflect real model-load state — pods are never killed mid-load, and traffic only routes once ready
  3. Rolling out a new image version causes zero dropped requests
  4. PyTorch's thread count is explicitly set to match the pod's CPU limit, avoiding cgroup throttling under load
**Plans**: TBD

### Phase 6: Polish, Differentiators & README
**Goal**: The finished project proves its own performance claims and is easy for a reviewer to understand, run, and evaluate in minutes.
**Mode:** mvp
**Depends on**: Phase 3, Phase 4, Phase 5
**Requirements**: PERF-01, PERF-02, PERF-03, DOC-01, DOC-02, DOC-03, DOC-04, DOC-05, DOC-06
**Success Criteria** (what must be TRUE):
  1. A published load test demonstrates p95 latency <100ms under 10+ concurrent requests, with CPU staying under 70%
  2. A reviewer can go from clone to a running local stack in under 5 minutes by following the README quickstart, aided by an architecture diagram
  3. The README documents key design decisions (including werf and the manual-deploy CI/CD boundary) and an honest limitations / "what I'd improve" section
  4. The Grafana dashboard has a working SLO alert that can be demonstrated firing and resolving
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6
(Phase 4 and Phase 5 have no direct dependency on each other once Phases 1-2 are done and may be worked in either order or in parallel.)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Inference API | 0/3 | Not started | - |
| 2. Containerization | 0/TBD | Not started | - |
| 3. Local Dev Stack & Dashboards | 0/TBD | Not started | - |
| 4. CI/CD Pipeline | 0/TBD | Not started | - |
| 5. Kubernetes Deployment (via werf) | 0/TBD | Not started | - |
| 6. Polish, Differentiators & README | 0/TBD | Not started | - |
