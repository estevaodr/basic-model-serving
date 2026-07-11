# Phase 6: Polish, Differentiators & README - Pattern Map

**Mapped:** 2026-07-10
**Files analyzed:** 4 (new/modified) + 5 (integration references)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/load-test.sh` | utility | batch | `scripts/rollout-zero-downtime.sh` + `scripts/docker.py` | role-match |
| `monitoring/grafana/provisioning/alerting/latency.yml` | config | event-driven | `monitoring/grafana/provisioning/alerting/downtime.yml` | exact |
| `tests/test_grafana_alerting.py` | test | file-I/O | `tests/test_grafana_alerting.py` (existing downtime tests) | exact |
| `README.md` | config | — | `README.md` (existing compose + alert demo sections) | partial |

**Integration references (unchanged, consumed by Phase 6 work):**

| File | Role | Data Flow | Used By |
|------|------|-----------|---------|
| `app/metrics/prometheus.py` | middleware + route | request-response | p95 alert PromQL; hey measures same histogram |
| `monitoring/grafana/dashboards/model-serving-overview.json` | config | request-response (PromQL) | p95 expression source for `latency.yml` |
| `tests/fixtures/sample.jpg` | fixture | file-I/O | hey multipart body; README curl examples |
| `tests/test_predict.py` | test | request-response | warm-up pattern; Phase 6 supersedes single-request skip |
| `scripts/rollout-zero-downtime.sh` | utility | batch | documented demo-script style for README |

## Pattern Assignments

### `scripts/load-test.sh` (utility, batch)

**Analogs:** `scripts/rollout-zero-downtime.sh` (bash script conventions), `scripts/docker.py` (multipart body + predict warm-up), `README.md` (curl `-F` examples)

**Bash script header** (`scripts/rollout-zero-downtime.sh` lines 1–3):

```1:3:scripts/rollout-zero-downtime.sh
#!/usr/bin/env bash
# Hammer /health/ready during a rolling update to prove zero sustained downtime (D-19).
set -euo pipefail
```

**Apply to:** `load-test.sh` — same shebang, `set -euo pipefail`, one-line purpose comment referencing PERF-01–03.

---

**Error handling + user-facing output** (`scripts/rollout-zero-downtime.sh` lines 10–15):

```10:15:scripts/rollout-zero-downtime.sh
if [[ -z "${API_URL}" ]]; then
  echo "error: minikube service ${K8S_API_SERVICE} -n ${K8S_NAMESPACE} --url returned no URL" >&2
  exit 1
fi

echo "Polling ${API_URL}/health/ready every 0.5s (Ctrl+C to stop)"
```

**Apply to:** Validate `hey` is installed (`command -v hey`), compose stack is up (`curl -sf http://localhost:8000/health/ready`), and `docker compose ps -q app` returns a container ID before running.

---

**Multipart body construction** (`scripts/docker.py` lines 119–136):

```119:136:scripts/docker.py
def _post_predict() -> dict[str, Any]:
    jpeg = _make_sample_jpeg()
    boundary = "----BasicModelServingBoundary"
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="sample.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode("utf-8")
        + jpeg
        + f"\r\n--{boundary}--\r\n".encode("utf-8")
    )
    request = urllib.request.Request(
        f"{BASE}/predict",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
```

**Shell translation for hey:** Build same structure with `printf` + `cat tests/fixtures/sample.jpg` into a temp file; pass to hey via `-D "$BODY_FILE"` and `-H "Content-Type: multipart/form-data; boundary=${BOUNDARY}"`. Field name must be `file` (matches FastAPI `UploadFile`).

---

**Warm-up predict pattern** (`tests/test_predict.py` lines 156–161):

```156:161:tests/test_predict.py
def test_predict_warm_path_latency_under_100ms(client, sample_jpeg_bytes):
    warm_up = client.post(
        "/predict",
        files={"file": ("test.jpg", sample_jpeg_bytes, "image/jpeg")},
    )
    assert warm_up.status_code == 200
```

**README curl warm-up** (`README.md` lines 78–80):

