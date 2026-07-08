# Phase 2: Containerization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-08
**Phase:** 2-Containerization
**Areas discussed:** Model weights strategy, Configurable env vars, Local container workflow

---

## Model Weights Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Bake at build time | Download weights during docker build (root in builder), copy to runtime, chown to appuser | ✓ |
| Download at startup | Smaller layers but TORCH_HOME + network + permission risk | |
| You decide | Planner picks based on PITFALLS.md | |

**User's choice:** Bake at build time

| Option | Description | Selected |
|--------|-------------|----------|
| Full predict smoke test | Run predict as non-root inside built container | ✓ |
| Load-only smoke test | Import + model load only | |
| No automated smoke | Trust build success | |

**User's choice:** Full predict smoke test as non-root user

| Option | Description | Selected |
|--------|-------------|----------|
| /app/.cache/torch | ENV TORCH_HOME, mkdir + chown before USER switch | ✓ |
| ~/.cache/torch | Under appuser home | |
| You decide | Planner picks | |

**User's choice:** /app/.cache/torch

| Option | Description | Selected |
|--------|-------------|----------|
| Accept larger image | ~100–200MB for baked weights, still <2GB | ✓ |
| Minimize size | Prefer runtime download | |
| Bake + optimize elsewhere | Bake weights, strip other bloat | |

**User's choice:** Accept larger image for reliability

---

## Configurable Env Vars

| Option | Description | Selected |
|--------|-------------|----------|
| Keep current 4 settings | TORCH_NUM_THREADS, MAX_UPLOAD_BYTES, URL_TIMEOUT, LOG_LEVEL | ✓ |
| Add host/port/env vars | Expand surface | |
| You decide — minimal | Planner adds only if required | |

**User's choice:** Keep current 4 settings only

| Option | Description | Selected |
|--------|-------------|----------|
| pydantic-settings convention | Auto-mapping field names to env vars | ✓ |
| Explicit Field aliases | Self-documenting but verbose | |
| You decide | | |

**User's choice:** Keep pydantic-settings convention

| Option | Description | Selected |
|--------|-------------|----------|
| .env.example file | List all vars with defaults at repo root | ✓ |
| README only | No extra file | |
| Both | .env.example + README | |

**User's choice:** .env.example file

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcode in Dockerfile CMD | host 0.0.0.0, port 8000, single worker | ✓ |
| Expose uvicorn via env | UVICORN_HOST/PORT/WORKERS | |
| Expose PORT only | PaaS convention | |

**User's choice:** Hardcode uvicorn bind in Dockerfile CMD

---

## Local Container Workflow

| Option | Description | Selected |
|--------|-------------|----------|
| uv run scripts in pyproject.toml | uv run docker-build, docker-run, docker-smoke | ✓ |
| Makefile or scripts/ helper | Traditional make targets | |
| README commands only | Copy-paste docker commands | |

**User's choice:** uv run scripts in pyproject.toml (user specified "create uvx commands" → clarified as uv run scripts)

| Option | Description | Selected |
|--------|-------------|----------|
| Full E2E smoke | build + health/ready + predict | ✓ |
| Build + health only | No predict in smoke | |
| Build + size only | No run verification | |

**User's choice:** Full E2E smoke

| Option | Description | Selected |
|--------|-------------|----------|
| Standard .dockerignore | Exclude .git, .venv, .planning, .env; keep tests/ | ✓ |
| Aggressive | Exclude tests/ too | |
| Minimal | Only .git and .venv | |

**User's choice:** Standard .dockerignore

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed local tag | basic-model-serving:local | ✓ |
| Git short SHA tag | Traceability per build | |
| You decide | | |

**User's choice:** Fixed local tag `basic-model-serving:local`

---

## Claude's Discretion

- Docker HEALTHCHECK endpoint (`/health/ready` vs `/health/live`) — user did not select this gray area
- pyproject.toml script structure and smoke implementation details
- Builder-stage weight download mechanism
- HEALTHCHECK probe tool choice (curl vs python urllib)

## Deferred Ideas

- Docker HEALTHCHECK endpoint — noted for planner discretion in CONTEXT.md
- docker-compose, CI, K8s — belong to Phases 3–5
