# Feature Research

**Domain:** ML model-serving REST API (portfolio/MLOps demonstration project)
**Researched:** 2026-07-06
**Confidence:** MEDIUM-HIGH

Sources for this research: production model-serving framework docs (KServe, BentoML, TorchServe, Triton, Seldon), FastAPI-for-ML best-practice write-ups, Prometheus/Grafana model-monitoring guides, and multiple 2026 "what hiring managers look for in an ML/MLOps portfolio" articles. A directly comparable open-source portfolio project (`flaviagaia/ml-model-serving-observability` — FastAPI + Prometheus + Grafana model serving demo) was found and used as a calibration point for scope. No official vendor docs were consulted via Context7 in this pass (gsd-tools/Context7 unavailable in this environment); findings below are cross-checked across 3+ independent web sources per claim and confidence is marked MEDIUM-HIGH rather than HIGH for that reason.

## Feature Landscape

### Table Stakes (Reviewers Expect These)

Missing any of these makes the project look unfinished or naive to a hiring-manager reviewer, even though none of them are visually impressive on their own. Most are already captured in `PROJECT.md` Active requirements — this table adds the precision needed to build them correctly and flags a couple of gaps.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `POST /predict` (image upload + URL), top-K predictions with confidence scores | Baseline function of any classification API; every comparable framework (TorchServe, BentoML, Triton) ships this as the default endpoint shape | LOW | Already in PROJECT.md. Return top-5, not top-1 — reviewers check that you didn't hardcode `argmax`. |
| Structured input validation via Pydantic + explicit 4xx errors | Every "production FastAPI ML" writeup treats this as non-negotiable; naive demos crash with 500s on bad input | LOW-MEDIUM | Validate file type/size, reject corrupt images, reject oversized uploads, reject non-image URLs — return typed error payload (code + message), not a raw stack trace. |
| Split liveness vs. readiness endpoints (`/health/live`, `/health/ready` or `/healthz`, `/readyz`) | Kubernetes-native best practice everywhere researched (KServe, TorchServe templates, every "FastAPI + K8s" guide); a single generic `/health` that returns 200 before the model is loaded causes real traffic-routing bugs in K8s | LOW | PROJECT.md currently says a single `/health` endpoint but also requires liveness/readiness probes — those two requirements are in tension. Recommend splitting into two endpoints: readiness returns 503 until the model is loaded into memory. |
| Model loaded once at startup (no per-request cold start) | Universal pattern across every serving framework and FastAPI-ML guide; per-request loading is the #1 rookie mistake called out in every source | LOW | Already in PROJECT.md. Use FastAPI `lifespan` context manager. |
| Auto-generated OpenAPI docs (`/docs`) | Free with FastAPI, expected by any reviewer who pokes at the API | LOW | Already in PROJECT.md. Add example request/response bodies via Pydantic `Field(examples=...)` — bare auto-docs without examples look unfinished. |
| Structured (JSON) logging with request IDs | Called out repeatedly as a baseline "production" signal, and needed to make Prometheus metrics/log correlation meaningful | LOW-MEDIUM | Not yet explicit in PROJECT.md — add as a should-have. Plain `print()`/default uvicorn logs read as a tutorial project. |
| Multi-stage Dockerfile, non-root user, small image, env-var config | Table stakes for any containerized service; every guide reviewed treats this as baseline hygiene | LOW-MEDIUM | Already in PROJECT.md (image <2GB target). |
| docker-compose stack for local dev (API + Prometheus + Grafana) | Reviewers who clone the repo expect `docker compose up` to work in under 5 minutes — this is called out explicitly in multiple "what hiring managers check" sources | LOW-MEDIUM | Already in PROJECT.md. This is also the #1 thing that determines whether a reviewer actually runs your project instead of just reading the README. |
| K8s Deployment + Service + ConfigMap, resource requests/limits, liveness/readiness probes, rolling updates | Baseline of "I can run this on Kubernetes, not just Docker" | MEDIUM | Already in PROJECT.md. |
| Prometheus metrics: request count, request duration (histogram), prediction count | Every serving framework surveyed (TorchServe, BentoML, Triton, KServe) ships Prometheus metrics by default — a serving API without a `/metrics` endpoint reads as incomplete | LOW-MEDIUM | Already in PROJECT.md. Use a `Histogram` for latency, not a `Summary` or `Gauge` — histograms let Prometheus/Grafana compute arbitrary percentiles server-side (confirmed across multiple sources as the correct metric type choice). |
| Basic Grafana dashboard (request rate, latency percentiles, error rate, uptime) | Baseline observability signal; the comparable portfolio project found in research ships exactly this | LOW-MEDIUM | Already in PROJECT.md (5-7 panels). |
| CI: lint + test + build + push on every push to `main` | Baseline "this isn't just local code" signal; explicitly called out in multiple hiring-manager-portfolio sources as a differentiator between DS and MLE portfolios | LOW-MEDIUM | Already in PROJECT.md. |
| README: architecture diagram, quickstart (<5 min), design-decision rationale | Called out by nearly every "what hiring managers look for" source as make-or-break — reviewers skim the README before running anything | LOW | Not a code feature, but treat it as a first-class deliverable, not an afterthought. Include a "what I'd improve" / limitations section — multiple sources flag this as a specific signal of engineering maturity that junior candidates skip. |

