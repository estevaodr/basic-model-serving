# Phase 1: Core Inference API - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** 1-Core Inference API
**Areas discussed:** Concurrent inference

---

## Concurrent Inference

### Handler structure

| Option | Description | Selected |
|--------|-------------|----------|
| Plain `def` handler | FastAPI offloads to thread pool; event loop stays free for /health and /metrics | ✓ |
| `async def` + `asyncio.to_thread()` | Keeps async style for URL download but explicitly offloads inference | |
| You decide | Pick whichever fits architecture best | |

**User's choice:** Plain `def` handler
**Notes:** Aligns with PITFALLS.md Pitfall 1 — synchronous PyTorch in `async def` blocks the event loop and serializes concurrent requests.

### Uvicorn workers

| Option | Description | Selected |
|--------|-------------|----------|
| Single worker | One model copy in memory; thread pool handles concurrency within process | ✓ |
| Multiple workers (1 per CPU) | True parallelism but N× model memory; better for K8s tuning later | |
| You decide | Defer worker count to deployment config | |

**User's choice:** Single worker
**Notes:** Appropriate for Phase 1 dev; worker count can be revisited at container/K8s deployment phases.

### Concurrency cap

| Option | Description | Selected |
|--------|-------------|----------|
| No explicit cap | Rely on FastAPI/Uvicorn default thread pool | ✓ |
| Semaphore cap | Max N concurrent inferences; 503 when saturated | |
| You decide | Match cap to pod CPU limit in Phase 5 | |

**User's choice:** No explicit cap
**Notes:** Sufficient for portfolio demo load target (10+ concurrent).

### PyTorch thread count

| Option | Description | Selected |
|--------|-------------|----------|
| Env-configurable with default | e.g. `TORCH_NUM_THREADS=2` via pydantic-settings | ✓ |
| Defer to Phase 5 | Use PyTorch defaults until K8s CPU limits defined | |
| Fixed default of 1 | Safest latency predictability | |

**User's choice:** Env-configurable with sensible default
**Notes:** Prevents cgroup CPU mismatch (PITFALLS.md Pitfall 2) without hardcoding K8s limits in Phase 1.

---

## Claude's Discretion

- Request contract (upload vs URL API shape)
- Response JSON format (labels, confidence representation)
- Validation error message verbosity
- URL guardrail strictness beyond API-05 minimum
- Project directory layout details
- Prometheus histogram bucket tuning

## Deferred Ideas

None — user selected only the concurrency gray area and chose to capture context after four questions.
