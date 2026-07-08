# Phase 3: Local Dev Stack & Dashboards - Context

**Gathered:** 2026-07-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a single-command local observability stack: `docker-compose up` starts the API (using the Phase 2 `basic-model-serving:local` image), Prometheus, and Grafana together. Grafana displays a provisioned "Model Serving Overview" dashboard with 5–7 panels showing live data from actual `/predict` traffic. Datasource, dashboard, and a downtime alert are provisioned from code (MON-05). Prometheus retains metrics for 7+ days (MON-04). A downtime alert fires when the API is unreachable (MON-03).

**Out of scope for this phase:** CI/CD (Phase 4), Kubernetes manifests or werf deploy (Phase 5), SLO/latency alert demo (DOC-06 → Phase 6), new API features, authentication, bind-mount hot-reload dev mode, `uv run compose-*` wrapper scripts, prediction-confidence histogram panels (OBS-01 → v2).

</domain>

<decisions>
## Implementation Decisions

### Dashboard Panels
- **D-01:** Use an **ops-standard panel set** (7 panels): request rate, p50 latency, p95 latency, error rate, prediction throughput, 4xx vs 5xx breakdown, service up/down, total predictions — aligned with portfolio reviewer expectations from FEATURES.md table stakes.
- **D-02:** Display latency as **percentile stat panels** (single-value p50/p95 numbers updating live), not time-series graphs — clearest at a glance for reviewers.
- **D-03:** Break down errors **by HTTP status code** (4xx vs 5xx panels) using existing `request_count{status=...}` labels from Phase 1 instrumentation.
- **D-04:** Single dashboard named **"Model Serving Overview"**, provisioned as Grafana **home dashboard** — reviewer lands on it immediately after login.

### Reviewer Workflow
- **D-05:** Primary entry command is plain **`docker compose up`** — no `uv run compose-up` wrapper. Documented as the quickstart path in README.
- **D-06:** Live dashboard data comes from **manual curl commands** documented in README (2–3 example `POST /predict` calls) — no bundled traffic generator script or compose profile.
- **D-07:** Expose **standard ports** on the host: API `:8000`, Grafana `:3000`, Prometheus `:9090`. Document in README quickstart table.
- **D-08:** Grafana uses **default admin credentials** (e.g., admin/admin) documented in README and `.env.example` — acceptable login friction for a local portfolio demo.

### Downtime Alert
- **D-09:** Alert rule lives in **Grafana unified alerting** (provisioned with dashboard/stack config), not Prometheus alerting rules — simpler for local demo; Prometheus rules deferred unless needed for Phase 5 K8s stack.
- **D-10:** Include **README demo steps** for the alert: stop API container → wait ~1 min → alert shows **Firing** in Grafana → restart → **Resolved**. Phase 6 (DOC-06) handles the separate SLO/latency alert demo.
- **D-11:** Fire after **~1 minute** of scrape/API failure — fast enough for live demo; account for model startup in compose `depends_on`/healthcheck so alert does not fire during normal boot.
- **D-12:** Notifications are **Grafana UI only** — no email, Slack, or webhook contact points for the local stack.

### Dev Iteration Loop
- **D-13:** **Image-only** API iteration — compose runs the built `basic-model-serving:local` image; code changes require `uv run docker-build` then `docker compose restart api` (or down/up). No bind-mount source override.
- **D-14:** Compose references **pre-built image** (`image: basic-model-serving:local`), not a `build:` directive — prerequisite step `uv run docker-build` documented before first `docker compose up`.
- **D-15:** Monitoring config is **provisioned static files** in `monitoring/` (per ARCHITECTURE.md layout) — edit JSON/YAML → `docker compose restart grafana|prometheus` to pick up changes. No Grafana UI-first export workflow.
- **D-16:** **No new `uv run` compose scripts** in Phase 3 — keep Phase 2's `docker-build|docker-run|docker-smoke` for single-container workflow; compose is plain Docker CLI.

### Carried Forward (not re-discussed — locked from prior phases, research, REQUIREMENTS.md)
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
- `monitoring/` subdirectory structure细节 (exact filenames under `monitoring/prometheus/` and `monitoring/grafana/`)
- Compose service names, network name, and volume strategy for Prometheus TSDB persistence across restarts

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope & requirements
- `.planning/PROJECT.md` — docker-compose local dev decision, monitoring active requirements, portfolio reviewer audience
- `.planning/REQUIREMENTS.md` — CONT-04, MON-02, MON-03, MON-04, MON-05 acceptance criteria
- `.planning/ROADMAP.md` — Phase 3 goal, success criteria, dependency on Phase 2