### Differentiators (Competitive Advantage for a Portfolio Piece)

These are what separate this project from the median "FastAPI + Docker" tutorial repo. None are required, but each buys credibility disproportionate to its cost. Pick a handful — don't try to do all of them (see MVP Definition).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Load-test results published in README (e.g. `locust`/`k6`/`hey` run against the deployed service, with a latency/throughput chart or table) | Directly answers the "can you talk about latency, scalability, error handling under load" signal that hiring-manager sources call out explicitly; most portfolio repos never actually load-test their own claims | LOW-MEDIUM | Cheap to add once the service exists — run `hey`/`locust` for 60s, paste p50/p95/p99 and RPS into the README next to the "<100ms" claim already promised in PROJECT.md. Turns an unverified performance claim into evidence. |
| Grafana dashboard screenshots + a documented latency/uptime SLO with an alert rule (e.g. "page if p95 > 200ms for 5m" or "alert if service down for 1m") | Moves observability from "metrics exist" to "I reasoned about reliability targets" — the SLO/alerting layer is what production teams actually do on top of raw dashboards, per Grafana's own SLO/burn-rate guidance and multiple monitoring writeups | LOW-MEDIUM | Builds directly on the already-planned Grafana dashboard; add 1-2 Prometheus alerting rules (`HighLatency`, `ServiceDown`) and show them firing/resolving in a screenshot. |
| Prediction-confidence histogram / class-distribution panel ("drift-lite" signal) | Every framework surveyed treats prediction-distribution monitoring as the entry point to drift detection; a confidence histogram is a cheap way to gesture at "I understand model monitoring goes beyond infra metrics" without building a real drift pipeline | LOW | Add `model_prediction_confidence` (histogram) and `model_predictions_total{class=...}` (counter) alongside the required request/latency metrics — same instrumentation effort, more interesting dashboard. |
| Lightweight `/model/info` (or `/version`) endpoint exposing model name, framework version, weights checksum/tag, git SHA of the running build | Signals awareness of model versioning/provenance — a common gap even in "production" demo repos — without building a full model registry | LOW | Static metadata computed at startup; near-zero cost, reads as thoughtful. |
| Minimal demo web page (single static HTML + JS, or Streamlit/Gradio) for drag-and-drop image upload and viewing predictions | Multiple hiring-manager sources explicitly value "a live URL/demo you can click," not just curl examples; removes friction for a reviewer skimming quickly | LOW-MEDIUM | Keep it thin — a static page hitting `/predict` via `fetch()`, or a 20-line Streamlit app. Do not build a real frontend app (see Anti-Features). |
| Zero-downtime rolling update demonstrated and documented (e.g. a short GIF/screenshot of `kubectl rollout status` with continuous curl traffic showing no dropped requests) | Turns an already-required K8s feature (rolling updates) into visible proof rather than an unverified checkbox | LOW | No new build — just a demo/capture step layered on required K8s work. |
| Integration tests hitting a running container (not just unit tests) in CI, including adversarial-input tests (corrupt image, oversized file, non-image URL) | Distinguishes "tests exist" from "tests are meaningful" — explicitly called out in hiring-manager source material as something reviewers check for | LOW-MEDIUM | Natural extension of the input-validation table-stakes item; reuses the same edge cases as test fixtures. |
| werf-based deploy documented as a deliberate tool choice with a short rationale (vs. plain `kubectl apply`/Helm) | Most comparable portfolio repos use bare kubectl or Helm; explaining *why* werf (giterminism, built-in image build+deploy, Helm-compatible charts) is a differentiator on tooling judgment, which the "design tradeoffs" signal from hiring-manager research rewards | LOW | Already the project's tool choice (see PROJECT.md Key Decisions) — the differentiator is writing the rationale down, not new engineering work. |

