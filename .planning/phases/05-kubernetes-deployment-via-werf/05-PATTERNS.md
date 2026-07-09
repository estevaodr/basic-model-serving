# Phase 5: Kubernetes Deployment (via werf) - Pattern Map

**Mapped:** 2026-07-09
**Files analyzed:** 14 (net-new/modified) + 8 (integration references)
**Analogs found:** 10 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `werf.yaml` | config | batch | `.planning/research/STACK.md` (lines 100–109) + `05-RESEARCH.md` Pattern 1 | partial — greenfield; no repo file |
| `.helm/Chart.yaml` | config | batch | `05-RESEARCH.md` Pattern 2 | no analog — first Helm chart |
| `.helm/Chart.lock` | config | batch | `05-RESEARCH.md` (dependency lock guidance) | no analog |
| `.helm/values.yaml` | config | transform | `docker-compose.yml` + `.env.example` | partial |
| `.helm/values-local.yaml` | config | transform | `scripts/docker.py` `IMAGE` tag + `05-RESEARCH.md` local converge | partial |
| `.helm/templates/deployment.yaml` | config | request-response | `docker-compose.yml` (`app` service) + `Dockerfile` HEALTHCHECK | role-match |
| `.helm/templates/service.yaml` | config | request-response | `docker-compose.yml` (`app.ports`) | partial |
| `.helm/templates/configmap.yaml` | config | transform | `.env.example` + `app/core/config.py` | exact |
| `.helm/templates/servicemonitor.yaml` | config | pub-sub | `monitoring/prometheus/prometheus.yml` + `app/metrics/prometheus.py` | partial |
| `.helm/templates/grafana-dashboard.yaml` | config | file-I/O | `monitoring/grafana/provisioning/dashboards/dashboard.yml` + compose Grafana volumes | partial |
| `.helm/dashboards/model-serving-overview.json` | config | request-response (PromQL) | `monitoring/grafana/dashboards/model-serving-overview.json` | exact — copy source |
| `scripts/rollout-zero-downtime.sh` | utility | request-response | `scripts/docker.py` `_wait_ready()` + `05-RESEARCH.md` Pattern 6 | role-match |
| `.gitignore` | config | — | self (extend for `.helm/charts/`) | partial |
| `README.md` | config | — | `README.md` Docker/CI sections | partial |

**Integration references (unchanged, consumed by K8s chart):**

| File | Role | Data Flow | Used By |
|------|------|-----------|---------|
| `Dockerfile` | config | batch | CI image + optional werf build; probe timing baseline |
| `app/core/config.py` | config | transform | ConfigMap keys → pydantic-settings |
| `app/api/routes/health.py` | route | request-response | startup/liveness/readiness probes |
| `app/metrics/prometheus.py` | middleware + route | request-response | ServiceMonitor `/metrics` scrape |
| `app/main.py` | app | request-response | `torch.set_num_threads(settings.torch_num_threads)` |
| `.github/workflows/deploy.yml` | config | event-driven | GHCR image coordinates + tag scheme |
| `docker-compose.yml` | config | batch | Parallel deploy target; env/health/monitoring patterns |
| `monitoring/grafana/dashboards/model-serving-overview.json` | config | request-response | Dashboard source of truth for K8s provisioning |

## Pattern Assignments

### `werf.yaml` (config, batch)

**Analogs:** `.planning/research/STACK.md` (minimal layout), `05-RESEARCH.md` Pattern 1 (deploy-only default)

**Do NOT use `global.werf.images.*` in templates on the default path** — CI image is external; use plain `values.image.repository/tag` + `--without-images` (Anti-Pattern 3).

---

**STACK.md minimal werf layout** (lines 100–109):

```yaml
project: basic-model-serving
configVersion: 1
---
image: api
dockerfile: Dockerfile
context: .
```

**Phase 5 translation:** Keep optional `image: api` block for explicit local `werf build` only. Default converge uses `--without-images` and Helm values — deploy-only is normal path (D-07).

---

**Default converge command** (`05-RESEARCH.md` Standard Stack):

```bash
werf converge --env local --dev --without-images \
  --set image.repository=ghcr.io/estevaodr/basic-model-serving \
  --set image.tag=$(git rev-parse --short HEAD)
```

