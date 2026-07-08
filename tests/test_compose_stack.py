"""Docker Compose stack E2E: API + Prometheus + Grafana."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from scripts import docker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
FIXTURE_IMAGE = PROJECT_ROOT / "tests" / "fixtures" / "sample.jpg"
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"

HOST = "127.0.0.1"
APP_PORT = 8000
PROMETHEUS_PORT = 9090
APP_BASE = f"http://{HOST}:{APP_PORT}"
PROMETHEUS_BASE = f"http://{HOST}:{PROMETHEUS_PORT}"


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        subprocess.run(
            ["docker", "info"],
            capture_output=True,
            check=True,
            timeout=10,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return False


def _ensure_env_file() -> None:
    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        ENV_FILE.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")


def _ensure_image() -> None:
    result = subprocess.run(
        ["docker", "image", "inspect", docker.IMAGE],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        docker.build()


def _compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


def _wait_ready(timeout: float = 180) -> None:
    deadline = time.monotonic() + timeout
    url = f"{APP_BASE}/health/ready"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError):
            pass
        time.sleep(1)
    raise TimeoutError(f"/health/ready did not return 200 within {timeout}s")


def _post_predict_fixture() -> dict:
    boundary = "----ComposeStackBoundary"
    image_bytes = FIXTURE_IMAGE.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="sample.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + image_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = urllib.request.Request(
        f"{APP_BASE}/predict",
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _prometheus_query(expr: str) -> list[dict]:
    query = urllib.parse.urlencode({"query": expr})
    url = f"{PROMETHEUS_BASE}/api/v1/query?{query}"
    with urllib.request.urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("data", {}).get("result", [])


@pytest.mark.docker
@pytest.mark.compose
def test_compose_stack_e2e():
    if not _docker_available():
        pytest.skip("Docker daemon not available")

    if not COMPOSE_FILE.exists():
        pytest.fail(f"docker-compose.yml not found at {COMPOSE_FILE}")

    _ensure_env_file()
    _ensure_image()

    try:
        up = _compose("up", "-d", "--wait", check=False)
        if up.returncode != 0:
            _wait_ready()
        else:
            _wait_ready(timeout=120)

        predictions = _post_predict_fixture()["predictions"]
        assert len(predictions) == 5

        up_results = _prometheus_query('up{job="app"}')
        assert up_results, "expected up{job=\"app\"} samples from Prometheus"
        assert any(item.get("value", [None, None])[1] == "1" for item in up_results)

        request_count_results = _prometheus_query("request_count_total")
        assert len(request_count_results) > 0
    finally:
        _compose("down", "-v", check=False)
