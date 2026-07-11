#!/usr/bin/env bash
# Compose hey benchmark for PERF-01–03: p50/p95/p99, RPS, error rate, peak CPU (D-01–D-05, D-07).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

API_BASE="http://localhost:8000"
PREDICT_URL="${API_BASE}/predict"
READY_URL="${API_BASE}/health/ready"
SAMPLE_IMAGE="${PROJECT_ROOT}/tests/fixtures/sample.jpg"
BOUNDARY="----BenchmarkBoundary7MA4YWxkTrZu0gW"
STATS_INTERVAL=2

if ! command -v hey >/dev/null 2>&1; then
  echo "error: hey is not installed (install from github.com/rakyll/hey only)" >&2
  echo "hint: go install github.com/rakyll/hey@latest && verify with hey -h" >&2
  exit 1
fi

if [[ ! -f "${SAMPLE_IMAGE}" ]]; then
  echo "error: sample image missing at ${SAMPLE_IMAGE}" >&2
  exit 1
fi

echo "Checking compose API readiness at ${READY_URL}"
if ! curl -sf "${READY_URL}" >/dev/null; then
  echo "error: ${READY_URL} is not reachable; start the stack with docker compose up" >&2
  exit 1
fi

APP_ID="$(docker compose ps -q app)"
if [[ -z "${APP_ID}" ]]; then
  echo "error: docker compose app service is not running" >&2
  exit 1
fi

BODY_FILE="$(mktemp)"
CPU_SAMPLES_FILE="$(mktemp)"
cleanup() {
  rm -f "${BODY_FILE}" "${CPU_SAMPLES_FILE}"
  if [[ -n "${STATS_PID:-}" ]]; then
    kill "${STATS_PID}" 2>/dev/null || true
    wait "${STATS_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

{
  printf -- '--%s\r\n' "${BOUNDARY}"
  printf 'Content-Disposition: form-data; name="file"; filename="sample.jpg"\r\n'
  printf 'Content-Type: image/jpeg\r\n\r\n'
  cat "${SAMPLE_IMAGE}"
  printf '\r\n--%s--\r\n' "${BOUNDARY}"
} > "${BODY_FILE}"

echo "Warming up ${PREDICT_URL} with multipart upload"
WARMUP_RESPONSE="$(curl -sf -X POST "${PREDICT_URL}" -F "file=@${SAMPLE_IMAGE}")"
if command -v jq >/dev/null 2>&1; then
  echo "${WARMUP_RESPONSE}" | jq -e '.predictions | length == 5' >/dev/null
fi

echo "Sampling docker stats every ${STATS_INTERVAL}s on app container ${APP_ID}"
: > "${CPU_SAMPLES_FILE}"
(
  while true; do
    docker stats "${APP_ID}" --no-stream --format '{{.CPUPerc}}' | tr -d '%' >> "${CPU_SAMPLES_FILE}"
    sleep "${STATS_INTERVAL}"
  done
) &
STATS_PID=$!

echo "Running hey -m POST -c 10 -z 60s against ${PREDICT_URL}"
set +e
HEY_OUTPUT="$(hey -m POST -c 10 -z 60s \
  -H "Content-Type: multipart/form-data; boundary=${BOUNDARY}" \
  -D "${BODY_FILE}" \
  "${PREDICT_URL}" 2>&1)"
HEY_EXIT=$?
set -e

kill "${STATS_PID}" 2>/dev/null || true
wait "${STATS_PID}" 2>/dev/null || true
STATS_PID=""

printf '%s\n' "${HEY_OUTPUT}"

PEAK_CPU="0"
if [[ -s "${CPU_SAMPLES_FILE}" ]]; then
  PEAK_CPU="$(sort -n "${CPU_SAMPLES_FILE}" | tail -1)"
fi

HOST_CORES="$(nproc 2>/dev/null || echo 1)"
if [[ -z "${HOST_CORES}" || "${HOST_CORES}" -lt 1 ]]; then
  HOST_CORES=1
fi
NORMALIZED_CPU="$(awk -v peak="${PEAK_CPU}" -v cores="${HOST_CORES}" 'BEGIN { printf "%.1f", peak / cores }')"

echo ""
echo "Peak CPU (app container, raw): ${PEAK_CPU}%"
echo "Peak CPU (normalized to host cores): ${NORMALIZED_CPU}%"

if [[ "${HEY_EXIT}" -ne 0 ]]; then
  echo "error: hey exited with status ${HEY_EXIT}" >&2
  exit "${HEY_EXIT}"
fi

if ! grep -q 'Latency distribution' <<< "${HEY_OUTPUT}"; then
  echo "error: hey output missing latency distribution" >&2
  exit 1
fi

TOTAL_REQUESTS=0
NON_200_COUNT=0
while IFS= read -r status_line; do
  if [[ "${status_line}" =~ \[([0-9]+)\][[:space:]]+([0-9]+)[[:space:]]+responses ]]; then
    code="${BASH_REMATCH[1]}"
    count="${BASH_REMATCH[2]}"
    TOTAL_REQUESTS=$((TOTAL_REQUESTS + count))
    if [[ "${code}" != "200" ]]; then
      NON_200_COUNT=$((NON_200_COUNT + count))
    fi
  fi
done < <(grep -E '^\s+\[[0-9]+\]' <<< "${HEY_OUTPUT}" || true)
if [[ -n "${TOTAL_REQUESTS}" && "${TOTAL_REQUESTS}" -gt 0 && "${NON_200_COUNT}" -gt $((TOTAL_REQUESTS / 2)) ]]; then
  echo "error: non-200 responses (${NON_200_COUNT}/${TOTAL_REQUESTS}) exceed majority threshold" >&2
  exit 1
fi
