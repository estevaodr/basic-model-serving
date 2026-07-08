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
