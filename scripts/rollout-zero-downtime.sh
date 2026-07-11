#!/usr/bin/env bash
# Hammer /health/ready during a rolling update to prove zero sustained downtime (D-19).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=k8s-env.sh
source "${SCRIPT_DIR}/k8s-env.sh"

API_URL=$(minikube service "${K8S_API_SERVICE}" -n "${K8S_NAMESPACE}" --url | head -1)
if [[ -z "${API_URL}" ]]; then
  echo "error: minikube service ${K8S_API_SERVICE} -n ${K8S_NAMESPACE} --url returned no URL" >&2
  exit 1
fi

echo "Polling ${API_URL}/health/ready every 0.5s (Ctrl+C to stop)"
while true; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "${API_URL}/health/ready" || echo "000")
  echo "$(date +%T) ${code}"
  sleep 0.5
done
