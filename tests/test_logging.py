import json

from app.core.logging import JsonFormatter


def test_request_emits_json_log_with_request_id(client, caplog):
    caplog.set_level("INFO", logger="app.request")

    response = client.get("/health/live")

    assert response.status_code == 200
    assert len(caplog.records) >= 1

    record = next(
        r for r in caplog.records if r.name == "app.request" and r.getMessage()
    )
    log_line = json.loads(JsonFormatter().format(record))

    assert log_line.get("request_id")
    assert log_line["method"] == "GET"
    assert log_line["path"] == "/health/live"
    assert log_line["status"] == 200
    assert "duration_ms" in log_line
    assert record.request_id == log_line["request_id"]


def test_response_includes_x_request_id_header(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert "x-request-id" in [h.lower() for h in response.headers.keys()]
    assert response.headers["x-request-id"]
