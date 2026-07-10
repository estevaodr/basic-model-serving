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
  - scripts/k8s-env.sh namespace and service name defaults for minikube access
  - .helm/values-local.yaml local image tag overrides for minikube image load (D-06)
  - README Kubernetes section with GHCR SHA and local converge paths (D-05, D-16, D-20)
  - Extended documentation contract tests in tests/test_helm_chart.py
affects: []

tech-stack:
  added: []
  patterns:
    - "TDD RED/GREEN for README and script contract tests before implementation"
    - "minikube service with -n basic-model-serving-local drives rollout readiness hammer script"
    - "values-local.yaml pullPolicy Never for minikube-loaded local tags"

key-files:
  created:
    - scripts/rollout-zero-downtime.sh
    - scripts/k8s-env.sh
    - .helm/values-local.yaml
  modified:
    - README.md
    - tests/test_helm_chart.py
    - scripts/docker.py
    - pyproject.toml

key-decisions:
  - "Rollout script uses bash curl loop every 0.5s per RESEARCH Pattern 6"
  - "README documents both GHCR SHA and local iteration converge paths with CI manual boundary"
  - "Grafana on k8s uses kube-prometheus-stack default admin/prom-operator; compose stack stays admin/admin"
  - "Bundled subchart Grafana Service is basic-model-serving-local-grafana, not prometheus-stack-grafana"

patterns-established:
  - "Pattern: Documentation contract tests assert README substrings for reviewer-ready commands"
  - "Pattern: Zero-downtime demo uses two-terminal workflow (rollout script + re-converge)"
  - "Pattern: scripts/k8s-env.sh centralizes werf namespace and service names for minikube"

requirements-completed: [K8S-05]

duration: 45min
completed: 2026-07-10
---

# Phase 5 Plan 03: Zero-Downtime Rollout Docs and Demo Summary

**Rollout readiness hammer script, local values override, README minikube+werf converge docs, and human-verified live deploy on minikube**

## Performance

- **Duration:** ~45 min (including human verification)
- **Started:** 2026-07-10T23:12:21Z
- **Completed:** 2026-07-10T23:51:00Z
- **Tasks:** 3/3 complete
- **Files modified:** 8

## Accomplishments

- Added TDD contract tests for rollout script, values-local.yaml, and README Kubernetes section
- Created `scripts/rollout-zero-downtime.sh` — polls `/health/ready` via `minikube service` with `-n basic-model-serving-local`
- Created `scripts/k8s-env.sh` — namespace and Grafana/API service name defaults
- Created `.helm/values-local.yaml` with `basic-model-serving:local` and `pullPolicy: Never`
- Added `docker-build-minikube` / `docker-load-minikube` helpers with correct minikube image verification
- Added README **Kubernetes (minikube + werf)** section with prerequisites, converge paths, service access, Grafana login, rollout demo
- **Human verified:** API `/health/ready` and `POST /predict` return 200 via NodePort; user approved checkpoint

## Task Commits

1. **Task 1: Rollout script, values-local, and README contract tests** — `6f6e753` (test RED), `c732fb7` (feat GREEN)
2. **Task 2: Human verify werf converge and zero-downtime rollout on minikube** — approved 2026-07-10
3. **Task 3: Finalize contract tests and CI-quality gate** — ruff + 79 pytest pass (post-approval fixes uncommitted)

## Files Created/Modified

- `scripts/rollout-zero-downtime.sh` — Bash curl loop hammering `/health/ready` during rolling updates
- `scripts/k8s-env.sh` — `K8S_NAMESPACE`, `K8S_API_SERVICE`, `K8S_GRAFANA_SERVICE` for minikube
- `.helm/values-local.yaml` — Local image overrides for `minikube image load` converge path
- `README.md` — Kubernetes section with namespace, werf `--values`, Grafana credentials, access URLs
- `scripts/docker.py` — `load_minikube()`, `build_and_load_minikube()`, fixed image name verification
- `pyproject.toml` — `docker-load-minikube`, `docker-build-minikube` scripts
- `tests/test_helm_chart.py` — rollout, README, values-local contract tests

## Decisions Made

- Followed RESEARCH Pattern 6 shell translation for rollout script (0.5s poll interval)
- `werf converge` uses `--values .helm/values-local.yaml` (not Helm `-f`)
- Grafana bundled under werf release → Service `basic-model-serving-local-grafana`
- kube-prometheus-stack default credentials: `admin` / `prom-operator`

## Deviations from Plan

- **Grafana service name:** Plan assumed `prometheus-stack-grafana` via `fullnameOverride`; actual bundled subchart Service is `{release}-grafana`. Documented and fixed in README/scripts.
- **Namespace:** `minikube service` without `-n` fails; all docs/scripts now pass `-n basic-model-serving-local`.
- **Local image pull:** `pullPolicy: Never` (not `IfNotPresent`) to prevent Docker Hub pull for local-only tags.

## Issues Encountered

- Initial execution host had no minikube — deferred to human checkpoint (resolved by user on laptop).
- `minikube service model-serving` defaults to `default` namespace — fixed with `k8s-env.sh`.

## User Setup Required

None.

## Next Phase Readiness

- Phase 5 complete — all K8S-01 through K8S-06 and PERF-04 artifacts delivered
- Phase 6 (Polish, Differentiators & README) unblocked

## Checkpoint Status

**Type:** human-verify
**Status:** APPROVED (2026-07-10)

User confirmed:
- `/health/ready` stable (10 sequential curls)
- `POST /predict` returns 200 via `http://192.168.49.2:32034`

## Self-Check: PASSED

- FOUND: scripts/rollout-zero-downtime.sh
- FOUND: scripts/k8s-env.sh
- FOUND: .helm/values-local.yaml
- FOUND: README.md
- FOUND: tests/test_helm_chart.py
- pytest: 79 passed
- ruff: check passed

---
*Phase: 05-kubernetes-deployment-via-werf*
*Completed: 2026-07-10*
