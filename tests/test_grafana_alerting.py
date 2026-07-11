"""Static contract validation for Grafana unified alerting provisioning."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOWNTIME_ALERT = (
    PROJECT_ROOT
    / "monitoring"
    / "grafana"
    / "provisioning"
    / "alerting"
    / "downtime.yml"
)
LATENCY_ALERT = (
    PROJECT_ROOT
    / "monitoring"
    / "grafana"
    / "provisioning"
    / "alerting"
    / "latency.yml"
)
DASHBOARD_JSON = (
    PROJECT_ROOT
    / "monitoring"
    / "grafana"
    / "dashboards"
    / "model-serving-overview.json"
)

FORBIDDEN_CONTACT_TERMS = (
    "slack",
    "email",
    "webhook",
    "contact_point",
    "contactPoint",
    "receiver",
    "pagerduty",
    "opsgenie",
)


def _alert_text() -> str:
    assert DOWNTIME_ALERT.exists(), f"Alert provisioning file missing: {DOWNTIME_ALERT}"
    return DOWNTIME_ALERT.read_text(encoding="utf-8")


def test_downtime_alert_yaml_contract():
    content = _alert_text()

    assert "Service Down" in content
    assert 'up{job="app"}' in content
    assert "prometheus" in content
    assert "1m" in content

    lowered = content.lower()
    for term in FORBIDDEN_CONTACT_TERMS:
        assert term not in lowered, (
            f"Alert config must not include contact point term: {term}"
        )


def test_downtime_alert_has_required_annotations():
    content = _alert_text()

    assert "Model serving API is unreachable" in content
    assert "Prometheus cannot scrape app:8000/metrics for 1 minute" in content


def test_downtime_alert_rule_group_interval():
    content = _alert_text()

    # Grafana scheduler base interval is 10s; rule group interval must be a multiple.
    assert "10s" in content


def _latency_alert_text() -> str:
    assert LATENCY_ALERT.exists(), f"Alert provisioning file missing: {LATENCY_ALERT}"
    return LATENCY_ALERT.read_text(encoding="utf-8")


def _dashboard_p95_expr() -> str:
    dashboard = json.loads(DASHBOARD_JSON.read_text(encoding="utf-8"))
    for panel in dashboard.get("panels", []):
        if panel.get("title") == "p95 Latency":
            for target in panel.get("targets", []):
                expr = target.get("expr")
                if expr:
                    return expr
    raise AssertionError("p95 Latency panel expr not found in dashboard")


def test_latency_alert_yaml_exists():
    assert LATENCY_ALERT.exists(), f"Alert provisioning file missing: {LATENCY_ALERT}"


def test_latency_alert_yaml_contract():
    content = _latency_alert_text()

    assert "High Latency" in content
    assert 'request_duration_bucket{path="/predict"}' in content
    assert "histogram_quantile(0.95" in content
    assert "2m" in content
    assert "100" in content
    assert "prometheus" in content

    lowered = content.lower()
    for term in FORBIDDEN_CONTACT_TERMS:
        assert term not in lowered, (
            f"Alert config must not include contact point term: {term}"
        )


def test_latency_alert_has_required_annotations():
    content = _latency_alert_text()

    lowered = content.lower()
    assert "p95" in lowered or "latency" in lowered
    assert "100ms" in content


def test_latency_alert_rule_group_interval():
    content = _latency_alert_text()

    # Grafana scheduler base interval is 10s; rule group interval must be a multiple.
    assert "10s" in content


def test_latency_alert_promql_matches_dashboard():
    content = _latency_alert_text()
    p95_expr = _dashboard_p95_expr()

    assert "histogram_quantile(0.95" in p95_expr
    assert p95_expr in content
