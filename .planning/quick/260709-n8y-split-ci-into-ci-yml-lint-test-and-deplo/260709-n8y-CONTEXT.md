# Quick Task 260709-n8y: Split CI into ci.yml (lint+test) and deploy.yml (docker build+push) - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Task Boundary

Split the current single-job `.github/workflows/ci.yml` into two workflows:

1. **`ci.yml`** — lint and test only (uv, ruff, pytest)
2. **`deploy.yml`** — Docker build and GHCR push

Supersedes Phase 4 **D-11** (single job). All other Phase 4 decisions (D-01–D-10, D-12–D-14) remain in effect unless explicitly overridden below.

**Out of scope:** Auto-deploy to Kubernetes, werf, compose/docker E2E in Actions, changes to Dockerfile or application code.

</domain>

<decisions>
## Implementation Decisions

### Workflow split
- **`ci.yml`** retains: checkout, setup-uv, CPU torch install, ruff check/format, pytest (exclude docker/compose markers).
- **`deploy.yml`** retains: checkout, Buildx, version read, GHCR login, metadata tags, build-push with GHA layer cache.
- Remove all Docker steps from `ci.yml`; remove all lint/test steps from `deploy.yml`.

### Triggers
- **`ci.yml`**: `push` to `main` and `pull_request` targeting `main` (D-01 unchanged).
- **`deploy.yml`**: **`push` to `main` only** — no `pull_request` trigger, no `workflow_run` coupling to CI.
- On `main` push, CI and deploy may run in parallel (user declined `workflow_run` gate).

### PR behavior (supersedes D-02 partially)
- **PRs run `ci.yml` only** (lint + test). No Docker build on PRs.
- **`main` push** runs both workflows; deploy builds and pushes to GHCR (D-02 push gate unchanged).

### Permissions
- **`ci.yml`**: `contents: read` only (no `packages: write`).
- **`deploy.yml`**: `contents: read` + `packages: write` for GHCR push.

### Concurrency (D-03)
- Each workflow file gets its own concurrency group: `${{ github.workflow }}-${{ github.ref }}`, `cancel-in-progress: true`.

### Contract tests
- Replace `test_d11_single_ci_job` with tests asserting two-workflow layout.
- Split or extend `tests/test_ci_workflow.py` (e.g. add deploy workflow tests) so D-01–D-14 behavior is still covered across both files.
- Update README `## CI/CD` to document two workflows and PR vs main behavior.

### Claude's Discretion
- Exact deploy workflow filename (`deploy.yml` unless strong reason otherwise).
- Whether to split test file into `test_ci_workflow.py` + `test_deploy_workflow.py` or one module with fixtures for both paths.
- Exact semver/SHA/latest tag expressions in deploy.yml (preserve current D-08 behavior).
- Minor README wording and section structure.

</decisions>

<specifics>
## Specific Ideas

- Preserve pins: `astral-sh/setup-uv@v8.3.2`, docker actions majors, push gate expression for main-only publish.
- GHCR image: `ghcr.io/estevaodr/basic-model-serving` (D-09).
- Local compose tag `basic-model-serving:local` unchanged.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/phases/04-ci-cd-pipeline/04-CONTEXT.md` — original D-01..D-14 (D-11 superseded)
- `.planning/phases/04-ci-cd-pipeline/04-VERIFICATION.md` — prior 9/9 pass; re-verify deploy path after split
- `.github/workflows/ci.yml` — current single-job implementation
- `tests/test_ci_workflow.py` — contract tests including D-11 single-job assertion
- `README.md` — CI/CD section

</canonical_refs>
