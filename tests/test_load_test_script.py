"""Static contract validation for scripts/load-test.sh."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOAD_TEST_SCRIPT = PROJECT_ROOT / "scripts" / "load-test.sh"


def _script_text() -> str:
    assert LOAD_TEST_SCRIPT.exists(), f"Load test script missing: {LOAD_TEST_SCRIPT}"
    return LOAD_TEST_SCRIPT.read_text(encoding="utf-8")


def test_load_test_script_exists():
    assert LOAD_TEST_SCRIPT.is_file(), "scripts/load-test.sh must exist"


def test_load_test_script_contract():
    content = _script_text()

    assert "hey" in content
    assert "-c 10" in content
    assert "-z 60s" in content
    assert "tests/fixtures/sample.jpg" in content
    assert "multipart/form-data" in content
    assert "boundary=" in content
    assert "/predict" in content
    assert "curl" in content
    assert "docker compose ps -q app" in content
    assert "docker stats" in content
    assert "set -euo pipefail" in content


def test_load_test_script_prerequisites_check():
    content = _script_text()

    assert "command -v hey" in content
    assert "health/ready" in content
