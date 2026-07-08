# Phase 3: Local Dev Stack & Dashboards - Pattern Map

**Mapped:** 2026-07-08
**Files analyzed:** 8 (new/modified) + 4 (integration references)
**Analogs found:** 5 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `docker-compose.yml` | config | batch | `Dockerfile` + `scripts/docker.py` | partial |
| `monitoring/prometheus/prometheus.yml` | config | pub-sub (pull scrape) | `app/metrics/prometheus.py` + `tests/test_metrics.py` | partial |
| `monitoring/grafana/dashboards/model-serving-overview.json` | config | request-response (PromQL query) | `app/metrics/prometheus.py` + `03-UI-SPEC.md` | partial |
| `monitoring/grafana/provisioning/datasources/prometheus.yml` | config | request-response | `03-RESEARCH.md` Pattern 3 | no analog |
| `monitoring/grafana/provisioning/dashboards/dashboard.yml` | config | file-I/O | `03-RESEARCH.md` Pattern 3 + `.planning/research/ARCHITECTURE.md` | no analog |
| `monitoring/grafana/provisioning/alerting/downtime.yml` | config | event-driven | `03-RESEARCH.md` Pattern 4 | no analog |
| `.env.example` | config | transform | `.env.example` (existing) + `tests/test_docker_config.py` | partial |
| `README.md` | config | — | `README.md` (existing Docker section) | partial |

**Integration references (unchanged, consumed by compose stack):**

| File | Role | Data Flow | Used By |
|------|------|-----------|---------|
| `app/metrics/prometheus.py` | middleware + route | request-response | Prometheus scrape `/metrics`; all dashboard PromQL |
| `Dockerfile` | config | batch | Compose `app` service image + HEALTHCHECK semantics |
| `scripts/docker.py` | utility | batch | `IMAGE` tag constant; health/predict polling patterns for README curl |
| `tests/fixtures/sample.jpg` | fixture | file-I/O | README manual traffic examples (D-06) |

## Pattern Assignments

### `docker-compose.yml` (config, batch)

**Analogs:** `Dockerfile` (HEALTHCHECK, image runtime), `scripts/docker.py` (image tag, readiness polling), `.env.example` (app env vars)

**Do NOT add `build:` directive** — locked D-14; compose consumes pre-built image only.

---

**Image tag constant** (`scripts/docker.py` lines 15–19):

```15:19:scripts/docker.py
IMAGE = "basic-model-serving:local"
CONTAINER_NAME = "basic-model-serving-smoke"
HOST = "127.0.0.1"
PORT = 8000
BASE = f"http://{HOST}:{PORT}"
```

**Compose translation:** `image: basic-model-serving:local` on `app` service; `ports: ["8000:8000"]`. Prerequisite `uv run docker-build` documented in README before first `docker compose up`.

---

**HEALTHCHECK probe** (`Dockerfile` lines 41–42):

```41:42:Dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3); exit(0 if r.status==200 else 1)"
```

**Compose translation:** Mirror probe in `app.healthcheck.test` using same `urllib` one-liner. Tune for compose boot grace (D-11): `interval: 10s`, `start_period: 60s`, `retries: 6` per `03-RESEARCH.md` Pattern 1 — longer than Dockerfile's 45s to absorb ResNet load before Prometheus scrapes.

---

**Readiness polling pattern** (`scripts/docker.py` lines 63–74):

```63:74:scripts/docker.py
def _wait_ready(timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    url = f"{BASE}/health/ready"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError):
            pass
        time.sleep(1)
    raise TimeoutError(f"/health/ready did not return 200 within {timeout}s")
```

**Compose translation:** `prometheus.depends_on.app.condition: service_healthy` gates scrape start until app healthcheck passes — prevents false-positive downtime alert during model load.

---

**App environment vars** (`.env.example` lines 1–5):

```1:5:.env.example
# Copy to .env for local development. Container config uses docker run -e or compose env (Phase 3).
TORCH_NUM_THREADS=2
MAX_UPLOAD_BYTES=1048576
URL_TIMEOUT=5.0
LOG_LEVEL=INFO
```

**Compose translation:** `app` service uses `env_file: .env` (same four pydantic-settings vars as Phase 2). Do not add Uvicorn env vars.

---