```78:80:README.md
curl -s -X POST http://localhost:8000/predict \
  -F "file=@tests/fixtures/sample.jpg" | jq .
```

**Apply to:** Run curl warm-up (with `jq -e '.predictions | length == 5'` assertion) before `hey -c 10 -z 60s`. Use `tests/fixtures/sample.jpg`, not generated JPEG from `docker.py`.

---

**Host/port constants** (`scripts/docker.py` lines 14–18):

```14:18:scripts/docker.py
IMAGE = "basic-model-serving:local"
CONTAINER_NAME = "basic-model-serving-smoke"
HOST = "127.0.0.1"
PORT = 8000
BASE = f"http://{HOST}:{PORT}"
```

**Apply to:** Target `http://localhost:8000/predict` (compose default). Resolve app container via `docker compose ps -q app` for `docker stats` — do not hard-code container name.

---

**Core load-test flow** (from `06-RESEARCH.md` Pattern 1–3 — no repo analog yet):

1. Build multipart body file from `tests/fixtures/sample.jpg`
2. Warm-up curl `/predict`
3. Background `docker stats` loop (2s interval) on app container
4. `hey -m POST -c 10 -z 60s -H ... -D "$BODY_FILE" http://localhost:8000/predict`
5. Kill stats loop; print peak CPU % and hey summary for README table

---

### `monitoring/grafana/provisioning/alerting/latency.yml` (config, event-driven)

**Analog:** `monitoring/grafana/provisioning/alerting/downtime.yml` (structural template), `monitoring/grafana/dashboards/model-serving-overview.json` (p95 PromQL)

**Full downtime alert skeleton** (`downtime.yml` lines 1–62):

```1:62:monitoring/grafana/provisioning/alerting/downtime.yml
apiVersion: 1
groups:
  - orgId: 1
    name: model-serving-downtime
    folder: Model Serving
    interval: 10s
    rules:
      - uid: service-down
        title: Service Down
        condition: B
        data:
          - refId: A
            relativeTimeRange:
              from: 600
              to: 0
            datasourceUid: prometheus
            model:
              editorMode: code
              expr: up{job="app"}
              instant: true
              intervalMs: 1000
              legendFormat: __auto
              maxDataPoints: 43200
              range: false
              refId: A
          - refId: B
            relativeTimeRange:
              from: 0
              to: 0
            datasourceUid: __expr__
            model:
              conditions:
                - evaluator:
                    params:
                      - 1
                    type: lt
                  operator:
                    type: and
                  query:
                    params:
                      - A
                  reducer:
                    params: []
                    type: last
                  type: query
              datasource:
                type: __expr__
                uid: __expr__
              expression: A
              intervalMs: 1000
              maxDataPoints: 43200
              refId: B
              type: threshold
        noDataState: OK
        execErrState: Error
        for: 1m
        labels:
          severity: critical
          team: model-serving
        annotations:
          summary: Model serving API is unreachable
          description: Prometheus cannot scrape app:8000/metrics for 1 minute. Check docker compose app service.
```

**Latency translation — copy structure, change these fields:**

| Property | Downtime (`downtime.yml`) | High Latency (`latency.yml`) |
|----------|---------------------------|------------------------------|
| Group name | `model-serving-downtime` | `model-serving-latency` |
| Rule uid | `service-down` | `high-latency` |
| Title | `Service Down` | `High Latency` |
| refId A expr | `up{job="app"}` | p95 PromQL (below) |
| Threshold type | `lt` params `[1]` | `gt` params `[100]` |
| `for` | `1m` | `2m` |
| severity label | `critical` | `warning` |
| summary | unreachable | p95 exceeds 100ms SLO |

---

**p95 PromQL from dashboard** (`model-serving-overview.json` lines 180–191):

```180:191:monitoring/grafana/dashboards/model-serving-overview.json
      "targets": [
        {
          "datasource": {
            "type": "prometheus",
            "uid": "prometheus"
          },
          "expr": "histogram_quantile(0.95, sum by (le) (rate(request_duration_bucket{path=\"/predict\"}[5m]))) * 1000",
          "refId": "A"
        }
      ],
      "title": "p95 Latency",
```

