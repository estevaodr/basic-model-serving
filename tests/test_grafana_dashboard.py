"""Static contract validation for Model Serving Overview Grafana dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_JSON = (
    PROJECT_ROOT
    / "monitoring"
    / "grafana"
    / "dashboards"
    / "model-serving-overview.json"
)
DASHBOARD_PROVIDER = (
    PROJECT_ROOT
    / "monitoring"
    / "grafana"
    / "provisioning"
    / "dashboards"
    / "dashboard.yml"
)

REQUIRED_PANEL_TITLES = [
    "Request Rate",
    "p50 Latency",
    "p95 Latency",
    "Error Rate",
    "Prediction Throughput",
    "HTTP Errors by Status",
    "Service Health",
    "Total Predictions",
]

STAT_PANEL_TITLES = {
    "p50 Latency",
    "p95 Latency",
    "Error Rate",
    "Service Health",
    "Total Predictions",
}

TIMESERIES_PANEL_TITLES = {
    "Request Rate",
    "Prediction Throughput",
    "HTTP Errors by Status",
}


def _load_dashboard() -> dict:
    assert DASHBOARD_JSON.exists(), f"Dashboard JSON missing: {DASHBOARD_JSON}"
    return json.loads(DASHBOARD_JSON.read_text(encoding="utf-8"))


def _panel_exprs(dashboard: dict) -> list[str]:
    exprs: list[str] = []
    for panel in dashboard.get("panels", []):
        for target in panel.get("targets", []):
            expr = target.get("expr")
            if expr:
                exprs.append(expr)
    return exprs


def _panel_by_title(dashboard: dict, title: str) -> dict:
    for panel in dashboard.get("panels", []):
        if panel.get("title") == title:
            return panel
    raise AssertionError(f"Panel not found: {title!r}")


def test_dashboard_json_exists_and_valid():
    dashboard = _load_dashboard()

    assert dashboard["uid"] == "model-serving-overview"
    assert dashboard["title"] == "Model Serving Overview"
    assert dashboard["editable"] is False


def test_dashboard_has_eight_panels_with_contract():
    dashboard = _load_dashboard()
    panels = dashboard.get("panels", [])

    assert len(panels) == 8

    titles = {panel.get("title") for panel in panels}
    assert titles == set(REQUIRED_PANEL_TITLES)

    for title in STAT_PANEL_TITLES:
        panel = _panel_by_title(dashboard, title)
        assert panel.get("type") == "stat", f"{title} must be stat panel"
        options = panel.get("options", {})
        graph_mode = options.get("graphMode") or options.get("graph_mode")
        assert graph_mode == "none", f"{title} stat panel must have graphMode none"

    for title in TIMESERIES_PANEL_TITLES:
        panel = _panel_by_title(dashboard, title)
        assert panel.get("type") == "timeseries", f"{title} must be timeseries panel"


def test_dashboard_promql_uses_phase1_metrics():
    dashboard = _load_dashboard()
    exprs = _panel_exprs(dashboard)
    joined = "\n".join(exprs)

    assert "request_count_total" in joined
    assert 'request_duration_bucket{path="/predict"}' in joined
    assert "prediction_count_total" in joined
    assert 'up{job="app"}' in joined
    assert "http_requests_total" not in joined

    for panel in dashboard.get("panels", []):
        for target in panel.get("targets", []):
            ds = target.get("datasource") or panel.get("datasource")
            if isinstance(ds, dict):
                assert ds.get("uid") == "prometheus"
            else:
                assert ds == "prometheus" or ds is None


def test_dashboard_provider_yaml_exists():
    assert DASHBOARD_PROVIDER.exists(), (
        f"Dashboard provider missing: {DASHBOARD_PROVIDER}"
    )
    provider = yaml.safe_load(DASHBOARD_PROVIDER.read_text(encoding="utf-8"))

    providers = provider.get("providers", [])
    assert len(providers) >= 1
    entry = providers[0]
    assert entry["name"] == "model-serving"
    assert entry["type"] == "file"
    assert entry["options"]["path"] == "/var/lib/grafana/dashboards"
