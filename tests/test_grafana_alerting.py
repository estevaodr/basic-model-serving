"""Static contract validation for Grafana unified alerting provisioning."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOWNTIME_ALERT = (
    PROJECT_ROOT / "monitoring" / "grafana" / "provisioning" / "alerting" / "downtime.yml"
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
        assert term not in lowered, f"Alert config must not include contact point term: {term}"


def test_downtime_alert_has_required_annotations():
    content = _alert_text()

    assert "Model serving API is unreachable" in content
    assert "Prometheus cannot scrape app:8000/metrics for 1 minute" in content


def test_downtime_alert_rule_group_interval():
    content = _alert_text()

    # Grafana scheduler base interval is 10s; rule group interval must be a multiple.
    assert "10s" in content
