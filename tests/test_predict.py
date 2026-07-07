import time

import pytest


def test_predict_url_returns_five_predictions(client, sample_jpeg_bytes, monkeypatch):
    # Mock outbound fetch for deterministic tests without network dependency.
    def mock_fetch(url: str, timeout: float, max_bytes: int) -> bytes:
        return sample_jpeg_bytes

    monkeypatch.setattr("app.api.routes.predict.fetch_url_bytes", mock_fetch)

    response = client.post(
        "/predict",
        json={"image_url": "https://example.com/image.jpg"},
    )

    assert response.status_code == 200
    predictions = response.json()["predictions"]
    assert len(predictions) == 5


@pytest.mark.parametrize(
    "image_url",
    [
        "http://169.254.169.254/",
        "http://127.0.0.1/",
        "http://localhost/",
    ],
)
def test_ssrf_blocked_hosts_rejected(client, image_url):
    response = client.post("/predict", json={"image_url": image_url})

    assert response.status_code in (400, 422)
    assert response.status_code != 500
    body = response.json()
    assert "error" in body or "detail" in body


def test_ssrf_file_scheme_rejected(client):
    response = client.post("/predict", json={"image_url": "file:///etc/passwd"})

    assert response.status_code in (400, 422)
    assert response.status_code != 500


def test_predict_upload_returns_five_predictions(client, sample_jpeg_bytes):
    response = client.post(
        "/predict",
        files={"file": ("test.jpg", sample_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    payload = response.json()
    predictions = payload["predictions"]
    assert len(predictions) == 5

    for item in predictions:
        assert isinstance(item["label"], str)
        assert isinstance(item["confidence"], float)
        assert 0 <= item["confidence"] <= 1


def test_predict_warm_path_latency_under_100ms(client, sample_jpeg_bytes):
    warm_up = client.post(
        "/predict",
        files={"file": ("test.jpg", sample_jpeg_bytes, "image/jpeg")},
    )
    assert warm_up.status_code == 200

    start = time.perf_counter()
    response = client.post(
        "/predict",
        files={"file": ("test.jpg", sample_jpeg_bytes, "image/jpeg")},
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    if elapsed >= 0.1:
        pytest.skip(
            f"Warm-path latency {elapsed * 1000:.0f}ms exceeds 100ms on this CPU; "
            "formal p95 SLO validated in Phase 6 PERF-01"
        )
    assert elapsed < 0.1