**Local iteration path:**

```bash
minikube image load basic-model-serving:local
werf converge --env local --dev --without-images \
  --set image.repository=basic-model-serving \
  --set image.tag=local \
  --set image.pullPolicy=IfNotPresent
```

**Constraints:**
- Always `--dev` for local iteration (giterminism relaxation — Pitfall 4)
- CI does **not** run werf — `deploy.yml` has no werf step (`tests/test_deploy_workflow.py` line 100–105)
- Release name follows werf `{project}-{env}` → `basic-model-serving-local` for `--env local`

---

### `.helm/Chart.yaml` (config, batch)

**Analog:** none in codebase — use `05-RESEARCH.md` Pattern 2

```yaml
apiVersion: v2
name: basic-model-serving
version: 0.1.0
dependencies:
  - name: kube-prometheus-stack
    version: "~87.12.0"
    repository: https://prometheus-community.github.io/helm-charts
```

**Post-create workflow:**

```bash
werf helm dependency update .helm
# commit Chart.lock; gitignore .helm/charts/*.tgz
```

**Note:** ARCHITECTURE.md (lines 92–105) shows hand-rolled Prom/Grafana templates — **superseded** by user decision D-01/D-02 (kube-prometheus-stack subchart).

---

### `.helm/values.yaml` (config, transform)

**Analogs:** `docker-compose.yml` (service topology), `.env.example` (app env defaults), `05-RESEARCH.md` subchart values excerpt

**App image defaults** (mirror `deploy.yml` + README GHCR section):

```yaml
image:
  repository: ghcr.io/estevaodr/basic-model-serving
  tag: latest          # overridden at converge: --set image.tag=<sha>
  pullPolicy: IfNotPresent
```

**kube-prometheus-stack nested values** (`05-RESEARCH.md` Pattern 2 excerpt):

```yaml
kube-prometheus-stack:
  prometheus:
    prometheusSpec:
      retention: 7d
      serviceMonitorSelectorNilUsesHelmValues: true
  grafana:
    service:
      type: NodePort
    sidecar:
      dashboards:
        enabled: true
        label: grafana_dashboard
        labelValue: "1"
```

**Compose translation table:**

| Compose (`docker-compose.yml`) | K8s values |
|-------------------------------|------------|
| `app.ports: "8000:8000"` | Service `type: NodePort`, port 8000 |
| `app.env_file: .env` | ConfigMap + `envFrom.configMapRef` |
| `prometheus` retention `7d` | `prometheus.prometheusSpec.retention: 7d` |
| `grafana.ports: "3000:3000"` | `grafana.service.type: NodePort` |
| `./monitoring/grafana/dashboards/` bind-mount | Sidecar ConfigMap from `.helm/dashboards/` |

---

### `.helm/templates/deployment.yaml` (config, request-response)

**Analogs:** `docker-compose.yml` (`app` service), `Dockerfile` HEALTHCHECK, `app/api/routes/health.py`, `app/main.py`

---

**Image reference pattern** (`05-RESEARCH.md` Pattern 1 — NOT werf global images):

```yaml
containers:
  - name: api
    image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
    imagePullPolicy: {{ .Values.image.pullPolicy | default "IfNotPresent" }}
    ports:
      - name: http
        containerPort: 8000
```

---

**ConfigMap env injection** (compose `env_file` equivalent):

```yaml
envFrom:
  - configMapRef:
      name: model-serving-config
```

---

**Resource limits** (locked D-13/D-14):

```yaml
resources:
  requests:
    cpu: "1"
    memory: 1Gi
  limits:
    cpu: "2"
    memory: 2Gi
```

---

**Rolling update strategy** (D-17/D-18):

```yaml
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
```

---

**Probe wiring** (`05-RESEARCH.md` Pattern 5 — maps to existing endpoints):

| Probe | Path | Source endpoint |
|-------|------|-----------------|
| startupProbe | `/health/ready` | `app/api/routes/health.py` lines 20–31 |
| readinessProbe | `/health/ready` | same |
| livenessProbe | `/health/live` | `app/api/routes/health.py` lines 15–17 |

