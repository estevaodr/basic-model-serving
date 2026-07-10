"""Static contract tests for werf.yaml and .helm app chart (K8S-01–K8S-04, K8S-06)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

WERF_PATH = Path("werf.yaml")
README_PATH = Path("README.md")
ROLLOUT_SCRIPT = Path("scripts/rollout-zero-downtime.sh")
VALUES_LOCAL = Path(".helm/values-local.yaml")
HELM_DIR = Path(".helm")
CHART_YAML = HELM_DIR / "Chart.yaml"
CHART_LOCK = HELM_DIR / "Chart.lock"
DEPLOYMENT_TEMPLATE = HELM_DIR / "templates" / "deployment.yaml"
SERVICE_TEMPLATE = HELM_DIR / "templates" / "service.yaml"
CONFIGMAP_TEMPLATE = HELM_DIR / "templates" / "configmap.yaml"
SERVICEMONITOR_TEMPLATE = HELM_DIR / "templates" / "servicemonitor.yaml"
GRAFANA_DASHBOARD_TEMPLATE = HELM_DIR / "templates" / "grafana-dashboard.yaml"
DASHBOARD_JSON = HELM_DIR / "dashboards" / "model-serving-overview.json"
DASHBOARD_SOURCE = Path("monitoring/grafana/dashboards/model-serving-overview.json")
VALUES_YAML = HELM_DIR / "values.yaml"
ENV_EXAMPLE_PATH = Path(".env.example")

REQUIRED_ENV_KEYS = (
    "TORCH_NUM_THREADS",
    "MAX_UPLOAD_BYTES",
    "URL_TIMEOUT",
    "LOG_LEVEL",
)

HELM_AVAILABLE = shutil.which("helm") is not None
skip_no_helm = pytest.mark.skipif(not HELM_AVAILABLE, reason="helm not installed")


@pytest.fixture(scope="module")
def env_example_values() -> dict[str, str]:
    text = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


@pytest.fixture(scope="module")
def rendered_manifests() -> str:
    """D-05: helm template with GHCR image coordinates (deploy-only path)."""
    if not HELM_AVAILABLE:
        pytest.skip("helm not installed")
    assert CHART_YAML.is_file(), "D-07: .helm/Chart.yaml must exist for render"
    result = subprocess.run(
        [
            "helm",
            "template",
            "test",
            str(HELM_DIR),
            "--set",
            "image.repository=ghcr.io/estevaodr/basic-model-serving",
            "--set",
            "image.tag=testsha",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_werf_yaml_exists():
    """D-05/D-07: werf.yaml required for manual werf converge (K8S-06)."""
    assert WERF_PATH.is_file(), "werf.yaml must exist at repo root"


def test_helm_chart_exists():
    """D-07: app Helm chart metadata at .helm/Chart.yaml (K8S-06)."""
    assert CHART_YAML.is_file(), ".helm/Chart.yaml must exist"


def test_werf_yaml_project_name():
    """D-05: werf project name basic-model-serving."""
    text = WERF_PATH.read_text(encoding="utf-8")
    assert "project: basic-model-serving" in text


def test_chart_has_kube_prometheus_dependency():
    """D-01/D-02: kube-prometheus-stack bundled as Helm subchart."""
    text = CHART_YAML.read_text(encoding="utf-8")
    assert "kube-prometheus-stack" in text, "D-01: Chart.yaml must list kube-prometheus-stack dependency"
    assert "prometheus-community.github.io/helm-charts" in text, (
        "D-02: dependency must come from official prometheus-community repo"
    )


def test_chart_lock_exists():
    """D-02: Chart.lock pins subchart versions after helm dependency update."""
    assert CHART_LOCK.is_file(), "D-02: .helm/Chart.lock must exist"
    text = CHART_LOCK.read_text(encoding="utf-8")
    assert "kube-prometheus-stack" in text, "D-02: Chart.lock must pin kube-prometheus-stack"


def test_servicemonitor_template_exists():
    """D-03: ServiceMonitor template required for Prometheus Operator scrape."""
    assert SERVICEMONITOR_TEMPLATE.is_file(), "D-03: .helm/templates/servicemonitor.yaml must exist"


def test_servicemonitor_release_label_uses_release_name():
    """D-03: release label must use Release.Name, not hardcoded prometheus-stack alone."""
    text = SERVICEMONITOR_TEMPLATE.read_text(encoding="utf-8")
    assert "Release.Name" in text, "D-03: ServiceMonitor release label must template .Release.Name"
    assert re.search(r"release:\s*\{\{\s*\.Release\.Name\s*\}\}", text), (
        "D-03: release label must be {{ .Release.Name }}"
    )
    assert not re.search(r"release:\s*prometheus-stack\s*$", text, re.MULTILINE), (
        "D-03: must not hardcode release: prometheus-stack without Release.Name"
    )


def test_servicemonitor_metrics_endpoint():
    """D-03: ServiceMonitor scrapes /metrics on http port."""
    text = SERVICEMONITOR_TEMPLATE.read_text(encoding="utf-8")
    assert "path: /metrics" in text, "D-03: ServiceMonitor endpoint path must be /metrics"
    assert re.search(r"port:\s*http", text), "D-03: ServiceMonitor endpoint port must be http"


def test_grafana_dashboard_configmap_template():
    """D-04: Grafana dashboard ConfigMap with sidecar label."""
    assert GRAFANA_DASHBOARD_TEMPLATE.is_file(), (
        "D-04: .helm/templates/grafana-dashboard.yaml must exist"
    )
    text = GRAFANA_DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
    assert "grafana_dashboard" in text, "D-04: dashboard ConfigMap must have grafana_dashboard label"


def test_dashboard_json_embedded():
    """D-04: Phase 3 dashboard JSON copied into chart dashboards/."""
    assert DASHBOARD_JSON.is_file(), (
        "D-04: .helm/dashboards/model-serving-overview.json must exist"
    )
    assert DASHBOARD_SOURCE.is_file(), "source dashboard JSON must exist"
    source_size = DASHBOARD_SOURCE.stat().st_size
    chart_size = DASHBOARD_JSON.stat().st_size
    assert chart_size >= source_size * 0.95, (
        f"D-04: chart dashboard size {chart_size} must be within 5% of source {source_size}"
    )


def test_deployment_template_replicas_and_rollout():
    """D-17/D-18: 2 replicas, maxUnavailable 0, maxSurge 1."""
    text = DEPLOYMENT_TEMPLATE.read_text(encoding="utf-8")
    assert re.search(r"replicas:\s*2", text), "D-17: expected 2 replicas"
    assert "maxUnavailable: 0" in text, "D-18: zero-downtime rollout"
    assert "maxSurge: 1" in text, "D-18: surge during rollout"


def test_deployment_template_resources():
    """D-13: CPU request 1 / limit 2, memory limit 2Gi."""
    text = DEPLOYMENT_TEMPLATE.read_text(encoding="utf-8")
    assert re.search(r"cpu:\s*[\"']?1[\"']?", text), "D-13: CPU request 1"
    assert re.search(r"cpu:\s*[\"']?2[\"']?", text), "D-13: CPU limit 2"
    assert "2Gi" in text, "D-13: memory limit 2Gi"


def test_deployment_template_configmap_envfrom():
    """D-15/K8S-03: envFrom configMapRef model-serving-config."""
    text = DEPLOYMENT_TEMPLATE.read_text(encoding="utf-8")
    assert "configMapRef:" in text
    assert "name: model-serving-config" in text


def test_deployment_template_probes():
    """K8S-04: startup/readiness on /health/ready, liveness on /health/live."""
    text = DEPLOYMENT_TEMPLATE.read_text(encoding="utf-8")
    assert "startupProbe:" in text
    assert "readinessProbe:" in text
    assert "livenessProbe:" in text
    assert "/health/ready" in text
    assert "/health/live" in text
    startup_section = text.split("startupProbe:", 1)[1].split("readinessProbe:", 1)[0]
    assert "failureThreshold: 24" in startup_section, "120s startup budget"


def test_deployment_template_image_values_pattern():
    """D-05: image from Values.image — not global.werf.images (Anti-Pattern 3)."""
    text = DEPLOYMENT_TEMPLATE.read_text(encoding="utf-8")
    assert "global.werf.images" not in text
    assert ".Values.image.repository" in text
    assert ".Values.image.tag" in text


def test_service_template_nodeport():
    """D-12/D-09: Service name model-serving, type NodePort, port 8000."""
    text = SERVICE_TEMPLATE.read_text(encoding="utf-8")
    assert "name: model-serving" in text
    assert "type: NodePort" in text
    assert re.search(r"port:\s*8000", text)


def test_configmap_template_env_vars(env_example_values: dict[str, str]):
    """D-15/PERF-04: ConfigMap mirrors .env.example four keys."""
    text = CONFIGMAP_TEMPLATE.read_text(encoding="utf-8")
    for key in REQUIRED_ENV_KEYS:
        assert key in text, f"ConfigMap missing {key}"
    for key, value in env_example_values.items():
        assert value in text, f"ConfigMap missing value for {key}"
    assert 'TORCH_NUM_THREADS: "2"' in text or "TORCH_NUM_THREADS: '2'" in text


@skip_no_helm
def test_rendered_deployment_image_ghcr(rendered_manifests: str):
    """D-05: rendered image uses --set repository and tag."""
    assert "ghcr.io/estevaodr/basic-model-serving:testsha" in rendered_manifests
    assert "global.werf.images" not in rendered_manifests


@skip_no_helm
def test_rendered_deployment_image_local():
    """D-06: local iteration path renders basic-model-serving:local."""
    result = subprocess.run(
        [
            "helm",
            "template",
            "test",
            str(HELM_DIR),
            "--set",
            "image.repository=basic-model-serving",
            "--set",
            "image.tag=local",
            "--set",
            "image.pullPolicy=IfNotPresent",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert 'image: "basic-model-serving:local"' in result.stdout


def test_values_kube_prometheus_retention():
    """D-02: prometheus retention 7d in subchart values."""
    text = VALUES_YAML.read_text(encoding="utf-8")
    assert "retention: 7d" in text, "kube-prometheus-stack prometheus retention must be 7d"


def test_values_grafana_nodeport():
    """D-10: Grafana NodePort for minikube service access."""
    text = VALUES_YAML.read_text(encoding="utf-8")
    assert "type: NodePort" in text, "kube-prometheus-stack grafana service must be NodePort"


@skip_no_helm
def test_rendered_servicemonitor_kind(rendered_manifests: str):
    """K8S-06: full stack render includes ServiceMonitor for /metrics scrape."""
    assert "kind: ServiceMonitor" in rendered_manifests
    assert "path: /metrics" in rendered_manifests


@skip_no_helm
def test_rendered_grafana_dashboard_configmap(rendered_manifests: str):
    """D-04: full stack render includes dashboard ConfigMap for Grafana sidecar."""
    assert "name: model-serving-overview" in rendered_manifests
    assert "grafana_dashboard" in rendered_manifests


def test_rollout_script_exists():
    """D-19: rollout script hammers /health/ready via minikube service URL."""
    assert ROLLOUT_SCRIPT.is_file(), "scripts/rollout-zero-downtime.sh must exist"
    assert ROLLOUT_SCRIPT.stat().st_mode & 0o111, "rollout script must be executable"
    text = ROLLOUT_SCRIPT.read_text(encoding="utf-8")
    assert "/health/ready" in text
    assert "minikube service model-serving" in text


def test_readme_k8s_section():
    """D-05/D-06/D-16/K8S-06: README documents minikube + werf converge paths."""
    text = README_PATH.read_text(encoding="utf-8")
    assert "Kubernetes" in text or "minikube + werf" in text
    assert "minikube start --cpus=4 --memory=8192" in text, "D-16: minikube sizing"
    assert "werf converge --without-images" in text, "D-05: GHCR SHA converge"
    assert "minikube service model-serving" in text, "D-09: API access"
    assert "minikube image load basic-model-serving:local" in text, "D-06: local iteration"
    assert "rollout-zero-downtime" in text, "D-19: zero-downtime demo"
    assert "does not deploy" in text.lower() or "does not run `werf converge`" in text, (
        "CI manual deploy boundary"
    )


def test_values_local_exists():
    """D-06: values-local.yaml overrides image for minikube image load path."""
    assert VALUES_LOCAL.is_file(), ".helm/values-local.yaml must exist"
    text = VALUES_LOCAL.read_text(encoding="utf-8")
    assert "repository: basic-model-serving" in text
    assert "tag: local" in text
    assert "pullPolicy: IfNotPresent" in text
