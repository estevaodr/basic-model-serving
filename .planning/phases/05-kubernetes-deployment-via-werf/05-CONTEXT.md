# Phase 5: Kubernetes Deployment (via werf) - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Deploy the CI-built API image to local minikube via `werf converge`, creating a self-healing, configurable, zero-downtime Kubernetes deployment: Deployment (CPU/memory requests/limits, 2 replicas), Service (`model-serving`), ConfigMap (four env vars), startup/liveness/readiness probes wired to model-load state, rolling updates with `maxUnavailable: 0`, and `TORCH_NUM_THREADS` matched to the pod CPU limit (K8S-01–K8S-06, PERF-04).

The werf chart also bundles **kube-prometheus-stack** so a single `werf converge` brings up in-cluster monitoring that scrapes `/metrics` via ServiceMonitor and provisions the Phase 3 **Model Serving Overview** Grafana dashboard.

**Out of scope for this phase:** Automated CI→K8s deploy (PROJECT.md Out of Scope), cloud K8s, HPA, Ingress, auth, new API features, formal load-test proof (PERF-01–03 → Phase 6), README polish beyond minimal deploy/rollout commands (Phase 6), SLO/latency alert demo (DOC-06 → Phase 6).

</domain>

<decisions>
## Implementation Decisions

### K8s Monitoring Stack
- **D-01:** Use **kube-prometheus-stack** (Prometheus Operator + bundled Grafana) — not hand-rolled Prometheus/Grafana manifests and not app-only without in-cluster monitoring.
- **D-02:** **Bundle kube-prometheus-stack in the werf chart** — one `werf converge` deploys app + monitoring together (not a separate one-time `helm install` in a side namespace).
- **D-03:** App chart includes a **ServiceMonitor** for `/metrics` with the correct **`release: prometheus-stack`** label (or equivalent matching the bundled stack's `serviceMonitorSelector`) — omitting this is a known silent-scrape failure mode.
- **D-04:** **Reuse Phase 3 dashboard** — provision `monitoring/grafana/dashboards/model-serving-overview.json` into the K8s Grafana instance (same "Model Serving Overview" panels reviewers already saw in compose).

### Image Source & werf Build Model
- **D-05:** **Default deploy** references the **CI-built GHCR image by short git SHA** — `ghcr.io/estevaodr/basic-model-serving:<sha>` passed at converge time (e.g. `--set image.tag=<sha>`); reproducible, matches Phase 4 tagging.
- **D-06:** **Local iteration path** documented: `uv run docker-build` → `minikube image load basic-model-serving:local` → `werf converge` with local tag override — fast inner loop without waiting for CI.
- **D-07:** `werf.yaml` keeps an **optional Docker build** definition but **defaults to external CI image** — deploy-only is the normal path; build only when explicitly requested (research Anti-Pattern 3: don't let werf and CI both own the default build).
- **D-08:** **No imagePullSecret** — GHCR package is public (Phase 4 D-10); minikube pulls anonymously.

### Service Exposure (Host → Cluster)
- **D-09:** API Service type supports **`minikube service`** — primary documented access path from the laptop (not kubectl port-forward, not raw NodePort docs).
- **D-10:** **Same `minikube service` pattern for Grafana** (and Prometheus if exposed) — consistent reviewer UX across API and monitoring UIs.
- **D-11:** **No Ingress** — no minikube ingress addon; keep exposure simple for a portfolio demo.
- **D-12:** API Kubernetes Service name is **`model-serving`** — used in `minikube service`, scrape targets, and ServiceMonitor selectors.

### Pod Resource Sizing & PERF-04
- **D-13:** API pod **CPU limit 2 / request 1** — enough headroom for ResNet-50 on a 4-CPU minikube node with monitoring stack co-resident.
- **D-14:** API pod **memory limit 2Gi / request 1Gi** — comfortable for baked ResNet-50 weights + PyTorch runtime overhead.
- **D-15:** **TORCH_NUM_THREADS = integer CPU limit** (value `2` when limit is `2`) supplied via **ConfigMap** — satisfies PERF-04; same four env vars as Phase 2 (`TORCH_NUM_THREADS`, `MAX_UPLOAD_BYTES`, `URL_TIMEOUT`, `LOG_LEVEL`).
- **D-16:** Document recommended minikube sizing: **`minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=20g`** — STACK.md default; sized for API + kube-prometheus-stack on one node.

### Zero-Downtime Rollout (K8S-05)
- **D-17:** API Deployment runs **2 replicas** — always one ready pod during rollouts.
- **D-18:** Rolling update strategy **`maxUnavailable: 0`, `maxSurge: 1`** — never drop below desired ready count during rollout.
- **D-19:** Zero-downtime proof via **documented curl loop** hammering `/health/ready` (or `/predict`) while a rollout runs — human-runnable script or README steps, not an in-cluster Job.
- **D-20:** Rollout demo triggered by **`minikube image load` + `werf converge` with new local tag** — fast iteration path; GHCR SHA deploy remains the documented "production-like" path but demo uses local reload.

### Carried Forward (not re-discussed — locked from prior phases, PROJECT.md, research)
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — K8S-01–K8S-06, PERF-04 acceptance criteria
- `.planning/ROADMAP.md` — Phase 5 goal, success criteria, dependency on Phases 1–2
- `.planning/PROJECT.md` — werf choice, manual deploy boundary, minikube-only, Out of Scope for CI→K8s

### Prior phase context
- `.planning/phases/02-containerization/02-CONTEXT.md` — Image tag `basic-model-serving:local`, four env vars, baked weights, health probes for K8s
- `.planning/phases/04-ci-cd-pipeline/04-CONTEXT.md` — GHCR tagging (SHA + latest + semver), public package, CI deploy-only boundary
- `.planning/phases/03-local-dev-stack-dashboards/03-CONTEXT.md` — Model Serving Overview dashboard, compose monitoring patterns (reuse dashboard JSON in K8s)

### Research
- `.planning/research/STACK.md` — werf v2 layout, minikube sizing, kube-prometheus-stack + ServiceMonitor pattern, `TORCH_NUM_THREADS` cgroup guidance, GHCR auth for local `werf converge`
- `.planning/research/ARCHITECTURE.md` — `.helm/` structure, werf.yaml binding, deploy-only CI image reference (Anti-Pattern 3), probe wiring, ConfigMap env injection
- `.planning/research/PITFALLS.md` — Pitfall 2 (thread/CPU mismatch), Pitfall 5 (startupProbe vs liveness mid-load), Pitfall 6 (minikube OOM)
- `.planning/research/SUMMARY.md` — Open monitoring topology tension (resolved here: kube-prometheus-stack bundled in werf)

### Implementation assets
- `Dockerfile` — Image CI builds and werf optionally builds; health endpoints for probes
- `app/core/config.py` — Four pydantic-settings env vars for ConfigMap
- `app/api/routes/health.py` — `/health/live`, `/health/ready` probe contracts
- `monitoring/grafana/dashboards/model-serving-overview.json` — Dashboard to provision in K8s Grafana
- `monitoring/prometheus/prometheus.yml` — Compose scrape config (reference only; K8s uses ServiceMonitor)
- `.github/workflows/deploy.yml` — GHCR push tags CI produces (SHA, latest, semver)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Dockerfile` + Phase 2 image — CI pushes to GHCR; local `basic-model-serving:local` loadable into minikube
- `app/core/config.py` — ConfigMap maps 1:1 to `TORCH_NUM_THREADS`, `MAX_UPLOAD_BYTES`, `URL_TIMEOUT`, `LOG_LEVEL`
- `app/api/routes/health.py` — Ready-made startup/liveness/readiness probe targets
- `app/metrics/prometheus.py` — `/metrics` endpoint scraped via ServiceMonitor
- `monitoring/grafana/dashboards/model-serving-overview.json` — Reuse as K8s Grafana provisioning source
- `.github/workflows/deploy.yml` — Source of truth for GHCR image coordinates and tag scheme

### Established Patterns
- CI owns build+push; werf owns deploy — image referenced by repo+tag, not rebuilt by default
- Model-load-aware readiness — `app.state.ready` gates `/health/ready`; startupProbe must cover load window
- Phase 3 compose uses hand-rolled monitoring; Phase 5 deliberately upgrades to Operator-based discovery in K8s
- Portfolio clarity — `minikube service` for reviewer-friendly URLs; no Ingress complexity

### Integration Points
- **Net-new:** `werf.yaml`, `.helm/` chart (Deployment, Service, ConfigMap, ServiceMonitor, kube-prometheus-stack values)
- **GHCR:** `ghcr.io/estevaodr/basic-model-serving:<sha>` default image ref at converge
- **minikube:** `minikube image load` for local-tag iteration; `minikube service model-serving` for API access
- **ConfigMap → pod env:** Same injection pattern as compose `environment:` / `.env`

</code_context>

<specifics>
## Specific Ideas

- User explicitly chose **kube-prometheus-stack bundled in werf** over the research-recommended separate `helm install` — single converge command is the hero workflow
- **ServiceMonitor with correct release label** — user aware of the silent-scrape footgun from research annotations
- **`minikube service` for both API and Grafana** — consistent with minikube-native reviewer experience
- **2 replicas + maxUnavailable: 0** — strong zero-downtime story for portfolio proof
- **Rollout demo via local image reload** — prioritizes fast demo iteration over waiting for CI on every rollout test
- **Reuse compose dashboard JSON** — visual continuity between Phase 3 compose demo and Phase 5 K8s demo

</specifics>

<deferred>
## Deferred Ideas

- **Separate one-time `helm install` for monitoring** — rejected; user chose bundled werf chart instead (STACK.md alternative)
- **Hand-rolled K8s Prometheus/Grafana manifests** — rejected in favor of kube-prometheus-stack
- **Ingress / minikube tunnel** — rejected; `minikube service` without Ingress addon
- **In-cluster Job for rollout proof** — rejected; curl loop in README/scripts preferred
- **GHCR-only deploy with no `minikube image load`** — rejected for iteration path; both paths documented but demo uses local load

None else — discussion stayed within phase scope

</deferred>

---

*Phase: 5-Kubernetes Deployment (via werf)*
*Context gathered: 2026-07-09*
