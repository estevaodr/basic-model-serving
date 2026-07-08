---
status: testing
phase: 01-core-inference-api
source:
  - 01-01-SUMMARY.md
  - 01-02-SUMMARY.md
  - 01-03-SUMMARY.md
  - 01-04-SUMMARY.md
started: 2026-07-07T20:48:00Z
updated: 2026-07-07T20:54:00Z
---

## Current Test

number: 2
name: Liveness Probe
expected: |
  GET /health/live returns 200 with {"status":"alive"} while server is running
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: Fresh server start succeeds; model loads; /health/live returns alive
result: pass

### 2. Liveness Probe
expected: GET /health/live returns 200 with {"status":"alive"} while server is running
result: [pending]

### 3. Readiness Probe
expected: GET /health/ready returns 200 with {"status":"ready"} after model finishes loading (not 503)
result: [pending]

### 4. Image Upload Prediction
expected: POST a JPEG file to /predict (multipart form field "file") returns 200 with exactly 5 predictions, each with a label string and confidence between 0 and 1
result: [pending]

### 5. Image URL Prediction
expected: POST JSON {"image_url":"https://upload.wikimedia.org/wikipedia/commons/3/3a/Cat03.jpg"} to /predict returns 200 with exactly 5 predictions with labels and confidence scores
result: [pending]

### 6. OpenAPI Documentation
expected: Browse http://localhost:8000/docs — /predict endpoint is documented with both upload and URL input modes and example payloads
result: [pending]

### 7. Prometheus Metrics
expected: GET /metrics returns Prometheus text with request_count, request_duration, and prediction_count metric names
result: [pending]

### 8. Request ID Header
expected: Any API response (e.g. GET /health/live) includes an X-Request-ID header with a UUID value
result: [pending]

### 9. Invalid Image Error
expected: POST a non-image file (e.g. text file) as upload to /predict returns 400 with structured JSON {"error":"...", "message":"..."} — not a raw 500 stack trace
result: [pending]

### 10. SSRF URL Rejection
expected: POST JSON {"image_url":"http://169.254.169.254/latest/meta-data/"} to /predict returns 400 with structured error (unsafe_url or similar) — request is blocked
result: [pending]

## Summary

total: 10
passed: 1
issues: 0
pending: 9
skipped: 0
blocked: 0

## Gaps

[none yet]