**Readiness contract** (`app/api/routes/health.py` lines 20–31):

```python
@router.get("/health/ready")
def health_ready(request: Request):
    if not getattr(request.app.state, "ready", False):
        return JSONResponse(
            status_code=503,
            content=ErrorDetail(
                error="not_ready",
                message="Model is not loaded yet",
                request_id=_request_id(),
            ).model_dump(),
        )
    return {"status": "ready"}
```

**Docker HEALTHCHECK baseline** (`Dockerfile` lines 41–42):

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3); exit(0 if r.status==200 else 1)"
```

**K8s probe values** (startup budget ≥ 120s — 2.7× Docker `start-period=45s`; compose uses 60s):

```yaml
startupProbe:
  httpGet:
    path: /health/ready
    port: http
  periodSeconds: 5
  failureThreshold: 24
  timeoutSeconds: 3
readinessProbe:
  httpGet:
    path: /health/ready
    port: http
  periodSeconds: 5
  failureThreshold: 3
  timeoutSeconds: 3
livenessProbe:
  httpGet:
    path: /health/live
    port: http
  periodSeconds: 10
  failureThreshold: 3
  timeoutSeconds: 3
```

**Compose healthcheck for comparison** (`docker-compose.yml` lines 8–19):

```yaml
healthcheck:
  test:
    [
      "CMD",
      "python",
      "-c",
      "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3); exit(0 if r.status==200 else 1)",
    ]
  interval: 10s
  timeout: 5s
  retries: 6
  start_period: 60s
```

---

### `.helm/templates/service.yaml` (config, request-response)

**Analog:** `docker-compose.yml` `app` service (lines 2–5)

**Compose:**

```yaml
app:
  image: basic-model-serving:local
  ports:
    - "8000:8000"
```

**K8s translation** (D-09/D-12 — NodePort for `minikube service`):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: model-serving
spec:
  type: NodePort
  selector:
    app.kubernetes.io/name: model-serving
  ports:
    - name: http
      port: 8000
      targetPort: 8000
```

**Access pattern:**

```bash
minikube service model-serving --url
```

Do **not** use ClusterIP-only — breaks D-09 without extra tunnel config.

---

### `.helm/templates/configmap.yaml` (config, transform)

**Analog:** `.env.example` + `app/core/config.py` — **exact 1:1 mapping**

**`.env.example`** (lines 1–5):

```bash
TORCH_NUM_THREADS=2
MAX_UPLOAD_BYTES=1048576
URL_TIMEOUT=5.0
LOG_LEVEL=INFO
```

**Pydantic field mapping** (`app/core/config.py` lines 4–10):

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    torch_num_threads: int = 2
    max_upload_bytes: int = 1048576
    url_timeout: float = 5.0
    log_level: str = "INFO"
```

**ConfigMap template** (PERF-04: `TORCH_NUM_THREADS` = CPU limit):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: model-serving-config
data:
  TORCH_NUM_THREADS: "2"        # matches resources.limits.cpu: "2"
  MAX_UPLOAD_BYTES: "1048576"
  URL_TIMEOUT: "5.0"
  LOG_LEVEL: "INFO"
```

**Runtime consumption** (`app/main.py` lines 27–28):

```python
async def lifespan(app: FastAPI):
    torch.set_num_threads(settings.torch_num_threads)
```

---

### `.helm/templates/servicemonitor.yaml` (config, pub-sub)

**Analogs:** `monitoring/prometheus/prometheus.yml` (scrape target), `app/metrics/prometheus.py` (metric names)

**Compose scrape config** (`monitoring/prometheus/prometheus.yml` lines 7–11):

```yaml
scrape_configs:
  - job_name: app
    metrics_path: /metrics
    static_configs:
      - targets: ['app:8000']
```

**K8s ServiceMonitor translation** (`05-RESEARCH.md` Pattern 3):

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: model-serving
  labels:
    release: {{ .Release.Name }}   # NOT hardcoded prometheus-stack
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: model-serving
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

