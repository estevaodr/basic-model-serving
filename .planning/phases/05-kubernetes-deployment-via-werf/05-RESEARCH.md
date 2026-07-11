# Phase 5: Kubernetes Deployment (via werf) - Research

**Researched:** 2026-07-09
**Domain:** werf + Helm/Nelm deploy to minikube, kube-prometheus-stack bundling, ML-serving probes, zero-downtime rollouts
**Confidence:** HIGH (locked CONTEXT decisions + verified official werf/kube-prometheus-stack/minikube docs) / MEDIUM (probe timing budgets, subchart resource tuning on 8GB minikube — not benchmarked on this host during research)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### K8s Monitoring Stack
- **D-01:** Use **kube-prometheus-stack** (Prometheus Operator + bundled Grafana) — not hand-rolled Prometheus/Grafana manifests and not app-only without in-cluster monitoring.
- **D-02:** **Bundle kube-prometheus-stack in the werf chart** — one `werf converge` deploys app + monitoring together (not a separate one-time `helm install` in a side namespace).
- **D-03:** App chart includes a **ServiceMonitor** for `/metrics` with the correct **`release: prometheus-stack`** label (or equivalent matching the bundled stack's `serviceMonitorSelector`) — omitting this is a known silent-scrape failure mode.
- **D-04:** **Reuse Phase 3 dashboard** — provision `monitoring/grafana/dashboards/model-serving-overview.json` into the K8s Grafana instance (same "Model Serving Overview" panels reviewers already saw in compose).

#### Image Source & werf Build Model
- **D-05:** **Default deploy** references the **CI-built GHCR image by short git SHA** — `ghcr.io/estevaodr/basic-model-serving:<sha>` passed at converge time (e.g. `--set image.tag=<sha>`); reproducible, matches Phase 4 tagging.
- **D-06:** **Local iteration path** documented: `uv run docker-build` → `minikube image load basic-model-serving:local` → `werf converge` with local tag override — fast inner loop without waiting for CI.
- **D-07:** `werf.yaml` keeps an **optional Docker build** definition but **defaults to external CI image** — deploy-only is the normal path; build only when explicitly requested (research Anti-Pattern 3: don't let werf and CI both own the default build).
- **D-08:** **No imagePullSecret** — GHCR package is public (Phase 4 D-10); minikube pulls anonymously.

#### Service Exposure (Host → Cluster)
- **D-09:** API Service type supports **`minikube service`** — primary documented access path from the laptop (not kubectl port-forward, not raw NodePort docs).
- **D-10:** **Same `minikube service` pattern for Grafana** (and Prometheus if exposed) — consistent reviewer UX across API and monitoring UIs.
- **D-11:** **No Ingress** — no minikube ingress addon; keep exposure simple for a portfolio demo.
- **D-12:** API Kubernetes Service name is **`model-serving`** — used in `minikube service`, scrape targets, and ServiceMonitor selectors.

#### Pod Resource Sizing & PERF-04
- **D-13:** API pod **CPU limit 2 / request 1** — enough headroom for ResNet-50 on a 4-CPU minikube node with monitoring stack co-resident.
- **D-14:** API pod **memory limit 2Gi / request 1Gi** — comfortable for baked ResNet-50 weights + PyTorch runtime overhead.
- **D-15:** **TORCH_NUM_THREADS = integer CPU limit** (value `2` when limit is `2`) supplied via **ConfigMap** — satisfies PERF-04; same four env vars as Phase 2 (`TORCH_NUM_THREADS`, `MAX_UPLOAD_BYTES`, `URL_TIMEOUT`, `LOG_LEVEL`).
- **D-16:** Document recommended minikube sizing: **`minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=20g`** — STACK.md default; sized for API + kube-prometheus-stack on one node.

#### Zero-Downtime Rollout (K8S-05)
- **D-17:** API Deployment runs **2 replicas** — always one ready pod during rollouts.
- **D-18:** Rolling update strategy **`maxUnavailable: 0`, `maxSurge: 1`** — never drop below desired ready count during rollout.
- **D-19:** Zero-downtime proof via **documented curl loop** hammering `/health/ready` (or `/predict`) while a rollout runs — human-runnable script or README steps, not an in-cluster Job.
- **D-20:** Rollout demo triggered by **`minikube image load` + `werf converge` with new local tag** — fast iteration path; GHCR SHA deploy remains the documented "production-like" path but demo uses local reload.

#### Carried Forward (not re-discussed — locked from prior phases, PROJECT.md, research)
- Deploy is **manual `werf converge`** from the developer laptop — CI stops at build+push (Phase 4)
- **werf** is the deploy tool; chart lives at **`.helm/`** + **`werf.yaml`** at repo root (research layout)
- Health probes use **`/health/live`** (process) and **`/health/ready`** (model loaded) — Phase 1/2; K8s needs **startupProbe** sized for model-load time (PITFALLS.md Pitfall 5)
- GHCR image `ghcr.io/estevaodr/basic-model-serving` with short SHA + latest + semver tags (Phase 4)
- Local compose tag `basic-model-serving:local` unchanged — compose and K8s are parallel deploy targets
- No HPA, no auth, no cloud K8s, no CI auto-deploy

### Claude's Discretion
- Exact **startupProbe** `failureThreshold × periodSeconds` budget from Docker HEALTHCHECK `--start-period=45s` baseline and minikube CPU reality
- **kube-prometheus-stack bundling mechanism** — Helm subchart dependency vs. werf helm chart with embedded values; planner picks cleanest single-converge layout
- Exact **ServiceMonitor** label key/value matching the bundled stack's release name and `serviceMonitorSelectorNilUsesHelmValues` setting
- **werf.yaml optional build** flag ergonomics (`--require-built-images` vs. env toggle) and local-tag vs. SHA values file structure
- Curl-loop rollout proof script location (`scripts/` vs. `docs/`) and exact endpoints to hammer
- Whether Prometheus UI is exposed via `minikube service` or documented port-forward only (Grafana is `minikube service`; Prometheus access is secondary)

### Deferred Ideas (OUT OF SCOPE)
- **Separate one-time `helm install` for monitoring** — rejected; user chose bundled werf chart instead (STACK.md alternative)
- **Hand-rolled K8s Prometheus/Grafana manifests** — rejected in favor of kube-prometheus-stack
- **Ingress / minikube tunnel** — rejected; `minikube service` without Ingress addon
- **In-cluster Job for rollout proof** — rejected; curl loop in README/scripts preferred
- **GHCR-only deploy with no `minikube image load`** — rejected for iteration path; both paths documented but demo uses local load
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| K8S-01 | Deployment manifest specifies CPU/memory resource requests and limits | Locked D-13/D-14 values; standard Deployment `resources` block in `.helm/templates/` |
| K8S-02 | Service exposes the API within the local minikube cluster | Service name `model-serving` (D-12); type **NodePort** for `minikube service` (D-09) |
| K8S-03 | ConfigMap supplies application configuration in-cluster | Four env vars map 1:1 to `app/core/config.py`; inject via `envFrom` / `configMapRef` |
| K8S-04 | Liveness, readiness, and startup probes reflect model-load state | `/health/live`, `/health/ready` endpoints exist; startupProbe budget ≥ Dockerfile `start-period=45s` + buffer |
| K8S-05 | Rolling updates achieve zero downtime | 2 replicas + `maxUnavailable: 0` + readiness gating; curl-loop proof script |
| K8S-06 | Deployment to minikube via manual `werf converge` | `werf.yaml` + `.helm/` chart; `--without-images` deploy-only default; no CI werf step |
| PERF-04 | PyTorch thread count matches pod CPU limit | ConfigMap `TORCH_NUM_THREADS=2` when CPU limit is `2`; app already calls `torch.set_num_threads()` in lifespan |
</phase_requirements>

## Summary

Phase 5 is a **greenfield Kubernetes packaging phase** — no `werf.yaml` or `.helm/` chart exists yet. The app, Dockerfile, CI GHCR push, compose monitoring, and health/metrics endpoints are ready; this phase wires them into a single `werf converge` that deploys the API **and** a bundled **kube-prometheus-stack** subchart.

The critical architectural decision from discuss-phase (resolving STACK.md vs ARCHITECTURE.md tension) is **locked**: bundle kube-prometheus-stack inside the werf Helm chart as a dependency, not a separate `helm install`. Deploy-only is the default path: CI owns build+push; werf references the GHCR image by SHA via Helm values and **`werf converge --without-images`**, avoiding Anti-Pattern 3 (dual build paths). An optional `image:` section in `werf.yaml` remains for explicit local `werf build` only.

The highest-risk footguns are operational, not code: **ServiceMonitor `release` label mismatch** (silent no-scrape), **startupProbe too short** (CrashLoopBackOff during model load), **minikube undersized** (OOM with kube-prometheus-stack), and **`imagePullPolicy: Always`** ignoring `minikube image load`. Each has a documented mitigation below.

**Primary recommendation:** Use a parent `.helm/` chart with (1) app templates (Deployment/Service/ConfigMap/ServiceMonitor), (2) `kube-prometheus-stack` Helm dependency (~87.x), (3) default converge command `werf converge --env local --dev --without-images --set image.tag=<sha>`, and (4) NodePort Services for `minikube service model-serving` and Grafana.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| API inference & health | API / Backend (pod) | — | FastAPI process serves `/predict`, `/health/*`, `/metrics` |
| App config (env vars) | Database / Storage (ConfigMap) | API pod | K8s ConfigMap injected as env; pydantic-settings reads at startup |
| In-cluster routing | API / Backend (Service) | — | `model-serving` ClusterIP/NodePort selects app pods |
| Host → cluster access | CDN / Static (minikube tunnel helper) | Service (NodePort) | `minikube service` creates host tunnel to NodePort — not Ingress |
| Metrics scrape config | Database / Storage (ServiceMonitor CR) | Monitoring operator | Prometheus Operator discovers ServiceMonitor CRs, not app code |
| Prometheus + Grafana runtime | API / Backend (monitoring pods) | — | kube-prometheus-stack subchart runs in-cluster; app stays pull-only at `/metrics` |
| Dashboard provisioning | Database / Storage (ConfigMap) | Grafana sidecar | Sidecar watches labeled ConfigMaps; no manual UI clicks |
| Image artifact | CI (GitHub Actions → GHCR) | Local docker build + `minikube image load` | werf deploy references pre-built image; does not rebuild by default |
| Rollout orchestration | API / Backend (Deployment controller) | werf/Nelm | Kubernetes rolling update + probe semantics; werf applies manifests |

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| werf | **1.2.339** on research host; docs target **v2.x** [CITED: werf.io/docs/v2] | Deploy orchestration (Nelm/Helm) | Project-locked; `--without-images`, `--env`, `--dev` confirmed on installed CLI |
| Helm (via werf) | 3.18.4 (host) | Chart templating + dependencies | werf uses Nelm, backward-compatible with Helm charts [CITED: werf.io/docs/v2/usage/deploy/overview.html] |
| kube-prometheus-stack | **87.12.2** (chart) / Prometheus Operator v0.92.1 [VERIFIED: helm search] | In-cluster Prometheus + Grafana + Operator | User-locked D-01/D-02; industry default for K8s monitoring |
| minikube | v1.36.0 (host) | Local K8s cluster | Project-locked; docker driver + explicit CPU/RAM |
| kubectl | v1.33.3 client (host) | Cluster inspection | Standard K8s CLI |

### Supporting (existing — not installed in this phase)

| Asset | Purpose |
|-------|---------|
| `ghcr.io/estevaodr/basic-model-serving:<short-sha>` | Default CI-built image (Phase 4 `deploy.yml` tags) |
| `basic-model-serving:local` | Local iteration image (`minikube image load`) |
| `monitoring/grafana/dashboards/model-serving-overview.json` | Dashboard JSON reused in K8s Grafana |
| `app/core/config.py` | ConfigMap key source (4 env vars) |
| `app/api/routes/health.py` | Probe HTTP targets |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Bundled kube-prometheus-stack (locked) | Separate `helm install` in `monitoring` ns | Rejected by user — breaks single-converge hero workflow |
| Hand-rolled Prom/Grafana manifests | kube-prometheus-stack | Rejected by user — loses Operator/ServiceMonitor pattern |
| `global.werf.images.*` in templates | Plain `values.image.repository/tag` + `--without-images` | External CI image is not a werf build artifact; plain values avoid dual-build confusion |
| `kubectl port-forward` for access | `minikube service` (locked) | port-forward is secondary; user wants reviewer-friendly minikube UX |
| Ingress / minikube tunnel | NodePort + `minikube service` | Rejected — no Ingress addon |

**Default converge (GHCR SHA):**
```bash
werf converge --env local --dev --without-images \
  --set image.repository=ghcr.io/estevaodr/basic-model-serving \
  --set image.tag=$(git rev-parse --short HEAD)
```

**Local iteration converge:**
```bash
minikube image load basic-model-serving:local
werf converge --env local --dev --without-images \
  --set image.repository=basic-model-serving \
  --set image.tag=local \
  --set image.pullPolicy=IfNotPresent
```

## Package Legitimacy Audit

> No new application runtime packages (pip/npm) in this phase. Only Helm chart dependencies from the official prometheus-community repository.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| kube-prometheus-stack (Helm chart) | Helm / Artifact Hub | Mature (years) | Very high | github.com/prometheus-community/helm-charts | OK | Approved — official chart repo |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Developer laptop (manual deploy — CI does NOT reach cluster)               │
│  git push → GitHub Actions → GHCR (sha/latest/semver)                       │
│  werf converge --without-images --set image.tag=<sha>                       │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ applies Helm release (Nelm)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  minikube cluster (namespace: basic-model-serving-local)                    │
│                                                                             │
│  ┌─────────────────────────────── werf .helm chart ─────────────────────┐  │
│  │  App templates                    kube-prometheus-stack (subchart)    │  │
│  │  ┌─────────────────────┐         ┌──────────────────────────────┐  │  │
│  │  │ Deployment (×2)      │         │ Prometheus Operator           │  │  │
│  │  │  FastAPI + ResNet-50 │◄─scrape─│ Prometheus StatefulSet        │  │  │
│  │  │  probes → /health/*  │  SM     │ Grafana + dashboard sidecar   │  │  │
│  │  │  env ← ConfigMap     │         │ (7d retention via values)     │  │  │
│  │  └──────────┬──────────┘         └───────────────┬──────────────┘  │  │
│  │             │ Service NodePort                     │ Grafana NodePort │  │
│  │             │ name: model-serving                  │                  │  │
│  └─────────────┼──────────────────────────────────────┼──────────────────┘  │
└────────────────┼──────────────────────────────────────┼─────────────────────┘
                 │                                      │
                 ▼                                      ▼
        minikube service model-serving          minikube service <grafana-svc>
        (API :8000)                             (Grafana :80 → 3000)
```

### Recommended Project Structure

```
.
├── werf.yaml                          # project config; optional image: api for local werf build
├── .helm/
│   ├── Chart.yaml                     # dependencies: kube-prometheus-stack
│   ├── Chart.lock                     # pinned subchart versions (commit)
│   ├── values.yaml                    # app + subchart values
│   ├── values-local.yaml              # optional: local tag overrides
│   └── templates/
│       ├── deployment.yaml            # 2 replicas, probes, resources, envFrom ConfigMap
│       ├── service.yaml               # name: model-serving, type: NodePort
│       ├── configmap.yaml             # 4 env vars, TORCH_NUM_THREADS=2
│       ├── servicemonitor.yaml        # /metrics, release label matches Release.Name
│       └── grafana-dashboard.yaml     # ConfigMap from model-serving-overview.json
├── scripts/
│   └── rollout-zero-downtime.sh       # curl loop during werf converge (discretion)
└── monitoring/grafana/dashboards/
    └── model-serving-overview.json    # source of truth (embedded or copied into chart)
```

### Pattern 1: Deploy-only werf (CI image, no werf rebuild)

**What:** Reference external GHCR image via Helm values; skip werf image build on default path.
**When to use:** Always for normal deploy (D-05, D-07, Anti-Pattern 3).
**Example:**
```yaml
# .helm/templates/deployment.yaml
containers:
  - name: api
    image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
    imagePullPolicy: {{ .Values.image.pullPolicy | default "IfNotPresent" }}
```
```bash
# Default path — no werf build, no --repo required
werf converge --env local --dev --without-images \
  --set image.repository=ghcr.io/estevaodr/basic-model-serving \
  --set image.tag=1bfce01
```
Source: [CITED: github.com/werf/werf deployment_scenarios.md] — `--without-images` disables build and werf image usage in templates; [CITED: werf.io/docs/v2/reference/cli/werf_converge] — flag confirmed on installed werf 1.2.339.

**Optional local werf build path** (explicit only):
```bash
werf converge --env local --dev --repo ghcr.io/estevaodr/basic-model-serving
# uses werf.yaml image: + global.werf.images in templates — NOT the default
```

### Pattern 2: Bundle kube-prometheus-stack as Helm subchart

**What:** Declare chart dependency; configure via nested values; single converge installs CRDs, Operator, Prometheus, Grafana.
**When to use:** Locked D-02.
**Example:**
```yaml
# .helm/Chart.yaml
apiVersion: v2
name: basic-model-serving
version: 0.1.0
dependencies:
  - name: kube-prometheus-stack
    version: "~87.12.0"
    repository: https://prometheus-community.github.io/helm-charts
```
```bash
werf helm dependency update .helm
# commit Chart.lock; add .helm/charts/*.tgz to .gitignore
```
```yaml
# .helm/values.yaml (excerpt)
kube-prometheus-stack:
  prometheus:
    prometheusSpec:
      retention: 7d
      serviceMonitorSelectorNilUsesHelmValues: true   # default — see Pattern 3
  grafana:
    service:
      type: NodePort
    sidecar:
      dashboards:
        enabled: true
        label: grafana_dashboard
        labelValue: "1"
    defaultDashboardsEnabled: true   # keep upstream K8s dashboards; add app dashboard via CM
```
Source: [CITED: werf.io/docs/v2/usage/deploy/charts.html] — dependencies + `werf helm dependency update`; [CITED: prometheus-community/helm-charts kube-prometheus-stack README] — Grafana sidecar loads dashboard ConfigMaps.

### Pattern 3: ServiceMonitor label matching (silent-scrape prevention)

**What:** Prometheus Operator selects ServiceMonitors by labels. With default `serviceMonitorSelectorNilUsesHelmValues: true`, only ServiceMonitors labeled `release: <Helm Release.Name>` are scraped.
**When to use:** Always (D-03).
**Example:**
```yaml
# .helm/templates/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: model-serving
  labels:
    release: {{ .Release.Name }}   # werf: basic-model-serving-local for --env local
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: model-serving
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

**Alternative (broader discovery, acceptable for single-app demo):** set `prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues: false` in subchart values — then any ServiceMonitor in watched namespaces is picked up; less label-sensitive but looser.

> **Note on D-03 wording:** CONTEXT mentions `release: prometheus-stack` as the canonical example from STACK.md (standalone `helm install prometheus-stack`). When bundled under werf, **Release.Name follows werf's `{project}-{env}` convention** (e.g. `basic-model-serving-local`), not `prometheus-stack`. Use `{{ .Release.Name }}` in templates — do not hardcode `prometheus-stack` unless werf release is explicitly named that.

Source: [CITED: prometheus-community/helm-charts values.yaml] — `serviceMonitorSelectorNilUsesHelmValues: true` default.

### Pattern 4: Provision Phase 3 Grafana dashboard via sidecar ConfigMap

**What:** Emit a ConfigMap containing `model-serving-overview.json` with label `grafana_dashboard: "1"`; kube-prometheus-stack Grafana sidecar auto-imports it.
**When to use:** D-04.
**Example:**
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
Place JSON at `.helm/dashboards/model-serving-overview.json` (copy or symlink from `monitoring/grafana/dashboards/`).

**Compatibility:** Existing dashboard panels reference datasource `uid: prometheus` — matches kube-prometheus-stack default sidecar datasource uid [verified in repo JSON + chart values `grafana.sidecar.datasources.uid: prometheus`].

Compose alert rules (`monitoring/grafana/provisioning/alerting/downtime.yml`) are **not** in Phase 5 scope (DOC-06 → Phase 6); dashboard panels alone satisfy MON-02 continuity for the K8s demo.

### Pattern 5: Model-load-aware probes (startup / liveness / readiness)

**What:** Three probe types map to existing endpoints; startupProbe covers model load window before liveness fires.
**When to use:** K8S-04; Pitfall 5 prevention.
**Recommended values (discretion resolved):**

| Probe | Path | periodSeconds | failureThreshold | Budget / behavior |
|-------|------|---------------|------------------|-------------------|
| startupProbe | `/health/ready` | 5 | 24 | **120s** max startup (Docker HEALTHCHECK `start-period=45s` × ~2.7 buffer; compose uses 60s) |
| readinessProbe | `/health/ready` | 5 | 3 | Removes unready pods from Service endpoints |
| livenessProbe | `/health/live` | 10 | 3 | Restarts hung process; only active **after** startupProbe succeeds |

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

Do **not** rely on long `initialDelaySeconds` on liveness — startupProbe supersedes that pattern [CITED: kubernetes.io/docs/concepts/workloads/pods/probes/].

### Pattern 6: Zero-downtime rolling update + curl proof

**What:** 2 replicas + surge 1 + readiness gating ensures Service always has ≥1 ready endpoint during rollout.
**Example:**
```yaml
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
```
**Proof script (D-19/D-20):**
```bash
# Terminal 1 — hammer readiness while rollout runs
API_URL=$(minikube service model-serving --url | head -1)
while true; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health/ready" || echo "000")
  echo "$(date +%T) $code"
  sleep 0.5
done

# Terminal 2 — trigger rollout
minikube image load basic-model-serving:local
werf converge --env local --dev --without-images \
  --set image.repository=basic-model-serving \
  --set image.tag=local \
  --set image.pullPolicy=IfNotPresent
```
Success criterion: no sustained `503`/`000` streak during rollout (transient 503 acceptable during pod churn).

### Anti-Patterns to Avoid

- **Hardcoding `release: prometheus-stack`** when werf release name is `basic-model-serving-local` — silent no metrics.
- **Using `$.Values.global.werf.images.api`** on the default deploy path — forces werf build or empty image when `--without-images` is set.
- **`imagePullPolicy: Always` with `minikube image load`** — cluster re-pulls from registry, ignoring loaded image.
- **Liveness on `/health/ready` without startupProbe** — CrashLoopBackOff during model load.
- **ClusterIP-only Services** — breaks `minikube service` without extra tunnel configuration (D-09/D-10 require NodePort).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Prometheus Operator + CRDs | Raw Prom Deployment + RBAC + CRD YAML | kube-prometheus-stack subchart | CRD lifecycle, scrape discovery, Grafana bundling |
| Service discovery for `/metrics` | Static `scrape_configs` in ConfigMap | ServiceMonitor CR | Operator-native pattern; same as production K8s monitoring |
| Grafana dashboard import | Manual UI upload | Sidecar-labeled ConfigMap | MON-05 provisioning-as-code continuity |
| K8s manifest apply ordering | Shell scripts applying YAML | werf converge (Nelm) | Release tracking, rollback, wait semantics |
| Zero-downtime rollout logic | Custom controller | Deployment `maxUnavailable: 0` + readiness | Built into Kubernetes |

**Key insight:** The portfolio value is demonstrating **standard** K8s monitoring and deploy tooling, not reimplementing Operator or rollout controllers.

## Common Pitfalls

### Pitfall 1: ServiceMonitor label mismatch → no metrics, no error

**What goes wrong:** Grafana dashboard loads but all panels show "No data"; `up{job=...}` missing for app.
**Why it happens:** Default `serviceMonitorSelectorNilUsesHelmValues: true` filters by `release` label.
**How to avoid:** Template `release: {{ .Release.Name }}` on ServiceMonitor; verify in Prometheus UI targets after deploy.
**Warning signs:** ServiceMonitor exists (`kubectl get servicemonitor`) but Prometheus **Targets** page doesn't list it.

### Pitfall 2: Startup probe too aggressive → CrashLoopBackOff

**What goes wrong:** Pod restarts during ResNet-50 load; rollout never completes.
**Why it happens:** Liveness fires before `app.state.ready` is true.
**How to avoid:** startupProbe on `/health/ready` with ≥120s budget; liveness on `/health/live` only.
**Warning signs:** `kubectl describe pod` shows liveness failures at consistent interval during early life.

### Pitfall 3: minikube OOM with kube-prometheus-stack + 2 app replicas

**What goes wrong:** Prometheus/Grafana or app pods `OOMKilled`; Pending pods.
**Why it happens:** Default minikube sizing (2GB) insufficient for full stack (Pitfall 6).
**How to avoid:** Locked D-16: `minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=20g`; set resource requests/limits on app pods.
**Warning signs:** `kubectl get events` shows OOMKilled; monitoring pods pending.

### Pitfall 4: werf giterminism blocks iteration

**What goes wrong:** "Nothing changed" after local edits without commit.
**Why it happens:** werf defaults to committed Git state.
**How to avoid:** Always use `--dev` for local iteration (documented in README); plain converge only from clean commits for reproducible demo.
**Warning signs:** werf errors mentioning uncommitted/untracked files.

### Pitfall 5: TORCH_NUM_THREADS ≠ CPU limit → cgroup throttling

**What goes wrong:** Latency spikes under load after K8s deploy despite fine compose behavior.
**Why it happens:** PyTorch defaults to host CPU count, not pod limit (Pitfall 2 in PITFALLS.md).
**How to avoid:** ConfigMap `TORCH_NUM_THREADS=2` matching `resources.limits.cpu: "2"` (D-15); already wired in `app/main.py`.
**Warning signs:** Elevated `nr_throttled` in pod cgroup stats during load.

### Pitfall 6: GHCR vs local image confusion

**What goes wrong:** `ImagePullBackOff` or wrong image running.
**Why it happens:** Mixed pullPolicy/tag between CI and local paths.
**How to avoid:** Document two explicit converge commands (SHA vs local); `IfNotPresent` for local load path.

## Code Examples

### werf.yaml (minimal + optional build)

```yaml
project: basic-model-serving
configVersion: 1
---
# Optional — used only when NOT passing --without-images
image: api
dockerfile: Dockerfile
context: .
```

### ConfigMap (PERF-04 + K8S-03)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: model-serving-config
data:
  TORCH_NUM_THREADS: "2"        # matches CPU limit (D-15)
  MAX_UPLOAD_BYTES: "1048576"
  URL_TIMEOUT: "5.0"
  LOG_LEVEL: "INFO"
```

### Deployment excerpt (resources + env + strategy)

```yaml
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    spec:
      containers:
        - name: api
          envFrom:
            - configMapRef:
                name: model-serving-config
          resources:
            requests:
              cpu: "1"
              memory: 1Gi
            limits:
              cpu: "2"
              memory: 2Gi
```

### Service (K8S-02, D-09)

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

Source patterns: [CITED: kubernetes.io/docs/concepts/workloads/pods/probes/], [CITED: minikube.sigs.k8s.io/docs/handbook/accessing/], [CITED: github.com/werf/werf deployment_scenarios.md].

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Long `initialDelaySeconds` on liveness | startupProbe + short liveness | K8s 1.20+ (GA) | Model-load apps avoid CrashLoopBackOff |
| Separate `helm install` for monitoring | Subchart in app werf chart | Phase 5 decision (2026-07-09) | Single converge command |
| werf rebuilds image at deploy | `--without-images` + GHCR ref | Phase 4 CI boundary + D-07 | CI owns artifact; werf owns manifests |
| `port-forward` for demo access | `minikube service` NodePort | Phase 5 decision | Reviewer-friendly URLs |

**Deprecated/outdated for this project:**
- ARCHITECTURE.md Anti-Pattern 2 (avoid kube-prometheus-stack) — **superseded** by user decision D-01/D-02
- STACK.md separate `helm install prometheus-stack` — **superseded** by bundled subchart
- Hardcoded `release: prometheus-stack` without verifying werf Release.Name — **unsafe** when release name differs

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | werf release name for `--env local` is `basic-model-serving-local` | ServiceMonitor labels | Silent scrape failure if name differs — verify with `werf converge` output or `helm list` |
| A2 | 120s startupProbe budget sufficient for ResNet-50 on 4-CPU minikube | Probes | CrashLoopBackOff — increase failureThreshold |
| A3 | kube-prometheus-stack ~87.x fits in 8GB minikube alongside 2 app replicas | Environment | OOM — trim default dashboards or reduce Prometheus retention/shards |
| A4 | Dashboard datasource uid `prometheus` matches bundled Grafana | Dashboard provision | Empty panels — add datasource override in subchart values |
| A5 | Installed werf 1.2.339 behaves like v2 docs for `--without-images` | Deploy-only | Flag missing or different semantics — verify `werf converge --help` on target machine |

## Open Questions

1. **Exact Grafana Service name for `minikube service`**
   - What we know: Subchart names Service `{Release.Name}-grafana` or similar depending on fullnameOverride.
   - What's unclear: Whether to set `kube-prometheus-stack.fullnameOverride: prometheus-stack` for stable docs matching STACK.md examples.
   - Recommendation: Set `fullnameOverride: prometheus-stack` in subchart values for predictable Service names (`prometheus-stack-grafana`) **or** document `minikube service -n basic-model-serving-local --url` with label selector; planner should pick one and align README.

2. **Prometheus UI exposure**
   - What we know: D-10 requires Grafana via `minikube service`; Prometheus is secondary discretion.
   - Recommendation: NodePort for Grafana only; document `kubectl port-forward svc/prometheus-operated 9090:9090` for optional Prometheus UI — keeps node port count lower.

3. **Chart.lock commit vs .gitignore for `.helm/charts/*.tgz`**
   - What we know: werf docs recommend gitignore tgz, commit Chart.lock.
   - Recommendation: Commit Chart.lock; gitignore `.helm/charts/`; CI lint job can run `werf helm dependency build` to validate.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | minikube docker driver | ✓ | 29.6.1 | — |
| minikube | K8S-02, K8S-06 | ✓ (not running) | v1.36.0 | `minikube start` per D-16 |
| kubectl | deploy verification | ✓ | v1.33.3 client | — |
| helm | chart dependency fetch | ✓ | v3.18.4 | werf bundles helm |
| werf | K8S-06 | ✓ | v1.2.339 | — |
| GHCR public pull | D-05 default deploy | ✓ (network) | — | `minikube image load` local path |
| 8GB RAM for minikube | D-16 + kube-prometheus-stack | ✓ (host assumed) | — | Reduce replicas to 1 **only if** demo fails — conflicts with K8S-05; prefer resize |

**Missing dependencies with no fallback:**
- None on research host — minikube cluster not started (expected pre-plan).

**Missing dependencies with fallback:**
- None blocking — cluster start is a documented prerequisite step in plan Wave 0.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No API auth by design (portfolio demo) |
| V3 Session Management | no | Stateless API |
| V4 Access Control | partial | Grafana admin password via Secret/env; change from chart default |
| V5 Input Validation | yes (app layer) | Already implemented — SSRF, upload limits; unchanged in Phase 5 |
| V6 Cryptography | no | No TLS inside minikube demo cluster |

### Known Threat Patterns for {stack}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Grafana default admin credentials | Spoofing | Override `grafana.adminPassword` via Secret in values |
| Over-broad ServiceMonitor selector (`NilUsesHelmValues: false`) | Information disclosure | Acceptable for local demo; scrapes only in-cluster metrics |
| Public GHCR image inspection | Information disclosure | No secrets in image layers (config via env); public by design D-08 |
| SSRF via `/predict` URL | Tampering | Already mitigated in app (Phase 1) — not Phase 5 scope |

## Sources

### Primary (HIGH confidence)
- werf deployment scenarios — `--without-images`, build/deploy split — https://github.com/werf/werf/blob/main/docs/pages_en/usage/deploy/deployment_scenarios.md
- werf deploy overview — Helm charts, Nelm — https://werf.io/docs/v2/usage/deploy/overview.html
- werf charts and dependencies — https://werf.io/docs/v2/usage/deploy/charts.html
- kube-prometheus-stack values — `serviceMonitorSelectorNilUsesHelmValues`, Grafana sidecar — https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/values.yaml
- Kubernetes probes — startup/liveness/readiness semantics — https://kubernetes.io/docs/concepts/workloads/pods/probes/
- minikube accessing apps — `minikube service` — https://minikube.sigs.k8s.io/docs/handbook/accessing/

### Secondary (MEDIUM confidence)
- Context7 `/werf/werf` — deploy patterns, `--without-images`, helm dependency update
- Context7 `/prometheus-community/helm-charts` — ServiceMonitor selector, Grafana sidecar dashboards
- Project files: `Dockerfile` (45s start-period), `deploy.yml` (GHCR tags), `05-CONTEXT.md` (locked decisions)
- `.planning/research/PITFALLS.md` — Pitfalls 2, 5, 6, 7

### Tertiary (LOW confidence)
- WebSearch synthesis on probe timing for ML workloads — validated against Kubernetes official docs and kserve PR pattern; specific 120s budget not benchmarked on this minikube node during research

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — werf flags verified on installed CLI; chart version from `helm search`; locked user decisions constrain choices
- Architecture: **HIGH** — deploy-only + subchart bundling follows official werf and prometheus-community patterns
- Pitfalls: **MEDIUM-HIGH** — well-documented community footguns; probe timing and minikube RAM need runtime validation during execute

**Research date:** 2026-07-09
**Valid until:** 2026-08-09 (stable tooling); re-check kube-prometheus-stack major version if execute slips >30 days
