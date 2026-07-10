# Werf/minikube defaults for --env local (source from other scripts: . scripts/k8s-env.sh)
# Namespace follows werf convention: {project}-{env} → basic-model-serving-local
export K8S_NAMESPACE="${K8S_NAMESPACE:-basic-model-serving-local}"
export K8S_API_SERVICE="${K8S_API_SERVICE:-model-serving}"
# Grafana Service when kube-prometheus-stack is bundled as a Helm subchart (not standalone prometheus-stack-grafana)
export K8S_GRAFANA_SERVICE="${K8S_GRAFANA_SERVICE:-basic-model-serving-local-grafana}"
