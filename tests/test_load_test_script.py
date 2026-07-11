"""Static contract validation for scripts/load-test.sh."""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOAD_TEST_SCRIPT = PROJECT_ROOT / "scripts" / "load-test.sh"

# Representative hey output (indented Summary/Status lines match real hey formatting).
HEY_OUTPUT_FIXTURE = """
Summary:
  Total:\t60.3667 secs
  Slowest:\t1.2345 secs
  Fastest:\t0.1234 secs
  Average:\t0.5678 secs
  Requests/sec:\t14.8261

Latency distribution:
  10% in 0.5000 secs
  50% in 0.6706 secs
  95% in 0.7981 secs

Status code distribution:
  [200]\t850 responses
  [500]\t45 responses
"""

HEY_OUTPUT_ALL_200_FIXTURE = """
Status code distribution:
  [200]\t895 responses
"""


def _script_text() -> str:
    assert LOAD_TEST_SCRIPT.exists(), f"Load test script missing: {LOAD_TEST_SCRIPT}"
    return LOAD_TEST_SCRIPT.read_text(encoding="utf-8")


def _script_lines_without_comments() -> str:
    return "\n".join(
        line
        for line in _script_text().splitlines()
        if not line.lstrip().startswith("#")
    )


def parse_status_distribution(hey_output: str) -> tuple[int, int]:
    """Mirror load-test.sh status-line parsing: total requests and non-200 count."""
    status_line_pattern = re.compile(r"^\s+\[(\d+)\]\s+(\d+)\s+responses", re.MULTILINE)
    total_requests = 0
    non_200_count = 0
    for match in status_line_pattern.finditer(hey_output):
        code = match.group(1)
        count = int(match.group(2))
        total_requests += count
        if code != "200":
            non_200_count += count
    return total_requests, non_200_count


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


def test_non_200_guard_parses_indented_status_lines():
    total, non_200 = parse_status_distribution(HEY_OUTPUT_FIXTURE)
    assert total == 895
    assert non_200 == 45


def test_total_requests_from_status_distribution():
    total, _ = parse_status_distribution(HEY_OUTPUT_ALL_200_FIXTURE)
    assert total == 895
    # Total: duration must not be mistaken for request count (60.3667 from fixture header).
    assert total != 60


def test_script_does_not_parse_total_duration_as_request_count():
    content = _script_lines_without_comments()
    assert "grep -E '^Total:'" not in content
    assert "awk '{print $2}'" not in content or "Total:" not in content


def test_normalized_cpu_output():
    content = _script_text()
    assert "nproc" in content
    assert "Peak CPU (app container, raw):" in content
    assert "Peak CPU (normalized to host cores):" in content
