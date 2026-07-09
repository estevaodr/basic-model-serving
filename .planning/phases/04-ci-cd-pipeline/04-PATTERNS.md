# Phase 4: CI/CD Pipeline - Pattern Map

**Mapped:** 2026-07-09
**Files analyzed:** 6 (1 create + 5 consume-unchanged)
**Analogs found:** 5 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `.github/workflows/ci.yml` | config | event-driven / batch | `.planning/research/STACK.md` (CI/CD sample, lines 210–257) | partial — no `.github/` workflows exist; sample is two-job + setup-python |
| `Dockerfile` (unchanged — CI builds) | config | file-I/O / transform | self (canonical image build) | exact — CI must build this file as-is |
| `requirements.txt` (unchanged — CI installs) | config | batch | self + Dockerfile RUN pattern | exact — two-step CPU torch contract |
| `requirements-dev.txt` (unchanged — CI installs) | config | batch | self | exact — ruff + pytest pins |
| `pyproject.toml` (unchanged — version + markers) | config | transform | self | exact — semver + pytest markers |
| `tests/` (unchanged — CI runs subset) | test | request-response | `tests/conftest.py` + marked E2E files | role-match — CI excludes docker/compose |

**Net-new only:** `.github/workflows/ci.yml`. All other rows are locked consume-only assets (D-07, D-08, D-12; CONTEXT code_context).

## Pattern Assignments

### `.github/workflows/ci.yml` (config, event-driven / batch)

**Analog (workflow skeleton):** `.planning/research/STACK.md` lines 210–257 — closest existing YAML for Actions → GHCR. **Do not copy blindly:** CONTEXT D-11 rejects the two-job split; D-07 replaces `setup-python`+pip with `setup-uv`; D-01/D-02 add PR triggers and gated push; D-04 requires pytest marker filter; D-03 adds concurrency.

**STACK.md baseline to adapt** (lines 210–257):
```yaml
name: CI
on:
  push:
    branches: [main]

permissions:
  contents: read
  packages: write        # required to push to ghcr.io

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check .
      - run: pytest

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: docker/setup-buildx-action@v4
      - uses: docker/login-action@v4
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/metadata-action@v6
        id: meta
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha,prefix=
            type=raw,value=latest,enable={{is_default_branch}}
      - uses: docker/build-push-action@v7
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Keep from STACK.md:**
- `permissions: contents: read` + `packages: write`
- Action majors: `checkout@v7`, `setup-buildx@v4`, `login@v4`, `metadata@v6`, `build-push@v7`
- `images: ghcr.io/${{ github.repository }}`
- `cache-from: type=gha` / `cache-to: type=gha,mode=max`
- `docker/login-action` with `GITHUB_TOKEN` (no PAT)

**Replace / add per CONTEXT + RESEARCH:**
| STACK.md | Phase 4 target |
|----------|----------------|
| `on.push` only | + `pull_request.branches: [main]` (D-01) |
| Two jobs `test` → `build-and-push` | Single job `ci` (D-11) |
| `setup-python` + bare pip | `astral-sh/setup-uv@v8` + two-step CPU torch (D-07, D-14) |
| `ruff check .` only | + `ruff format --check .` (D-06) |
| `pytest` (all tests) | `pytest -m "not docker and not compose"` (D-04) |
| `push: true` always | `push: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}` (D-02, D-12) |
| SHA + latest only | + bare semver from `pyproject.toml` (D-08) |
| No concurrency | `concurrency` cancel-in-progress (D-03) |

**Canonical target skeleton:** prefer `04-RESEARCH.md` Code Examples (lines 307–386) over STACK.md for the final workflow shape.

**Path convention:** `.planning/research/ARCHITECTURE.md` line 110 — `.github/workflows/ci.yml`.

---

### `Dockerfile` (config, file-I/O — consume unchanged)

**Analog:** self — CI builds this file; do not introduce a CI-specific Dockerfile.

**Two-step CPU torch install** (lines 6–12) — CI host venv must mirror this contract:
```dockerfile
RUN pip install --no-cache-dir \
    torch==2.12.1 \
    torchvision==0.27.1 \
    --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir -r requirements.txt
