---
phase: 02-containerization
plan: 01
subsystem: infra
tags: [docker, multi-stage, pytorch-cpu, uv, smoke-test]

requires:
  - phase: 01-core-inference-api
    provides: Working FastAPI app, ResNet-50 model, health probes, requirements pins
provides:
  - Multi-stage Dockerfile with CPU-only torch and baked ResNet-50 weights
  - Non-root runtime (appuser uid 1000) with TORCH_HOME=/app/.cache/torch
  - Host-side uv run docker-build|docker-run|docker-smoke workflow
  - Automated @pytest.mark.docker E2E smoke test scaffold
affects: [03-local-dev-stack, 04-ci-cd, 05-kubernetes]

tech-stack:
  added: [pyproject.toml, hatchling, scripts/docker.py host helpers]
  patterns: [builder-stage weight bake, site-packages copy runtime, urllib HEALTHCHECK on /health/ready]

key-files:
  created:
    - Dockerfile
    - .dockerignore
    - pyproject.toml
    - scripts/docker.py
    - tests/test_docker_smoke.py
  modified: []

key-decisions:
  - "Image tag fixed at basic-model-serving:local for Phase 2 local builds"
  - "Smoke _wait_ready retries on ConnectionResetError during model load startup"

patterns-established:
  - "Two-stage build: CPU torch index RUN, then requirements.txt, then ResNetClassifier() bake"
  - "uv [project.scripts] entry points for docker-build/run/smoke (not Makefile)"

requirements-completed: [CONT-01, CONT-02]

duration: 25min
completed: 2026-07-08
---

# Phase 2 Plan 01 Summary

**Portable ~1.35GB Docker image serves real predictions as non-root with baked CPU torch weights and one-command smoke verification.**

## Performance

- **Duration:** ~25 min (includes first Docker build)
- **Tasks:** 2/2
- **Image size:** 1,353,802,841 bytes (<2GB)

## Accomplishments

- Multi-stage `Dockerfile` on `python:3.12-slim` with dedicated CPU torch install and build-time weight bake
- `.dockerignore` excludes dev artifacts; `appuser` (uid 1000) runs inference without cache permission errors
- `uv run docker-smoke` validates build, size, non-root uid, `/health/ready`, and `POST /predict` with 5 predictions

## Task Commits

1. **Task 1: Smoke scaffold + uv scripts** - `b292daa` (test)
2. **Task 2: Dockerfile + .dockerignore** - `8f375fe` (feat)

## Files Created

- `Dockerfile` — builder/runtime stages, HEALTHCHECK on `/health/ready`, hardcoded uvicorn CMD
- `.dockerignore` — standard exclusions per D-11
- `pyproject.toml` — `[project.scripts]` for docker-build/run/smoke
- `scripts/docker.py` — host E2E orchestration
- `tests/test_docker_smoke.py` — docker-marked integration test

## Verification

- `docker image inspect` size < 2GB ✓
- `docker run id -u` → 1000 ✓
- `uv run docker-smoke` exit 0 ✓
