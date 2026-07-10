#!/usr/bin/env bash
# Hammer /health/ready during a rolling update to prove zero sustained downtime (D-19).
set -euo pipefail

API_URL=$(minikube service model-serving --url | head -1)
if [[ -z "${API_URL}" ]]; then
  echo "error: minikube service model-serving --url returned no URL" >&2
  exit 1
fi

echo "Polling ${API_URL}/health/ready every 0.5s (Ctrl+C to stop)"
while true; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health/ready" || echo "000")
  echo "$(date +%T) ${code}"
  sleep 0.5
done