```

**Core build pattern** (lines 1–18): multi-stage builder with baked ResNet weights via `ResNetClassifier()` — this is why `type=gha,mode=max` is mandatory for CI-04.

**Runtime / health** (lines 20–44): unchanged by Phase 4; Buildx builds full image including HEALTHCHECK + non-root USER.

**Anti-pattern:** Do not call `scripts/docker.py` / `uv run docker-build` from Actions — those tag `basic-model-serving:local` for compose/dev only.

---

### `requirements.txt` + `requirements-dev.txt` (config, batch — consume unchanged)

**Analog:** self — CI installs these pins; no new PyPI packages this phase.

**Two-step contract comment** (`requirements.txt` lines 1–4):
```text
# CPU-only torch — two-step install:
# 1. pip install torch==2.12.1 torchvision==0.27.1 --index-url https://download.pytorch.org/whl/cpu
# 2. pip install -r requirements.txt
```

**Dev pins** (`requirements-dev.txt`):
```text
pytest==9.1.1
ruff==0.15.20
```

**CI install translation** (uv, per RESEARCH Pattern 2):
```yaml
- run: |
    uv venv
    source .venv/bin/activate
    uv pip install torch==2.12.1 torchvision==0.27.1 \
      --index-url https://download.pytorch.org/whl/cpu
    uv pip install -r requirements.txt -r requirements-dev.txt
```

Never single-step `uv pip install -r requirements.txt` without the CPU index first (CUDA wheel pitfall).

---

### `pyproject.toml` (config, transform — consume unchanged)

**Analog:** self — semver source + pytest marker registry.

**Version for GHCR semver tag** (lines 1–4):
```toml
[project]
name = "basic-model-serving"
version = "0.1.0"
requires-python = ">=3.12"
```

**CI version extract pattern** (RESEARCH / tomllib):
```bash
VERSION=$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])")
echo "version=$VERSION" >> "$GITHUB_OUTPUT"
```
Tag as bare `0.1.0` (no `v` prefix) — discretion resolution.

**Markers CI must honor** (lines 19–23):
```toml
[tool.pytest.ini_options]
markers = [
    "docker: needs Docker daemon for container E2E",
    "compose: needs Docker daemon and docker compose stack",
]
```

**Local-only scripts** (lines 7–10) — `docker-build` / `docker-run` / `docker-smoke` stay host-side; CI uses `docker/build-push-action`, not these entry points.

---

### `tests/` (test, request-response — consume unchanged)

**Analog for why torch is required in CI:** `tests/conftest.py` lines 1–13 — session `TestClient` imports real `app.main:app`:
```python
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
```

**Analog for what CI must exclude:**

`tests/test_docker_smoke.py` lines 24–28:
```python
@pytest.mark.docker
def test_docker_smoke_e2e():
    if not _docker_available():
        pytest.skip("Docker daemon not available")
    docker.smoke()
```

`tests/test_compose_stack.py` lines 188–189:
```python
@pytest.mark.docker
@pytest.mark.compose
def test_compose_stack_e2e():
```

**CI test command:**
```bash
pytest -m "not docker and not compose"
```
Do not use `--ignore=tests/test_docker*` — markers are the established gate (RESEARCH Don't Hand-Roll).

---

### `scripts/docker.py` (utility — local only; anti-analog for CI)

**Role:** Host-side build/smoke for `basic-model-serving:local`.

**Local image tag** (lines 15–24):
```python
IMAGE = "basic-model-serving:local"
...
def build() -> None:
    subprocess.run(["docker", "build", "-t", IMAGE, "."], check=True)