**Apply to:** Use this exact expression as refId A `expr` in `latency.yml`. Threshold B > 100 (milliseconds). Keep `noDataState: OK` to avoid idle false positives.

---

**Histogram buckets backing the alert** (`app/metrics/prometheus.py` lines 13–18):

```13:18:app/metrics/prometheus.py
REQUEST_DURATION = Histogram(
    "request_duration",
    "Request duration in seconds",
    ["method", "path"],
    buckets=(0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0),
)
```

**Apply to:** Alert and dashboard share `request_duration_bucket{path="/predict"}` — do not add new metrics. `path` label comes from `PrometheusMiddleware` route template extraction (lines 35–43).

---

### `tests/test_grafana_alerting.py` (test, file-I/O — extend)

**Analog:** existing downtime contract tests in same file

**Module header + path constants** (`test_grafana_alerting.py` lines 1–15):

```1:15:tests/test_grafana_alerting.py
"""Static contract validation for Grafana unified alerting provisioning."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOWNTIME_ALERT = (
    PROJECT_ROOT
    / "monitoring"
    / "grafana"
    / "provisioning"
    / "alerting"
    / "downtime.yml"
)
```

**Apply to:** Add parallel `LATENCY_ALERT` constant pointing to `latency.yml`.

---

**Forbidden contact terms guard** (`test_grafana_alerting.py` lines 17–26, 42–46):

```17:26:tests/test_grafana_alerting.py
FORBIDDEN_CONTACT_TERMS = (
    "slack",
    "email",
    "webhook",
    "contact_point",
    "contactPoint",
    "receiver",
    "pagerduty",
    "opsgenie",
)
```

```42:46:tests/test_grafana_alerting.py
    lowered = content.lower()
    for term in FORBIDDEN_CONTACT_TERMS:
        assert term not in lowered, (
            f"Alert config must not include contact point term: {term}"
        )
```

**Apply to:** Reuse `FORBIDDEN_CONTACT_TERMS` in new latency tests — D-14 locks Grafana UI-only notifications.

---

**Downtime contract test pattern** (`test_grafana_alerting.py` lines 34–46):

```34:46:tests/test_grafana_alerting.py
def test_downtime_alert_yaml_contract():
    content = _alert_text()

    assert "Service Down" in content
    assert 'up{job="app"}' in content
    assert "prometheus" in content
    assert "1m" in content

    lowered = content.lower()
    for term in FORBIDDEN_CONTACT_TERMS:
        assert term not in lowered, (
            f"Alert config must not include contact point term: {term}"
        )
```

**Latency extension pattern** (mirror structure):

```python
LATENCY_ALERT = PROJECT_ROOT / "monitoring/grafana/provisioning/alerting/latency.yml"

def test_latency_alert_yaml_contract():
    content = LATENCY_ALERT.read_text(encoding="utf-8")
    assert "High Latency" in content
    assert 'request_duration_bucket{path="/predict"}' in content
    assert "histogram_quantile(0.95" in content
    assert "2m" in content
    assert "100" in content
    for term in FORBIDDEN_CONTACT_TERMS:
        assert term not in content.lower()

def test_latency_alert_has_required_annotations():
    content = LATENCY_ALERT.read_text(encoding="utf-8")
    assert "p95" in content.lower() or "latency" in content.lower()
    assert "100ms" in content

def test_latency_alert_rule_group_interval():
    content = LATENCY_ALERT.read_text(encoding="utf-8")
    assert "10s" in content  # Grafana scheduler base interval
```

---

**Dashboard cross-reference pattern** (`test_grafana_dashboard.py` lines 104–112):

```104:112:tests/test_grafana_dashboard.py
def test_dashboard_promql_uses_phase1_metrics():
    dashboard = _load_dashboard()
    exprs = _panel_exprs(dashboard)
    joined = "\n".join(exprs)

    assert "request_count_total" in joined
    assert 'request_duration_bucket{path="/predict"}' in joined
    assert "prediction_count_total" in joined
    assert 'up{job="app"}' in joined
```

**Apply to:** Optional assertion that latency alert expr substring matches dashboard p95 panel — prevents alert/dashboard drift.