### Anti-Features (Would Look Like Scope Creep for This Portfolio Project)

These are the features that *sound* impressive and that comparable production frameworks (KServe, Seldon, Triton) all support — which is exactly why they're tempting to bolt on. For a single-model, local-K8s, solo portfolio project they would dilute focus, blow the "<10 min pipeline" / "<5 min quickstart" targets, and signal poor scope judgment rather than skill. Several are already correctly excluded in PROJECT.md's Out of Scope section; this table adds the ecosystem context for *why* they're commonly requested and what to do instead.

| Feature | Why Requested | Why Problematic Here | Alternative |
|---------|---------------|------------------|-------------|
| Multi-model registry / multi-model serving | Every serving framework surveyed (BentoML, TorchServe, Triton, KServe) supports it natively, so it feels like "the real thing" | Project has one fixed pretrained model by design (PROJECT.md); adding a registry is infra for a problem that doesn't exist yet and roughly doubles API surface/testing burden | Already excluded in PROJECT.md. The `/model/info` differentiator above gives the versioning *signal* without the registry *infrastructure*. |
| Authentication/authorization (API keys, OAuth) | "Production APIs need auth" is a reasonable-sounding instinct | No real users/tenants exist; adds a whole security surface (key management, secrets) to review and secure for a local demo that's already excluded from scope | Already excluded in PROJECT.md. Mention as a "would add for a multi-tenant deployment" line in the README's limitations section instead of building it. |
| Horizontal Pod Autoscaler (HPA) / scale-to-zero (Knative) | KServe/Seldon both showcase autoscaling (including scale-to-zero) as a headline feature | Minikube is single-node with fixed local resources; HPA has nothing meaningful to scale against and can't be demonstrated credibly without generating sustained load against a laptop cluster | Already excluded in PROJECT.md. Document resource requests/limits as the "autoscaling would key off these" hook, defer HPA to "future work." |
| Automated CI → K8s deploy (GitOps operator, Argo CD/Flux, self-hosted runner) | Nearly every "complete MLOps pipeline" article treats CI/CD as ending in automatic deployment | GitHub-hosted runners architecturally cannot reach a local minikube cluster; forcing this in would mean standing up a self-hosted runner or tunnel purely for pipeline aesthetics, not for the skill being demonstrated | Already excluded in PROJECT.md. Manual `werf converge`, clearly documented as a deliberate boundary, demonstrates the same CI/CD competence without fake automation. |
| Cloud Kubernetes (EKS/GKE/AKS) | KServe/Seldon docs assume cloud K8s as the default target, so it feels like the "correct" environment | Introduces real cost and cloud-account setup for a solo portfolio project with no production traffic; also expands scope into cloud IAM/networking that isn't the skill being showcased here | Already excluded in PROJECT.md. minikube demonstrates the same manifests/probes/rollout mechanics. |
| Model training / fine-tuning pipeline, experiment tracking (MLflow/W&B), feature store | "End-to-end ML lifecycle" articles push training-to-serving as the gold-standard portfolio project | This project's value proposition is explicitly the *serving* lifecycle (API → containers → orchestration → observability → CI/CD) for a fixed pretrained model; bolting on training conflates two different skill stories and roughly doubles project scope | Already excluded in PROJECT.md. If pursued later, treat as a separate portfolio project so each one has a focused narrative. |
| A/B testing / canary traffic-splitting infrastructure (Seldon-style, Istio traffic mirroring) | Seldon Core and KServe both list this as a flagship feature | Requires two model versions to split traffic between, which doesn't exist (single fixed model); building the traffic-split machinery with nothing to split traffic *to* is pure scope theater | The zero-downtime rolling-update differentiator above demonstrates deployment-safety thinking without needing a second model version. |
| Full distributed tracing stack (Jaeger/Tempo + OpenTelemetry instrumentation across services) | "Observability" articles often bundle metrics+logs+traces as a single required trio | This is a single-container service calling into one in-process model — there's no multi-hop request path for traces to usefully illuminate; standing up a tracing backend for one hop is disproportionate infra | Structured logs with a request ID (already a table-stakes item above) give the same debuggability signal at a fraction of the cost. |
| Dynamic/adaptive request batching for throughput | Every high-performance serving framework (Triton, BentoML, TorchServe) highlights batching as a core feature | Meaningful batching requires either GPU inference or sustained concurrent load to show a throughput win; on a CPU-only local demo it adds real complexity (queuing, timeout tuning) for a benefit that's hard to demonstrate convincingly within scope | Load-testing differentiator above already exercises concurrency (10+ concurrent requests per PROJECT.md); mention batching as a documented "next step for higher-throughput scenarios" in the README instead of implementing it. |
| GPU inference optimization (TensorRT/ONNX Runtime, CUDA) | Triton and most "production inference" content assumes GPU as the default performance lever | Local minikube target is CPU-only by design (no cloud spend); introducing a GPU code path that can never be exercised in the target environment is dead code | Plain PyTorch CPU inference is the correct scope match; if the <100ms target is at risk on CPU, that's a performance-tuning problem (e.g. `torch.set_num_threads`, half precision) not a new feature. |
| Custom Kubernetes Operator / CRDs | KServe's whole value proposition is a custom CRD (`InferenceService`) | Building a CRD/controller for a single static Deployment is infrastructure for a problem (managing many model deployments) this project doesn't have | Plain Deployment/Service/ConfigMap manifests (already in scope) fully cover a single fixed-model service. |
| Rate limiting / API gateway (Kong, Envoy, Traefik) | Common "production hardening" checklist item | No real external traffic or abuse vector exists for a local/portfolio demo; adds a whole extra component to deploy and document for no observable benefit in a reviewer's 5-minute run-through | Note as a "would add before public internet exposure" line in the README limitations section. |
| Message-queue-based async inference (Kafka/RabbitMQ/Celery) | "Scalable ML systems" content often recommends decoupling inference via a queue | ResNet-50 inference is sub-second and synchronous by nature; introducing async queueing adds a distributed-systems failure mode (message loss, backpressure, dead-letter handling) with no corresponding latency or scale requirement in PROJECT.md (target is <100ms synchronous) | Keep `/predict` synchronous; it directly serves the stated <100ms core value. |

