"""Static contract tests for .github/workflows/deploy.yml (Docker build+push)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

DEPLOY_WORKFLOW_PATH = Path(".github/workflows/deploy.yml")
PROJECT_VERSION = "0.1.0"


@pytest.fixture(scope="module")
def workflow_text() -> str:
    assert DEPLOY_WORKFLOW_PATH.is_file(), (
        ".github/workflows/deploy.yml must exist (CI-03 deploy artifact)"
    )
    return DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")


def test_deploy_workflow_file_exists():
    """Deploy workflow is the GHCR publish entrypoint."""
    assert DEPLOY_WORKFLOW_PATH.is_file()


def test_deploy_triggers_push_to_main_only(workflow_text: str):
    """Main push only — no pull_request trigger."""
    assert re.search(r"push:\s*\n\s*branches:\s*\[main\]", workflow_text)
    assert "pull_request" not in workflow_text


def test_d03_concurrency_cancel_in_progress(workflow_text: str):
    """D-03: concurrency group cancels in-progress runs."""
    assert "cancel-in-progress: true" in workflow_text
    assert "github.workflow" in workflow_text
    assert "github.ref" in workflow_text


def test_deploy_permissions_contents_read_packages_write(workflow_text: str):
    """T-04-01: deploy workflow scopes GHCR push via packages:write."""
    assert re.search(r"contents:\s*read", workflow_text)
    assert re.search(r"packages:\s*write", workflow_text)


def test_deploy_has_single_deploy_job(workflow_text: str):
    """Single deploy job — no quality-gate / build-and-push split."""
    assert re.search(r"^\s*deploy:\s*$", workflow_text, re.MULTILINE)
    assert "quality-gate" not in workflow_text
    assert "build-and-push" not in workflow_text
    jobs_section = workflow_text.split("jobs:", 1)[1]
    job_names = re.findall(r"^\s{2}(\w+):\s*$", jobs_section, re.MULTILINE)
    assert job_names == ["deploy"], (
        f"expected exactly one job 'deploy', got {job_names}"
    )


def test_d02_d12_push_gated_to_main_push_event(workflow_text: str):
    """D-02/D-12: main push publishes to GHCR."""
    assert (
        "github.event_name == 'push' && github.ref == 'refs/heads/main'"
        in workflow_text
    )
    assert "docker/build-push-action@v7" in workflow_text


def test_d13_gha_docker_layer_cache(workflow_text: str):
    """D-13: GitHub Actions cache for Docker layers."""
    assert "cache-from: type=gha" in workflow_text
    assert "cache-to: type=gha,mode=max" in workflow_text


def test_d08_d09_ghcr_metadata_tags(workflow_text: str):
    """D-08/D-09: SHA, latest, and bare semver tags on main."""
    assert "ghcr.io/${{ github.repository }}" in workflow_text
    assert "type=sha,prefix=,format=short" in workflow_text
    assert "type=raw,value=latest" in workflow_text
    assert "type=raw,value=${{ steps.version.outputs.version }}" in workflow_text
    assert (
        PROJECT_VERSION in workflow_text
        or "steps.version.outputs.version" in workflow_text
    )


def test_docker_buildx_and_login_actions(workflow_text: str):
    """D-12: official docker actions with pinned majors."""
    assert "docker/setup-buildx-action@v4" in workflow_text
    assert "docker/login-action@v4" in workflow_text
    assert "docker/metadata-action@v6" in workflow_text
    assert "actions/checkout@v7" in workflow_text


def test_no_lint_test_or_setup_uv_in_deploy(workflow_text: str):
    """Deploy workflow must not run lint, test, or uv install steps."""
    assert "astral-sh/setup-uv" not in workflow_text
    assert "ruff check" not in workflow_text
    assert "pytest" not in workflow_text


def test_no_werf_or_compose_e2e_or_docker_scripts(workflow_text: str):
    """Excluded tooling: werf, compose E2E, scripts.docker."""
    assert "werf" not in workflow_text.lower()
    assert "docker-compose" not in workflow_text
    assert "scripts.docker" not in workflow_text
    assert "uv run docker" not in workflow_text