---

### `README.md` (config — extend at top only)

**Analog:** existing README structure — prepend new sections, preserve lines 5–278 unchanged

**Current opening** (`README.md` lines 1–4):

```1:4:README.md
# Basic Model Serving

Portfolio-grade ResNet-50 image classification API with health probes, Prometheus metrics, and structured logging.

## Docker
```

**Apply to:** Keep title + one-line value prop. Insert TL;DR, Architecture, Performance Results, Design Decisions, Limitations between line 4 and `## Docker`. Add horizontal rule `---` before `## Docker` per `06-RESEARCH.md` Pattern 5.

---

**Compose quickstart pattern** (`README.md` lines 48–72):

```48:72:README.md
## Local observability stack

Run the API together with Prometheus and Grafana for live dashboards during development.

**Prerequisites:** Build the app image once before the first compose start:

```bash
uv run docker-build
```

Copy `.env.example` to `.env` if you have not already (compose reads app settings from `.env`).

### Start the stack

```bash
docker compose up
```

| Service | URL | Purpose |
|---------|-----|---------|
| API | http://localhost:8000 | `/predict`, `/docs`, `/metrics` |
| Grafana | http://localhost:3000 | Dashboards and alerting UI |
| Prometheus | http://localhost:9090 | Metrics storage and targets |

Log in to Grafana with `admin` / `admin`. After login you land on the **Model Serving Overview** home dashboard.
```

**Apply to:** TL;DR Quickstart condenses this to 4–6 commands (clone → `uv run docker-build` → `docker compose up` → curl predict → open Grafana). Link to detailed sections below for deep readers (D-15, D-18).

---

**Alert demo numbered steps** (`README.md` lines 96–103):

```96:103:README.md
### Alert demo (Service Down)

1. With the stack running, open Grafana → **Alerting** → **Alert rules** and confirm **Service Down** is listed.
2. Stop the API: `docker compose stop app`
3. Wait ~60–90 seconds.
4. Confirm **Service Down** transitions to **Firing** in Grafana Alerting.
5. Restart the API: `docker compose start app`
6. Wait for `/health/ready`, then ~60 seconds — alert returns to **Normal**.
```

**Apply to:** Add parallel `### Alert demo (High Latency)` section in observability stack area (or Performance Results). Mirror numbered-step format. Note Pitfall 3 from RESEARCH: sustained hey load is primary demo; stop-container may fire Service Down first.

---

**Traffic generation curl** (`README.md` lines 74–85):

```74:85:README.md
### Generate traffic

Send sample predictions so panels populate:

```bash
curl -s -X POST http://localhost:8000/predict \
  -F "file=@tests/fixtures/sample.jpg" | jq .

# Optional 4xx example (non-image upload)
curl -s -X POST http://localhost:8000/predict \
  -F "file=@README.md"
```

**Apply to:** Performance Results section references `./scripts/load-test.sh` and underlying hey command. Reuse same fixture path and curl style.

---

**Performance table template** (from `06-RESEARCH.md` — no repo analog):

```markdown
| Metric | Value |
|--------|------:|
| p50 latency | 42 ms |
| p95 latency | 78 ms |
| p99 latency | 115 ms |
| RPS | 22.1 |
| Error rate | 0.0% |
| Peak CPU (app container) | 58% |

**Run date:** 2026-07-10
**Host:** 8-core / 16GB RAM / Linux, Docker 29.x
**Command:** `./scripts/load-test.sh` (hey -c 10 -z 60s, compose stack)
```

**Apply to:** Populate with actual hey output. If p95 > 100ms, add honest note + `TORCH_NUM_THREADS` tuning (D-09).

---

**Mermaid architecture diagram** (from `06-RESEARCH.md` lines 174–208 — no repo analog):

Use `flowchart TB` with subgraphs: reviewer (curl/hey, browser), compose (app, prometheus, grafana), cicd (ci.yml, deploy.yml, GHCR), k8s (werf, deployment, kube-prometheus-stack). Embed in fenced ` ```mermaid ` block (D-16).

---

**Design Decisions content** (from CONTEXT D-19 — no code analog):