## Feature Dependencies

```
[Model loaded at startup]
    └──requires──> [Readiness endpoint reflects load state]
                       └──requires──> [K8s readiness probe wired to /health/ready]
                                          └──enables──> [Zero-downtime rolling updates]

[Pydantic input validation + structured errors]
    └──enables──> [Adversarial-input integration tests in CI]

[Prometheus metrics instrumentation (request_count, request_duration, prediction_count)]
    └──requires──> [/metrics endpoint exposed by API]
    └──enables──> [Grafana dashboard]
                      └──enables──> [SLO alerting rules]
                      └──enables──> [Prediction-confidence / class-distribution panel]

[docker-compose stack (API + Prometheus + Grafana)]
    └──enables──> [Fast local iteration on dashboard + alerting before touching K8s]

[K8s manifests (Deployment/Service/ConfigMap/probes)]
    └──requires──> [Dockerfile + image pushed to GHCR]
    └──enables──> [werf converge deploy]
                      └──enables──> [Zero-downtime rolling-update demo]

[Working deployed service (compose or minikube)]
    └──requires──> [Load-test results in README]

[/model/info endpoint] ──enhances──> [README design-decision narrative]

[Demo web page] ──requires──> [/predict endpoint + CORS enabled if served from a different origin]

[Batching] ──conflicts──> [Simplicity/scope target for this project] (see Anti-Features)
[Auth/authz] ──conflicts──> [Local/portfolio-demo framing — no real users to authenticate] (see Anti-Features)
```

### Dependency Notes

- **Readiness probe requires model-loaded state:** the readiness endpoint must read a real "is the model in memory" flag set at the end of the FastAPI `lifespan` startup hook, not just return a static 200 — otherwise K8s will route traffic before the model is ready and the "zero-downtime rolling update" differentiator will actually show dropped/failed requests during rollout.
- **Grafana dashboard requires Prometheus metrics to exist first:** don't build dashboard panels for metrics that haven't been instrumented; this dictates phase ordering (instrument → scrape → visualize → alert).
- **SLO alerting enhances the Grafana dashboard, not the API:** it's a config layer added after the base dashboard renders correctly — sequence it as a follow-on task, not part of the same unit of work.
- **Load-test results require a running deployment target:** can't produce credible latency numbers until the service is at least running via docker-compose; sequence this after the local dev stack is stable, and again after minikube deploy for a "docker-compose vs. K8s" comparison if time allows.
- **Batching conflicts with the project's scope target:** it's the single feature from the "table stakes at the framework level" list (KServe/Triton/BentoML all ship it) that is explicitly *not* worth doing here — including it would meaningfully increase complexity (request queuing, timeout semantics) without a demonstrable payoff in a CPU-only, low-concurrency local demo.
- **Auth/HPA/GitOps conflict with the "local, single-user, no cloud spend" framing:** all three are already correctly excluded in PROJECT.md; this research confirms the exclusion reasoning holds up against how the broader ecosystem treats these as flagship features (i.e., they're excluded for good scope reasons, not because they're unimportant in general).

