---
quick_id: 260709-n8y
status: complete
date: 2026-07-09
description: Split CI into ci.yml (lint+test) and deploy.yml (docker build+push)
---

# Quick Task 260709-n8y Summary

## Outcome

Split the monolithic CI workflow into two files per locked CONTEXT decisions:

- **`.github/workflows/ci.yml`** — lint + test on **PRs to `main` only**; `contents: read`
- **`.github/workflows/deploy.yml`** — Docker build + GHCR push on **`main` push only**; `packages: write`

Supersedes Phase 4 D-11 (single job). PRs no longer run Docker builds. Direct `main` pushes skip lint/test (PR merge is the gate).

## Resume (2026-07-09)

Removed `push` trigger from `ci.yml` per user request — lint/test no longer runs on direct main pushes.

## Tasks Completed

| Task | Status | Notes |
|------|--------|-------|
| 1. Split workflows | ✓ | deploy.yml created; docker steps removed from ci.yml |
| 2. Contract tests | ✓ | test_deploy_workflow.py added; D-11 replaced |
| 3. README | ✓ | Two-workflow docs with PR vs main table |

## Verification

- `260709-n8y-VERIFICATION.md`: 6/6 passed
- `pytest tests/test_ci_workflow.py tests/test_deploy_workflow.py`: 21 passed

## Decisions Applied

- Deploy trigger: main push only (no PR, no workflow_run)
- PR behavior: ci.yml only — no Docker on PRs
- Permissions split: ci read-only; deploy packages:write