### Prior phase context (upstream decisions)
- `.planning/phases/01-core-inference-api/01-CONTEXT.md` — Metrics instrumentation, histogram buckets, route-template labels
- `.planning/phases/02-containerization/02-CONTEXT.md` — Image tag `basic-model-serving:local`, uv docker scripts, no compose in Phase 2
- `app/metrics/prometheus.py` — Metric names, labels, histogram buckets consumed by dashboard PromQL
- `Dockerfile` — Image consumed by compose API service
- `pyproject.toml` / `scripts/docker.py` — Existing `uv run docker-build|docker-run|docker-smoke` workflow

### Research (architecture, features, stack)
- `.planning/research/ARCHITECTURE.md` — `monitoring/` directory layout, compose vs K8s scrape config split, build order (compose stack after Dockerfile + metrics)
- `.planning/research/FEATURES.md` — Table-stakes dashboard panels (request rate, latency percentiles, error rate, uptime); SLO alerting deferred to differentiator layer (Phase 6)
- `.planning/research/STACK.md` — Prometheus/Grafana versions and patterns; kube-prometheus-stack guidance applies to Phase 5, not Phase 3 compose
- `.planning/research/SUMMARY.md` — Phase ordering: instrument → scrape → visualize → alert

### State
- `.planning/STATE.md` — Current project position after Phase 2

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/metrics/prometheus.py` — `request_count{method,path,status}`, `request_duration{method,path}` histogram, `prediction_count` counter — all dashboard PromQL derives from these
- `Dockerfile` + Phase 2 image — compose API service runs `basic-model-serving:local`; no rebuild in compose
- `tests/fixtures/sample.jpg` — sample image for README curl examples and manual traffic generation
- `uv run docker-build` — documented prerequisite before first `docker compose up`

### Established Patterns
- Phase 1 route-template path labels on metrics — dashboard queries should use template paths (e.g., `/predict`), not raw URLs
- Phase 2 env-var config via pydantic-settings — compose passes same four vars (`TORCH_NUM_THREADS`, etc.) via `environment:` or `.env`
- ARCHITECTURE.md prescribes `monitoring/prometheus/prometheus.yml` (compose scrape target `app:8000`) and `monitoring/grafana/provisioning/` for datasource + dashboard JSON

### Integration Points
- Prometheus scrapes `http://app:8000/metrics` on the compose network — API service name must match scrape config
- Grafana datasource points at Prometheus service DNS on compose network — provisioned via `datasources/*.yml`
- `/health/ready` — compose healthcheck and alert startup grace should respect model-load time
- README quickstart section — will gain compose instructions, port table, curl examples, alert demo steps (Phase 3 deliverable, not Phase 6)

</code_context>

<specifics>
## Specific Ideas

- User wants an **ops-standard dashboard** that reads as production-aware to hiring-manager reviewers, not a minimal 5-panel skim
- **Plain `docker compose up`** as the hero command — consistent with standard Docker conventions; no uv wrapper layer
- **Manual curl traffic** keeps the demo transparent (reviewer sees exactly what generates metrics)
- **Grafana unified alerting with README demo steps** — tangible proof MON-03 is met without standing up Alertmanager or webhooks
- **Image-only dev loop** prioritizes dev/prod parity over bind-mount convenience — acceptable because Phase 2 bake is the source of truth

</specifics>

<deferred>
## Deferred Ideas

- **SLO/latency alert demo** — Phase 6 (DOC-06); Phase 3 covers downtime only (MON-03)
- **`uv run compose-up` / `compose-smoke` scripts** — user rejected; plain Docker CLI for compose
- **Bind-mount API source for hot reload** — user rejected; rebuild image workflow retained
- **Bundled traffic generator** (script or compose profile) — user chose manual curl in README
- **Anonymous Grafana access** — user chose default admin credentials instead
- **Prediction-confidence histogram panel** — v2 OBS-01; not in Phase 3 panel set
- **kube-prometheus-stack for K8s** — Phase 5 open decision; does not block Phase 3 hand-rolled compose stack

</deferred>

---

*Phase: 3-Local Dev Stack & Dashboards*
*Context gathered: 2026-07-08*
