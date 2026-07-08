# Phase 3: Local Dev Stack & Dashboards - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-08
**Phase:** 3-Local Dev Stack & Dashboards
**Areas discussed:** Dashboard panels, Reviewer workflow, Downtime alert, Dev iteration loop

---

## Dashboard Panels

| Option | Description | Selected |
|--------|-------------|----------|
| Ops-standard set | Request rate, p50/p95 latency, error rate, prediction throughput, 4xx vs 5xx breakdown, service up/down, total predictions | ✓ |
| Reviewer-minimal | 5 panels only: request rate, p95 latency, error rate, prediction count, uptime | |
| Latency-focused | Heavy histogram/percentile panels (p50/p75/p95/p99) plus request rate and error rate | |

**User's choice:** Ops-standard set
**Notes:** Chose ops-standard for portfolio reviewer signal; 7 panels within MON-02 range.

### Latency display

| Option | Description | Selected |
|--------|-------------|----------|
| Percentile stat panels | Single-value p50/p95 numbers updating live | ✓ |
| Time-series graphs | Latency lines over time | |
| Both | Stat panels plus one latency-over-time graph | |

**User's choice:** Percentile stat panels

### Error breakdown

| Option | Description | Selected |
|--------|-------------|----------|
| By HTTP status code | 4xx vs 5xx panels using `request_count{status=...}` | ✓ |
| Single error-rate panel | One combined non-2xx percentage | |
| By endpoint path | Error rate split by `/predict` vs health/metrics | |

**User's choice:** By HTTP status code

### Dashboard organization

| Option | Description | Selected |
|--------|-------------|----------|
| Single named dashboard | "Model Serving Overview", auto-loaded as Grafana home | ✓ |
| Single dashboard, no home override | Reviewer navigates manually | |
| Two dashboards | Overview + Latency Detail split across boards | |

**User's choice:** Single named dashboard as Grafana home

---

## Reviewer Workflow

| Option | Description | Selected |
|--------|-------------|----------|
| `docker compose up` only | Standard command, documented in README | ✓ |
| `uv run compose-up` | Matches Phase 2 uv script pattern | |
| Both | Plain compose plus optional uv wrapper with pre-checks | |

**User's choice:** `docker compose up` only

### Traffic generation

| Option | Description | Selected |
|--------|-------------|----------|
| Manual curl in README | 2–3 curl commands to hit `/predict` | ✓ |
| Bundled traffic script | Automated sample requests after compose up | |
| Optional compose profile | `--profile demo` with one-shot traffic container | |

**User's choice:** Manual curl in README

### Port exposure

| Option | Description | Selected |
|--------|-------------|----------|
| Standard ports | API :8000, Grafana :3000, Prometheus :9090 | ✓ |
| Grafana on :3001 | Avoid :3000 conflicts | |
| Minimal expose | Grafana + API only; Prometheus internal | |

**User's choice:** Standard ports

### Grafana authentication

| Option | Description | Selected |
|--------|-------------|----------|
| Default admin credentials | admin/admin documented in README and `.env.example` | ✓ |
| Anonymous view-only | No login required | |
| Env-configured credentials | `GRAFANA_ADMIN_*` in `.env.example` | |

**User's choice:** Default admin credentials

---

## Downtime Alert

| Option | Description | Selected |
|--------|-------------|----------|
| Grafana unified alerting | Rule in provisioned config; fires in Grafana UI | ✓ |
| Prometheus alerting rules | `up{job="api"} == 0` in prometheus.yml | |
| Both layers | Prometheus rule + Grafana contact point | |

**User's choice:** Grafana unified alerting

### Alert demonstration

| Option | Description | Selected |
|--------|-------------|----------|
| README demo steps | Stop API → wait ~1 min → Firing → restart → Resolved | ✓ |
| Configured only | Rule exists, no README demo | |
| Automated compose test | Verify provisioned JSON only | |

**User's choice:** README demo steps

### Alert timing

| Option | Description | Selected |
|--------|-------------|----------|
| Fast (1 min) | Fire after ~1 minute of scrape failure | ✓ |
| Conservative (5 min) | Fire after 5 minutes | |
| Model-aware | Blackbox check on `/health/ready` | |

**User's choice:** Fast (1 min)

### Notification delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Grafana UI only | Visible in Alerting tab; no external channels | ✓ |
| Webhook placeholder | Optional localhost contact point | |
| Grafana UI + container logs | Alert state in logs too | |

**User's choice:** Grafana UI only

---

## Dev Iteration Loop

| Option | Description | Selected |
|--------|-------------|----------|
| Image-only | Rebuild with `uv run docker-build` then restart compose | ✓ |
| Bind-mount source | Mount `./app` for live code changes | |
| Optional override file | Default image; gitignored override for bind-mount | |

**User's choice:** Image-only

### Compose image source

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-built image reference | `image: basic-model-serving:local`; build prerequisite documented | ✓ |
| Compose builds on up | `build:` directive; `docker compose up --build` | |
| Both paths | Build in compose with cached fallback | |

**User's choice:** Pre-built image reference

### Monitoring config iteration

| Option | Description | Selected |
|--------|-------------|----------|
| Provisioned static files | Edit `monitoring/` → restart grafana/prometheus | ✓ |
| Bind-mount monitoring configs | Mount `./monitoring` for faster restart cycle | |
| Grafana UI first, export later | Build in UI then export JSON | |

**User's choice:** Provisioned static files

### uv compose scripts

| Option | Description | Selected |
|--------|-------------|----------|
| No uv compose scripts | Plain `docker compose up/down` only | ✓ |
| `uv run compose-smoke` | Stack health + predict + datasource check | |
| `uv run compose-up` + smoke | Full wrapper scripts | |

**User's choice:** No uv compose scripts

---

## Claude's Discretion

- Prometheus scrape interval and compose healthcheck tuning for startup grace
- Grafana admin password literal and env wiring
- Dashboard JSON visual styling within locked panel set
- Alert rule PromQL/query expression details
- Exact `monitoring/` file layout and compose service/volume names

## Deferred Ideas

- SLO/latency alert demo → Phase 6 (DOC-06)
- `uv run compose-*` wrapper scripts → rejected for Phase 3
- Bind-mount hot reload → rejected; image rebuild workflow retained
- Bundled traffic generator → rejected; manual curl chosen
- Anonymous Grafana → rejected; default credentials chosen
- Prediction-confidence histogram → v2 OBS-01
