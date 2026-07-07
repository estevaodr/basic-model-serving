---
phase: 01-core-inference-api
fixed_at: 2026-07-07T20:45:00Z
review_path: .planning/phases/01-core-inference-api/01-REVIEW.md
iteration: 2
findings_in_scope: 2
fixed: 1
already_fixed: 1
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-07-07T20:45:00Z
**Source review:** `.planning/phases/01-core-inference-api/01-REVIEW.md`
**Iteration:** 2

**Summary:**
- Findings in scope: 2 (Info only)
- Fixed: 1
- Already fixed: 1
- Skipped: 0

## Fixed Issues

### IN-01: Misleading torch install comment in requirements.txt

**Files modified:** `requirements.txt`
**Commit:** 82d3f82
**Applied fix:** Updated header comment to document the two-step install procedure: install torch/torchvision from the PyTorch CPU index first, then install remaining packages from PyPI via `pip install -r requirements.txt`.

## Already Fixed Issues

### IN-02: Health probe 503 body differs from API error contract

**Files modified:** `app/api/routes/health.py`
**Commit:** 5d38cf9 (iteration 1, WR-02)
**Status:** already_fixed
**Verified:** `/health/ready` returns `ErrorDetail(error="not_ready", message="Model is not loaded yet", request_id=...)` on 503, consistent with the structured error contract.

## Prior Iteration (1) — Critical & Warning Fixes

All six critical/warning findings were fixed in iteration 1:

| Finding | Commit | Summary |
|---------|--------|---------|
| CR-01 | 157b92a | Stream-read multipart uploads with early size cutoff |
| WR-01 | 9bf2b5f | Pin DNS resolution to prevent rebinding TOCTOU |
| WR-02 | 5d38cf9 | Use `ErrorDetail` shape for 503 `not_ready` responses |
| WR-03 | 00641b4 / 84cc74c | Catch Pillow decode errors as `invalid_image` client errors |
| WR-04 | d3005b8 | Cap JSON request body size with streaming reader |
| WR-05 | 84cc74c | Narrow `ValueError` catch to `AddressValueError` only |

---

_Fixed: 2026-07-07T20:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