**Critical label rule:** With `serviceMonitorSelectorNilUsesHelmValues: true`, ServiceMonitor must carry `release: {{ .Release.Name }}` (e.g. `basic-model-serving-local`). Hardcoding `release: prometheus-stack` causes **silent no-scrape** (D-03, Pitfall 1).

**Metrics contract** (`app/metrics/prometheus.py` lines 8–19, 24–26):

```python
REQUEST_COUNT = Counter("request_count", "Total HTTP requests", ["method", "path", "status"])
REQUEST_DURATION = Histogram("request_duration", "Request duration in seconds", ["method", "path"], ...)
PREDICTION_COUNT = Counter("prediction_count", "Successful predictions")

@metrics_router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

Dashboard PromQL uses `request_count_total`, `request_duration_bucket`, `prediction_count_total` — unchanged from Phase 3.

---

### `.helm/templates/grafana-dashboard.yaml` (config, file-I/O)

**Analogs:** `monitoring/grafana/provisioning/dashboards/dashboard.yml`, compose Grafana volume mounts, Phase 3 dashboard JSON

**Compose provisioning provider** (`monitoring/grafana/provisioning/dashboards/dashboard.yml`):

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

**Compose bind-mount** (`docker-compose.yml` lines 41–48):

```yaml
grafana:
  volumes:
    - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
    - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
  environment:
    GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH: /var/lib/grafana/dashboards/model-serving-overview.json
```

**K8s sidecar ConfigMap pattern** (`05-RESEARCH.md` Pattern 4):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: model-serving-overview
  labels:
    grafana_dashboard: "1"
data:
  model-serving-overview.json: |
    {{ .Files.Get "dashboards/model-serving-overview.json" | nindent 4 }}
```

**Dashboard datasource UID** (`monitoring/grafana/dashboards/model-serving-overview.json` lines 13–16):

```json
"datasource": {
  "type": "prometheus",
  "uid": "prometheus"
}
```

Matches kube-prometheus-stack default sidecar datasource uid — no override needed if uid stays `prometheus`.

**Do NOT provision** compose alert rules (`monitoring/grafana/provisioning/alerting/downtime.yml`) — Phase 6 scope (DOC-06).

---

### `.helm/dashboards/model-serving-overview.json` (config, request-response)

**Analog:** `monitoring/grafana/dashboards/model-serving-overview.json` — **exact copy**

Copy or symlink from `monitoring/grafana/dashboards/model-serving-overview.json` into `.helm/dashboards/` for `.Files.Get` embedding. Phase 3 dashboard is source of truth — visual continuity between compose and K8s demos (D-04).

---

### `scripts/rollout-zero-downtime.sh` (utility, request-response)

**Analogs:** `scripts/docker.py` `_wait_ready()`, `05-RESEARCH.md` Pattern 6

**Readiness polling** (`scripts/docker.py` lines 63–74):

```python
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

**Shell translation** (D-19/D-20):

```bash
#!/usr/bin/env bash
API_URL=$(minikube service model-serving --url | head -1)
while true; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health/ready" || echo "000")
  echo "$(date +%T) $code"
  sleep 0.5
done
```

**Rollout trigger** (second terminal):

```bash
minikube image load basic-model-serving:local
werf converge --env local --dev --without-images \
  --set image.repository=basic-model-serving \
  --set image.tag=local \
  --set image.pullPolicy=IfNotPresent
