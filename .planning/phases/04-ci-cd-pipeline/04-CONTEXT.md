# Phase 4: CI/CD Pipeline - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Every push to `main` is automatically linted, tested, built, and published to GHCR — no manual release steps. Pull requests targeting `main` get the same lint/test/build feedback without pushing an image. Pipeline must complete in under 10 minutes (CI-01–CI-04).

**Out of scope for this phase:** Auto-deploy to Kubernetes / `werf converge` from CI (PROJECT.md Out of Scope — hosted runners cannot reach local minikube), Kubernetes manifests or werf chart work (Phase 5), README polish / load-test proof (Phase 6), new API features, authentication, running `@pytest.mark.docker` / `@pytest.mark.compose` E2E in Actions.

</domain>

<decisions>
## Implementation Decisions

### Trigger Scope
- **D-01:** Workflow triggers on **`push` to `main`** and **`pull_request` targeting `main`** — not on every feature-branch push without a PR.
- **D-02:** **PRs run lint + test + Docker build (no push).** **`main` runs lint + test + build + push to GHCR.**
- **D-03:** Use a **concurrency group** that **cancels in-progress runs** when a newer commit arrives on the same PR or `main` ref.

### CI Test Matrix
- **D-04:** Quality steps run **unit/API tests only** — exclude `@pytest.mark.docker` and `@pytest.mark.compose` (those stay local / Phase 2–3 verification).
- **D-05:** Lint and test run in the **same job, sequential**: `ruff` then `pytest` (fail fast on lint).
- **D-06:** Lint means **`ruff check` + `ruff format --check`** — both must pass.
- **D-07:** Install Python deps in CI with **`uv`**, preserving the **CPU torch index** two-step install pattern from `requirements.txt` / Dockerfile (tests load the real app via `TestClient`).

### GHCR Tagging
- **D-08:** On successful `main` push, tag and push: **short git SHA (7–12 chars)** + **`latest`** + **semver from `pyproject.toml`** (currently `0.1.0`).
- **D-09:** Image name is **`ghcr.io/<owner>/<repo>`** — for this repo: `ghcr.io/estevaodr/basic-model-serving`.
- **D-10:** GHCR package visibility is **public** so reviewers can `docker pull` without auth.

### Job Layout & Speed
- **D-11:** **Single job** pipeline: lint → test → build → (push only when `github.ref == refs/heads/main`). Prefer simplicity over a separate `quality-gate` / `build-and-push` split.
- **D-12:** Docker build uses **`docker/build-push-action` + Buildx**, with `push` gated to `main` so PRs still exercise the Dockerfile.
- **D-13:** Docker layer cache via **GitHub Actions cache (`cache-from` / `cache-to: type=gha`)** — critical for baked ResNet weights and the <10 min budget.
- **D-14:** **Cache uv/pip** dependency installs for the lint/test portion of the job.

### Carried Forward (not re-discussed — locked from prior phases, PROJECT.md, research)
- CI stops at build+push — no `werf converge` / K8s deploy from Actions
- GHCR is the registry; local tag `basic-model-serving:local` remains for compose/dev
- Lint tool = ruff; test runner = pytest (already in `requirements-dev.txt`)
- Multi-stage Dockerfile with CPU-only torch and build-time baked weights (Phase 2)
- `permissions: packages: write` required for GHCR push with `GITHUB_TOKEN`
- Phase 5 will consume GHCR tags via werf; do not rebuild the image in werf (research anti-pattern)

