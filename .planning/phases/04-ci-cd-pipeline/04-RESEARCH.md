# Phase 4: CI/CD Pipeline - Research

**Researched:** 2026-07-09
**Domain:** GitHub Actions → GHCR (lint/test/build/push)
**Confidence:** HIGH

## Summary

Phase 4 adds a single net-new workflow (`.github/workflows/ci.yml`) that lint/tests with uv+ruff+pytest, then builds the existing multi-stage Dockerfile with Buildx. On `main`, it pushes `ghcr.io/estevaodr/basic-model-serving` tagged with short SHA + `latest` + bare semver from `pyproject.toml`. PRs targeting `main` run the same lint/test/build path with `push: false`. No werf, no K8s deploy, no docker/compose E2E in Actions.

The <10 minute budget (CI-04) is dominated by the Docker build (~1.35GB local image with baked ResNet weights). Cold runs without GHA layer cache are the risk; warm `cache-from/cache-to: type=gha,mode=max` is the mitigation. Lint+unit tests are cheap once torch is cached via `astral-sh/setup-uv` (`enable-cache: true`). GHCR packages start **private**; making the package public is a one-time post-first-push UI step (or optional API), not automatic from repo visibility.

**Primary recommendation:** One job, sequential steps — checkout → setup-uv (3.12 + cache) → two-step CPU torch install → ruff → pytest `-m "not docker and not compose"` → Buildx + metadata + build-push (`push` only on `main`) — with `permissions: contents: read` + `packages: write`, concurrency cancel-in-progress, and a human checkpoint to set GHCR visibility public after the first successful push.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Workflow triggers on **`push` to `main`** and **`pull_request` targeting `main`** — not on every feature-branch push without a PR.
- **D-02:** **PRs run lint + test + Docker build (no push).** **`main` runs lint + test + build + push to GHCR.**
- **D-03:** Use a **concurrency group** that **cancels in-progress runs** when a newer commit arrives on the same PR or `main` ref.
- **D-04:** Quality steps run **unit/API tests only** — exclude `@pytest.mark.docker` and `@pytest.mark.compose` (those stay local / Phase 2–3 verification).
- **D-05:** Lint and test run in the **same job, sequential**: `ruff` then `pytest` (fail fast on lint).
- **D-06:** Lint means **`ruff check` + `ruff format --check`** — both must pass.
- **D-07:** Install Python deps in CI with **`uv`**, preserving the **CPU torch index** two-step install pattern from `requirements.txt` / Dockerfile (tests load the real app via `TestClient`).
- **D-08:** On successful `main` push, tag and push: **short git SHA (7–12 chars)** + **`latest`** + **semver from `pyproject.toml`** (currently `0.1.0`).
- **D-09:** Image name is **`ghcr.io/<owner>/<repo>`** — for this repo: `ghcr.io/estevaodr/basic-model-serving`.
- **D-10:** GHCR package visibility is **public** so reviewers can `docker pull` without auth.
- **D-11:** **Single job** pipeline: lint → test → build → (push only when `github.ref == refs/heads/main`). Prefer simplicity over a separate `quality-gate` / `build-and-push` split.
- **D-12:** Docker build uses **`docker/build-push-action` + Buildx**, with `push` gated to `main` so PRs still exercise the Dockerfile.
- **D-13:** Docker layer cache via **GitHub Actions cache (`cache-from` / `cache-to: type=gha`)** — critical for baked ResNet weights and the <10 min budget.
- **D-14:** **Cache uv/pip** dependency installs for the lint/test portion of the job.

### Claude's Discretion
- Exact short-SHA length within 7–12 (e.g. `github.sha` truncated to 7 vs 12) — planner picks a conventional default
- Exact uv install invocation / `astral-sh/setup-uv` version pins — planner/researcher
- Whether semver tag is `0.1.0` only or also `v0.1.0` prefix — prefer bare `0.1.0` matching `pyproject.toml` unless docs strongly prefer `v` prefix
- Workflow filename (e.g. `.github/workflows/ci.yml`) — follow ARCHITECTURE.md `ci.yml` unless a strong reason not to
- How to make the GHCR package public (API/action step vs documented one-time UI toggle) — researcher confirms current GitHub best practice

