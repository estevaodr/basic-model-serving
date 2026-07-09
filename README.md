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

## CI/CD

Continuous integration is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

### Triggers

The workflow runs on:

- **Push to `main`** — lint, test, Docker build, and publish to GitHub Container Registry (GHCR)
- **Pull requests targeting `main`** — lint, test, and Docker build only (no image push)

Feature-branch pushes without an open PR do not trigger CI.

### What CI runs

Each run executes a single job in order:

1. **Lint** — `ruff check` and `ruff format --check`
2. **Test** — `pytest` excluding `@pytest.mark.docker` and `@pytest.mark.compose` markers
3. **Build** — multi-stage Docker image via Buildx (same `Dockerfile` as local dev)
4. **Push** — only on successful `main` pushes (not on pull requests)

CI does **not** run `werf converge`, deploy to Kubernetes, or target minikube. Deployment is handled separately in later phases.

### GHCR image and tags

On successful `main` pushes, the image is published to:

```
ghcr.io/estevaodr/basic-model-serving
```

Tags applied on `main`:

| Tag | Example | Description |
|-----|---------|-------------|
| Short git SHA | `a1b2c3d` | First 7 characters of the commit SHA |
| `latest` | `latest` | Most recent successful `main` build |
| Bare semver | `0.1.0` | Version from `pyproject.toml` (no `v` prefix) |

Pull examples (after the one-time public visibility step below):

```bash
docker pull ghcr.io/estevaodr/basic-model-serving:latest
docker pull ghcr.io/estevaodr/basic-model-serving:0.1.0
docker pull ghcr.io/estevaodr/basic-model-serving:a1b2c3d
```

No personal access token is required for anonymous pull once the package is public.

### Local dev vs CI images

Local development and the compose stack continue to use the locally built tag:

```bash
docker build -t basic-model-serving:local .
```

CI images on GHCR are for reviewers and downstream deployment — not a replacement for `basic-model-serving:local` during day-to-day development.

### One-time GHCR public visibility

GHCR packages default to **private**, even when the repository is public. After the **first successful push to `main`**, make the package pullable without authentication:

1. Open [GitHub → Packages → basic-model-serving](https://github.com/estevaodr/basic-model-serving/pkgs/container/basic-model-serving) (or navigate via your profile → Packages)
2. Go to **Package settings**
3. Scroll to **Danger Zone** → **Change visibility**
4. Select **Public** and confirm

This change is **irreversible**. Once public, anyone can pull the image without logging in to GHCR.