Five subsections with rationale paragraphs: werf choice, CI→K8s manual deploy boundary, sync `def` `/predict`, ResNet-50 over ResNet-18, compose vs K8s monitoring split. Reference existing README K8s and CI sections rather than duplicating.

---

**Limitations format** (from CONTEXT D-20/D-21 — no code analog):

5–8 bullets, each: **Gap** — what you'd do next. Topics: auth, HPA, cloud K8s, GPU, batching, rate limiting, Grafana default creds.

## Shared Patterns

### Grafana Unified Alerting YAML Shape
**Source:** `monitoring/grafana/provisioning/alerting/downtime.yml`
**Apply to:** `latency.yml`

Two-step query model: refId A (Prometheus instant query) → refId B (Grafana expression threshold). Folder `Model Serving`, group `interval: 10s`, `noDataState: OK`, `execErrState: Error`, labels `team: model-serving`.

### Custom Prometheus Metrics (do not rename)
**Source:** `app/metrics/prometheus.py`
**Apply to:** Alert PromQL, dashboard panels, load-test validation

| Metric | PromQL name | Key label |
|--------|-------------|-----------|
| `request_duration` | `request_duration_bucket` | `path="/predict"` |
| `request_count` | `request_count_total` | `status` |
| `prediction_count` | `prediction_count_total` | — |

Do not use `http_requests_total` or instrumentator defaults.

### Multipart Upload Contract
**Source:** `scripts/docker.py` `_post_predict`, `README.md` curl examples
**Apply to:** `load-test.sh`, hey body file

- Field name: `file`
- Content-Type: `multipart/form-data`
- Fixture: `tests/fixtures/sample.jpg`
- Expected response: 5 predictions with `label` + `confidence`

### Bash Script Conventions
**Source:** `scripts/rollout-zero-downtime.sh`
**Apply to:** `scripts/load-test.sh`

- `#!/usr/bin/env bash` + `set -euo pipefail`
- Descriptive comment referencing phase requirement ID
- Errors to stderr with `exit 1`
- User-facing progress echoes before long-running commands

### Static YAML Contract Tests
**Source:** `tests/test_grafana_alerting.py`
**Apply to:** Extend for `latency.yml`

- `PROJECT_ROOT` path resolution via `Path(__file__).resolve().parents[1]`
- String assertions on title, PromQL fragments, `for` duration
- `FORBIDDEN_CONTACT_TERMS` scan on all alert YAML files
- Separate tests for annotations and rule group interval

### README Additive Extension
**Source:** `README.md` existing sections
**Apply to:** Top prepend only (D-17)

- Do not rewrite `## Docker`, `## Local observability stack`, `## CI/CD`, `## Kubernetes`
- Match existing markdown style: `**Prerequisites:**`, numbered demo steps, service URL tables, fenced bash blocks
- Cross-link new TL;DR to detailed sections below

### Compose-First Reviewer Path
**Source:** `README.md` observability stack + `docker-compose.yml` (implicit)
**Apply to:** Load test target, quickstart, performance evidence

Canonical benchmark runs against `docker compose up` stack on `localhost:8000` — not minikube/werf (D-01).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Mermaid diagram in README | config | — | No Mermaid in repo yet; use `06-RESEARCH.md` diagram |
| Performance results table | config | — | No published benchmark table yet; template in RESEARCH |
| Design Decisions / Limitations prose | config | — | Narrative content; locked topics in CONTEXT D-19/D-20 |

## Metadata

**Analog search scope:** `scripts/`, `monitoring/grafana/`, `tests/`, `app/metrics/`, `README.md`, `.planning/phases/03-local-dev-stack-dashboards/03-PATTERNS.md`
**Files scanned:** 22
**Pattern extraction date:** 2026-07-10
**Primary references:** `downtime.yml` (alert structure), `test_grafana_alerting.py` (contract tests), `scripts/docker.py` (multipart), `scripts/rollout-zero-downtime.sh` (bash style), `model-serving-overview.json` (p95 PromQL)
**Net-new territory:** `scripts/load-test.sh` (first hey/load-test script), README top sections (first Mermaid + performance table)