**Three-service stack skeleton** (from `03-RESEARCH.md` Pattern 1 — no repo analog yet):

```yaml
services:
  app:
    image: basic-model-serving:local
    ports: ["8000:8000"]
    env_file: .env
    healthcheck: { ... urllib /health/ready probe, start_period: 60s ... }

  prometheus:
    image: prom/prometheus:v3.3.0
    ports: ["9090:9090"]
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
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
      GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: /var/lib/grafana/dashboards/model-serving-overview.json
    depends_on:
      - prometheus

volumes:
  prometheus-data:
```

**Constraints:** No `uv run compose-*` scripts (D-16). Plain `docker compose up` entry command (D-05). Named volume for TSDB persistence (MON-04).

---

### `monitoring/prometheus/prometheus.yml` (config, pub-sub)

**Analogs:** `app/metrics/prometheus.py` (metric names/labels), `tests/test_metrics.py` (exported name verification)

**Do NOT use** `http_requests_total` — project uses custom `request_count` (see `test_no_instrumentator_default_names`).

---

**Metric definitions consumed by scrape** (`app/metrics/prometheus.py` lines 8–19):

```8:19:app/metrics/prometheus.py
REQUEST_COUNT = Counter(
    "request_count",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_DURATION = Histogram(
    "request_duration",
    "Request duration in seconds",
    ["method", "path"],
    buckets=(0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0),
)
PREDICTION_COUNT = Counter("prediction_count", "Successful predictions")
```

**Prometheus export naming:** Counters become `request_count_total`, `prediction_count_total`; histogram becomes `request_duration_bucket`. Dashboard PromQL must use `_total` / `_bucket` suffixes.

---

**Route template path labels** (`app/metrics/prometheus.py` lines 35–43):

```35:43:app/metrics/prometheus.py
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)

        REQUEST_COUNT.labels(
            method=request.method,
            path=path,
            status=str(response.status_code),
        ).inc()
        REQUEST_DURATION.labels(method=request.method, path=path).observe(elapsed)
```

**Scrape config implication:** Dashboard queries filter `path="/predict"` (route template from `app/api/routes/predict.py` line 101), not raw URLs.

---

**Metric name verification test** (`tests/test_metrics.py` lines 13–20):

```13:20:tests/test_metrics.py
def test_metrics_endpoint_returns_required_names(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "request_count" in body
    assert "request_duration" in body
    assert "prediction_count" in body
```

**Wave 0 smoke:** After curl traffic, confirm `request_count_total` and `request_duration_bucket` at `http://localhost:8000/metrics` before locking dashboard PromQL.

---

**Compose scrape + retention pattern** (`03-RESEARCH.md` Pattern 2):

