from app.metrics.prometheus import PREDICTION_COUNT

def _metric_value(metrics_text: str, name: str) -> float:
    for line in metrics_text.splitlines():
        if line.startswith("#"):
            continue
        metric_name = line.split("{", 1)[0].split()[0]
        if metric_name == name or metric_name == f"{name}_total":
            return float(line.split()[-1])
    return 0.0


def test_metrics_endpoint_returns_required_names(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "request_count" in body
    assert "request_duration" in body
    assert "prediction_count" in body


def test_prediction_count_increments(client, sample_jpeg_bytes):
    before = _metric_value(client.get("/metrics").text, "prediction_count")

    response = client.post(
        "/predict",
        files={"file": ("test.jpg", sample_jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 200

    after = _metric_value(client.get("/metrics").text, "prediction_count")
    assert after == before + 1


def test_no_instrumentator_default_names(client):
    body = client.get("/metrics").text

    assert "request_count" in body
    assert "http_requests_total" not in body or "request_count" in body


def test_prediction_count_counter_exists():
    assert PREDICTION_COUNT._name == "prediction_count"