```

**Apply to CI:** Do **not** reuse this module. CI publishes `ghcr.io/${{ github.repository }}` via Buildx; compose continues to use `:local` (`docker-compose.yml` line 3). Keep the two tagging worlds separate (CONTEXT integration points).

## Shared Patterns

### Permissions (GHCR push)
**Source:** `.planning/research/STACK.md` lines 215–217; RESEARCH Pitfall 1  
**Apply to:** `.github/workflows/ci.yml` (workflow or job level)
```yaml
permissions:
  contents: read
  packages: write
```
Omission → GHCR 403 — most common failure mode.

### Two-step CPU torch install
**Source:** `Dockerfile` lines 6–12; `requirements.txt` lines 1–4  
**Apply to:** CI lint/test venv install steps  
```dockerfile
# Pattern: torch/torchvision from CPU index FIRST, then full requirements
--index-url https://download.pytorch.org/whl/cpu
```
Use `--index-url`, never `--extra-index-url` alone for the torch step.

### Docker layer cache (CI-04)
**Source:** STACK.md lines 255–256; RESEARCH Pattern 1  
**Apply to:** `docker/build-push-action` step  
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```
`mode=max` required for multi-stage builder layers (torch + baked weights).

### Conditional push (PR vs main)
**Source:** RESEARCH Pattern 1 (CONTEXT D-02, D-12)  
**Apply to:** build-push step  
```yaml
push: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
```
PRs still build (exercise Dockerfile + warm cache); only `main` push publishes.

### Metadata tags (SHA + latest + semver)
**Source:** STACK.md metadata-action (SHA/latest) + RESEARCH Pattern 3 (semver)  
**Apply to:** tag generation on every build; push applies tags only on main  
```yaml
tags: |
  type=sha,prefix=,format=short
  type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
  type=raw,value=${{ steps.version.outputs.version }},enable=${{ github.ref == 'refs/heads/main' }}
```
Short SHA length **7** (metadata-action default); semver **bare** from `pyproject.toml`.

### Concurrency cancel
**Source:** RESEARCH Pattern 4 (CONTEXT D-03)  
**Apply to:** workflow top-level  
```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

### Pytest marker exclusion
**Source:** `pyproject.toml` markers + `tests/test_docker_smoke.py` / `tests/test_compose_stack.py`  
**Apply to:** CI test step  
```bash
pytest -m "not docker and not compose"
```

### Local vs GHCR image names
**Source:** `scripts/docker.py` (`basic-model-serving:local`); `docker-compose.yml` line 3; CONTEXT D-09  
**Apply to:** CI tags only GHCR; leave local tag untouched  
- Local/compose: `basic-model-serving:local`  
- CI/GHCR: `ghcr.io/estevaodr/basic-model-serving` (`ghcr.io/${{ github.repository }}`)

### Lint fail-fast
**Source:** CONTEXT D-05, D-06  
**Apply to:** sequential steps before pytest  
```bash
ruff check .
ruff format --check .
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.github/workflows/ci.yml` (as executable workflow) | config | event-driven | **No `.github/` directory or workflow files exist.** Closest is planning-doc sample in STACK.md (partial). Planner should use `04-RESEARCH.md` Code Examples as the implementation template, copying install/build contracts from Dockerfile / requirements / pyproject. |

**Also no in-repo analog for:**
- `astral-sh/setup-uv` usage (local uv exists; no Actions wiring yet)
- GHCR login / package visibility automation (package does not exist until first main push — document UI checkpoint)

## Metadata

**Analog search scope:** `.github/` (empty), `Dockerfile`, `requirements*.txt`, `pyproject.toml`, `scripts/`, `tests/`, `docker-compose.yml`, `.planning/research/STACK.md`, `.planning/research/ARCHITECTURE.md`, `.cursor/rules/`  
**Files scanned:** ~25 relevant paths (0 workflows; 11 test modules; research CI samples)  
**Pattern extraction date:** 2026-07-09  
**Planner note:** Prefer RESEARCH skeleton over STACK.md for job layout; prefer Dockerfile/requirements for install semantics; prefer pyproject for version + markers.