```yaml
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

**Key constraints:**
- `job_name: app` must match alert query `up{job="app"}` and dashboard Service Health panel
- `targets: ['app:8000']` uses compose DNS — service name `app` must match compose service key
- Explicit `7d` retention in config file (MON-04), not implicit default
- `scrape_interval: 15s` + alert `for: 1m` = 4 failed scrapes before firing

---

### `monitoring/grafana/dashboards/model-serving-overview.json` (config, request-response)

**Analogs:** `app/metrics/prometheus.py` (PromQL inputs), `03-UI-SPEC.md` (layout/thresholds/copy)

**No existing dashboard JSON in repo** — hand-author or export from Grafana UI once, then commit. UI-SPEC is the design contract.

---

**Required dashboard metadata** (`03-UI-SPEC.md` lines 32, 142–147):

```
"uid": "model-serving-overview"
"title": "Model Serving Overview"
"editable": false
"refresh": "10s"
"timezone": "browser"
Default time range: Last 15 minutes
Tags: model-serving, portfolio, phase-3
```

**Home dashboard env** (compose `grafana` service): `GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/var/lib/grafana/dashboards/model-serving-overview.json`

---

**Panel inventory** (`03-UI-SPEC.md` lines 149–180) — exactly 8 panels:

| Panel | Type | PromQL |
|-------|------|--------|
| Request Rate | timeseries | `sum(rate(request_count_total[5m]))` |
| p50 Latency | stat | `histogram_quantile(0.50, sum by (le) (rate(request_duration_bucket{path="/predict"}[5m])))` |
| p95 Latency | stat | `histogram_quantile(0.95, sum by (le) (rate(request_duration_bucket{path="/predict"}[5m])))` |
| Error Rate | stat | `sum(rate(request_count_total{status=~"5.."}[5m])) / sum(rate(request_count_total[5m]))` |
| Prediction Throughput | timeseries | `rate(prediction_count_total[5m])` |
| HTTP Errors by Status | timeseries (2 queries) | 4xx: `sum(rate(request_count_total{status=~"4.."}[5m]))`; 5xx: `sum(rate(request_count_total{status=~"5.."}[5m]))` |
| Service Health | stat | `up{job="app"}` |
| Total Predictions | stat | `prediction_count_total` |

**Datasource UID:** `prometheus` — must match provisioning datasource file.

---

**Stat panel rules** (`03-UI-SPEC.md` lines 184–195, D-02):

- p50, p95, error rate, service health, total predictions → **Stat** type, `graphMode: none` (no sparkline)
- Latency units: **milliseconds** — Prometheus exports seconds; multiply in PromQL (`* 1000`) or use Grafana unit transform
- Latency thresholds: green `< 100ms`, yellow `100–200ms`, red `> 200ms` (aligned with histogram `0.1` bucket in `prometheus.py` line 17)
- Service Health value mappings: `1` → `UP` (green), `0` → `DOWN` (red)

---

**Grid layout** (`03-UI-SPEC.md` lines 153–162):

| Panel | Grid (x, y, w, h) |
|-------|-------------------|
| Request Rate | (0, 0, 12, 8) |
| p50 Latency | (12, 0, 6, 4) |
| p95 Latency | (18, 0, 6, 4) |
| Error Rate | (12, 4, 12, 4) |
| Prediction Throughput | (0, 8, 12, 8) |
| HTTP Errors by Status | (12, 8, 12, 8) |
| Service Health | (0, 16, 6, 4) |
| Total Predictions | (6, 16, 6, 4) |

---

### `monitoring/grafana/provisioning/datasources/prometheus.yml` (config, request-response)

**Analog:** none in codebase — use `03-RESEARCH.md` Pattern 3

```yaml
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

**Constraints:**
- `url: http://prometheus:9090` — compose service DNS name must match compose `prometheus` service key
- `uid: prometheus` — referenced by dashboard JSON `"datasource": {"type": "prometheus", "uid": "prometheus"}` and alert rule `datasourceUid`

---

### `monitoring/grafana/provisioning/dashboards/dashboard.yml` (config, file-I/O)

**Analog:** `.planning/research/ARCHITECTURE.md` layout (lines 84–91) + `03-RESEARCH.md` Pattern 3

