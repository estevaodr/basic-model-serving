# Phase 3: Local Dev Stack & Dashboards - Research

**Researched:** 2026-07-08
**Domain:** docker-compose observability stack (Prometheus + Grafana provisioning-as-code)
**Confidence:** HIGH

## Summary

Phase 3 wires the existing `basic-model-serving:local` image (Phase 2) into a three-service compose stack with Prometheus and Grafana. No new application instrumentation is required — all dashboard PromQL derives from Phase 1 metrics in `app/metrics/prometheus.py`: `request_count` (Counter → exported as `request_count_total`), `request_duration` (Histogram → `request_duration_bucket`), and `prediction_count` (Counter → `prediction_count_total`). Labels use route template paths (e.g., `path="/predict"`), not raw URLs.

The deliverable is infrastructure-as-code under `monitoring/` plus a root `docker-compose.yml`. Prometheus scrapes `http://app:8000/metrics` on the compose network; Grafana gets a provisioned Prometheus datasource and a file-provisioned **Model Serving Overview** dashboard with seven ops-standard panels (request rate, p50/p95 stat panels, error rate, prediction throughput, 4xx/5xx breakdown, service up, total predictions). MON-04 retention is explicit **7d** — prefer the config-file `storage.tsdb.retention.time` field in `prometheus.yml` (current Prometheus direction) over the deprecated CLI flag [CITED: prometheus.io command-line docs, PR #17026]. MON-03 downtime alerting uses **Grafana unified alerting** provisioned in `monitoring/grafana/provisioning/alerting/`, querying Prometheus `up{job="..."}` with `for: 1m`, UI-only (no contact points).

Home dashboard (D-04) has no native org-preferences YAML provisioner in Grafana OSS [CITED: Grafana preferences API docs]. The file-based approach is `GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH` pointing at the same dashboard JSON bind-mounted into the container [CITED: Grafana configuration — `default_home_dashboard_path`]. Set a fixed `uid` in the dashboard JSON (e.g., `model-serving-overview`) for stable linking.

Startup ordering must prevent false-positive downtime alerts: `app` healthcheck on `/health/ready` (reuse Dockerfile semantics, ~45–60s start_period), `prometheus` with `depends_on: app: condition: service_healthy`, `grafana` depending on `prometheus`. With `scrape_interval: 15s` and alert `for: 1m`, normal boot stays below the alert threshold.

**Primary recommendation:** Add `docker-compose.yml` + `monitoring/{prometheus,grafana}/` static provisioning; pin official `prom/prometheus` and `grafana/grafana` images; document `uv run docker-build` → `docker compose up` → manual curl traffic → Grafana `:3000` in README.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Dashboard Panels
- **D-01:** Use an **ops-standard panel set** (7 panels): request rate, p50 latency, p95 latency, error rate, prediction throughput, 4xx vs 5xx breakdown, service up/down, total predictions — aligned with portfolio reviewer expectations from FEATURES.md table stakes.
- **D-02:** Display latency as **percentile stat panels** (single-value p50/p95 numbers updating live), not time-series graphs — clearest at a glance for reviewers.
- **D-03:** Break down errors **by HTTP status code** (4xx vs 5xx panels) using existing `request_count{status=...}` labels from Phase 1 instrumentation.
- **D-04:** Single dashboard named **"Model Serving Overview"**, provisioned as Grafana **home dashboard** — reviewer lands on it immediately after login.

#### Reviewer Workflow
- **D-05:** Primary entry command is plain **`docker compose up`** — no `uv run compose-up` wrapper. Documented as the quickstart path in README.
- **D-06:** Live dashboard data comes from **manual curl commands** documented in README (2–3 example `POST /predict` calls) — no bundled traffic generator script or compose profile.
- **D-07:** Expose **standard ports** on the host: API `:8000`, Grafana `:3000`, Prometheus `:9090`. Document in README quickstart table.
- **D-08:** Grafana uses **default admin credentials** (e.g., admin/admin) documented in README and `.env.example` — acceptable login friction for a local portfolio demo.

#### Downtime Alert
- **D-09:** Alert rule lives in **Grafana unified alerting** (provisioned with dashboard/stack config), not Prometheus alerting rules — simpler for local demo; Prometheus rules deferred unless needed for Phase 5 K8s stack.
- **D-10:** Include **README demo steps** for the alert: stop API container → wait ~1 min → alert shows **Firing** in Grafana → restart → **Resolved**. Phase 6 (DOC-06) handles the separate SLO/latency alert demo.
- **D-11:** Fire after **~1 minute** of scrape/API failure — fast enough for live demo; account for model startup in compose `depends_on`/healthcheck so alert does not fire during normal boot.
- **D-12:** Notifications are **Grafana UI only** — no email, Slack, or webhook contact points for the local stack.

#### Dev Iteration Loop
- **D-13:** **Image-only** API iteration — compose runs the built `basic-model-serving:local` image; code changes require `uv run docker-build` then `docker compose restart api` (or down/up). No bind-mount source override.
- **D-14:** Compose references **pre-built image** (`image: basic-model-serving:local`), not a `build:` directive — prerequisite step `uv run docker-build` documented before first `docker compose up`.
- **D-15:** Monitoring config is **provisioned static files** in `monitoring/` (per ARCHITECTURE.md layout) — edit JSON/YAML → `docker compose restart grafana|prometheus` to pick up changes. No Grafana UI-first export workflow.
- **D-16:** **No new `uv run` compose scripts** in Phase 3 — keep Phase 2's `docker-build|docker-run|docker-smoke` for single-container workflow; compose is plain Docker CLI.

#### Carried Forward (not re-discussed — locked from prior phases, research, REQUIREMENTS.md)
- Phase 1 metrics at `/metrics`: `request_count`, `request_duration` (histogram, buckets tuned around 100ms SLO), `prediction_count` — no new instrumentation in Phase 3 unless a panel truly requires it
- Phase 2 image tag `basic-model-serving:local` and `uv run docker-build` prerequisite workflow
- MON-05: Grafana datasource + dashboard provisioned as code on startup — no manual UI clicking
- MON-04: Prometheus `--storage.tsdb.retention.time=7d` (or equivalent) — explicit, not default
- CONT-04: docker-compose runs API + Prometheus + Grafana together
- Separate Prometheus scrape config for compose (`app:8000` container DNS) vs K8s Service DNS — per ARCHITECTURE.md; Phase 3 uses compose variant only
- Phase 5 open decision (kube-prometheus-stack vs hand-rolled K8s manifests) does not affect Phase 3 compose stack

### Claude's Discretion

- Exact Prometheus `scrape_interval` and compose healthcheck/`depends_on` tuning to prevent false-positive downtime alerts during model load
- Grafana admin password literal and whether to wire via compose `environment:` or `.env`
- Dashboard JSON visual styling (colors, thresholds, panel grid layout) within the locked ops-standard panel set
- Alert rule query expression (Prometheus `up` metric vs explicit health endpoint check)
- `monitoring/` subdirectory structure details (exact filenames under `monitoring/prometheus/` and `monitoring/grafana/`)
- Compose service names, network name, and volume strategy for Prometheus TSDB persistence across restarts

### Deferred Ideas (OUT OF SCOPE)

- **SLO/latency alert demo** — Phase 6 (DOC-06); Phase 3 covers downtime only (MON-03)
- **`uv run compose-up` / `compose-smoke` scripts** — user rejected; plain Docker CLI for compose
- **Bind-mount API source for hot reload** — user rejected; rebuild image workflow retained
- **Bundled traffic generator** (script or compose profile) — user chose manual curl in README
- **Anonymous Grafana access** — user chose default admin credentials instead
- **Prediction-confidence histogram panel** — v2 OBS-01; not in Phase 3 panel set
- **kube-prometheus-stack for K8s** — Phase 5 open decision; does not block Phase 3 hand-rolled compose stack
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CONT-04 | `docker-compose.yml` runs the API, Prometheus, and Grafana together for local development | Three-service compose with shared network; API uses pre-built `basic-model-serving:local`; ports 8000/9090/3000; no `build:` in compose |
| MON-02 | Grafana dashboard displays 5-7 key metrics with real data | Seven-panel **Model Serving Overview** with PromQL on Phase 1 metrics; stat panels for p50/p95; manual curl traffic in README |
| MON-03 | Alert is configured for service downtime | Grafana unified alerting file in `provisioning/alerting/`; `up == 0` for 1m; README stop/restart demo steps |
| MON-04 | Metrics are retained for 7+ days | Explicit `storage.tsdb.retention.time: 7d` in `prometheus.yml` + named volume for TSDB persistence |
| MON-05 | Grafana datasource and dashboard are provisioned as code | `provisioning/datasources/*.yml`, `provisioning/dashboards/*.yml` + dashboard JSON, `provisioning/alerting/*.yml` |
</phase_requirements>

## Project Constraints (from .cursor/rules/)

- **GSD workflow:** Phase implementation should run through GSD execute-phase workflow; do not bypass planning artifacts [CITED: `.cursor/rules/gsd.mdc`].
- **Local dev inner loop:** docker-compose is the chosen fast iteration path (not Skaffold/Tilt/minikube for day-to-day API + dashboard work) [CITED: `.cursor/rules/gsd.mdc`, PROJECT.md].
- **Stack fixed:** Python 3.12, FastAPI, Prometheus, Grafana — no alternative observability stack for compose phase.
- **Phase 2 scripts preserved:** Keep `uv run docker-build|docker-run|docker-smoke`; compose uses plain `docker compose` CLI only (D-16).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTTP inference + `/metrics` export | API / Backend (existing FastAPI app) | — | App owns metric emission; unchanged in Phase 3 |
| Metric scrape + TSDB retention | Observability infra (Prometheus container) | — | Pull-based scrape; retention is Prometheus config, not app code |
| Dashboard visualization + alerting | Observability infra (Grafana container) | — | Query-time read from Prometheus; unified alerting lives in Grafana |
| Compose orchestration + networking | Developer host / container runtime | — | `docker-compose.yml` wires DNS (`app`, `prometheus`, `grafana`) |
| Monitoring config as code | Repo `monitoring/` (infra config) | — | Static YAML/JSON bind-mounted; not baked into app image |
| Local image build prerequisite | Developer host (`uv run docker-build`) | — | Phase 2 workflow; compose consumes artifact, does not build |
| Reviewer quickstart documentation | Documentation (README) | — | Plain `docker compose up`, port table, curl examples, alert demo |

## Standard Stack

### Core

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| `basic-model-serving:local` | Phase 2 image | API service in compose | Locked D-14; pre-built, non-root, `/health/ready` + `/metrics` |
| `prom/prometheus` | v3.3.0 (pin tag) | Metrics scrape + 7d TSDB | Official image; static scrape config for compose [CITED: prometheus.io installation docs] |
| `grafana/grafana` | 11.6.x (pin tag) | Dashboards + unified alerting | Official image; file provisioning for datasources/dashboards/alerts [VERIFIED: Context7 `/grafana/grafana`] |
| Docker Compose | v2+ (v5.3.1 local) | Multi-container orchestration | Locked D-05 entry command [VERIFIED: local `docker compose version`] |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `curl` | system | Generate dashboard traffic | README manual examples (D-06) |
| `uv run docker-build` | uv 0.8.3 | Build API image before compose | First-time and code-change iteration (D-13) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled compose Prometheus/Grafana | kube-prometheus-stack in compose | Overkill for local demo; locked for Phase 5 K8s only |
| Prometheus alerting rules + Alertmanager | Grafana unified alerting | User locked Grafana alerting for local stack (D-09) |
| `build:` in compose for API | Pre-built `basic-model-serving:local` | User locked image-only loop (D-13/D-14) |
| Org preferences YAML for home dashboard | `GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH` | No native org-preferences file provisioner in OSS; env var is file-based and demo-friendly |

**Image pin verification (run before planning locks tags):**
```bash
docker pull prom/prometheus:v3.3.0
docker pull grafana/grafana:11.6.0
```

## Package Legitimacy Audit

> Phase 3 adds **no PyPI/npm packages**. Trust boundary is official Docker Hub images.

| Image | Registry | Source | Verdict | Disposition |
|-------|----------|--------|---------|-------------|
| `prom/prometheus` | Docker Hub `prom` org | github.com/prometheus/prometheus | OK | Approved — pin semver tag |
| `grafana/grafana` | Docker Hub `grafana` org | github.com/grafana/grafana | OK | Approved — pin semver tag |

**Packages removed due to [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Developer host
    │
    ├─ uv run docker-build ──► basic-model-serving:local image (Phase 2)
    │
    └─ docker compose up
           │
           ├─► [app:8000]  FastAPI + ResNet-50 + /metrics
           │        ▲
           │        │ GET /metrics (pull scrape, every 15s)
           │        │
           ├─► [prometheus:9090]  TSDB (retention 7d, named volume)
           │        ▲
           │        │ PromQL queries
           │        │
           └─► [grafana:3000]  provisioned datasource + dashboard + alert
                    │
                    └─► Browser :3000 (admin login → home dashboard)

Manual traffic: curl POST /predict :8000 ──► increments request_count_total,
               request_duration_bucket, prediction_count_total ──► scraped ──► panels update
```

### Recommended Project Structure

```
.
├── docker-compose.yml
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml          # compose scrape: app:8000, retention 7d
│   └── grafana/
│       ├── dashboards/
│       │   └── model-serving-overview.json
│       └── provisioning/
│           ├── datasources/
│           │   └── prometheus.yml
│           ├── dashboards/
│           │   └── dashboard.yml
│           └── alerting/
│               └── downtime.yml
├── .env.example                    # + GF_SECURITY_ADMIN_* (D-08)
└── README.md                       # compose quickstart, ports, curl, alert demo
```

### Pattern 1: Compose stack with pre-built API image

**What:** Root `docker-compose.yml` declares three services on one user-defined network; API uses `image: basic-model-serving:local` (no `build:`).

**When to use:** Locked D-14; dev/prod parity over bind-mount hot reload.

**Example:**
```yaml
# Source: Docker Compose docs — depends_on service_healthy
services:
  app:
    image: basic-model-serving:local
    ports: ["8000:8000"]
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3); exit(0 if r.status==200 else 1)"]
      interval: 10s
      timeout: 5s
      retries: 6
      start_period: 60s
    env_file: .env

  prometheus:
    image: prom/prometheus:v3.3.0
    ports: ["9090:9090"]
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - --config.file=/etc/prometheus/prometheus.yml
      - --web.enable-lifecycle
    depends_on:
      app:
        condition: service_healthy

  grafana:
    image: grafana/grafana:11.6.0
    ports: ["3000:3000"]
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
      GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: /var/lib/grafana/dashboards/model-serving-overview.json
    depends_on:
      - prometheus

volumes:
  prometheus-data:
```

### Pattern 2: Prometheus compose scrape + retention

**What:** Static scrape target uses compose DNS `app:8000`; retention explicit in config file.

**Example:**
```yaml
# Source: prometheus.io getting started + configuration (retention PR #17026)
global:
  scrape_interval: 15s
  evaluation_interval: 15s

storage:
  tsdb:
    retention:
      time: 7d

scrape_configs:
  - job_name: app
    metrics_path: /metrics
    static_configs:
      - targets: ['app:8000']
```

### Pattern 3: Grafana provisioning-as-code

**What:** Bind-mount `provisioning/`; datasource with fixed `uid`; dashboard provider points at JSON directory; alerting rules in `provisioning/alerting/`.

**Datasource example:**
```yaml
# Source: Grafana docs — Provision Prometheus data source
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    uid: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    jsonData:
      httpMethod: POST
```

**Dashboard provider example:**
```yaml
# Source: Grafana docs — dashboard provisioning
apiVersion: 1
providers:
  - name: model-serving
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
```

### Pattern 4: Downtime alert (Grafana unified alerting)

**What:** Provision alert rule querying `up{job="app"} == 0` with `for: 1m`; no contact points (UI-only, D-12).

**Recommendation:** Export a working rule from Grafana UI once (Alerting → Export) after manual validation, then commit the YAML to `provisioning/alerting/downtime.yml`. Hand-authoring the `data:` query block is error-prone [CITED: Grafana file provisioning docs].

**Prometheus-native equivalent (do NOT use in Phase 3):**
```yaml
# Deferred to Phase 5 if needed — D-09 locks Grafana alerting for compose
- alert: ServiceDown
  expr: up{job="app"} == 0
  for: 1m
```

### Anti-Patterns to Avoid

- **Scrape before app ready without health gating:** Causes `up=0` and risks alert noise — use `depends_on: service_healthy` on Prometheus.
- **Default 15d retention left implicit:** MON-04 requires explicit 7d+ — document in config, not "we'll change later."
- **Dashboard PromQL on raw URL paths:** High-cardinality and wrong labels — filter `path="/predict"` (route template).
- **Using `http_requests_total`:** Phase 1 uses custom `request_count` — panels must target `request_count_total`.
- **Grafana UI-first dashboard creation:** Violates MON-05 — JSON + provider YAML in git from the start.
- **Alertmanager / Slack for local demo:** Out of scope (D-12); adds moving parts with no portfolio benefit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Metric collection | Custom push agent or log parsing | Prometheus pull scrape of `/metrics` | Standard; app stays unaware of scraper |
| Dashboard persistence | Manual JSON export workflow | Grafana file provisioning | MON-05; reproducible on `compose up` |
| Datasource setup | Post-start curl/API scripts | `provisioning/datasources/*.yml` | Idempotent startup; no race with UI |
| Downtime detection | Custom health poller | Grafana alert on Prometheus `up` metric | Native; aligns with scrape failure semantics |
| Compose orchestration | Shell wrapper scripts | Plain `docker compose up` | Locked D-05/D-16 |
| TSDB storage | Host bind-mount without named volume | Docker named volume `prometheus-data` | Survives container recreate; predictable permissions |

**Key insight:** Phase 3 is wiring and visualization only — the app already emits the right metrics; hand-rolling observability plumbing duplicates Prometheus/Grafana strengths.

## Common Pitfalls

### Pitfall 1: False-positive downtime alert during model load

**What goes wrong:** Alert fires on first `docker compose up` before ResNet-50 finishes loading.

**Why it happens:** Prometheus scrapes `/metrics` before `/health/ready` returns 200; `up=0` or failed scrapes accumulate.

**How to avoid:** App healthcheck with `start_period: 60s`; Prometheus `depends_on: app: condition: service_healthy`; alert `for: 1m` (locked D-11); `scrape_interval: 15s`.

**Warning signs:** Alert Firing within 90s of stack start without user stopping API.

### Pitfall 2: Empty dashboard panels (metric name mismatch)

**What goes wrong:** Panels show "No data" despite traffic.

**Why it happens:** PromQL references `request_count` instead of `request_count_total`; or wrong `job` label on `up`.

**How to avoid:** Verify metric names at `http://localhost:8000/metrics` after curl traffic; match `job_name` in prometheus.yml to alert/dashboard queries.

**Warning signs:** Prometheus Targets UI shows `app` UP but Grafana panels empty.

### Pitfall 3: Missing image on first compose up

**What goes wrong:** `docker compose up` fails — image not found.

**Why it happens:** D-14 — compose does not build; user skipped `uv run docker-build`.

**How to avoid:** README prerequisite callout before compose quickstart.

**Warning signs:** `pull access denied` or `No such image: basic-model-serving:local`.

### Pitfall 4: Retention not actually 7d

**What goes wrong:** MON-04 checkbox met in docs only; Prometheus still uses 15d default or ephemeral storage lost on volume omission.

**How to avoid:** Set `storage.tsdb.retention.time: 7d` in `prometheus.yml`; mount named volume; verify via Prometheus UI → Status → TSDB Stats.

**Warning signs:** No `storage` block in config; no `prometheus-data` volume in compose.

### Pitfall 5: Home dashboard not shown after login

**What goes wrong:** Reviewer lands on default Grafana home, not Model Serving Overview.

**Why it happens:** Org `homeDashboardUID` not set; provisioning does not auto-star dashboards.

**How to avoid:** Set `GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH` to provisioned JSON path; set `"uid": "model-serving-overview"` in dashboard JSON.

**Warning signs:** Login shows generic Grafana home; dashboard only under Browse.

## Code Examples

### PromQL for dashboard panels (Phase 1 metric names)

```promql
# Source: prometheus.io histogram_quantile docs + app/metrics/prometheus.py
# Request rate (all paths)
sum(rate(request_count_total[5m]))

# p50 / p95 latency for /predict (stat panels — D-02)
histogram_quantile(0.50, sum by (le) (rate(request_duration_bucket{path="/predict"}[5m])))
histogram_quantile(0.95, sum by (le) (rate(request_duration_bucket{path="/predict"}[5m])))

# Error rate (5xx / all)
sum(rate(request_count_total{status=~"5.."}[5m]))
/ sum(rate(request_count_total[5m]))

# 4xx vs 5xx breakdown (D-03)
sum(rate(request_count_total{status=~"4.."}[5m]))
sum(rate(request_count_total{status=~"5.."}[5m]))

# Prediction throughput
rate(prediction_count_total[5m])

# Total predictions (counter raw value)
prediction_count_total

# Service up (job must match prometheus.yml job_name)
up{job="app"}
```

### README curl traffic (D-06)

```bash
# File upload — uses tests/fixtures/sample.jpg
curl -s -X POST http://localhost:8000/predict \
  -F "file=@tests/fixtures/sample.jpg" | jq .

# Optional: trigger 4xx for error panels
curl -s -X POST http://localhost:8000/predict \
  -F "file=@README.md" | jq .
```

### Alert demo steps (D-10)

```bash
docker compose stop app
# Wait ~60–90s → Grafana → Alerting → Service Down → Firing
docker compose start app
# Wait ~60s → Resolved
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prometheus retention CLI flags only | `storage.tsdb.retention` in prometheus.yml | Prometheus PR #17026 | Prefer config file for MON-04; CLI flag still works but deprecated |
| Grafana legacy alerting | Unified alerting + file provisioning | Grafana 9+ | Phase 3 uses `provisioning/alerting/` |
| `docker-compose` (v1 binary) | `docker compose` (v2 plugin) | Docker Compose v2 | Locked command D-05 |
| kube-prometheus-stack for all envs | Hand-rolled compose stack; K8s stack TBD Phase 5 | Project decision | ARCHITECTURE.md anti-pattern for portfolio K8s; compose is simpler |

**Deprecated/outdated:**
- Bind-mount API source for compose hot reload — rejected (D-13)
- `prometheus-fastapi-instrumentator` default metric names — project uses custom `request_count` in `app/metrics/prometheus.py`

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `prom/prometheus:v3.3.0` and `grafana/grafana:11.6.0` are appropriate pin targets | Standard Stack | Patch version may need bump; planner should verify tags exist before lock |
| A2 | `GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH` satisfies D-04 home dashboard | Pattern 1 | If Grafana changes env var semantics, fallback is API `PUT /api/org/preferences` init script (adds scope) |
| A3 | Hand-exported Grafana alert YAML is acceptable for MON-05 | Pattern 4 | If export format differs across Grafana patch versions, planner adds validation step |
| A4 | `request_count_total` / `request_duration_bucket` are the exported names | PromQL examples | Verify at `/metrics` — prometheus_client naming is consistent but should be confirmed in Wave 0 smoke |

## Open Questions (RESOLVED)

1. **Exact Grafana alert YAML shape** — **RESOLVED**
   - Resolution: Bootstrap via one-time Grafana UI export after manual rule creation against `up{job="app"}`, then commit sanitized YAML to `monitoring/grafana/provisioning/alerting/downtime.yml` (03-03 Task 1). Hand-authoring the `data:` query block is error-prone; UI export is the fastest path to MON-03/MON-05.

2. **Grafana admin password via `.env` vs inline compose** — **RESOLVED**
   - Resolution: Use inline `environment:` on the compose `grafana` service with `GF_SECURITY_ADMIN_USER=admin` and `GF_SECURITY_ADMIN_PASSWORD=admin` (03-01 Task 2). Document in README and as commented lines in `.env.example` (03-03 Task 2). Do NOT add uncommented `GF_*` keys to `.env.example` — would break `tests/test_docker_config.py`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker Engine | compose stack | ✓ | 29.6.1 | — (blocking) |
| Docker Compose plugin | `docker compose up` | ✓ | v5.3.1 | — (blocking) |
| `basic-model-serving:local` image | API service | ✗ until build | — | Run `uv run docker-build` first (D-14) |
| `uv` | docker-build prerequisite | ✓ | 0.8.3 | Plain `docker build` |
| `curl` | README traffic examples | ✓ | system | wget/httpie in docs |
| `jq` | README examples (optional) | ✓ | system | Omit jq pipe in minimal docs |

**Missing dependencies with no fallback:**
- Docker daemon (required for entire phase)

**Missing dependencies with fallback:**
- Local image absent until `uv run docker-build` — documented prerequisite, not a tooling gap

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth on API (project out of scope) |
| V3 Session Management | no | — |
| V4 Access Control | no | Local demo only |
| V5 Input Validation | yes (existing) | Phase 1 Pydantic validation — unchanged |
| V6 Cryptography | no | No TLS on local compose ports |
| V14 Configuration | yes | Default Grafana admin creds documented for local use only (D-08); not for production |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Grafana default credentials on exposed port | Spoofing / Elevation | Document local-only; do not expose `:3000` to internet |
| Prometheus admin API open | Tampering | Local demo; no `--web.enable-admin-api` |
| SSRF via `/predict` URL mode | Spoofing | Already mitigated Phase 1 (API-05) — unchanged |

## Sources

### Primary (HIGH confidence)
- Context7 `/grafana/grafana` — dashboard/datasource/alerting file provisioning
- Context7 `/prometheus/prometheus` — scrape config, retention, histogram_quantile
- Context7 `/docker/compose` — `depends_on: condition: service_healthy`

### Secondary (MEDIUM confidence)
- [Grafana administration — provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/) — provisioning directory layout
- [Grafana alerting file provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/) — alert YAML location
- [Prometheus command-line flags](https://prometheus.io/docs/prometheus/latest/command-line/prometheus/) — retention deprecation
- [Prometheus PR #17026](https://github.com/prometheus/prometheus/pull/17026) — retention in config file

### Tertiary (LOW confidence)
- GitHub issue #12119 — home dashboard via `default_home_dashboard_path` (community pattern)

### Codebase
- `app/metrics/prometheus.py` — metric names, labels, histogram buckets
- `Dockerfile` — HEALTHCHECK on `/health/ready`, start_period 45s
- `.planning/research/ARCHITECTURE.md` — `monitoring/` layout, compose vs K8s scrape split

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — official Docker images + documented provisioning patterns
- Architecture: HIGH — locked CONTEXT decisions + existing metrics contract
- Pitfalls: HIGH — boot ordering and metric naming are well-known failure modes

**Research date:** 2026-07-08  
**Valid until:** 2026-08-08 (Grafana/Prometheus patch releases may bump pin tags)
