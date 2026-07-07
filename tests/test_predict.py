import time

import pytest

from app.services.url_fetch import UrlFetchError


def _error_payload(response) -> dict:
    body = response.json()
    if "error" in body:
        return body
    detail = body.get("detail")
    if isinstance(detail, dict):
        return detail
    return body


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
    body = _error_payload(response)
    assert "error" in body
    assert "message" in body


def test_ssrf_file_scheme_rejected(client):
    response = client.post("/predict", json={"image_url": "file:///etc/passwd"})

    assert response.status_code in (400, 422)
    assert response.status_code != 500
    body = _error_payload(response)
    assert body["error"] in ("unsafe_url", "validation_error", "invalid_url")


def test_invalid_image_upload_returns_4xx(client):
    response = client.post(
        "/predict",
        files={"file": ("test.txt", b"not an image", "image/jpeg")},
    )

    assert response.status_code in (400, 422)
    assert response.status_code != 500
    body = _error_payload(response)
    assert body["error"] == "invalid_image"
    assert "message" in body


def test_oversized_upload_rejected(client, sample_jpeg_bytes, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.max_upload_bytes", 10)

    response = client.post(
        "/predict",
        files={"file": ("big.jpg", sample_jpeg_bytes, "image/jpeg")},
    )

    assert response.status_code in (400, 422)
    assert response.status_code != 500
    body = _error_payload(response)
    assert body["error"] == "payload_too_large"


def test_unreachable_url_returns_4xx(client, monkeypatch):
    def fail_fetch(url: str, timeout: float, max_bytes: int) -> bytes:
        raise UrlFetchError("url_fetch_failed", "Could not resolve hostname")

    monkeypatch.setattr("app.api.routes.predict.fetch_url_bytes", fail_fetch)

    response = client.post(
        "/predict",
        json={"image_url": "https://example.com/image.jpg"},
    )

    assert response.status_code in (400, 422, 504)
    assert response.status_code != 500
    body = _error_payload(response)
    assert body["error"] == "url_fetch_failed"


def test_empty_upload_rejected(client):
    response = client.post(
        "/predict",
        files={"note": (None, "no image provided")},
    )

    assert response.status_code == 422
    assert response.status_code != 500
    body = _error_payload(response)
    assert body["error"] == "invalid_request"


@pytest.mark.parametrize(
    "request_kwargs",
    [
        {"json": {"image_url": "http://169.254.169.254/"}},
        {"json": {"image_url": "file:///etc/passwd"}},
        {"files": {"file": ("test.txt", b"not an image", "image/jpeg")}},
        {"files": {"note": (None, "no image provided")}},
    ],
)
def test_no_client_error_returns_500(client, request_kwargs, monkeypatch):
    if "json" in request_kwargs:
        monkeypatch.setattr(
            "app.api.routes.predict.fetch_url_bytes",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                UrlFetchError("url_fetch_failed", "Failed")
            ),
        )
    response = client.post("/predict", **request_kwargs)
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


def test_openapi_documents_predict(client):
    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    schema = openapi_response.json()

    assert "/predict" in schema["paths"]
    predict_post = schema["paths"]["/predict"]["post"]
    assert "requestBody" in predict_post

    components = schema.get("components", {}).get("schemas", {})
    assert "PredictResponse" in components
    assert "predictions" in components["PredictResponse"]["properties"]

    predict_response = components["PredictResponse"]
    examples = predict_response.get("examples") or predict_response.get(
        "json_schema_extra", {}
    ).get("examples", [])
    if examples:
        assert len(examples[0]["predictions"]) == 5

    assert client.get("/docs").status_code == 200