```yaml
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

**Bind-mount pairing** (compose `grafana` volumes):
- `./monitoring/grafana/provisioning` → `/etc/grafana/provisioning`
- `./monitoring/grafana/dashboards` → `/var/lib/grafana/dashboards`

---

### `monitoring/grafana/provisioning/alerting/downtime.yml` (config, event-driven)

**Analog:** none in codebase — use `03-RESEARCH.md` Pattern 4 + `03-UI-SPEC.md` Alert Visualization section

**Locked alert contract** (`03-UI-SPEC.md` lines 256–267):

| Property | Value |
|----------|-------|
| Rule name | `Service Down` |
| Query | `up{job="app"} == 0` |
| `for` duration | `1m` |
| Contact points | None (UI-only, D-12) |
| Evaluation interval | `15s` (match scrape) |

**Recommendation from research:** Implement alert once in Grafana UI against `up{job="app"}`, export YAML, commit — hand-authoring `data:` query block is error-prone. Labels: `severity=critical`, `team=model-serving` (optional).

**Copy contract** (`03-UI-SPEC.md` lines 234–241):
- Summary: `Model serving API is unreachable`
- Description: `Prometheus cannot scrape app:8000/metrics for 1 minute. Check docker compose app service.`

---

### `.env.example` (config, transform)

**Analog:** existing `.env.example` + `tests/test_docker_config.py` field-validation pattern

**Existing API vars unchanged** — four pydantic-settings fields only:

```1:5:.env.example
# Copy to .env for local development. Container config uses docker run -e or compose env (Phase 3).
TORCH_NUM_THREADS=2
MAX_UPLOAD_BYTES=1048576
URL_TIMEOUT=5.0
LOG_LEVEL=INFO
```

**Phase 3 additions (Grafana only — NOT pydantic Settings fields):**

```bash
# Grafana (compose stack only — not read by FastAPI app)
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin
```

**Important:** Do NOT add Grafana vars to `app/core/config.py` or break `test_env_example_matches_settings_fields` — that test asserts `.env.example` keys == `Settings.model_fields` only:

```10:19:tests/test_docker_config.py
def test_env_example_matches_settings_fields():
    example_path = Path(".env.example")
    lines = [
        line.strip()
        for line in example_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    keys = {line.split("=", 1)[0] for line in lines}
    expected = {_env_name(name) for name in Settings.model_fields}
    assert keys == expected
```

**Pattern:** Add Grafana vars in a **commented section below** the app vars, OR document in README only and wire via compose `environment:` inline. If adding uncommented `GF_*` keys, update `test_docker_config.py` to exclude Grafana keys from the Settings assertion — planner discretion per D-08.

---

### `README.md` (config)

**Analog:** `README.md` existing Docker section (lines 1–46)

**Current Docker section structure** (`README.md` lines 5–46):

```5:46:README.md
## Docker

**Prerequisites:** Docker Engine, [uv](https://docs.astral.sh/uv/) (recommended)

### Build
...
### Run
...
### Configuration
...
### Smoke test
...
```

**Phase 3 additions (new `## Local observability stack` section after Docker):**

1. **Prerequisite callout:** `uv run docker-build` before first `docker compose up` (D-14)
2. **Hero command:** `docker compose up` (D-05)
3. **Port table** (D-07): API `:8000`, Grafana `:3000`, Prometheus `:9090`
4. **Grafana login** (D-08): `admin` / `admin`
5. **Manual curl traffic** (D-06) — reuse `scripts/docker.py` multipart pattern or `tests/fixtures/sample.jpg`:

```bash
curl -s -X POST http://localhost:8000/predict \
  -F "file=@tests/fixtures/sample.jpg" | jq .
```

6. **Image-only iteration loop** (D-13): `uv run docker-build` → `docker compose restart app`
7. **Alert demo steps** (D-10): `docker compose stop app` → wait ~60–90s → Grafana Alerting → Firing → `docker compose start app` → Resolved
8. **Config reload** (D-15): edit `monitoring/` files → `docker compose restart grafana|prometheus`

**Preserve existing** `uv run docker-build|docker-run|docker-smoke` section — Phase 2 single-container workflow unchanged (D-16).

---

## Shared Patterns

### Metrics Contract (Phase 1 → Phase 3)

**Source:** `app/metrics/prometheus.py` + `tests/test_metrics.py`
**Apply to:** `prometheus.yml` scrape target, dashboard PromQL, alert `up{job="app"}`

| Metric | Exported name | Labels | Dashboard use |
|--------|---------------|--------|---------------|
| `request_count` | `request_count_total` | `method`, `path`, `status` | Request rate, error rate, 4xx/5xx breakdown |
| `request_duration` | `request_duration_bucket` | `method`, `path` | p50/p95 latency (`path="/predict"`) |
| `prediction_count` | `prediction_count_total` | none | Throughput + total counter |

Middleware wired in `app/main.py` line 47: `app.add_middleware(PrometheusMiddleware)`; metrics route at line 63: `app.include_router(metrics_router)`.

### Health Probe Contract

**Source:** `Dockerfile` HEALTHCHECK + `app/api/routes/health.py`
**Apply to:** Compose `app.healthcheck`, `depends_on: service_healthy`, downtime alert boot grace

| Probe | Endpoint | Compose use |
|-------|----------|-------------|
| Readiness | `/health/ready` | Healthcheck + Prometheus scrape gate |
| Liveness | `/health/live` | Not used in Phase 3 compose |

Probe returns 503 until `app.state.ready=True` (model loaded in lifespan).

### Image Tag & Build Prerequisite

**Source:** `scripts/docker.py` line 15
**Apply to:** Compose `app.image`, README prerequisite

```
basic-model-serving:local  ←  uv run docker-build (no build: in compose)
```

### Environment Configuration (API only)

**Source:** `.env.example` + `app/core/config.py`
**Apply to:** Compose `app.env_file`

Four app vars: `TORCH_NUM_THREADS`, `MAX_UPLOAD_BYTES`, `URL_TIMEOUT`, `LOG_LEVEL`. Grafana admin creds are compose/Grafana-only — separate from pydantic Settings.

### Manual Traffic Generation

**Source:** `scripts/docker.py` `_post_predict()` (lines 77–99) + `tests/conftest.py` JPEG fixture
**Apply to:** README curl examples (D-06)

Use `tests/fixtures/sample.jpg` for file-upload example. Optional 4xx example: POST non-image file to populate error panels.

### Phase 2 Docker Workflow (preserved)

**Source:** `pyproject.toml` + `scripts/docker.py`
**Apply to:** README — unchanged single-container path

```
uv run docker-build   → prerequisite for compose
uv run docker-run     → single-container dev (unchanged)
uv run docker-smoke   → E2E without compose (unchanged)
```

No new `[project.scripts]` entries for compose (D-16).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `monitoring/grafana/provisioning/datasources/prometheus.yml` | config | request-response | First Grafana provisioning file in repo — use `03-RESEARCH.md` Pattern 3 |
| `monitoring/grafana/provisioning/dashboards/dashboard.yml` | config | file-I/O | First dashboard provider in repo — use `ARCHITECTURE.md` + `03-RESEARCH.md` Pattern 3 |
| `monitoring/grafana/provisioning/alerting/downtime.yml` | config | event-driven | First alerting provision in repo — UI export recommended per `03-RESEARCH.md` Pattern 4 |

## Metadata

**Analog search scope:** Repo root (`Dockerfile`, `docker-compose.yml` absent), `monitoring/` (absent), `app/metrics/`, `scripts/`, `tests/`, `.env.example`, `README.md`, `.planning/phases/02-containerization/02-PATTERNS.md`, `.planning/research/ARCHITECTURE.md`, `03-RESEARCH.md`, `03-UI-SPEC.md`
**Files scanned:** 48
**Pattern extraction date:** 2026-07-08
**Primary references:** Phase 1 metrics (`app/metrics/prometheus.py`, `tests/test_metrics.py`), Phase 2 container patterns (`Dockerfile`, `scripts/docker.py`, `02-PATTERNS.md`), Phase 3 research/UI contracts
**Net-new territory:** All `monitoring/` files and `docker-compose.yml` — no prior compose or Grafana JSON in codebase; planner must lean on `03-RESEARCH.md` examples for provisioning YAML shape

## PATTERN MAPPING COMPLETE

**Phase:** 3 - Local Dev Stack & Dashboards
**Files classified:** 8 new/modified + 4 integration references
**Analogs found:** 5 / 8

### Coverage
- Files with partial analog: 5 (`docker-compose.yml`, `prometheus.yml`, dashboard JSON, `.env.example`, `README.md`)
- Files with no analog: 3 (Grafana provisioning YAML files — datasources, dashboards, alerting)
- Files with exact analog: 0 (all Phase 3 deliverables are net-new infrastructure wiring)

### Key Patterns Identified
- **Pre-built image compose:** `image: basic-model-serving:local` from `scripts/docker.py`; no `build:` — `uv run docker-build` prerequisite
- **Health-gated scrape:** Compose healthcheck mirrors Dockerfile `urllib` `/health/ready` probe; Prometheus `depends_on: service_healthy` prevents boot-time alert noise
- **Metric naming:** Dashboard PromQL uses `request_count_total`, `request_duration_bucket`, `prediction_count_total` — not instrumentator defaults
- **Route template labels:** Filter `path="/predict"` in latency/error queries — matches `PrometheusMiddleware` route.path extraction
- **Provisioning-as-code:** Bind-mount `monitoring/grafana/provisioning/` + `dashboards/`; home dashboard via `GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH`
- **Settings/env separation:** API vars stay in pydantic Settings; Grafana `GF_*` creds are compose-only — preserve `test_docker_config.py` contract
- **Phase 2 workflow preserved:** `uv run docker-build|docker-run|docker-smoke` unchanged; compose is plain `docker compose up`

### File Created
`.planning/phases/03-local-dev-stack-dashboards/03-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner should reference concrete excerpts above when writing PLAN.md task actions — especially metric naming from `app/metrics/prometheus.py`, healthcheck from `Dockerfile`, and UI-SPEC panel/grid contracts for dashboard JSON.