### Claude's Discretion
- Exact short-SHA length within 7–12 (e.g. `github.sha` truncated to 7 vs 12) — planner picks a conventional default
- Exact uv install invocation / `astral-sh/setup-uv` version pins — planner/researcher
- Whether semver tag is `0.1.0` only or also `v0.1.0` prefix — prefer bare `0.1.0` matching `pyproject.toml` unless docs strongly prefer `v` prefix
- Workflow filename (e.g. `.github/workflows/ci.yml`) — follow ARCHITECTURE.md `ci.yml` unless a strong reason not to
- How to make the GHCR package public (API/action step vs documented one-time UI toggle) — researcher confirms current GitHub best practice

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — CI-01–CI-04 (push to main, lint/test, build+push GHCR, <10 min)
- `.planning/ROADMAP.md` — Phase 4 goal and success criteria
- `.planning/PROJECT.md` — GHCR choice, CI does not auto-deploy, Out of Scope for CI→K8s

### Prior phase context
- `.planning/phases/02-containerization/02-CONTEXT.md` — Local tag `basic-model-serving:local`; GHCR/SHA tagging deferred to Phase 4; Dockerfile/smoke patterns
- `.planning/phases/03-local-dev-stack-dashboards/03-CONTEXT.md` — Compose consumes local image; CI out of Phase 3 scope

### Research
- `.planning/research/STACK.md` — ruff/pytest versions, GitHub Actions → GHCR patterns, werf not needed in CI
- `.planning/research/ARCHITECTURE.md` — `.github/workflows/ci.yml` layout; lint → test → build → push; CI stops before deploy
- `.planning/research/SUMMARY.md` — Phase CI deliverables, `packages: write`, `type=gha` cache for torch layers, <10 min trap

### Implementation assets
- `Dockerfile` — Multi-stage image CI must build (and push on main)
- `requirements.txt` / `requirements-dev.txt` — Pinned runtime + pytest/ruff; CPU torch install order
- `pyproject.toml` — Semver source (`version = "0.1.0"`); existing `uv run` docker scripts
- `tests/` — Markers `docker` / `compose` to exclude; unit/API suite for CI

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Dockerfile` — Production image; CI builds this with Buildx (no separate CI Dockerfile)
- `requirements.txt` + `requirements-dev.txt` — Exact pins for uv/pip install in CI
- `pyproject.toml` — Version for semver tags; `[tool.pytest.ini_options]` markers already define `docker` / `compose`
- `scripts/docker.py` / `uv run docker-*` — Local workflow only; CI uses Actions build-push, not these scripts
- `tests/conftest.py` — Session `TestClient` loads real app (torch required in CI)

### Established Patterns
- Two-step CPU torch install (index URL then rest of requirements) — must be preserved in CI and Docker
- Pytest markers gate daemon-heavy E2E — CI excludes them via `-m` expression
- Portfolio clarity over maximal production hardening — single-job workflow preferred over multi-job split

### Integration Points
- New file: `.github/workflows/ci.yml` (net-new; no workflows exist yet)
- GHCR package `ghcr.io/estevaodr/basic-model-serving` — consumed later by Phase 5 werf / README pull examples
- Local `basic-model-serving:local` tag unchanged — compose and local smoke stay independent of GHCR

</code_context>

<specifics>
## Specific Ideas

- User clarified trigger split explicitly: **lint/test for PRs and build+push for main**, then upgraded PRs to also **build without push**
- Prefer **uv in CI** to stay consistent with local `uv run` docker scripts
- Prefer **semver + latest + short SHA** for a reviewer-friendly GHCR story
- Prefer **single-job** simplicity over the research doc’s two-job `quality-gate` → `build-and-push` split

</specifics>

<deferred>
## Deferred Ideas

- **Auto-deploy from CI to Kubernetes** — Out of scope (local minikube unreachable from hosted runners); Phase 5 is manual `werf converge`
- **Docker smoke / compose E2E in Actions** — Explicitly excluded from CI test matrix; remain local verification
- **Adversarial-input integration tests in CI** — Research SUMMARY lists under polish; belongs in Phase 6 if pursued
- **Separate lint vs test parallel jobs** — Rejected for this phase in favor of sequential single job

None else — discussion stayed within phase scope

</deferred>

---

*Phase: 4-CI/CD Pipeline*
*Context gathered: 2026-07-09*
