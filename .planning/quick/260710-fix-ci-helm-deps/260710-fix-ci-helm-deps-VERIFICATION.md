---
status: passed
verified: 2026-07-11T00:01:00Z
---

# Verification: Fix CI helm deps

- [x] Root cause confirmed: missing `kube-prometheus-stack` in `.helm/charts/` on CI
- [x] `helm dependency build .helm` restores charts from `Chart.lock`
- [x] `pytest -m "not docker and not compose"` — 79 passed