### Deferred Ideas (OUT OF SCOPE)
- **Auto-deploy from CI to Kubernetes** — Out of scope (local minikube unreachable from hosted runners); Phase 5 is manual `werf converge`
- **Docker smoke / compose E2E in Actions** — Explicitly excluded from CI test matrix; remain local verification
- **Adversarial-input integration tests in CI** — Research SUMMARY lists under polish; belongs in Phase 6 if pursued
- **Separate lint vs test parallel jobs** — Rejected for this phase in favor of sequential single job
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CI-01 | GitHub Actions pipeline runs on every push to `main` | `on.push.branches: [main]` (+ PR trigger per D-01) |
| CI-02 | Pipeline runs automated linting and tests | ruff check + format --check; pytest with marker exclusion |
| CI-03 | Pipeline builds the Docker image and pushes it to GHCR | build-push-action + login-action; push gated to main |
| CI-04 | Pipeline completes in <10 minutes | type=gha Docker cache + setup-uv enable-cache; exclude docker/compose E2E |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Workflow trigger / concurrency | CDN / Static (CI platform) | — | GitHub Actions owns event routing and cancel-in-progress |
| Lint + unit/API tests | API / Backend (runner) | — | Hosted runner executes ruff/pytest against app code; torch required for TestClient |
| Dependency install/cache | API / Backend (runner) | CDN / Static (Actions cache) | uv installs into runner; GHA cache stores uv cache blobs |
| Docker image build | CDN / Static (Buildx on runner) | — | Buildx builds Dockerfile; layers cached via type=gha |
| Image publish (GHCR) | CDN / Static (registry) | — | ghcr.io stores artifacts; GITHUB_TOKEN + packages:write |
| Package visibility (public) | CDN / Static (GitHub Packages settings) | — | Visibility is package metadata, not build output — one-time admin action |
| K8s / werf deploy | — | — | Explicitly out of scope for this phase |

## Standard Stack

### Core

| Library / Action | Version | Purpose | Why Standard |
|------------------|---------|---------|--------------|
| `actions/checkout` | v7.0.0 (tag) | Clone repo | Current major; GitHub docs examples use v6/v7 [VERIFIED: gh api releases] |
| `astral-sh/setup-uv` | v8.3.2 | Install uv + cache | Official Astral action; `enable-cache` uploads uv cache [CITED: github.com/astral-sh/setup-uv] |
| `docker/setup-buildx-action` | v4.2.0 | Enable Buildx | Required for type=gha cache backend [VERIFIED: gh api releases] |
| `docker/login-action` | v4.4.0 | Auth to ghcr.io | Official GHCR login with GITHUB_TOKEN [CITED: docs.github.com publish-docker-images] |
| `docker/metadata-action` | v6.2.0 | Generate tags/labels | Standard for sha/latest/raw tags [VERIFIED: gh api releases] |
| `docker/build-push-action` | v7.3.0 | Build (+ conditional push) | Official Buildx wrapper; `push: false` on PRs [CITED: docker/build-push-action] |
| uv | (via setup-uv) | pip-compatible installs | Locked by D-07; official PyTorch CPU install path [CITED: docs.astral.sh/uv pytorch] |
| ruff | 0.15.20 (pinned in requirements-dev.txt) | Lint + format check | Already project pin [VERIFIED: requirements-dev.txt] |
| pytest | 9.1.1 (pinned) | Unit/API tests | Already project pin; markers in pyproject.toml [VERIFIED: requirements-dev.txt] |
| Python | 3.12 | Runtime for tests | Matches Dockerfile `python:3.12-slim` and `requires-python = ">=3.12"` |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `gh` CLI (optional step) | runner-provided | PATCH package visibility | Only if planner chooses API over UI for D-10 |
| GITHUB_TOKEN | ambient | GHCR push auth | Always — do not add a PAT for push |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Single job (D-11) | Two-job quality-gate → build-and-push (STACK.md sample) | Split is clearer for status checks but rejected for portfolio simplicity |
| `astral-sh/setup-uv` | `actions/setup-python` + pip | Slower installs; contradicts D-07 |
| `type=gha` cache | Registry cache / no cache | Registry needs extra image; no cache fails CI-04 cold |
| UI for public package | REST PATCH visibility | UI is official documented path for personal accounts; API is optional automation |

