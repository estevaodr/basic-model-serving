# Basic Model Serving

Portfolio-grade ResNet-50 image classification API with health probes, Prometheus metrics, and structured logging.

## Docker

**Prerequisites:** Docker Engine, [uv](https://docs.astral.sh/uv/) (recommended)

### Build

```bash
docker build -t basic-model-serving:local .
# or
uv run docker-build
```

### Run

```bash
docker run --rm -p 8000:8000 basic-model-serving:local
# or
uv run docker-run
```

API: http://127.0.0.1:8000 — docs at `/docs`, metrics at `/metrics`.

### Configuration

Application settings are supplied via environment variables (see `.env.example`):

```bash
docker run --rm -p 8000:8000 \
  -e TORCH_NUM_THREADS=4 \
  -e LOG_LEVEL=DEBUG \
  basic-model-serving:local
```

Copy `.env.example` to `.env` for local non-container runs. Uvicorn host, port, and worker count are fixed in the Dockerfile CMD (`0.0.0.0:8000`, single worker).

### Smoke test

Full E2E verification (build, image size, non-root user, health, predict):

```bash
uv run docker-smoke
```

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

### Generate traffic

Send sample predictions so panels populate:

```bash
curl -s -X POST http://localhost:8000/predict \
  -F "file=@tests/fixtures/sample.jpg" | jq .

# Optional 4xx example (non-image upload)
curl -s -X POST http://localhost:8000/predict \
  -F "file=@README.md"
```

### Image-only iteration

After code changes, rebuild and restart only the API container:

```bash
uv run docker-build
docker compose restart app
```

### Alert demo (Service Down)

1. With the stack running, open Grafana → **Alerting** → **Alert rules** and confirm **Service Down** is listed.
2. Stop the API: `docker compose stop app`
3. Wait ~60–90 seconds.
4. Confirm **Service Down** transitions to **Firing** in Grafana Alerting.
5. Restart the API: `docker compose start app`
6. Wait for `/health/ready`, then ~60 seconds — alert returns to **Normal**.

### Reload monitoring config

After editing files under `monitoring/`, restart the affected service:

```bash
docker compose restart grafana
docker compose restart prometheus
```

### Troubleshooting

If dashboard panels show **No data**, verify the Prometheus target `app` is **UP** at http://localhost:9090/targets.
