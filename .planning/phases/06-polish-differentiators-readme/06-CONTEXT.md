# Phase 6: Polish, Differentiators & README - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove the project's performance claims and make the repo reviewer-ready: publish load-test evidence (PERF-01–03, DOC-05), finish README polish (architecture diagram, <5 min quickstart, design rationale, limitations — DOC-01–04), and add a demonstrable Grafana **SLO/latency** alert distinct from the existing downtime alert (DOC-06).

**Depends on:** Phases 3 (compose stack + dashboards), 4 (CI/GHCR), 5 (K8s/werf deploy).

**Out of scope for this phase:** New API features, auth, HPA, cloud K8s, CI auto-deploy to K8s, adversarial-input CI tests (optional future), `/model/info` endpoint, demo web page, prediction-confidence histogram (v2 OBS-01), minikube load-test path as canonical benchmark, K8s SLO alert provisioning (compose only for DOC-06).

</domain>

<decisions>
## Implementation Decisions

### Load Test Methodology (PERF-01–03)
- **D-01:** Canonical benchmark runs against the **Docker Compose stack** (`docker compose up`) — not minikube/werf. Aligns with STACK.md guidance and reviewer reproducibility.
- **D-02:** Load generator is **`hey`** — single binary, no new Python deps; command documented in README for reproducibility.
- **D-03:** Concurrency pattern: **10 parallel workers for 60 seconds** — directly satisfies PERF-02 (10+ concurrent requests).
- **D-04:** Request payload: **`tests/fixtures/sample.jpg` multipart upload** to `POST /predict` — same image as README curl examples; realistic inference path.
- **D-05:** Warm up the service with at least one successful `/predict` before the timed run (planner/executor discretion on exact pre-step).

### Performance Results Presentation (DOC-05)
- **D-06:** Publish a **markdown table** in README with: **p50, p95, p99 latency, RPS, error rate, and CPU %** during the run.
- **D-07:** CPU measurement via **`docker stats`** (or equivalent) on the `app` container during the hey run — satisfies PERF-03 (<70% under normal load).
- **D-08:** Document **test host specs and run date** alongside results — honest context that numbers are environment-specific.
- **D-09:** If p95 exceeds 100ms on the test host, **publish actual numbers anyway** with an honest note and point to tuning knobs (`TORCH_NUM_THREADS`, resource limits) — do not hide or skip results.

### SLO Latency Alert (DOC-06)
- **D-10:** New Grafana unified alerting rule named **"High Latency"** — separate from existing **"Service Down"** downtime alert (Phase 3).
- **D-11:** Threshold: **p95 `/predict` latency > 100ms for 2 minutes** — matches PROJECT.md core value and dashboard panel SLO descriptions.
- **D-12:** Provision alert in **compose Grafana only** (`monitoring/grafana/provisioning/alerting/`) — mirrors Phase 3 downtime alert pattern; K8s alert deferred.
- **D-13:** README demo steps: run **`hey` load** → **stop API container** mid-run → alert transitions to **Firing** → restart API → alert **resolves** after recovery (same tangible demo style as downtime alert).
- **D-14:** Notifications remain **Grafana UI only** — no email/Slack/webhook contact points (consistent with Phase 3 D-12).

### README Structure & Reviewer Journey (DOC-01, DOC-02)
- **D-15:** **Compose-first quickstart** at the top of README — reviewer goes from clone to running stack in <5 minutes via `docker compose up`; K8s remains an advanced section below.
- **D-16:** Architecture diagram is **Mermaid embedded in README** — renders on GitHub; no committed binary diagram assets.
- **D-17:** Add new sections **near the top**: Quickstart, Architecture (Mermaid), Performance Results, Design Decisions, Limitations — **keep existing** Docker/CI/K8s detail sections intact.
- **D-18:** Add a **TL;DR quickstart** above detailed sections — reviewers who skim get the fast path; deep readers keep full CI/K8s documentation.

### Design Decisions & Limitations (DOC-03, DOC-04)
- **D-19:** Highlight **five core decisions** in a dedicated subsection: **werf choice**, **CI→K8s manual deploy boundary**, **sync `def` `/predict` handler**, **ResNet-50 over ResNet-18**, **compose vs K8s monitoring split** (hand-rolled compose vs kube-prometheus-stack in K8s).
- **D-20:** **Limitations** section uses honest engineer tone: **5–8 bullets** of real gaps (auth, HPA, cloud K8s, GPU, batching, rate limiting, etc.).
- **D-21:** Each limitation follows **gap + what you'd do next** format — shows judgment, not just awareness.
- **D-22:** Dedicated **"Design Decisions"** and **"Limitations"** subsections in README — not woven inline or separate ADR files.

### Carried Forward (not re-discussed — locked from prior phases)
- Phase 3 **Service Down** downtime alert and demo steps remain — DOC-06 adds latency alert only
- Phase 3 compose ports, Grafana credentials (`admin`/`admin`), Model Serving Overview dashboard
- Phase 4 CI split (`ci.yml` + `deploy.yml`), GHCR tagging, public package, no CI deploy
- Phase 5 manual `werf converge`, minikube sizing, zero-downtime rollout script, K8s Grafana `admin`/`prom-operator`
- Warm-path latency smoke in `tests/test_predict.py` skips on slow CPUs — Phase 6 provides formal concurrent proof
- Portfolio reviewer audience — clarity and documented decisions over maximal production hardening