```

**Success criterion:** No sustained `503`/`000` streak during rollout (transient 503 during pod churn acceptable).

**Script conventions:** Follow `scripts/docker.py` style — module docstring, constants at top, subprocess/curl with explicit timeouts. Register in README; no `pyproject.toml` script entry unless planner chooses (D-16 compose precedent: plain shell command documented).

---

### `.gitignore` (config — modify)

**Analog:** self — extend for Helm chart artifacts

**Add:**

```
.helm/charts/
```

**Commit:** `Chart.lock` (pinned subchart versions). **Ignore:** `.helm/charts/*.tgz` (rebuilt via `werf helm dependency update`).

---

### `README.md` (config — modify)

**Analog:** existing Docker + CI sections (`README.md` lines 5–46, 130–186)

**New section:** `## Kubernetes (minikube + werf)` after CI/GHCR section

**Document (minimum):**

1. **Prerequisites:** minikube sizing (D-16):
   ```bash
   minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=20g
   ```
2. **GHCR deploy path** (production-like):
   ```bash
   werf converge --env local --dev --without-images \
     --set image.repository=ghcr.io/estevaodr/basic-model-serving \
     --set image.tag=$(git rev-parse --short HEAD)
   ```
3. **Local iteration path** (D-06): `uv run docker-build` → `minikube image load basic-model-serving:local` → converge with local tag + `IfNotPresent`
4. **Access:** `minikube service model-serving` (API), `minikube service <grafana-svc>` (Grafana)
5. **Zero-downtime demo:** curl loop script + rollout trigger (D-19/D-20)
6. **Boundary:** CI does not deploy — preserve existing line (`README.md` line 150)

**Preserve:** Docker section, compose stack section, CI/GHCR section unchanged.

---

## Shared Patterns

### Deploy-Only CI Boundary (Phase 4 → Phase 5)

**Source:** `.github/workflows/deploy.yml` + `tests/test_deploy_workflow.py`
**Apply to:** `werf.yaml`, README, all converge docs

CI builds and pushes; werf deploys manually from laptop:

```yaml
# deploy.yml — build+push only, no werf
- uses: docker/build-push-action@v7
  with:
    push: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
    tags: ${{ steps.meta.outputs.tags }}
```

GHCR coordinates:

```yaml
images: ghcr.io/${{ github.repository }}
tags: |
  type=sha,prefix=,format=short
  type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
  type=raw,value=${{ steps.version.outputs.version }},enable=${{ github.ref == 'refs/heads/main' }}
```

No `imagePullSecret` — public GHCR package (D-08).

### Local vs GHCR Image Tags

**Source:** `scripts/docker.py` line 15; `docker-compose.yml` line 3; `deploy.yml`
**Apply to:** `values.yaml`, converge commands, README

| Context | Repository | Tag | pullPolicy |
|---------|------------|-----|------------|
| Local dev / compose | `basic-model-serving` | `local` | default |
| K8s local iteration | `basic-model-serving` | `local` | `IfNotPresent` |
| K8s GHCR deploy | `ghcr.io/estevaodr/basic-model-serving` | short SHA | default |

**Anti-pattern:** `imagePullPolicy: Always` with `minikube image load` — ignores loaded image.

### Health Probe Contract (Phase 1/2 → Phase 5)

**Source:** `app/api/routes/health.py` + `Dockerfile` HEALTHCHECK + `docker-compose.yml` healthcheck
**Apply to:** Deployment probes

| Endpoint | Returns | K8s probe |
|----------|---------|-----------|
| `/health/live` | 200 always | livenessProbe |
| `/health/ready` | 503 until model loaded | startupProbe + readinessProbe |

Model load sets `app.state.ready = True` in lifespan (`app/main.py` lines 29–31).

### ConfigMap ↔ Pydantic Settings

**Source:** `.env.example` + `app/core/config.py`
**Apply to:** ConfigMap template, Deployment `envFrom`

Four env vars only — same as compose `.env`. Grafana admin creds stay in subchart values, not app ConfigMap.

### Metrics Contract (Phase 3 → Phase 5)

**Source:** `app/metrics/prometheus.py` + Phase 3 dashboard JSON
**Apply to:** ServiceMonitor path, dashboard provisioning

- Scrape path: `/metrics` on port `http` (8000)
- Scrape interval: `15s` (matches compose `prometheus.yml` global)
- Dashboard datasource uid: `prometheus`
- ServiceMonitor `release` label must match werf Release.Name

### Monitoring Topology Upgrade (Compose → K8s)

**Source:** `docker-compose.yml` vs `05-RESEARCH.md` Pattern 2

| Compose (Phase 3) | K8s (Phase 5) |
|-------------------|---------------|
| Hand-rolled Prometheus container | kube-prometheus-stack subchart |
| Static `scrape_configs` in `prometheus.yml` | ServiceMonitor CR + Operator discovery |
| Grafana file provisioning bind-mount | Sidecar-labeled ConfigMap |
| `depends_on: service_healthy` | readinessProbe gates Service endpoints |

Single `werf converge` replaces separate `helm install prometheus-stack` (user-locked D-02).

### minikube Service Exposure

**Source:** `05-CONTEXT.md` D-09/D-10
**Apply to:** Service types, README access docs

- API: `minikube service model-serving`
- Grafana: `minikube service <grafana-svc>` (NodePort via subchart values)
- Prometheus UI: optional `kubectl port-forward` (secondary discretion)
- No Ingress, no minikube tunnel (D-11)

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.helm/Chart.yaml` | config | batch | First Helm chart in repo — use `05-RESEARCH.md` Pattern 2 |
| `.helm/Chart.lock` | config | batch | Generated by `werf helm dependency update` — no prior lockfile |
| `.helm/templates/servicemonitor.yaml` | config | pub-sub | No ServiceMonitor/Operator CRs exist — compose uses static scrape only |
| `.helm/templates/grafana-dashboard.yaml` | config | file-I/O | Compose uses bind-mount provisioning; K8s uses sidecar ConfigMap pattern (RESEARCH Pattern 4) |

## Metadata

**Analog search scope:** Repo root, `app/`, `monitoring/`, `scripts/`, `.github/workflows/`, `.planning/research/`, `.planning/phases/03-*`, `.planning/phases/04-*`, `.cursor/rules/`
**Files scanned:** ~35 relevant paths (0 werf/helm files — greenfield K8s packaging)
**Pattern extraction date:** 2026-07-09
**Primary references:** Phase 2 container (`Dockerfile`, `docker-compose.yml`, `.env.example`), Phase 3 monitoring (`prometheus.yml`, Grafana provisioning, dashboard JSON), Phase 4 CI (`deploy.yml`, `04-PATTERNS.md`), Phase 5 research patterns
**Net-new territory:** All `werf.yaml`, `.helm/` chart templates, ServiceMonitor, kube-prometheus-stack subchart wiring — planner must lean on `05-RESEARCH.md` for Helm/kube-prometheus-stack specifics; app/config/health/metrics contracts are fully covered by existing code excerpts above

## PATTERN MAPPING COMPLETE

**Phase:** 5 - Kubernetes Deployment (via werf)
**Files classified:** 14 net-new/modified + 8 integration references
**Analogs found:** 10 / 14

### Coverage
- Files with exact analog: 2 (`configmap.yaml` mapping, dashboard JSON copy)
- Files with role-match analog: 2 (`deployment.yaml`, `rollout-zero-downtime.sh`)
- Files with partial analog: 6 (`werf.yaml`, `values.yaml`, `service.yaml`, `servicemonitor.yaml`, `grafana-dashboard.yaml`, `README.md`, `.gitignore`)
- Files with no analog: 4 (`Chart.yaml`, `Chart.lock`, ServiceMonitor CR pattern, sidecar dashboard ConfigMap — all greenfield K8s)

### Key Patterns Identified
- **Deploy-only werf:** `--without-images` + plain `values.image.repository/tag`; optional `werf.yaml` build for local only — CI owns GHCR artifact
- **Compose → K8s parity:** ConfigMap mirrors `.env.example`; probes mirror Dockerfile/compose healthcheck; dashboard JSON reused verbatim
- **ServiceMonitor release label:** Template `{{ .Release.Name }}`, never hardcode `prometheus-stack` — silent scrape failure otherwise
- **Model-load probes:** startupProbe on `/health/ready` (120s budget); liveness on `/health/live` only after startup succeeds
- **Zero-downtime rollout:** 2 replicas + `maxUnavailable: 0` + readiness gating; curl loop proof from `scripts/docker.py` polling pattern
- **PERF-04:** ConfigMap `TORCH_NUM_THREADS=2` matches CPU limit; consumed by `torch.set_num_threads()` in lifespan
- **minikube access:** NodePort Services + `minikube service` for API and Grafana — no Ingress

### File Created
`.planning/phases/05-kubernetes-deployment-via-werf/05-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner should reference concrete excerpts above when writing PLAN.md — especially deploy-only werf converge commands, ConfigMap↔Settings mapping, probe values from Dockerfile baseline, and ServiceMonitor label matching werf Release.Name.
