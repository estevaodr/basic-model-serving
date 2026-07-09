"""Static contract tests for .github/workflows/ci.yml (D-01..D-14)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WORKFLOW_PATH = Path(".github/workflows/ci.yml")
PROJECT_VERSION = "0.1.0"


@pytest.fixture(scope="module")
def workflow_text() -> str:
    assert WORKFLOW_PATH.is_file(), (
        ".github/workflows/ci.yml must exist (CI-01 workflow artifact)"
    )
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_ci_workflow_file_exists():
    """D-01: workflow file is the CI entrypoint."""
    assert WORKFLOW_PATH.is_file()


def test_d01_triggers_push_and_pr_to_main(workflow_text: str):
    """D-01: push to main and PRs targeting main."""
    assert re.search(r"push:\s*\n\s*branches:\s*\[main\]", workflow_text)
    assert re.search(
        r"pull_request:\s*\n\s*branches:\s*\[main\]", workflow_text
    )


def test_d03_concurrency_cancel_in_progress(workflow_text: str):
    """D-03: concurrency group cancels in-progress runs."""
    assert "cancel-in-progress: true" in workflow_text
    assert "github.workflow" in workflow_text
    assert "github.ref" in workflow_text


def test_permissions_contents_read_packages_write(workflow_text: str):
    """T-04-01: minimal token scopes for GHCR push."""
    assert re.search(r"contents:\s*read", workflow_text)
    assert re.search(r"packages:\s*write", workflow_text)


def test_d11_single_ci_job(workflow_text: str):
    """D-11: single job named ci — no quality-gate / build-and-push split."""
    assert re.search(r"^\s*ci:\s*$", workflow_text, re.MULTILINE)
    assert "quality-gate" not in workflow_text
    assert "build-and-push" not in workflow_text
    jobs_section = workflow_text.split("jobs:", 1)[1]
    job_names = re.findall(r"^\s{2}(\w+):\s*$", jobs_section, re.MULTILINE)
    assert job_names == ["ci"], f"expected exactly one job 'ci', got {job_names}"


def test_d07_d14_setup_uv_python_cache(workflow_text: str):
    """D-07/D-14: astral-sh/setup-uv with Python 3.12 and enable-cache."""
    assert "astral-sh/setup-uv@v8" in workflow_text
    assert 'python-version: "3.12"' in workflow_text
    assert "enable-cache: true" in workflow_text


def test_d07_cpu_torch_two_step_install(workflow_text: str):
    """D-07: CPU torch index then requirements.txt + requirements-dev.txt."""
    assert "download.pytorch.org/whl/cpu" in workflow_text
    assert "torch==2.12.1" in workflow_text
    assert "torchvision==0.27.1" in workflow_text
    assert "requirements.txt" in workflow_text
    assert "requirements-dev.txt" in workflow_text


def test_d05_d06_ruff_check_and_format_before_pytest(workflow_text: str):
    """D-05/D-06: ruff check and ruff format --check before pytest."""
    check_idx = workflow_text.index("ruff check")
    format_idx = workflow_text.index("ruff format --check")
    pytest_idx = workflow_text.index('pytest -m "not docker and not compose"')
    assert check_idx < format_idx < pytest_idx


def test_d04_pytest_excludes_docker_and_compose_markers(workflow_text: str):
    """D-04: CI runs unit/API tests only."""
    assert "not docker and not compose" in workflow_text


def test_d02_d12_push_gated_to_main_push_event(workflow_text: str):
    """D-02/D-12: PRs build without push; main push publishes."""
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
    assert f"type=raw,value=${{{{ steps.version.outputs.version }}}}" in workflow_text
    assert PROJECT_VERSION in workflow_text or "steps.version.outputs.version" in workflow_text


def test_docker_buildx_and_login_actions(workflow_text: str):
    """D-12: official docker actions with pinned majors."""
    assert "docker/setup-buildx-action@v4" in workflow_text
    assert "docker/login-action@v4" in workflow_text
    assert "docker/metadata-action@v6" in workflow_text
    assert "actions/checkout@v7" in workflow_text


def test_no_werf_or_compose_e2e_or_docker_scripts(workflow_text: str):
    """Excluded tooling: werf, compose E2E, scripts.docker."""
    assert "werf" not in workflow_text.lower()
    assert "docker-compose" not in workflow_text
    assert "scripts.docker" not in workflow_text
    assert "uv run docker" not in workflow_text
