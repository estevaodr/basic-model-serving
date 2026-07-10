---
phase: 05-kubernetes-deployment-via-werf
plan: 01
subsystem: infra
tags: [werf, helm, kubernetes, minikube, nodeport, configmap, probes]

requires:
  - phase: 04-ci-cd-pipeline
    provides: GHCR image coordinates and deploy-only CI boundary
  - phase: 02-containerization
    provides: Dockerfile health probes and four env vars for ConfigMap
provides:
  - werf.yaml deploy-only project config with optional image build
  - App-only .helm chart (Deployment, Service, ConfigMap)
  - Static contract tests for Helm/werf chart surface
affects:
  - 05-02 (kube-prometheus-stack subchart extension)
  - 05-03 (werf converge verification)

tech-stack:
  added: [werf, helm]
  patterns:
    - Deploy-only image via Values.image.repository/tag + --without-images
    - NodePort Service for minikube service access
    - ConfigMap envFrom for pydantic-settings parity with compose

key-files:
  created:
    - werf.yaml
    - .helm/Chart.yaml
    - .helm/values.yaml
    - .helm/templates/deployment.yaml
    - .helm/templates/service.yaml
    - .helm/templates/configmap.yaml
    - tests/test_helm_chart.py
  modified: []

key-decisions:
  - "App-only chart in 05-01; kube-prometheus-stack deferred to 05-02 per plan split"
  - "Image reference uses plain Helm values, not global.werf.images (D-05 Anti-Pattern 3)"
  - "startupProbe failureThreshold 24 × periodSeconds 5 = 120s model-load budget"

patterns-established:
  - "Pattern: TDD contract tests with template file assertions + helm template render checks"
  - "Pattern: 2 replicas + maxUnavailable 0 + maxSurge 1 zero-downtime baseline"

requirements-completed: [K8S-01, K8S-02, K8S-03, K8S-04, K8S-06, PERF-04]

duration: 2min
completed: 2026-07-10
---

# Phase 5 Plan 01: App Helm Chart and werf.yaml Summary

**Deploy-only werf config and app-only Helm chart with 2-replica probes, NodePort service, and ConfigMap env injection — TDD contract tests green**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-10T23:06:08Z
- **Completed:** 2026-07-10T23:08:13Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Created `tests/test_helm_chart.py` with 13 contract tests covering D-05 through D-18 decisions
- Implemented `werf.yaml` and `.helm/` app chart (Deployment, Service, ConfigMap) satisfying K8S-01–K8S-04, K8S-06, PERF-04
- Verified CI marker filter (`pytest -m "not docker and not compose"`) passes with new tests; helm template renders GHCR and local image sets

## Task Commits

Each task was committed atomically:

1. **Task 1: Failing Helm/werf app chart contract tests** - `564d5c1` (test)
2. **Task 2: Implement werf.yaml and app Helm chart templates** - `502f2d3` (feat)
3. **Task 3: Verify helm render output and lint suite compatibility** - `f59dcc2` (test)

## Files Created/Modified

- `werf.yaml` - werf project config with optional `image: api` build block (D-07)
- `.helm/Chart.yaml` - App-only chart metadata, no monitoring dependency yet
- `.helm/values.yaml` - Default GHCR image repository/tag/pullPolicy
- `.helm/templates/deployment.yaml` - 2-replica Deployment with probes, resources, rolling strategy
- `.helm/templates/service.yaml` - NodePort Service `model-serving` on port 8000
- `.helm/templates/configmap.yaml` - Four env vars including `TORCH_NUM_THREADS=2`
- `tests/test_helm_chart.py` - Static contract suite for chart and werf surface

## Decisions Made

- Followed plan split: monitoring subchart intentionally omitted (05-02 scope)
- Used template file content assertions plus `helm template` render checks for dual verification
- Preserved deploy-only image pattern — no `global.werf.images` in templates

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- App chart ready for 05-02 to add kube-prometheus-stack dependency, ServiceMonitor, and Grafana dashboard provisioning
- Default converge path documented in plan interfaces: `werf converge --env local --dev --without-images --set image.tag=<sha>`

## Self-Check: PASSED

- FOUND: werf.yaml
- FOUND: .helm/Chart.yaml
- FOUND: .helm/values.yaml
- FOUND: .helm/templates/deployment.yaml
- FOUND: .helm/templates/service.yaml
- FOUND: .helm/templates/configmap.yaml
- FOUND: tests/test_helm_chart.py
- FOUND: 564d5c1
- FOUND: 502f2d3
- FOUND: f59dcc2

---
*Phase: 05-kubernetes-deployment-via-werf*
*Completed: 2026-07-10*
