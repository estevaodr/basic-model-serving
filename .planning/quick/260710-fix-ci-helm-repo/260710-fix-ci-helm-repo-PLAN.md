# Quick Task: Fix CI helm repo add before dependency build

## Problem
After adding `helm dependency build`, CI still fails on fresh runners:
```
Error: no repository definition for https://prometheus-community.github.io/helm-charts
```

## Fix
Add `helm repo add prometheus-community` before `helm dependency build` in ci.yml.

## Acceptance
- Simulated fresh helm (no repos): repo add + dependency build + helm template tests pass
