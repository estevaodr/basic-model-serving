---
quick_id: 260710-fix-ci-helm-repo
status: complete
verified: 2026-07-11T00:04:00Z
---

# Quick Task: Fix CI helm repo add

Follow-up to `260710-fix-ci-helm-deps`. `helm dependency build` on a fresh GitHub Actions runner requires the chart repository to be registered first.

## Fix
```yaml
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm dependency build .helm
```

## Verification
- Reproduced error without repo; passes after repo add
- Helm render tests pass
