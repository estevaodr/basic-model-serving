---
phase: 05-kubernetes-deployment-via-werf
plan: 02
subsystem: infra
tags: [helm, kube-prometheus-stack, servicemonitor, grafana, prometheus, werf, minikube]

requires:
  - phase: 05-kubernetes-deployment-via-werf
    plan: 01
    provides: App-only .helm chart with Deployment, Service, ConfigMap, and contract test baseline
provides:
  - kube-prometheus-stack ~87.12.0 bundled as Helm subchart dependency
  - ServiceMonitor with release {{ .Release.Name }} for /metrics scrape
  - Grafana dashboard ConfigMap provisioning Phase 3 Model Serving Overview JSON
  - Chart.lock pinned subchart versions; .helm/charts/ gitignored
affects:
  - 05-03 (werf converge verification and README k8s section)

tech-stack:
  added: [kube-prometheus-stack]
  patterns:
    - Helm subchart dependency with nested values for prometheus/grafana config
    - ServiceMonitor release label tied to .Release.Name (not hardcoded prometheus-stack)
    - Grafana sidecar dashboard provisioning via labeled ConfigMap + .Files.Get

key-files:
  created:
    - .helm/Chart.lock
    - .helm/templates/servicemonitor.yaml
    - .helm/templates/grafana-dashboard.yaml
    - .helm/dashboards/model-serving-overview.json
  modified:
    - .helm/Chart.yaml
    - .helm/values.yaml
    - .gitignore
    - tests/test_helm_chart.py

key-decisions:
  - "kube-prometheus-stack fullnameOverride prometheus-stack for stable minikube service names"
  - "ServiceMonitor release label uses {{ .Release.Name }} per D-03, not hardcoded prometheus-stack"
  - "Phase 3 dashboard JSON copied verbatim into .helm/dashboards/ for .Files.Get embedding"

patterns-established:
  - "Pattern: TDD monitoring contract tests before Chart.yaml dependency and templates"
  - "Pattern: Chart.lock committed, vendored .helm/charts/ gitignored"

requirements-completed: [K8S-06]

duration: 2min
completed: 2026-07-10
---

# Phase 5 Plan 02: kube-prometheus-stack Monitoring Bundle Summary

**Single werf chart bundles kube-prometheus-stack with ServiceMonitor scrape of /metrics and Grafana sidecar dashboard provisioning from Phase 3 JSON**

## Performance

- **Duration:** 2 min
- **Started:** 2026-07-10T23:09:00Z
- **Completed:** 2026-07-10T23:11:07Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Extended `tests/test_helm_chart.py` with 10 monitoring contract tests covering D-01 through D-04 and D-10
- Bundled kube-prometheus-stack ~87.12.5 as Helm dependency with 7d retention, NodePort Grafana, and dashboard sidecar
- Created ServiceMonitor (`release: {{ .Release.Name }}`, `/metrics` on port http) and Grafana dashboard ConfigMap from Phase 3 JSON
- Full stack `helm template` renders ServiceMonitor and dashboard ConfigMap; 23 helm tests pass; CI marker suite 76 passed

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend contract tests for monitoring templates and subchart** - `dc2cb25` (test)
2. **Task 2: Bundle kube-prometheus-stack and implement ServiceMonitor + dashboard** - `00571cd` (feat)
3. **Task 3: Validate full chart render and subchart values** - `5093328` (test)

## Files Created/Modified

- `.helm/Chart.yaml` - Added kube-prometheus-stack ~87.12.0 dependency from prometheus-community repo
- `.helm/Chart.lock` - Pinned kube-prometheus-stack 87.12.5 digest
- `.helm/values.yaml` - Subchart values: 7d retention, NodePort Grafana, sidecar dashboards, fullnameOverride
- `.helm/templates/servicemonitor.yaml` - Prometheus Operator scrape config for model-serving /metrics
- `.helm/templates/grafana-dashboard.yaml` - ConfigMap with grafana_dashboard label for sidecar import
- `.helm/dashboards/model-serving-overview.json` - Exact copy of Phase 3 dashboard JSON
- `.gitignore` - Added `.helm/charts/` to ignore vendored subchart tgz
- `tests/test_helm_chart.py` - 10 new monitoring + render validation tests (23 total)

## Decisions Made

- Used `fullnameOverride: prometheus-stack` for stable Grafana service name `prometheus-stack-grafana` on minikube
- ServiceMonitor `release` label templates `.Release.Name` to match werf release naming (e.g. `basic-model-serving-local`)
- Dashboard embedded via `.Files.Get` from chart-local copy, not symlink to monitoring/ source

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for 05-03: werf converge verification, README k8s section, and rollout demo script
- `helm template` and contract tests green; cluster deploy (`werf converge`) not yet verified in this plan

## Self-Check: PASSED

- FOUND: .helm/Chart.lock
- FOUND: .helm/templates/servicemonitor.yaml
- FOUND: .helm/templates/grafana-dashboard.yaml
- FOUND: .helm/dashboards/model-serving-overview.json
- FOUND: dc2cb25
- FOUND: 00571cd
- FOUND: 5093328

---
*Phase: 05-kubernetes-deployment-via-werf*
*Completed: 2026-07-10*
