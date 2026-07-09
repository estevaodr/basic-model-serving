---
phase: 03-local-dev-stack-dashboards
reviewed: 2026-07-08T20:58:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - docker-compose.yml
  - monitoring/prometheus/prometheus.yml
  - monitoring/grafana/provisioning/datasources/prometheus.yml
  - monitoring/grafana/provisioning/dashboards/dashboard.yml
  - monitoring/grafana/provisioning/alerting/downtime.yml
  - monitoring/grafana/dashboards/model-serving-overview.json
  - .env.example
  - pyproject.toml
  - README.md
  - tests/test_compose_stack.py
  - tests/test_grafana_dashboard.py
  - tests/test_grafana_alerting.py
findings:
  critical: 0
  warning: 4
  info: 2
  total: 6
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-07-08T20:58:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 3 delivers a coherent local observability stack: compose wiring, Prometheus scrape config, Grafana dashboard/datasource/alert provisioning, and README quickstart. PromQL aligns with Phase 1 metric names (`request_count_total`, `request_duration_bucket`, `prediction_count_total`), health-gated scrape ordering is correct, and the Service Down alert semantics (`up{job="app"}` threshold `lt 1`, `for: 1m`) match the intended downtime contract.

No blockers were found. Four warnings cover brittle first-run compose behavior, misleading retention documentation, dashboard edge cases with zero traffic, and alert blind spots when query data is absent or Prometheus is unavailable.

## Warnings

### WR-01: Compose hard-requires `.env` file on host

**File:** `docker-compose.yml:6-7`
**Issue:** The `app` service declares `env_file: .env`. Docker Compose fails immediately if that file is missing (`env file ... not found`), even though `Settings` has sensible defaults and compose could inject vars via `environment:` or an optional env file. A reviewer who runs `docker compose up` before copying `.env.example` gets a hard failure unrelated to the image build step.
**Fix:** Document more prominently (already in README), or make first-run resilient by inlining defaults in compose `environment:` and treating `.env` as optional:

```yaml
services:
  app:
    environment:
      TORCH_NUM_THREADS: ${TORCH_NUM_THREADS:-2}
      MAX_UPLOAD_BYTES: ${MAX_UPLOAD_BYTES:-1048576}
      URL_TIMEOUT: ${URL_TIMEOUT:-5.0}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    env_file:
      - path: .env
        required: false
```

(Requires Compose file format 2.24+ for `required: false`.)

### WR-02: Prometheus retention documented in config file but enforced only via CLI flag

**File:** `monitoring/prometheus/prometheus.yml:4-5`, `docker-compose.yml:31`
**Issue:** MON-04 retention is enforced by `--storage.tsdb.retention.time=7d` on the compose command line. The config file only sets `external_labels.retention_policy: "7d"`, which is a label metadata field—not a retention directive. Operators or grep-based checks that read `prometheus.yml` alone can believe retention is configured in-file when it is not; removing the CLI flag silently drops the 7-day guarantee.
**Fix:** Add an explicit comment in `prometheus.yml` pointing to the compose CLI flag as the source of truth, and/or add a static test (or compose config assertion) that `docker-compose.yml` includes `--storage.tsdb.retention.time=7d`.

### WR-03: Error Rate panel returns NaN with zero traffic

**File:** `monitoring/grafana/dashboards/model-serving-overview.json:253`
**Issue:** The Error Rate stat uses `sum(rate(...5xx...)) / sum(rate(...total...))`. With no HTTP traffic both rates are zero, so PromQL division yields `NaN` and the stat shows "No data" rather than a meaningful `0%`. This is confusing on a fresh stack before curl traffic and differs from the intended "0% errors" reading.
**Fix:** Guard the denominator, e.g.:

```promql
sum(rate(request_count_total{status=~"5.."}[5m]))
/
clamp_min(sum(rate(request_count_total[5m])), 1e-9)
```

Or use `or vector(0)` / Grafana "No value → 0" field override for empty results.

### WR-04: Service Down alert uses `noDataState: OK`, creating false negatives

**File:** `monitoring/grafana/provisioning/alerting/downtime.yml:54`
**Issue:** `noDataState: OK` prevents the alert from firing when the `up{job="app"}` query returns no series (e.g., Prometheus down, scrape job misnamed, target removed from config). The rule title implies API unreachability, but monitoring outages or config drift fail silently instead of surfacing as Firing or Alerting. Boot grace is correctly handled elsewhere (`depends_on: service_healthy`), so `NoData → OK` is not needed to suppress startup noise.
**Fix:** Change to `noDataState: Alerting` (or `NoData`) so absent scrape data is treated as a failure mode, or add a companion alert on Prometheus/Grafana datasource health.

## Info

### IN-01: Grafana admin credentials hardcoded in compose

**File:** `docker-compose.yml:45-46`
**Issue:** `GF_SECURITY_ADMIN_USER` / `GF_SECURITY_ADMIN_PASSWORD` are set to `admin`/`admin` inline. Acceptable for local portfolio demo (auth explicitly out of scope), but worth noting if the stack is ever exposed beyond localhost.
**Fix:** No change required for Phase 3; for hardened deployments, load from env/secrets and document rotation.

### IN-02: `.env.example` Grafana vars are commented and unused by compose

**File:** `.env.example:7-9`, `docker-compose.yml:44-47`
**Issue:** Commented `GF_*` lines in `.env.example` suggest env-file configuration, but the Grafana service reads credentials from inline `environment:` only. Harmless but slightly inconsistent with the comment block.
**Fix:** Either add a comment that compose ignores these (credentials are in `docker-compose.yml`), or wire Grafana via `${GF_SECURITY_ADMIN_USER:-admin}` substitution from `.env`.

---

_Reviewed: 2026-07-08T20:58:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
