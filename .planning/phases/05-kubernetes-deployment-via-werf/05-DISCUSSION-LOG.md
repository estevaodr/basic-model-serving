# Phase 5: Kubernetes Deployment (via werf) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-09
**Phase:** 5-Kubernetes Deployment (via werf)
**Areas discussed:** K8s monitoring stack, Image source, Service exposure, Resource sizing, Rollout strategy

---

## K8s Monitoring Stack

| Option | Description | Selected |
|--------|-------------|----------|
| kube-prometheus-stack | Operator + ServiceMonitor; industry-standard | ✓ |
| Hand-rolled manifests | Plain Deployment+ConfigMap like compose; lighter on minikube | |
| App-only in K8s | No in-cluster monitoring; compose is the monitoring demo | |
| You decide | Claude picks best portfolio fit | |

**User's choice:** kube-prometheus-stack

| Option | Description | Selected |
|--------|-------------|----------|
| Separate one-time helm install | Monitoring in own namespace; werf manages app only | |
| Bundled in werf chart | Single werf converge deploys app + monitoring | ✓ |
| You decide | | |

**User's choice:** Bundled in werf chart

| Option | Description | Selected |
|--------|-------------|----------|
| ServiceMonitor in app chart | With correct release: prometheus-stack label | ✓ |
| PodMonitor | Alternative discovery CRD | |
| You decide | | |

**User's choice:** ServiceMonitor in app chart

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse Phase 3 dashboard | Model Serving Overview JSON via provisioning | ✓ |
| kube-prometheus-stack defaults | Prove scraping only; skip custom dashboard | |
| You decide | | |

**User's choice:** Reuse Phase 3 dashboard

---

## Image Source

| Option | Description | Selected |
|--------|-------------|----------|
| GHCR by git SHA | Reproducible CI-built image at converge time | ✓ |
| GHCR latest | Simplest; less reproducible | |
| You decide | | |

**User's choice:** GHCR by git SHA (default deploy path)

| Option | Description | Selected |
|--------|-------------|----------|
| minikube image load | Fast local iteration without GHCR pull | ✓ |
| werf converge --dev only | Relaxes giterminism; still pulls GHCR | |
| GHCR only | Every deploy from registry | |
| You decide | | |

**User's choice:** minikube image load for local iteration

| Option | Description | Selected |
|--------|-------------|----------|
| Deploy-only werf.yaml | No default build; external CI image | |
| Optional werf build | Build config present; default external image | ✓ |
| You decide | | |

**User's choice:** Optional werf build (default external CI image)

| Option | Description | Selected |
|--------|-------------|----------|
| Public GHCR, no pull secret | Matches Phase 4 public package | ✓ |
| Document optional imagePullSecret | Future-proof for private packages | |
| You decide | | |

**User's choice:** Public GHCR, no pull secret

---

## Service Exposure

| Option | Description | Selected |
|--------|-------------|----------|
| ClusterIP + port-forward | Simplest kubectl workflow | |
| NodePort | Fixed host port | |
| minikube service | minikube-native URL opening | ✓ |
| You decide | | |

**User's choice:** minikube service for API

| Option | Description | Selected |
|--------|-------------|----------|
| minikube service for both | API and Grafana same pattern | ✓ |
| API minikube service; monitoring port-forward | Split access patterns | |
| You decide | | |

**User's choice:** minikube service for API and Grafana

| Option | Description | Selected |
|--------|-------------|----------|
| No Ingress | minikube service / port-forward only | ✓ |
| minikube ingress addon | Host-based routing | |
| You decide | | |

**User's choice:** No Ingress

| Option | Description | Selected |
|--------|-------------|----------|
| model-serving | Matches ARCHITECTURE.md DNS examples | ✓ |
| api | Matches compose service name | |
| You decide | | |

**User's choice:** Service name `model-serving`

---

## Resource Sizing

| Option | Description | Selected |
|--------|-------------|----------|
| 1 CPU limit / 500m request | Conservative | |
| 2 CPU limit / 1 request | Headroom for ResNet-50 + threads=2 | ✓ |
| 4 CPU limit / 2 request | Aggressive; may starve monitoring | |
| You decide | | |

**User's choice:** 2 CPU limit / 1 request

| Option | Description | Selected |
|--------|-------------|----------|
| 1Gi limit / 512Mi request | Tight for model weights | |
| 2Gi limit / 1Gi request | Comfortable for ResNet-50 runtime | ✓ |
| 4Gi limit / 2Gi request | Generous; pressures 8GB node | |
| You decide | | |

**User's choice:** 2Gi limit / 1Gi request

| Option | Description | Selected |
|--------|-------------|----------|
| TORCH_NUM_THREADS = CPU limit | ConfigMap value 2 when limit is 2 (PERF-04) | ✓ |
| Half of CPU limit | Headroom for Uvicorn | |
| You decide | | |

**User's choice:** TORCH_NUM_THREADS matches CPU limit integer

| Option | Description | Selected |
|--------|-------------|----------|
| 4 CPU / 8GB / 20GB disk | STACK.md recommended minikube sizing | ✓ |
| 6 CPU / 12GB | For 16GB+ laptops | |
| Document only | README guidance without enforcement | |
| You decide | | |

**User's choice:** Document 4 CPU / 8GB / 20GB minikube start

---

## Rollout Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| 1 replica | maxUnavailable 0 + maxSurge 1 | |
| 2 replicas | Always one ready during rollout | ✓ |
| You decide | | |

**User's choice:** 2 replicas

| Option | Description | Selected |
|--------|-------------|----------|
| maxUnavailable 0, maxSurge 1 | Never drop below ready count | ✓ |
| maxUnavailable 25% | Faster; brief capacity dip | |
| You decide | | |

**User's choice:** maxUnavailable 0, maxSurge 1

| Option | Description | Selected |
|--------|-------------|----------|
| Documented curl loop | Hammer endpoint during rollout | ✓ |
| In-cluster Job | Automated poll during rollout | |
| Manual eyeball | kubectl rollout status only | |
| You decide | | |

**User's choice:** Documented curl loop for zero-downtime proof

| Option | Description | Selected |
|--------|-------------|----------|
| New GHCR SHA after CI | Production-like flow | |
| minikube image load + converge | Fast local demo | ✓ |
| Document both | CI for realism, local for speed | |
| You decide | | |

**User's choice:** Rollout demo via minikube image load

---

## Claude's Discretion

- startupProbe timing budget
- kube-prometheus-stack subchart vs embedded values layout
- ServiceMonitor label exact matching
- werf optional build flag ergonomics
- Curl-loop script location
- Prometheus UI exposure (secondary to Grafana)

## Deferred Ideas

- Separate helm install for monitoring (rejected — bundled in werf)
- Hand-rolled K8s monitoring manifests (rejected)
- Ingress addon (rejected)
- In-cluster rollout proof Job (rejected)
- GHCR-only with no minikube image load (rejected for iteration)