## MVP Definition

### Launch With (v1)

Matches PROJECT.md's Active requirements, with two precision additions surfaced by this research.

- [ ] `POST /predict` (upload + URL), top-5 predictions with confidence — core value proposition
- [ ] Pydantic input validation + structured JSON error responses — prevents the API looking naive on bad input
- [ ] Split `/health/live` and `/health/ready` endpoints (readiness gated on model-loaded flag) — makes the required K8s probes actually correct, not just present
- [ ] Auto-generated `/docs` with example payloads
- [ ] Structured (JSON) logging with request IDs — cheap, makes metrics/log correlation possible later
- [ ] Multi-stage Dockerfile (non-root, <2GB, env-var config)
- [ ] docker-compose stack (API + Prometheus + Grafana)
- [ ] K8s Deployment/Service/ConfigMap, resource requests/limits, probes, rolling updates, deployed via werf
- [ ] Prometheus metrics: request count, request duration (histogram), prediction count
- [ ] Grafana dashboard, 5-7 panels, downtime alert, 7+ day retention
- [ ] GitHub Actions CI: lint, test, build, push to GHCR, <10 min
- [ ] README: architecture diagram, <5 min quickstart, design-decision rationale, limitations/"what I'd improve" section

### Add After Validation (v1.x)

Add once the core pipeline runs end-to-end and is demonstrably stable — these are the differentiators that turn a competent baseline into a standout portfolio piece.

- [ ] Load-test results (locust/k6/hey) published in README next to the latency claim — trigger: once the service is deployed and stable enough to hold still for a benchmark
- [ ] SLO alerting rules (latency, downtime) layered on the existing Grafana dashboard — trigger: after the base dashboard is confirmed showing real data
- [ ] Prediction-confidence histogram / class-distribution panel — trigger: same instrumentation pass as the required Prometheus metrics, low incremental cost
- [ ] `/model/info` metadata endpoint — trigger: quick add once the model-loading code path is stable
- [ ] Zero-downtime rollout demo (screenshot/GIF) — trigger: once werf deploy to minikube is working end-to-end
- [ ] Adversarial-input integration tests in CI — trigger: once input validation logic is finalized

### Future Consideration (v2+)

Defer until there's a concrete reason to add them (e.g. a second project milestone, or specific interview feedback that these are gaps).

- [ ] Minimal demo web page (static HTML or Streamlit) — defer until API + docs are polished; nice-to-have, not required to prove the skill set
- [ ] Request batching — defer indefinitely for this project; only relevant if it evolves toward a GPU/high-throughput story
- [ ] Model versioning / multi-model registry — defer to a dedicated project if pursuing multi-model serving as its own skill demonstration

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `/predict` with top-5 + confidence | HIGH | LOW | P1 |
| Input validation + structured errors | HIGH | LOW | P1 |
| Split liveness/readiness probes | HIGH | LOW | P1 |
| Prometheus metrics + Grafana dashboard | HIGH | MEDIUM | P1 |
| K8s manifests + werf deploy | HIGH | MEDIUM | P1 |
| CI (lint/test/build/push) | HIGH | MEDIUM | P1 |
| README with diagram + rationale + limitations | HIGH | LOW | P1 |
| Load-test results in README | MEDIUM-HIGH | LOW | P2 |
| SLO alerting on Grafana dashboard | MEDIUM | LOW | P2 |
| Prediction-confidence panel | MEDIUM | LOW | P2 |
| `/model/info` endpoint | MEDIUM | LOW | P2 |
| Zero-downtime rollout demo | MEDIUM | LOW | P2 |
| Demo web page | MEDIUM | LOW-MEDIUM | P3 |
| Request batching | LOW (for this scope) | HIGH | P3 (do not build) |
| Multi-model registry | LOW (for this scope) | HIGH | P3 (do not build) |

**Priority key:**
- P1: Must have — matches PROJECT.md's Active requirements
- P2: Should have, add once P1 is stable — differentiators with low marginal cost
- P3: Nice to have / explicitly deferred — either genuinely optional (demo UI) or an anti-feature for this scope (batching, registry)

