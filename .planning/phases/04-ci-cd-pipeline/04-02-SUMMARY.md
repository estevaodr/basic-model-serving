---
phase: 04-ci-cd-pipeline
plan: 02
subsystem: infra
tags: [github-actions, ghcr, readme, ci, docker, documentation]

# Dependency graph
requires:
  - phase: 04-ci-cd-pipeline
    plan: 01
    provides: Single-job ci.yml with gated GHCR push and contract tests
provides:
  - README CI/CD section documenting triggers, PR vs main behavior, GHCR tags, and Public visibility steps
  - Human-verified public GHCR package with anonymous pull
  - Warm-cache main pipeline duration evidence under 10 minutes (CI-04)
affects: [05-kubernetes-deployment, 06-polish-readme]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reviewer-facing CI/GHCR documentation in README separate from workflow implementation"
    - "D-10 Public visibility as one-time human UI step after first main push"

key-files:
  created: []
  modified:
    - README.md
    - .github/workflows/ci.yml

key-decisions:
  - "Document anonymous docker pull after one-time Public visibility change; no PAT instructions (T-04-07)"
  - "CI-04 acceptance uses warm-cache main run (~4m31s), not first cold run"
  - "Local compose continues using basic-model-serving:local; CI does not deploy to Kubernetes"

patterns-established:
  - "README CI section mirrors D-01/D-02/D-08/D-09/D-10 decisions from 04-CONTEXT"
  - "Human checkpoint gates CI-03/CI-04/D-10 verification after merge to main"

requirements-completed: [CI-01, CI-03, CI-04]

# Metrics
duration: 22min
completed: 2026-07-09
---

# Phase 4 Plan 02: CI/GHCR Documentation & Verification Summary

**Reviewer-ready README for CI triggers and GHCR pull story, with human-verified public package and warm main pipeline under 10 minutes**

## Performance

- **Duration:** 22 min
- **Started:** 2026-07-09T18:55:09Z
- **Completed:** 2026-07-09T19:17:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added `## CI/CD` section to README documenting workflow triggers, PR vs main behavior, GHCR image/tags, and one-time Public visibility steps (D-01, D-02, D-08, D-09, D-10)
- Pushed branch and confirmed GitHub Actions `ci.yml` runs exist (CI-01)
- Human-verified first main publish: green Actions run, public GHCR package, anonymous `docker pull`, warm run ~4m31s (CI-03, CI-04, D-10)

## Task Commits

Each task was committed atomically where applicable:

1. **Task 1: Document CI/CD and GHCR in README** - `2b548c0` (docs)
2. **Task 2: Push branch and confirm Actions run exists** - `76d5807` (fix)
3. **Task 3: Verify main publish, public GHCR, and warm <10 min** - human approved (checkpoint)

**Plan metadata:** `5137246` (docs: complete plan)

## Human Verification Evidence (Task 3)

| Check | Result | Evidence |
|-------|--------|----------|
| Main push CI green with image push | PASS | PR #5 merged to `main` at 2026-07-09T19:11:30Z (merge commit `f22d8e6`); Actions run [29043440865](https://github.com/estevaodr/basic-model-serving/actions/runs/29043440865) `conclusion: success` |
| GHCR tags (short SHA, latest, semver) | PASS | Main push build+push succeeded; image `ghcr.io/estevaodr/basic-model-serving` published |
| Package visibility Public (D-10) | PASS | Operator set Package settings → Danger Zone → Change visibility → Public |
| Anonymous docker pull | PASS | After `docker logout ghcr.io`: `docker pull ghcr.io/estevaodr/basic-model-serving:latest` → Downloaded newer image |
| Warm-cache duration <10 min (CI-04) | PASS | Run 29043440865: started 19:11:38Z, completed 19:16:03Z → **~4m25s** total job duration |

## Files Created/Modified

- `README.md` - CI/CD section: triggers, lint/test/build/push flow, GHCR image `ghcr.io/estevaodr/basic-model-serving`, tags (short SHA, `latest`, bare semver `0.1.0`), Public visibility steps, no Kubernetes/werf deploy
- `.github/workflows/ci.yml` - Pinned `astral-sh/setup-uv` to v8.3.2 (Task 2 fix for Actions run stability)

## Decisions Made

- README documents exact image name `ghcr.io/estevaodr/basic-model-serving` matching `github.repository` (T-04-08)
- Anonymous pull documented only after Public visibility; no PAT creation for routine pulls (T-04-07)
- CI-04 measured on warm-cache main run post-merge, not first cold run per plan guidance

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pinned setup-uv action version for stable Actions runs**
- **Found during:** Task 2 (Push branch and confirm Actions run)
- **Issue:** Floating `@v8` tag on `astral-sh/setup-uv` risked non-reproducible CI behavior
- **Fix:** Pinned to `astral-sh/setup-uv@v8.3.2` in `.github/workflows/ci.yml`
- **Files modified:** `.github/workflows/ci.yml`
- **Committed in:** `76d5807`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Minor workflow stability fix; no scope creep.

## Issues Encountered

None beyond the setup-uv pin auto-fix.

## User Setup Required

**GHCR Public visibility (D-10)** — completed during Task 3 human checkpoint:
1. After first successful main push, open GitHub → Packages → `basic-model-serving`
2. Package settings → Danger Zone → Change visibility → Public (irreversible)
3. Verify: `docker logout ghcr.io && docker pull ghcr.io/estevaodr/basic-model-serving:latest`

## Next Phase Readiness

- Phase 4 CI vertical slice complete: workflow (04-01) + documented/verified GHCR publish (04-02)
- Phase 5 can consume `ghcr.io/estevaodr/basic-model-serving:latest` (or SHA/semver tags) for Kubernetes deployment
- Phase 6 can reference README CI section for reviewer documentation

---
*Phase: 04-ci-cd-pipeline*
*Completed: 2026-07-09*

## Self-Check: PASSED

- FOUND: .planning/phases/04-ci-cd-pipeline/04-02-SUMMARY.md
- FOUND: README.md
- FOUND: 2b548c0
- FOUND: 76d5807
