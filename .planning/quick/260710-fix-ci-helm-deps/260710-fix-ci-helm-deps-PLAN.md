# Quick Task: Fix CI helm template test failures on PR #8

## Problem
CI `test` job fails on `tests/test_helm_chart.py` helm template tests because `.helm/charts/` is gitignored and CI never runs `helm dependency build`.

## Fix
1. Add `azure/setup-helm@v4` to `.github/workflows/ci.yml`
2. Run `helm dependency build .helm` before pytest
3. Verify locally without pre-existing charts directory

## Acceptance
- `helm dependency build .helm` succeeds on clean checkout
- `pytest -m "not docker and not compose"` passes including helm render tests