## Competitor Feature Analysis

"Competitors" here means comparable serving frameworks/templates a reviewer might mentally benchmark this project against, plus the one directly comparable open-source portfolio project found during research.

| Feature | KServe / Seldon / Triton (enterprise frameworks) | `flaviagaia/ml-model-serving-observability` (comparable portfolio repo) | Our Approach |
|---------|--------------|--------------|--------------|
| Serving API | Multi-framework runtimes, gRPC + HTTP, OpenAPI/OpenAI-protocol | FastAPI, typed REST API | FastAPI REST API (upload + URL), matches the portfolio-scale comparable, skips gRPC as unneeded surface |
| Health/readiness | Native K8s revision-based health, scale-to-zero readiness | `/health`, `/ready` | Split `/health/live` + `/health/ready` gated on model-loaded flag — same pattern, correctly wired to K8s probes |
| Metrics | Built-in Prometheus metrics per runtime | `model_inference_requests_total`, `model_inference_latency_seconds` (histogram), `model_predictions_total`, `model_prediction_confidence`, `model_metadata` | Same core metric set (request count, latency histogram, prediction count) plus confidence histogram as a P2 differentiator |
| Dashboards | Pre-built Grafana templates per runtime | Pre-provisioned Grafana dashboard, version-controlled | Version-controlled Grafana dashboard provisioning (not manual clicking) — treat provisioning-as-code as part of the table-stakes bar, since the comparable project already does this |
| Versioning | Native (K8s revisions, model repository directory structure, archive metadata) | Not emphasized | Lightweight `/model/info` metadata endpoint only — full versioning/registry is out of scope (see Anti-Features) |
| Batching | Native, often "best-in-class" (Triton) | Not present | Explicitly excluded (see Anti-Features) — disproportionate complexity for CPU-only, low-concurrency local demo |
| Autoscaling / traffic splitting | Core selling point (scale-to-zero, canary, A/B) | Not present | Explicitly excluded — no cloud K8s, no second model version to split traffic to |
| Deploy tooling | Framework-specific CRDs / Helm charts | Not documented in depth | werf (documented as a deliberate tradeoff vs. plain kubectl/Helm) — a differentiator on tooling judgment, since most comparable repos don't reason about this choice explicitly |
| CI/CD | Out of scope for the frameworks themselves (infra, not app) | Not emphasized | GitHub Actions build+push, explicitly stopping short of auto-deploy with documented rationale (runner can't reach local minikube) |

## Sources

- KServe framework overview and Grafana dashboard docs — https://kserve.github.io/website/docs/next/model-serving/predictive-inference/frameworks/overview , https://kserve.github.io/website/docs/model-serving/predictive-inference/observability/grafana-dashboards
- Model serving framework comparisons (KServe/Seldon/TorchServe/Triton/BentoML feature matrices) — AiOps School "Top 5 Model Serving Frameworks", AI Wiki "Model Serving Frameworks - Complete Guide", Reintech "BentoML vs Seldon Core vs KServe" (2026), "The Holy Grail" Ch. 45
- FastAPI-for-ML production patterns (lifespan model loading, liveness/readiness split, Pydantic validation) — zenvanriel.com "Deploying AI with Docker and FastAPI", Medium "Building Production-Quality APIs for ML Systems" (Naman Lazarus, 2026), helain-zimmermann.com "Deploying ML Models with FastAPI and Docker", jaredai-website "FastAPI for ML Engineers"
- Prometheus/Grafana model-monitoring patterns and SLO/alerting design — agentbus.sh "How to Build a Model Monitoring Dashboard with Prometheus and Grafana", Grafana Cloud docs "SLI example for latency", OneUptime "How to Build Burn Rate Alerts"
- Directly comparable portfolio repo (calibration point for scope) — `github.com/flaviagaia/ml-model-serving-observability`
- "What hiring managers look for in an MLOps/ML portfolio" — theaimarketpulse.com "ML Portfolio Projects That Get You Hired", VeriiPro "Cracking the MLOps Role", InterviewKickstart "Machine Learning Engineer Portfolio: The Complete Guide", InterviewNode "How to Build a Strong ML Portfolio", MentorCruise "Career Roadmap: How to Build an AI Portfolio That Gets You Hired"
- Project context — `/home/estevao/src/brenz/basic-model-serving/.planning/PROJECT.md`

---
*Feature research for: ML model-serving REST API (portfolio project)*
*Researched: 2026-07-06*
