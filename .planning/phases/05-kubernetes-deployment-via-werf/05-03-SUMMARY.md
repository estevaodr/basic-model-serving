---
phase: 05-kubernetes-deployment-via-werf
plan: 03
subsystem: infra
tags: [werf, minikube, kubernetes, rollout, zero-downtime, readme, helm]

requires:
  - phase: 05-kubernetes-deployment-via-werf
    plan: 02
    provides: kube-prometheus-stack bundle, ServiceMonitor, Grafana dashboard provisioning
provides:
  - scripts/rollout-zero-downtime.sh curl loop for /health/ready during rollout (D-19)
  - .helm/values-local.yaml local image tag overrides for minikube image load (D-06)
  - README Kubernetes section with GHCR SHA and local converge paths (D-05, D-16, D-20)
  - Extended documentation contract tests in tests/test_helm_chart.py
affects: []

tech-stack:
  added: []
  patterns:
    - "TDD RED/GREEN for README and script contract tests before implementation"
    - "minikube service model-serving --url drives rollout readiness hammer script"
    - "values-local.yaml for IfNotPresent pull with minikube image load path"

key-files:
  created:
    - scripts/rollout-zero-downtime.sh
    - .helm/values-local.yaml
  modified:
    - README.md
    - tests/test_helm_chart.py

key-decisions:
  - "Rollout script uses bash curl loop every 0.5s per RESEARCH Pattern 6"
  - "README documents both GHCR SHA and local iteration converge paths with CI manual boundary"
  - "values-local.yaml mirrors D-06 image coordinates separate from default values.yaml"

patterns-established:
  - "Pattern: Documentation contract tests assert README substrings for reviewer-ready commands"
  - "Pattern: Zero-downtime demo uses two-terminal workflow (rollout script + re-converge)"

requirements-completed: []

duration: 2min
completed: 2026-07-10
---

# Phase 5 Plan 03: Zero-Downtime Rollout Docs and Demo Summary

**Rollout readiness hammer script, local values override, and README minikube+werf converge docs with contract test coverage — pending live minikube verification**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-10T23:12:21Z
- **Completed:** 2026-07-10T23:14:31Z (checkpoint — human verify pending)
- **Tasks:** 1/3 complete (Task 2 blocked on minikube)
- **Files modified:** 4

## Accomplishments

- Added TDD contract tests for rollout script, values-local.yaml, and README Kubernetes section
- Created `scripts/rollout-zero-downtime.sh` — polls `/health/ready` via `minikube service model-serving --url` every 0.5s
- Created `.helm/values-local.yaml` with `basic-model-serving:local` and `pullPolicy: IfNotPresent`
- Added README **Kubernetes (minikube + werf)** section covering prerequisites, GHCR SHA converge, local iteration, service access, zero-downtime demo, and CI boundary
- 37 helm + deploy workflow contract tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Rollout script, values-local, and README contract tests** — `6f6e753` (test RED), `c732fb7` (feat GREEN)
2. **Task 2: Human verify werf converge and zero-downtime rollout on minikube** — *pending checkpoint*
3. **Task 3: Finalize contract tests and CI-quality gate** — *blocked on Task 2 approval*

## Files Created/Modified

- `scripts/rollout-zero-downtime.sh` — Bash curl loop hammering `/health/ready` during rolling updates
- `.helm/values-local.yaml` — Local image overrides for `minikube image load` converge path
- `README.md` — Kubernetes section with minikube sizing, werf converge commands, access URLs, rollout demo
- `tests/test_helm_chart.py` — `test_rollout_script_exists`, `test_readme_k8s_section`, `test_values_local_exists`

## Decisions Made

- Followed RESEARCH Pattern 6 shell translation for rollout script (0.5s poll interval, timestamp + HTTP code output)
- README uses single-line `werf converge` commands so contract tests match required substrings
- CI boundary stated as plain "CI does not deploy to Kubernetes" for test assertion compatibility

## Deviations from Plan

None - plan executed exactly as written through Task 1. Task 2 paused at checkpoint because minikube cluster is not running on this host.

## Issues Encountered

- **Minikube not available:** `minikube status` reports profile "minikube" not found. Live converge and zero-downtime rollout verification deferred to human checkpoint (Task 2).

## User Setup Required

None - no external service configuration required. Human must start minikube locally to complete Task 2 verification.

## Next Phase Readiness

- Automated artifacts ready for live verification: rollout script, values-local.yaml, README commands
- **Blocked:** K8S-05 human approval requires running minikube with steps in Task 2 checkpoint
- Task 3 (ruff + full pytest marker suite) runs after user types "approved"

## Checkpoint Status

**Type:** human-verify (blocking)
**Blocked by:** No running minikube cluster on execution host

### Verification steps for user

1. Start minikube: `minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=20g`
2. Build and load local image: `uv run docker-build` then `minikube image load basic-model-serving:local`
3. Initial deploy: `werf converge --env local --dev --without-images -f .helm/values-local.yaml --set image.repository=basic-model-serving --set image.tag=local --set image.pullPolicy=IfNotPresent`
4. Verify API: `minikube service model-serving --url` then `curl /health/ready` returns 200
5. Verify Grafana: `minikube service prometheus-stack-grafana -n basic-model-serving-local --url` — Model Serving Overview dashboard visible
6. Terminal 1: run `./scripts/rollout-zero-downtime.sh`
7. Terminal 2: rebuild (`uv run docker-build`), `minikube image load basic-model-serving:local`, re-run werf converge with same local flags
8. Confirm curl loop shows no sustained 503/000 streak

**Resume signal:** Type "approved" or describe issues found during minikube verification

## Self-Check: PASSED

- FOUND: scripts/rollout-zero-downtime.sh
- FOUND: .helm/values-local.yaml
- FOUND: README.md
- FOUND: tests/test_helm_chart.py
- FOUND: 6f6e753
- FOUND: c732fb7

---
*Phase: 05-kubernetes-deployment-via-werf*
*Completed: 2026-07-10 (checkpoint pending)*
