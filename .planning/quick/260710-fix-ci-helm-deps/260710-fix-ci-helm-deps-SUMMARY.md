---
quick_id: 260710-fix-ci-helm-deps
status: complete
verified: 2026-07-11T00:01:00Z
---

# Quick Task: Fix CI helm template test failures

**CI on PR #8 failed** because `helm template` tests require vendored `kube-prometheus-stack` charts, but `.helm/charts/` is gitignored and CI never ran `helm dependency build`.

## Fix
- Added `azure/setup-helm@v4` to `.github/workflows/ci.yml`
- Added `helm dependency build .helm` step before pytest

## Verification
- Simulated clean checkout: removed `.helm/charts/`, ran `helm dependency build`, helm render tests pass
- Full suite: 79 passed
