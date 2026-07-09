# Phase 4: CI/CD Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-09
**Phase:** 4-CI/CD Pipeline
**Areas discussed:** Trigger scope, CI test matrix, GHCR tagging, Job layout & speed

---

## Trigger Scope

| Option | Description | Selected |
|--------|-------------|----------|
| `main` only | Literal CI-01; simplest | |
| `main` + PRs | PR feedback before merge | ✓ (via "You decide" + freeform) |
| You decide | Claude picks default | ✓ then refined |

**User's choice:** Lint/test for PRs and build+push for main; then chose PR build-without-push; triggers = push to main + PR targeting main; cancel in-progress concurrency.

**Notes:** First answer was freeform on top of "You decide": "lint, test for PRs and build and push for main". Follow-ups locked build-on-PR (no push), event set, and concurrency cancel.

---

## CI Test Matrix

| Option | Description | Selected |
|--------|-------------|----------|
| Unit/API only | Exclude docker/compose markers | ✓ |
| Also Docker smoke | E2E after build in Actions | |
| Also compose E2E | Full stack in CI | |
| You decide | | |

**Follow-ups:**

| Option | Description | Selected |
|--------|-------------|----------|
| Same job sequential ruff→pytest | | ✓ |
| Parallel lint/test jobs | | |
| ruff check only | | |
| ruff check + format --check | | ✓ |
| pip + CPU torch | | |
| uv for CI installs | | ✓ |

**User's choice:** Unit/API only; sequential lint then test; ruff check + format --check; uv installs.

**Notes:** None.

---

## GHCR Tagging

| Option | Description | Selected |
|--------|-------------|----------|
| SHA only | Immutable pin | |
| SHA + latest | Common portfolio pattern | |
| SHA + latest + semver from pyproject | | ✓ |
| You decide | | |

**Follow-ups:**

| Option | Description | Selected |
|--------|-------------|----------|
| `ghcr.io/<owner>/<repo>` | | ✓ |
| Explicit package name | | |
| Public package | | ✓ |
| Private package | | |
| Full SHA tag | | |
| Short SHA (7–12) | | ✓ |

**User's choice:** Short SHA + latest + semver; `ghcr.io/estevaodr/basic-model-serving`; public; short SHA.

**Notes:** Repo confirmed public (`estevaodr/basic-model-serving`); pyproject version `0.1.0`.

---

## Job Layout & Speed

| Option | Description | Selected |
|--------|-------------|----------|
| Two jobs quality-gate → build-and-push | Matches research | |
| Single job | Simpler YAML | ✓ |
| Three jobs | Max split | |
| You decide | | |

**Follow-ups:**

| Option | Description | Selected |
|--------|-------------|----------|
| Docker cache type=gha | | ✓ |
| Registry cache | | |
| Both | | |
| build-push-action + Buildx | | ✓ |
| Plain docker CLI | | |
| Cache uv/pip | | ✓ |
| No dep cache | | |

**User's choice:** Single job; gha Docker cache; build-push-action; cache uv/pip.

**Notes:** User preferred single-job simplicity over ARCHITECTURE.md’s two-job split.

---

## Claude's Discretion

- Exact short-SHA truncation length (7 vs 12)
- uv/setup-uv action version pins
- Semver tag with or without `v` prefix (lean bare `0.1.0`)
- Workflow filename (`ci.yml` preferred)
- Mechanism to set GHCR package public

## Deferred Ideas

- CI→K8s auto-deploy (out of scope)
- Docker/compose E2E in Actions (excluded from matrix)
- Adversarial CI tests (Phase 6 candidate)
- Parallel lint/test jobs (rejected)
