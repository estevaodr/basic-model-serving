"""Host-side Docker build, run, and E2E smoke helpers for basic-model-serving."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

IMAGE = "basic-model-serving:local"
CONTAINER_NAME = "basic-model-serving-smoke"
HOST = "127.0.0.1"
PORT = 8000
BASE = f"http://{HOST}:{PORT}"
MAX_IMAGE_BYTES = 2_000_000_000


def build() -> None:
    subprocess.run(["docker", "build", "-t", IMAGE, "."], check=True)


def run() -> str:
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER_NAME],
        capture_output=True,
        check=False,
    )
    result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "-p",
            f"{PORT}:{PORT}",
            "--name",
            CONTAINER_NAME,
            IMAGE,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    container_id = result.stdout.strip()
    print(f"Container {container_id} listening on {BASE}")
    return container_id


def _make_sample_jpeg() -> bytes:
    from PIL import Image

    image = Image.new("RGB", (64, 64), color=(128, 64, 32))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def _wait_ready(timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    url = f"{BASE}/health/ready"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionResetError, OSError):
            pass
        time.sleep(1)
    raise TimeoutError(f"/health/ready did not return 200 within {timeout}s")


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
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    predictions = payload.get("predictions", [])
    if len(predictions) != 5:
        raise AssertionError(f"expected 5 predictions, got {len(predictions)}")
    for item in predictions:
        if "label" not in item or "confidence" not in item:
            raise AssertionError(f"prediction missing label/confidence: {item}")
    return payload


def _assert_image_size() -> None:
    size = int(
        subprocess.check_output(
            ["docker", "image", "inspect", IMAGE, "--format", "{{.Size}}"],
            text=True,
        ).strip()
    )
    if size >= MAX_IMAGE_BYTES:
        raise AssertionError(f"image size {size} bytes exceeds {MAX_IMAGE_BYTES}")


def _assert_non_root(container_id: str) -> None:
    uid = subprocess.check_output(
        ["docker", "exec", container_id, "id", "-u"],
        text=True,
    ).strip()
    if uid != "1000":
        raise AssertionError(f"expected uid 1000, got {uid}")


def _assert_cpu_torch(container_id: str) -> None:
    output = subprocess.check_output(
        ["docker", "exec", container_id, "pip", "show", "torch"],
        text=True,
    )
    if "+cpu" not in output and any(
        tag in output for tag in ("+cu124", "+cu121", "+cu118")
    ):
        raise AssertionError("torch appears to be CUDA build, expected CPU-only wheel")


def _stop_container() -> None:
    subprocess.run(
        ["docker", "stop", CONTAINER_NAME],
        capture_output=True,
        check=False,
    )


def smoke() -> None:
    print("Step 1/6: docker build")
    build()
    print("Step 2/6: verify image size < 2GB")
    _assert_image_size()
    container_id = ""
    try:
        print("Step 3/6: start container")
        container_id = run()
        print("Step 4/6: verify non-root user")
        _assert_non_root(container_id)
        print("Step 5/6: wait for /health/ready")
        _wait_ready()
        print("Step 6/6: POST /predict")
        _post_predict()
        _assert_cpu_torch(container_id)
    finally:
        _stop_container()
    print("docker-smoke: all checks passed")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"build", "run", "smoke"}:
        print("Usage: python -m scripts.docker [build|run|smoke]", file=sys.stderr)
        raise SystemExit(2)
    command = sys.argv[1]
    if command == "build":
        build()
    elif command == "run":
        run()
    else:
        smoke()


if __name__ == "__main__":
    main()
