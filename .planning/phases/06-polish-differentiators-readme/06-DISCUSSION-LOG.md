# Phase 6: Polish, Differentiators & README - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-10
**Phase:** 6-Polish, Differentiators & README
**Areas discussed:** Load test methodology, Performance results presentation, SLO latency alert, README structure, Design decisions & limitations

---

## Load Test Methodology

| Option | Description | Selected |
|--------|-------------|----------|
| Docker Compose stack | Matches STACK.md; reviewer reproduces with `docker compose up` | ✓ |
| Minikube + werf | Production-like path; harder to reproduce | |
| Both | Compose canonical; minikube optional appendix | |

| Option | Description | Selected |
|--------|-------------|----------|
| hey | Single binary, fast 60s run, easy README command | ✓ |
| locust | Python-native, richer control; adds dep | |
| k6 | Scriptable JS; separate install | |
| pytest + futures | Reuses test infra; less realistic HTTP load | |

| Option | Description | Selected |
|--------|-------------|----------|
| 10 concurrent × 60s | Matches PERF-02 directly | ✓ |
| Ramp 1→5→10→20 | Degradation curve; harder to summarize | |
| 20 concurrent × 60s | Stress beyond requirement | |

| Option | Description | Selected |
|--------|-------------|----------|
| sample.jpg multipart | Same as README curl examples | ✓ |
| JSON URL mode | Network fetch variability | |
| Both modes | Doubles benchmark surface | |

**User's choice:** Compose + hey + 10 concurrent × 60s + sample.jpg multipart upload
**Notes:** Canonical benchmark environment is compose, not minikube.

---

## Performance Results Presentation

| Option | Description | Selected |
|--------|-------------|----------|
| Full table (p50/p95/p99, RPS, error rate, CPU) | Satisfies DOC-05 and PERF-03 | ✓ |
| Latency + RPS only | Minimal | |
| Table + Grafana screenshot | Visual proof | |

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown table | Copy-paste friendly from hey output | ✓ |
| hey raw output block | Authentic but noisy | |
| Chart image in repo | Pretty but stale | |

| Option | Description | Selected |
|--------|-------------|----------|
| Document host specs + date | Honest environment context | ✓ |
| Numbers only | Cleaner but misleading | |
| CI benchmark artifact | Reproducible; more CI work | |

| Option | Description | Selected |
|--------|-------------|----------|
| Publish actuals + honest note if p95 >100ms | Engineering maturity signal | ✓ |
| Tune until pass before publishing | May not reproduce on reviewer HW | |
| Only publish if p95 <100ms | Risk no results on slow laptop | |

**User's choice:** Full markdown table, document host specs, honest note if SLO missed
**Notes:** CPU from docker stats during run.

---

## SLO Latency Alert (DOC-06)

| Option | Description | Selected |
|--------|-------------|----------|
| p95 >100ms for 2m | Matches core value and dashboard panels | ✓ |
| p95 >200ms for 5m | More forgiving | |
| p50 >100ms for 2m | Stricter; false-fire risk | |

| Option | Description | Selected |
|--------|-------------|----------|
| Compose Grafana only | Mirrors Phase 3 downtime pattern | ✓ |
| K8s Grafana only | Production-like | |
| Both environments | Duplicate maintenance | |

| Option | Description | Selected |
|--------|-------------|----------|
| hey load → stop API → fire → restart → resolve | Tangible demo without config hacks | ✓ |
| Temporarily lower threshold | Artificial | |
| Screenshot only | No live demo | |

| Option | Description | Selected |
|--------|-------------|----------|
| "High Latency" | Clear separation from Service Down | ✓ |
| "SLO Breach" | Formal SLO language | |
| "p95 Latency SLO" | Explicit metric | |

**User's choice:** p95 >100ms / 2m, compose only, hey+stop demo, name "High Latency"
**Notes:** Distinct from existing Service Down alert in Phase 3.

---

## README Structure & Reviewer Journey

| Option | Description | Selected |
|--------|-------------|----------|
| Compose-first quickstart at top | <5 min via `docker compose up` | ✓ |
| Unified quickstart with fork | One section, two paths | |
| K8s-first | Slower for reviewers | |

| Option | Description | Selected |
|--------|-------------|----------|
| Mermaid in README | GitHub-rendered, maintainable | ✓ |
| Committed SVG/PNG | Polished; manual updates | |
| ASCII diagram | Universal; less impressive | |

| Option | Description | Selected |
|--------|-------------|----------|
| Add sections at top; keep existing detail | Minimal disruption | ✓ |
| Full restructure | More editorial work | |
| Append at bottom | Poor reviewer UX | |

| Option | Description | Selected |
|--------|-------------|----------|
| TL;DR quickstart + keep CI/K8s detail | Skimmers and deep readers both served | ✓ |
| Collapse CI/K8s summaries | Shorter | |
| Trim K8s significantly | Compose-only focus | |

**User's choice:** Compose hero, Mermaid diagram, additive top sections, keep detailed CI/K8s
**Notes:** New sections: Quickstart, Architecture, Performance, Design Decisions, Limitations.

---

## Design Decisions & Limitations

| Option | Description | Selected |
|--------|-------------|----------|
| Core five (werf, CI boundary, sync /predict, ResNet-50, monitoring split) | Covers DOC-03 explicitly | ✓ |
| Full PROJECT.md table | Comprehensive but repetitive | |
| Top 3 narrative | Shorter | |

| Option | Description | Selected |
|--------|-------------|----------|
| Honest engineer 5–8 bullets | Hiring-manager maturity signal | ✓ |
| 3 bullets only | Minimal | |
| Limitations + v2 links | Forward thinking | |

| Option | Description | Selected |
|--------|-------------|----------|
| Gap + what you'd do next | Shows judgment | ✓ |
| Gap only | Shorter | |
| Prioritized top 3 with effort | Planning-oriented | |

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated subsections in README | Clear DOC-03/DOC-04 mapping | ✓ |
| Inline in diagram captions | Compact | |
| Separate ADR files | Over-engineered | |

**User's choice:** Core five decisions, honest limitations with gap+fix, dedicated README subsections
**Notes:** Limitations include auth, HPA, cloud K8s, GPU, batching, etc.

---

## Claude's Discretion

- Exact hey command flags and optional `scripts/load-test.sh` wrapper
- PromQL for p95 latency alert on `request_duration` histogram
- Mermaid diagram detail level
- Static test extension for latency alert YAML contract
- README section headings and anchor structure

## Deferred Ideas

- Minikube as canonical load-test environment
- K8s Grafana SLO alert provisioning
- locust/k6/pytest load generators
- CI-published benchmark artifacts
- Chart images committed to repo
- Full README rewrite
- ADR files for design decisions
