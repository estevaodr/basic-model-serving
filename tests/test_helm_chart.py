"""Static contract tests for werf.yaml and .helm app chart (K8S-01–K8S-04, K8S-06)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

WERF_PATH = Path("werf.yaml")
HELM_DIR = Path(".helm")
CHART_YAML = HELM_DIR / "Chart.yaml"
DEPLOYMENT_TEMPLATE = HELM_DIR / "templates" / "deployment.yaml"
SERVICE_TEMPLATE = HELM_DIR / "templates" / "service.yaml"
CONFIGMAP_TEMPLATE = HELM_DIR / "templates" / "configmap.yaml"
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


def test_chart_no_kube_prometheus_stack_dependency():
    """Monitoring subchart is 05-02 scope — app-only chart here."""
    text = CHART_YAML.read_text(encoding="utf-8")
    assert "kube-prometheus-stack" not in text


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
