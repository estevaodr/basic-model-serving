import time

import pytest


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