### Claude's Discretion
- Exact `hey` flags (`-c 10 -z 60s` vs duration-based), output parsing, and whether to wrap in `scripts/load-test.sh` or `uv run` helper
- PromQL expression for p95 latency alert (histogram quantile on `request_duration` with `/predict` path label)
- Mermaid diagram components and level of detail (API, Prometheus, Grafana, GHCR, minikube, werf)
- Exact limitation bullet list within the 5–8 range and which v2 items from REQUIREMENTS.md to reference
- Whether to add a static test asserting the new alert YAML contract (mirror `tests/test_grafana_alerting.py` pattern)
- Exact README section headings and anchor links for navigation

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — PERF-01–03, DOC-01–06 acceptance criteria
- `.planning/ROADMAP.md` — Phase 6 goal, success criteria, MVP mode, dependency on Phases 3–5
- `.planning/PROJECT.md` — Core value (<100ms), Out of Scope (auth, HPA, cloud K8s, CI auto-deploy), Key Decisions table

### Prior phase context
- `.planning/phases/03-local-dev-stack-dashboards/03-CONTEXT.md` — Downtime alert pattern, compose ports, dashboard panels, SLO deferred to Phase 6
- `.planning/phases/04-ci-cd-pipeline/04-CONTEXT.md` — CI deploy-only boundary, GHCR tags
- `.planning/phases/05-kubernetes-deployment-via-werf/05-CONTEXT.md` — K8s monitoring, manual werf deploy, zero-downtime demo

### Research
- `.planning/research/FEATURES.md` — Load-test differentiator, SLO alerting, README as first-class deliverable, limitations signal
- `.planning/research/STACK.md` — hey/locust guidance, compose-first load test, histogram buckets around 100ms
- `.planning/research/PITFALLS.md` — Thread/CPU mismatch, event-loop blocking, histogram bucket tuning
- `.planning/research/SUMMARY.md` — Phase 6 deliverables list, build order

### Implementation assets
- `README.md` — Existing Docker, compose, CI/CD, K8s sections to preserve and extend
- `tests/fixtures/sample.jpg` — Benchmark payload and README curl examples
- `tests/test_predict.py` — Warm-path latency smoke (architectural enablement; formal proof here)
- `tests/test_grafana_alerting.py` — Static contract pattern for alert provisioning YAML
- `tests/test_grafana_dashboard.py` — Dashboard panel contracts (p50/p95 latency panels)
- `monitoring/grafana/provisioning/alerting/downtime.yml` — Existing downtime alert to complement
- `monitoring/grafana/dashboards/model-serving-overview.json` — Dashboard with SLO target annotations
- `monitoring/prometheus/prometheus.yml` — Compose scrape config
- `app/metrics/prometheus.py` — `request_duration` histogram metric for p95 alert PromQL
- `docker-compose.yml` — Compose stack target for load test
- `scripts/rollout-zero-downtime.sh` — Reference for documented demo-script pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `README.md` — ~280 lines with working Docker, compose, CI/CD, and K8s sections; extend at top, don't rewrite
- `tests/fixtures/sample.jpg` — Standard benchmark and demo image
- `monitoring/grafana/provisioning/alerting/downtime.yml` — Template for new High Latency alert YAML
- `tests/test_grafana_alerting.py` — Contract tests for alert provisioning (extend for latency rule)
- `monitoring/grafana/dashboards/model-serving-overview.json` — p50/p95 panels already reference 100ms SLO
- `app/metrics/prometheus.py` — Histogram buckets tuned around 100ms; alert queries derive from these
- Phase 3 README alert demo steps — Pattern to mirror for High Latency demo

### Established Patterns
- Compose is the hero local path; K8s is advanced/manual — Phase 6 load test reinforces compose-first
- Grafana unified alerting provisioned as YAML — no manual UI setup
- Portfolio evidence over checkbox claims — published numbers and demo steps, not just config files
- Honest engineering when hardware can't meet SLO — skip in unit tests (Phase 1), document in README (Phase 6)

### Integration Points
- **Net-new:** `monitoring/grafana/provisioning/alerting/latency.yml` (or similar), load-test script/docs, README top sections (Quickstart, Architecture, Performance, Decisions, Limitations)
- **Extend:** `tests/test_grafana_alerting.py` for latency alert contract
- **README:** Mermaid diagram, performance table, two alert demo sections (downtime existing + latency new)

</code_context>

<specifics>
## Specific Ideas

- User wants **evidence, not claims** — hey benchmark with published table next to the <100ms promise
- **Compose + hey** keeps reviewer reproduction aligned with the <5 min quickstart
- **High Latency alert** is intentionally separate from Service Down — two distinct demo stories
- **Mermaid diagram** for maintainability on GitHub without binary assets
- **Honest limitations** with gap+fix format — hiring-manager maturity signal
- **Keep detailed CI/K8s docs** — add TL;DR quickstart above, don't trim working sections

</specifics>

<deferred>
## Deferred Ideas

- **Minikube load-test path** — user chose compose as canonical; K8s numbers optional future appendix only
- **K8s Grafana SLO alert** — compose only for DOC-06; K8s inherits dashboard panels but not new alert rule
- **locust/k6/pytest load generators** — user chose hey
- **CI-published benchmark artifacts** — user chose local run with documented host specs
- **Generated chart images in repo** — user chose markdown table
- **Full README rewrite** — user chose additive top sections
- **ADR files for decisions** — user chose README subsections

None else — discussion stayed within phase scope

</deferred>

---

*Phase: 6-Polish, Differentiators & README*
*Context gathered: 2026-07-10*