**Installation:** No new PyPI/npm packages. Workflow file only. Dev deps already in `requirements-dev.txt`.

**Version verification (2026-07-09):**
- `actions/checkout` → v7.0.0 [VERIFIED: gh api]
- `astral-sh/setup-uv` → v8.3.2 [VERIFIED: gh api]
- `docker/setup-buildx-action` → v4.2.0 [VERIFIED: gh api]
- `docker/login-action` → v4.4.0 [VERIFIED: gh api]
- `docker/metadata-action` → v6.2.0 [VERIFIED: gh api]
- `docker/build-push-action` → v7.3.0 [VERIFIED: gh api]

**Pinning recommendation:** Prefer major tags (`@v7`, `@v8`, `@v4`, `@v6`) for readability in a portfolio repo, matching STACK.md style. SHA-pinning is GitHub’s security recommendation but optional here. [CITED: docs.github.com publish-docker-images]

## Package Legitimacy Audit

> This phase installs **no new** application packages. It reuses pinned `pytest`/`ruff` and marketplace Actions.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| pytest (existing pin) | PyPI | mature (seam flagged “too-new” on latest release date) | n/a in seam | github.com/pytest-dev/pytest | SUS (false positive) | Approved — already in repo; official pytest |
| ruff (existing pin) | PyPI | mature (seam flagged “too-new”) | n/a in seam | docs.astral.sh/ruff | SUS (false positive) | Approved — already in repo; official Astral |
| astral-sh/setup-uv | GitHub Actions | v8.3.2 | — | github.com/astral-sh/setup-uv | OK (authoritative) | Approved |
| docker/*-action | GitHub Actions | current majors | — | github.com/docker/* | OK (authoritative) | Approved |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** pytest/ruff seam false positives only — no planner checkpoint needed (already project dependencies)

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────┐     push/PR to main      ┌──────────────────────────────┐
│  Developer  │ ───────────────────────► │  GitHub Actions (ci.yml)     │
└─────────────┘                          │  concurrency: cancel stale   │
                                         └──────────────┬───────────────┘
                                                        │
                    ┌───────────────────────────────────┼────────────────────────┐
                    │ SINGLE JOB                        ▼                        │
                    │  1. checkout                                                   │
                    │  2. setup-uv (python 3.12, enable-cache)                      │
                    │  3. uv venv + two-step CPU torch + requirements(-dev)          │
                    │  4. ruff check + ruff format --check  ──fail──► job fails     │
                    │  5. pytest -m "not docker and not compose" ──fail──► fails    │
                    │  6. setup-buildx + metadata (sha/latest/semver)               │
                    │  7. login ghcr.io (always OK; push gated)                     │
                    │  8. build-push-action                                         │
                    │        │                                                     │
                    │        ├─ PR:  push=false (build only, still warms cache)    │
                    │        └─ main: push=true ──► ghcr.io/estevaodr/...          │
                    └──────────────────────────────────────────────────────────────┘
                                                        │
                                                        ▼ (first main success)
                                         ┌──────────────────────────────┐
                                         │ GHCR package (private default)│
                                         │ Human: set visibility Public  │
                                         └──────────────────────────────┘
```

### Recommended Project Structure

```
.github/
└── workflows/
    └── ci.yml          # net-new — only CI artifact this phase
Dockerfile              # unchanged — CI builds this file
requirements.txt        # runtime + torch pins (two-step install)
requirements-dev.txt    # pytest + ruff
pyproject.toml          # version = "0.1.0" for semver tag; pytest markers
tests/                  # unit/API only in CI; docker/compose deselected
```

### Pattern 1: Single-job conditional push

**What:** One `ci` job; `push: ${{ github.ref == 'refs/heads/main' && github.event_name == 'push' }}` (or equivalent) so PRs build without publishing.
**When to use:** Always for this phase (D-02, D-11, D-12).
**Example:**

```yaml
# Source: synthesized from docs.github.com publish-docker-images + docker/build-push-action
- uses: docker/build-push-action@v7
  with:
    context: .
    push: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
    tags: ${{ steps.meta.outputs.tags }}
    labels: ${{ steps.meta.outputs.labels }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### Pattern 2: uv two-step CPU torch install

**What:** Match Dockerfile/requirements comments — torch from CPU index first, then full requirements + dev.
**When to use:** Always (D-07); TestClient loads real app (`tests/conftest.py`).
**Example:**

```yaml
# Source: https://docs.astral.sh/uv/guides/integration/pytorch/
- uses: astral-sh/setup-uv@v8
  with:
    python-version: "3.12"
    enable-cache: true
- run: |
    uv venv
    source .venv/bin/activate
    uv pip install torch==2.12.1 torchvision==0.27.1 \
      --index-url https://download.pytorch.org/whl/cpu
    uv pip install -r requirements.txt -r requirements-dev.txt
```

### Pattern 3: metadata tags (SHA + latest + bare semver)

**What:** `docker/metadata-action` for SHA/latest; extract `version` from `pyproject.toml` into `type=raw`.
**When to use:** Tag generation on every build; push only applies tags on main.
**Discretion defaults:** short SHA length **7** (metadata-action default); semver tag **bare `0.1.0`** (no `v` prefix).

```yaml
# Source: docker/metadata-action README (type=sha, type=raw, is_default_branch)
- id: version
  run: |
    VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
    echo "version=$VERSION" >> "$GITHUB_OUTPUT"
- id: meta
  uses: docker/metadata-action@v6
  with:
    images: ghcr.io/${{ github.repository }}
    tags: |
      type=sha,prefix=,format=short
      type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
      type=raw,value=${{ steps.version.outputs.version }},enable=${{ github.ref == 'refs/heads/main' }}
```

### Pattern 4: Concurrency cancel

```yaml
# Source: docs.github.com workflow-syntax concurrency
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### Anti-Patterns to Avoid

- **Missing `permissions: packages: write`:** Causes GHCR 403 on push — most common failure [CITED: STACK.md / GitHub Packages docs]
- **Running `@pytest.mark.docker` / `compose` in Actions:** Exceeds time budget; needs daemon/compose stack (deferred)
- **`werf` / `werf converge` in CI:** Cannot reach local minikube; out of scope
- **`push: true` on pull_request:** Pollutes GHCR with PR tags; contradicts D-02
- **Skipping `mode=max` on multi-stage Dockerfile:** Intermediate builder layers (torch + baked weights) may not cache [CITED: Docker build cache docs]
- **Single-step `uv pip install -r requirements.txt` without CPU index:** Pulls CUDA wheels; huge download / wrong artifact [CITED: uv pytorch guide]
- **Assuming public repo ⇒ public GHCR package:** Visibility is independent; package defaults private [CITED: docs.github.com packages visibility]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image tagging | Shell `echo ${GITHUB_SHA::7}` sprawl | `docker/metadata-action` | Labels, multi-tag, branch enable flags |
| GHCR auth | Custom PAT / docker config JSON | `docker/login-action` + `GITHUB_TOKEN` | Ambient token; least privilege with permissions block |
| Docker layer cache | Manual `actions/cache` on `/var/lib/docker` | `cache-from/to: type=gha` | Buildx-native; works with BuildKit |
| uv install on runner | curl install script | `astral-sh/setup-uv` | Caching + version management built-in |
| Marker filtering | `pytest --ignore=tests/test_docker*` | `-m "not docker and not compose"` | Markers already registered; compose file also has docker mark |

**Key insight:** The hard parts (GHCR auth, Buildx cache protocol, tag metadata) are solved by official actions — custom shell only for reading `pyproject.toml` version and the uv two-step install.

## Common Pitfalls

### Pitfall 1: GHCR 403 Forbidden on push
**What goes wrong:** Build succeeds, push fails with 403.
**Why it happens:** Default `GITHUB_TOKEN` lacks `packages: write` unless workflow sets it; or package exists unlinked to repo.
**How to avoid:** Set `permissions: { contents: read, packages: write }` at job or workflow level; first publish from Actions links package to repo.
**Warning signs:** `denied: permission_denied` / `403` in build-push logs.

### Pitfall 2: Cold Docker build blows <10 min budget
**What goes wrong:** First run or cache-evicted run exceeds 10 minutes.
**Why it happens:** ~1.35GB image; torch CPU wheel + ResNet bake in builder stage; GHA cache default 10GB/repo with LRU eviction.
**How to avoid:** Always `cache-from` + `cache-to: type=gha,mode=max`; keep Buildx current (cache API v2); do not run docker/compose E2E in CI.
**Warning signs:** Long `pip install torch` / weight download steps every run; cache miss logs.

### Pitfall 3: Accidental CUDA torch in CI venv
**What goes wrong:** Test install pulls multi-GB CUDA wheels; slow or OOM.
**Why it happens:** Forgot `--index-url https://download.pytorch.org/whl/cpu` on first install step.
**How to avoid:** Two-step install identical to Dockerfile comments; never use `--extra-index-url` alone for torch.
**Warning signs:** Multi-minute pip resolve; CUDA libs in site-packages.

### Pitfall 4: Package private after “successful” CI
**What goes wrong:** Reviewers cannot `docker pull` without auth despite green CI.
**Why it happens:** First publish creates **private** package; repo public ≠ package public.
**How to avoid:** Document one-time Package settings → Danger Zone → Change visibility → Public after first main push. Optional: `gh api` PATCH (user/org packages API).
**Warning signs:** `denied: permission_denied: read_package` for anonymous pulls.

### Pitfall 5: Pytest collects docker/compose E2E
**What goes wrong:** CI hangs waiting for Docker daemon or compose stack.
**Why it happens:** Missing `-m` expression; markers exist but default is “run all”.
**How to avoid:** `pytest -m "not docker and not compose"` (33/36 tests locally with this filter).
**Warning signs:** Collection includes `test_docker_smoke` / `test_compose_stack`.

### Pitfall 6: Login/push on PR without gating
**What goes wrong:** PR builds attempt push or create unwanted tags.
**Why it happens:** Copied STACK.md sample with unconditional `push: true`.
**How to avoid:** Gate `push` on `main` + `push` event; still run build on PRs.

## Code Examples

### Canonical workflow skeleton (planner starting point)

```yaml
# Source: composition of GitHub docs + docker/* actions + CONTEXT D-01..D-14
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  packages: write

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - uses: astral-sh/setup-uv@v8
        with:
          python-version: "3.12"
          enable-cache: true

      - name: Install dependencies (CPU torch)
        run: |
          uv venv
          source .venv/bin/activate
          uv pip install torch==2.12.1 torchvision==0.27.1 \
            --index-url https://download.pytorch.org/whl/cpu
          uv pip install -r requirements.txt -r requirements-dev.txt

      - name: Lint
        run: |
          source .venv/bin/activate
          ruff check .
          ruff format --check .

      - name: Test
        run: |
          source .venv/bin/activate
          pytest -m "not docker and not compose"

      - uses: docker/setup-buildx-action@v4

      - name: Read version
        id: version
        run: |
          VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"

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
            type=sha,prefix=,format=short
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
            type=raw,value=${{ steps.version.outputs.version }},enable=${{ github.ref == 'refs/heads/main' }}

      - uses: docker/build-push-action@v7
        with:
          context: .
          push: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### GHCR public visibility (recommended: one-time UI)

Per GitHub Docs — after first successful push:

1. Open package `basic-model-serving` under user `estevaodr`
2. Package settings → Danger Zone → Change visibility → **Public**
3. Confirm (irreversible)

[CITED: https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility]

**Planner note:** Add `checkpoint:human-verify` after first green main run. Do not block workflow merge on automation — package does not exist until first push (`gh api users/estevaodr/packages/container/basic-model-serving` → 404 as of research date).

Optional API (user-scoped, after package exists) — community pattern, not primary docs path for personal accounts:

```bash
# [ASSUMED] user packages PATCH shape mirrors org API; verify against GitHub REST docs at implement time
gh api --method PATCH "/user/packages/container/basic-model-serving" -f visibility=public
```

Prefer documenting the UI path in PLAN verification; skip API automation unless user asks.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| GHA cache API v1 for Buildx | Cache API v2 only | 2025-04 (v1 sunset) | Need current Buildx via setup-buildx-action |
| Hard 10GB cache cap | 10GB free + configurable higher | 2025-11 | Eviction still possible; enough for one large image + uv cache |
| Two-job CI in STACK.md sample | Single job (D-11) | Phase 4 discuss | Simpler status; sequential fail-fast |
| setup-python + pip | setup-uv + uv pip | D-07 | Faster + consistent with local uv scripts |

**Deprecated/outdated:**
- Relying on GHA cache v1 / old Buildx — will error with legacy service shutdown message
- Assuming STACK.md two-job layout — superseded by CONTEXT D-11

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | User-scoped `gh api PATCH /user/packages/container/...` works like org API for visibility | Code Examples / D-10 | API step fails — UI path still works (preferred) |
| A2 | Warm GHA cache keeps full pipeline under 10 minutes on ubuntu-latest | Pitfalls / CI-04 | May need to measure first runs; cold run may exceed budget once |
| A3 | `mode=max` is sufficient to cache builder-stage torch + weight layers | Standard Stack | Partial cache hits; still slow — may need Dockerfile layer tweaks later (out of phase unless CI-04 fails) |
| A4 | Login on PRs is harmless even when push=false | Pattern 1 | Negligible; if token policy changes, gate login to main only |

**If wrong:** Prefer UI for A1; treat first cold run as known exception for A2 and document warm-run SLA for CI-04 verification.

## Open Questions

1. **CI-04 verification of cold vs warm**
   - What we know: Local image ~1.35GB; type=gha is required; cold torch download is the long pole.
   - What's unclear: Exact cold-run duration on GitHub-hosted runners for this Dockerfile.
   - Recommendation: Accept first-ever run may be borderline; verify CI-04 on a **warm-cache** main run. If cold consistently >10m, follow-up is Dockerfile cache-layer tuning (not in deferred list — escalate only if measured).

2. **Whether to gate `docker/login-action` to main only**
   - What we know: Push is gated; login on PR is common and usually fine.
   - Recommendation: Keep login unconditional for simplicity unless security review objects.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker (local) | Manual smoke only | ✓ | 29.6.1 | — (not needed in Actions; runners have Docker) |
| gh CLI | Optional visibility API | ✓ | 2.45.0 | UI toggle for D-10 |
| uv (local) | Pattern validation | ✓ | 0.8.3 | setup-uv installs on runner |
| Python 3.12 | Tests | ✓ | 3.12.3 | setup-uv python-version |
| GitHub Actions (hosted) | CI execution | ✓ (repo on github.com) | — | — |
| GHCR package | Push target | ✗ not created yet | — | Created on first main push |

**Missing dependencies with no fallback:** none for planning/execution of workflow file.

**Missing dependencies with fallback:** GHCR package (created by first push); public visibility (human UI).

## Project Constraints (from .cursor/rules/)

From `.cursor/rules/gsd.mdc` / PROJECT.md:

- Tech stack fixed: GitHub Actions, GHCR, Docker, Python/PyTorch/FastAPI — do not substitute registries or CI systems
- CI/CD reachability: hosted runners cannot reach local minikube — CI stops at build+push
- Prefer GSD workflow entry points for repo edits (planner/executor context)
- No project-local skills under `.cursor/skills/` or `.agents/skills/`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | partial | GITHUB_TOKEN for GHCR; no app auth in scope |
| V3 Session Management | no | — |
| V4 Access Control | yes | Least-privilege `permissions:` block; public package intentional (D-10) |
| V5 Input Validation | no | CI config only; app validation already Phase 1 |
| V6 Cryptography | no | Use platform TLS to ghcr.io; never hand-roll |

### Known Threat Patterns for GitHub Actions → GHCR

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Over-privileged GITHUB_TOKEN | Elevation of Privilege | Explicit `contents: read` + `packages: write` only |
| Accidental private→public data leak | Information Disclosure | Public image is intentional; no secrets in image (weights are public ResNet) |
| Supply-chain action tag move | Tampering | Prefer major tags or SHA pins; use official docker/* and astral-sh actions |
| Cache poisoning via PR | Tampering | GHA cache isolation by default; still build PRs without push |
| Secret exfiltration via malicious PR workflow | Information Disclosure | Workflow only on this repo’s trusted Actions; no custom secrets required |

## Sources

### Primary (HIGH / MEDIUM confidence)

- Context7 `/astral-sh/setup-uv` — enable-cache, python-version [CITED]
- Context7 `/astral-sh/uv` — PyTorch CPU `--index-url` install [CITED]
- Context7 `/docker/build-push-action` — push boolean, type=gha cache [CITED]
- Context7 `/docker/metadata-action` — type=sha (default short=7), type=raw, is_default_branch [CITED]
- Context7 `/websites/github_en_actions` — concurrency cancel-in-progress; packages:write [CITED]
- Context7 `/pytest-dev/pytest` — `-m "not …"` expressions [CITED]
- GitHub Docs — Configuring package visibility (public irreversible; default private) [VERIFIED: webfetch]
- GitHub Docs — Publishing Docker images to GHCR [VERIFIED: webfetch]
- Docker Docs — GHA cache backend / size limits [CITED: docs.docker.com/build/cache/backends/gha/]
- Local codebase — Dockerfile, requirements*, pyproject markers, conftest TestClient, image size ~1353802841 bytes [VERIFIED: filesystem]

### Secondary

- `.planning/research/STACK.md` — baseline workflow; packages:write; type=gha [CITED]
- `.planning/research/ARCHITECTURE.md` — `ci.yml` path; CI stops before deploy [CITED]
- `.planning/research/SUMMARY.md` — 403 and <10 min traps [CITED]
- GitHub Changelog 2025-11 — cache can exceed 10GB [CITED: websearch]

### Tertiary (LOW)

- Community `gh api` PATCH for package visibility automation [ASSUMED] — prefer UI

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — action versions verified via GitHub Releases API; patterns from official docs
- Architecture: HIGH — locked by CONTEXT; maps cleanly to single workflow file
- Pitfalls: HIGH — packages:write, private-by-default, torch index, and cache budget are well-documented
- CI-04 timing: MEDIUM — warm-cache expectation strong; cold-run unmeasured on hosted runners

**Research date:** 2026-07-09
**Valid until:** 2026-08-09 (Actions majors move periodically; re-check action tags if planning slips >30 days)

## Discretion Resolutions (for planner)

| Topic | Resolution | Rationale |
|-------|------------|-----------|
| Short SHA length | **7** | metadata-action default; within D-08 7–12 |
| Semver tag form | **bare `0.1.0`** | Matches pyproject; no `v` prefix |
| Workflow path | **`.github/workflows/ci.yml`** | ARCHITECTURE.md |
| setup-uv pin | **`astral-sh/setup-uv@v8`** (latest v8.3.2) | Current major |
| GHCR public | **One-time UI after first push** + PLAN human checkpoint | Official docs; package 404 until first push; API optional |
