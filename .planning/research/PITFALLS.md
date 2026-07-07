# Pitfalls Research

**Domain:** ML model-serving REST API — PyTorch/FastAPI + Docker + minikube (Kubernetes) + werf + Prometheus/Grafana + GitHub Actions CI (build/push only, no auto-deploy)
**Researched:** 2026-07-06
**Confidence:** HIGH (cross-checked against Kubernetes, Prometheus, werf, OWASP, and Pillow official docs; MEDIUM where only community/blog sources were available — flagged inline)

## Critical Pitfalls

### Pitfall 1: Blocking the event loop with synchronous PyTorch inference

**What goes wrong:**
The `/predict` endpoint is declared `async def` and calls `model(input_tensor)` directly. PyTorch's CPU forward pass is synchronous and CPU-bound. Since Python's asyncio event loop is single-threaded, that one inference call freezes the loop for its entire duration — every other concurrent request (including `/health`) queues behind it. Under the project's own "10+ concurrent requests" requirement, p50 latency can jump from ~15ms to 300ms+ because requests serialize instead of running in FastAPI's thread pool.

**Why it happens:**
`async def` looks like the "modern FastAPI way," so it's the default reach even for CPU-bound work. Developers conflate "async" with "runs in parallel" — it only helps I/O-bound waiting, not CPU-bound compute.

**How to avoid:**
- Define the `/predict` endpoint as plain `def` (not `async def`) — FastAPI automatically offloads synchronous `def` handlers to its internal thread pool, keeping the event loop free.
- If you need `async def` (e.g., to `await` the URL-download branch), explicitly offload the blocking `model.forward()` call with `await asyncio.to_thread(...)`.
- Load the model once at startup (FastAPI `lifespan`/`on_event("startup")`), never per-request.
- Wrap inference in `torch.no_grad()` and call `model.eval()` once at load time.

**Warning signs:**
- p50 latency is fine under 1 concurrent request but degrades sharply (10x+) as concurrency rises past ~5-10 requests, even though CPU usage isn't pegged.
- `/health` requests become slow specifically while `/predict` requests are in flight.

**Phase to address:** API phase (inference endpoint implementation) — verify with a concurrency load test (e.g., 10 parallel requests) before moving to containerization.

---

### Pitfall 2: Thread-count vs. Kubernetes CPU-limit mismatch causes throttling collapse

**What goes wrong:**
PyTorch defaults `torch.get_num_threads()` to the number of *logical CPUs on the host*, not the container's Kubernetes CPU limit. `os.cpu_count()`/`multiprocessing.cpu_count()` behave the same way — they read the node's total cores, ignoring the pod's cgroup quota. If the Deployment sets `resources.limits.cpu: "1"` on a minikube node with 4+ vCPUs, PyTorch will spin up 4+ intra-op threads that all fight over a 1-CPU cgroup quota. The kernel's CFS scheduler throttles the container, and you see periods of `cpu.stat` throttling with p95/p99 latency spikes far worse than a correctly-threaded single-core process — directly threatening the <100ms and "CPU <70%" requirements.

**Why it happens:**
Container CPU limits are enforced via cgroup quotas, which are invisible to standard OS APIs (`os.cpu_count()`, `sched_getaffinity` in some runtimes). This is a well-known but frequently rediscovered footgun across Python/Go/Java ML-serving stacks.

**How to avoid:**
- Explicitly call `torch.set_num_threads(N)` at startup, where `N` matches the pod's CPU **limit** (or **request**, if you want to leave headroom), not the host's core count. Read `/sys/fs/cgroup/cpu.max` (cgroup v2) at boot to detect it programmatically, or just hardcode it from the same value used in the Deployment's `resources.limits.cpu`.
- Keep CPU `requests` and `limits` equal (Guaranteed QoS) for a latency-sensitive single-replica demo — this avoids surprise throttling once the node is under any load.
- For concurrency beyond one request at a time, prefer multiple Uvicorn workers over many PyTorch intra-op threads (1 worker per allocated CPU is a safer starting rule of thumb for CPU-bound inference than the generic `2×cores+1`) — but remember each worker loads its own full copy of the model into memory, so size `resources.requests/limits.memory` accordingly.

**Warning signs:**
- Latency is fine in local `docker-compose` (no CPU limit) but degrades specifically after deploying to minikube with `resources.limits.cpu` set.
- `kubectl exec` into the pod and check `cat /sys/fs/cgroup/cpu.stat` — nonzero/climbing `nr_throttled` and `throttled_usec` confirms this.

**Phase to address:** Kubernetes phase (resource requests/limits) — but the thread-count fix belongs in the API phase (startup code); write a note-to-self to revisit thread config once K8s resource limits are decided.

---

### Pitfall 3: Docker image bloats to 5-8GB because pip pulls CUDA-enabled PyTorch by default

**What goes wrong:**
`pip install torch` (or `torch` listed plainly in `requirements.txt`) resolves to the default PyPI wheel, which bundles full CUDA/cuDNN/NCCL libraries (`nvidia-cublas`, `nvidia-cusparse`, etc.) even on a CPU-only build. This alone can add 2.5-6GB to the image — blowing the project's explicit <2GB budget by 3-4x before any other dependency is added.

**Why it happens:**
The CPU-only wheel isn't the PyPI default; it's a separate index. Most tutorials and even AI-generated requirements files omit the CPU index URL because CUDA is assumed for training contexts.

**How to avoid:**
- Install torch from the CPU-only index explicitly: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu` (use `--index-url`, not `--extra-index-url`, on the torch install step specifically — `--extra-index-url` can still let pip's resolver prefer the CUDA wheel).
- Install torch *before* other dependencies in its own `RUN` layer so the CPU constraint is locked in before anything else can pull a conflicting requirement.
- Use a multi-stage Dockerfile: build wheels in a `python:3.11-slim` (or similar) builder stage, then copy only the installed site-packages / wheels into a clean runtime stage — this drops build toolchains (gcc, headers) that otherwise add 300-400MB.
- After building, run `docker images` and `du -sh` inside the container on `site-packages` to confirm where size actually went before assuming the base image is the problem.

**Warning signs:**
- `docker build` succeeds but `docker images` shows the tag at 4GB+.
- `pip show torch` inside the container reports a `+cu1xx` or unsuffixed version rather than `+cpu`.

**Phase to address:** Docker phase — this is a build-time check; add "image size <2GB" and "torch version ends in `+cpu`" as explicit acceptance criteria for the Dockerfile task.

---

### Pitfall 4: Non-root user breaks PyTorch's model cache and (if used) low-port binding

**What goes wrong:**
Two related failures surface only after switching `USER` to non-root (a project requirement):
1. `torch.hub`/`torchvision.models` default cache directory resolves to `~/.cache/torch/hub`. If the non-root user has no `$HOME` set or no write permission there, model loading throws `PermissionError: [Errno 13] Permission denied: '/.cache'` — often at container *runtime* (during weight download/load), not at build time, so it can pass a quick smoke build and fail on first real request or first cold start on a fresh node.
2. If the app (or a reverse proxy in front of it) tries to bind to a port <1024 (e.g., port 80), the non-root user gets `PermissionError`/`EACCES` — Linux reserves privileged ports for root by default.

**Why it happens:**
Switching to a non-root `USER` late in Dockerfile authoring is a common "security checklist" afterthought, so directory ownership and cache paths aren't verified against the new user until something crashes.

**How to avoid:**
- Bake the ResNet-50 weights into the image at build time (as root, during the build stage) rather than downloading them at container startup as the non-root runtime user — this also avoids a network dependency on first request and helps meet "model loaded in memory, no cold start."
- If weights must be fetched at runtime, explicitly set `ENV TORCH_HOME=/app/.cache/torch` (or similar) pointing at a directory you `mkdir` and `chown` to the non-root UID *before* the `USER` instruction switches.
- Use Uvicorn/FastAPI on a port ≥1024 (e.g., 8000) inside the container; if you need port 80 externally, map it via the Kubernetes Service (`port: 80` → `targetPort: 8000`), never by binding the container process itself to 80.
- Add a Dockerfile smoke test (`docker run --rm <image> python -c "import torch; m = torch.hub.load(...)"` as the final USER) to CI so this fails fast in the build phase, not in minikube.

**Warning signs:**
- `docker run` as the final non-root user throws `PermissionError` on first prediction request even though `docker build` succeeded.
- Works fine with `docker run -u root` but fails with the Dockerfile's declared `USER`.

**Phase to address:** Docker phase — verify by running the built image locally (not just building it) as part of the Docker task's acceptance check.

---

### Pitfall 5: Liveness probe kills the pod mid-model-load → CrashLoopBackOff

**What goes wrong:**
A `livenessProbe` on `/health` with a short `initialDelaySeconds` (e.g., 5-10s) fires before the ResNet-50 weights finish loading into memory (loading + first warm-up inference can take longer on constrained minikube CPU). Kubernetes kills the container for "failing" liveness, it restarts, fails again at the same point, and the pod enters `CrashLoopBackOff` — looking like an application crash when it's actually a probe misconfiguration. This directly threatens the "zero-downtime rolling updates" requirement, since a pod that never becomes Ready will stall a rollout.

**Why it happens:**
Liveness and readiness probe defaults/examples in most tutorials assume near-instant startup (a stateless CRUD API), not a process that loads a few hundred MB of weights into memory first.

**How to avoid:**
- Add a `startupProbe` on `/health` (or a dedicated `/health/startup`) with `failureThreshold × periodSeconds` sized to comfortably exceed worst-case model-load time on minikube's CPU (e.g., `failureThreshold: 30, periodSeconds: 2` = 60s budget). Liveness and readiness are suppressed until the startup probe passes once.
- Make `/health` return non-200 (or a distinct `/ready` returning 503) until the model object is actually loaded and a warm-up inference has succeeded — not just "the process is up." Otherwise the probe passes immediately and defeats its own purpose.
- Keep the liveness probe simple after startup (process alive) and let readiness gate traffic — don't reuse a single endpoint for both if their semantics differ.

**Warning signs:**
- `kubectl get pods` shows repeated restarts with `CrashLoopBackOff`; `kubectl describe pod` events show liveness failures timed exactly at the same offset after each restart.
- Works fine with `kubectl run` / local Docker (no probes) but fails only once deployed to K8s.

**Phase to address:** Kubernetes phase (probes) — write the model-aware `/health` semantics in the API phase, then wire the startup/liveness/readiness probes in the K8s phase.

---

### Pitfall 6: minikube runs out of memory/CPU once Prometheus + Grafana + kube-state-metrics + the app all compete for one node

**What goes wrong:**
minikube's default `minikube start` allocation (often 2 CPUs / ~4GB, driver-dependent) is sized for "run one small app," not "run one small app plus a full observability stack." Prometheus, Grafana, and (if installed via the common kube-prometheus-stack Helm chart) kube-state-metrics and node-exporter collectively want real headroom. On an under-provisioned node this manifests as pods `OOMKilled`, the API server becoming sluggish/unresponsive, or new pods stuck `Pending`.

**Why it happens:**
"Local minikube, zero cost" naturally biases toward minimal resource allocation, but a monitoring stack is not lightweight — it's easy to under-budget when sizing the cluster for the app alone and bolting on monitoring later.

**How to avoid:**
- Start minikube with explicit generous resources up front: e.g., `minikube start --cpus=4 --memory=6000` (adjust to host capacity) rather than accepting defaults.
- Prefer lightweight Prometheus/Grafana deployment for a portfolio-scale demo over the full kube-prometheus-stack (which also installs Alertmanager, node-exporter, kube-state-metrics, and multiple CRDs) — a minimal `prometheus` + `grafana` Deployment/Service pair scraping only your app's `/metrics` endpoint meets the stated requirements (custom app metrics, 5-7 dashboard panels, downtime alert) with a much smaller footprint.
- Set `resources.requests/limits` on every pod (app, Prometheus, Grafana) so the scheduler and OOM killer behave predictably instead of one component silently starving another.
- Confirm actual usage with `kubectl top pods` / `kubectl top nodes` before declaring the monitoring phase done, not just "it deployed."

**Warning signs:**
- `kubectl get events --sort-by=.metadata.creationTimestamp` shows `OOMKilled` or `Pending` (insufficient CPU/memory) events after adding the monitoring stack.
- The cluster was stable running the app alone and became unstable only after installing Prometheus/Grafana.

**Phase to address:** Kubernetes/Monitoring phase boundary — size the minikube VM (or document the required `minikube start` flags in the README) as part of the monitoring phase's setup, before deploying the observability stack.

---

### Pitfall 7: werf's giterminism silently deploys stale code because local changes aren't committed

**What goes wrong:**
werf enforces "giterminism" by default: `werf converge` builds and deploys from the current **Git commit**, not the working directory. If you edit a file and run `werf converge` without committing, werf either errors or (worse, if using `--dev` carelessly) behaves in a way that's easy to misread — the net effect for a solo dev used to `docker build .` picking up whatever's on disk is confusion: "I changed the code and redeployed, but the old behavior is still there." This is the single most-reported day-to-day werf friction point.

**Why it happens:**
Every other tool in this stack (`docker build`, `kubectl apply`, plain Helm) reads straight from the filesystem. werf's reproducibility guarantee is a deliberate design choice, but it's the opposite of what a solo dev's iteration muscle-memory expects, and the error messages about uncommitted files are easy to skim past.

**How to avoid:**
- During local iteration, use `werf converge --dev` (or `WERF_DEV=1`), which explicitly allows uncommitted and untracked files (still respecting `.gitignore`). Document this in the README as the standard local dev command.
- Reserve plain `werf converge` (no `--dev`) for the "final, reproducible deploy from a real commit" path you'd want to demonstrate to a reviewer — e.g., after committing, run `werf converge` and show it matches exactly what's in Git.
- Remember `werf converge` requires `--env`/`$WERF_ENV` to compute the Helm release name and namespace — decide and document this once (e.g., `WERF_ENV=local`) rather than rediscovering it per session.

**Warning signs:**
- "I edited the Dockerfile/app code, ran `werf converge`, and nothing changed" — check `git status` first; uncommitted changes are the most likely cause.
- werf errors mention "uncommitted" or "untracked" files blocking the build.

**Phase to address:** Kubernetes/Deploy phase — document the `--dev` vs. no-flag distinction in the README's "local development" section as part of this phase's deliverables.

---

### Pitfall 8: Server-Side Request Forgery (SSRF) via the "predict from image URL" feature

**What goes wrong:**
The spec explicitly allows `/predict` to accept an image URL and fetch it server-side. Without validation, an attacker (or an automated scanner, since this is a public portfolio repo) can pass `http://169.254.169.254/latest/meta-data/` (cloud metadata endpoint), `http://localhost:9090/...` (Prometheus, if co-located), or internal minikube service IPs, turning the API into a proxy that probes the internal network — and this is precisely the kind of finding a hiring-manager reviewer or an automated security scanner would flag on a "production-style" ML API.

**Why it happens:**
"Accept an image URL and download it" is treated as a convenience feature, not a network-facing action; the SSRF class of bugs is under-recognized outside dedicated security review.

**How to avoid:**
- Restrict accepted URL schemes to `http`/`https` only (reject `file://`, `gopher://`, etc.).
- Resolve the hostname to its IP address(es) *before* fetching, and reject anything in private/loopback/link-local ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`) using Python's `ipaddress.is_private`/`is_loopback`/`is_link_local`. Note: resolve-then-check is vulnerable to DNS-rebinding if there's a gap between check and connect — for a portfolio project, documenting this limitation is acceptable, but do the check.
- Disable automatic redirect-following (or re-validate the destination on every redirect hop) — a URL that first resolves to a public IP but redirects to `169.254.169.254` bypasses a naive one-time check.
- Enforce a strict request timeout (e.g., 3-5s) and a maximum response size on the download so a malicious or huge URL can't hang or exhaust the worker.
- If feasible, keep an allowlist of expected image hosts as the stricter alternative — reasonable for a demo where "predict from URL" is a nice-to-have.

**Warning signs:**
- No dedicated URL-validation function exists between "receive URL from client" and "issue outbound HTTP GET."
- The image-URL code path shares the exact same `httpx`/`requests` call pattern as any other outbound integration, with no IP/scheme checks.

**Phase to address:** API phase — this must be in the initial `/predict` implementation, not retrofitted; call it out explicitly in that phase's acceptance criteria (OWASP SSRF Cheat Sheet is the canonical reference).

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Skip `torch.set_num_threads()` tuning, rely on PyTorch defaults | Simpler startup code | CPU thread oversubscription once K8s CPU limits are applied (Pitfall 2) | Never once resource limits are set; fine only in unconstrained local `docker-compose` dev |
| Use `kube-prometheus-stack` Helm chart "because it's the standard" | Fast install, batteries included | Installs far more than minikube's node can comfortably run (Pitfall 6) | Acceptable only if you've explicitly sized minikube's `--cpus`/`--memory` to match |
| Leave Prometheus default histogram buckets (`.005…10` seconds) | Zero config | Poor resolution right around the 100ms SLO boundary — can't accurately compute p95 near the threshold that matters most | Never for the latency metric that's this project's core value prop; fine for auxiliary metrics |
| Download model weights at container startup instead of baking into the image | Smaller image, "always latest weights" | Cold-start network dependency, contradicts "no cold start" requirement, and surfaces the non-root cache-permission bug at runtime (Pitfall 4) | Never for a fixed, pinned model version like this project's |
| Accept any image URL without SSRF checks "since it's just a demo" | Faster to ship the URL-fetch feature | Public repo + working SSRF = a real, embarrassing, easily-scanned finding | Never — this is cheap to fix and expensive to be caught with |
| Skip `werf --dev` and just commit-and-converge every iteration | Avoids learning giterminism nuance | Extremely slow inner loop (a commit per tweak); use `docker-compose` for iteration instead, per the project's own plan | Acceptable if you lean on docker-compose for iteration and reserve werf for deploy checkpoints only |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|-------------------|
| GitHub Actions → GHCR | Workflow gets `403 Forbidden` on push because the default `GITHUB_TOKEN` lacks `packages: write`, or the org/repo's Actions settings default to read-only | Add `permissions: packages: write` (and `contents: read`) at the job level; on first successful push from the workflow, GHCR auto-links Actions access for that repo — if the package was ever pushed via a PAT first, you may need to add the repo under the package's "Manage Actions access" manually |
| minikube → GHCR (pulling the built image) | Deployment references `ghcr.io/...` and gets `ImagePullBackOff` because minikube's runtime has no credentials for a private package, or because CI never actually deployed (by design) so the "latest" tag in the manifest doesn't match what's locally available | Since this project explicitly keeps deploy manual/local, prefer building directly into minikube's Docker daemon (`eval $(minikube docker-env)` then `docker build`) or `minikube image load <tag>` for the local werf-driven deploy, with `imagePullPolicy: IfNotPresent`/`Never`; reserve the GHCR pull path (with an `imagePullSecrets` docker-registry secret) only if you deliberately want to demonstrate pulling the CI-published image |
| minikube ↔ imagePullPolicy | Manifest still says `imagePullPolicy: Always`, so Kubernetes ignores the freshly-loaded local image and tries (and fails, or silently pulls stale) a registry pull anyway | Set `IfNotPresent` or `Never` explicitly whenever deploying a locally-built/loaded image; only use `Always` when genuinely pulling from GHCR |
| Prometheus (persistent storage) on minikube | Prometheus pod fails to start with a persistent volume because it runs as a non-root user by default and the mounted volume is root-owned | Set the correct `fsGroup`/`securityContext` on the Prometheus pod spec so the mounted volume is group-writable by the Prometheus UID, or use an `initContainer` to `chown` the volume before the main container starts |
| Grafana → Prometheus data source | Dashboard queries return "No data" because the data source URL uses `localhost` instead of the in-cluster Service DNS name | Point Grafana's Prometheus data source at the Kubernetes Service DNS (e.g., `http://prometheus:9090`), not `localhost` — this only works across pods, not across host/container boundaries |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Uvicorn single worker, default thread pool, `async def` inference | Fine for 1 request at a time in manual testing | Use plain `def` handlers (thread-pool offload) or explicit multi-worker Uvicorn sized to actual CPU allocation | Breaks at the project's own "10+ concurrent requests" requirement (Pitfall 1) |
| PyTorch default thread count in a CPU-limited container | Looks fine in `docker-compose` (no CPU limit) or with 1 replica idle | Pin `torch.set_num_threads()` to the pod's CPU limit | Breaks specifically after deploying to K8s with `resources.limits.cpu` set (Pitfall 2) |
| No request body size cap on `/predict` multipart upload | Fine with small test images | Enforce a max upload size (e.g., 5-10MB) before passing bytes to Pillow; reject early | Breaks (memory spike / slow request) the first time someone (or a scanner) uploads a large or maliciously-crafted image |
| CI pipeline with no Docker layer or pip cache | Fine on the very first run | Add `cache-from`/`cache-to: type=gha` on `docker/build-push-action`, and/or a BuildKit `--mount=type=cache,target=/root/.cache/pip` layer for the torch install step | Breaks the "<10 minute pipeline" requirement almost immediately, since re-downloading PyTorch wheels alone can take several minutes per run |
| Prometheus with no retention/size cap on minikube's PV | Fine for the first few days of a demo | Set both `--storage.tsdb.retention.time` (e.g., `10d` to satisfy the "7+ day" requirement) and `--storage.tsdb.retention.size` at ~80-85% of the allocated PV size (compaction temporarily exceeds the configured limit, so leave headroom) | Breaks (disk full, Prometheus crash) once the PV fills — easy to miss on a demo you only run for a few days, but worth configuring correctly to show you know the gotcha |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Fetching user-supplied image URLs without validation | SSRF — internal network/cloud-metadata probing via the model API (Pitfall 8) | Scheme allowlist + private/loopback IP denylist on resolved hostname + no auto-redirect-follow + timeout + size cap |
| Trusting `Content-Type`/file extension on multipart upload | Attacker uploads a non-image (or polyglot) file labeled `image/jpeg`; can also be used to probe for parser vulnerabilities | Verify actual file type via magic bytes (`python-magic` or Pillow's own format sniffing on `Image.open()`), not the client-declared MIME type or filename extension |
| Calling `Image.load()`/decoding immediately with `Image.MAX_IMAGE_PIXELS` unset or set to `None` | Decompression-bomb DoS — a tiny file expands to gigabytes in memory, crashing the pod | Never set `MAX_IMAGE_PIXELS = None`; use `Image.open()` for cheap metadata + `verify()` first, and treat `DecompressionBombWarning` as a hard error, not a warning to log and ignore |
| Running Prometheus/Grafana with default/no auth on a network-reachable Service | Anyone who can reach the Grafana Service can view dashboards; default Grafana admin credentials (`admin`/`admin`) are widely scanned for | Change default Grafana admin credentials via a Secret/env var at deploy time even for a local demo; don't expose `NodePort`/`LoadBalancer` for Grafana beyond what's needed for the demo walkthrough |
| GHCR package left public by default without review | Anyone can pull and inspect the built image, including any secrets accidentally baked into layers | Explicitly decide public vs. private for the GHCR package, and audit the Dockerfile for baked-in secrets (should be none — config is via env vars per the spec) before making it public |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Generic 500 error on invalid/corrupt image upload | Reviewer testing the API with a bad file sees an unhelpful stack trace instead of a clean error | Catch `PIL.UnidentifiedImageError`/decompression-bomb exceptions explicitly and return a structured 400 with a clear message |
| `/health` returns 200 even when the model failed to load | Silent failure — pod looks "ready" in K8s but every `/predict` call 500s | Make `/health`/readiness check actual model-loaded state, not just "process is running" (ties into Pitfall 5) |
| No indication of which image formats/sizes are accepted in `/docs` | Reviewer has to trial-and-error to find working inputs | Document accepted formats, max size, and both upload modes (multipart + URL) clearly in the FastAPI route's docstring/OpenAPI metadata so `/docs` is self-explanatory |
| Grafana dashboard with metrics but no alert wired to anything visible in the demo | Reviewer can't tell if "alerting" actually works without digging into Alertmanager config | Include one deliberately-triggerable alert (e.g., stop the app pod and show the "service down" alert fire in Grafana/Alertmanager) as part of the demo script |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Docker image built:** Often missing the CPU-only torch check — verify `docker images` shows <2GB and `pip show torch` inside the container reports a `+cpu` version, not `+cu1xx`.
- [ ] **Non-root user set:** Often missing a working directory/cache permission check — verify by actually *running* the container (not just building it) through a full predict request as the non-root user, including a fresh model-cache scenario.
- [ ] **Kubernetes probes configured:** Often missing a `startupProbe`, so a liveness/readiness probe alone "looks configured" but will `CrashLoopBackOff` under real model-load timing — verify by watching `kubectl get pods -w` through a full pod restart, not just checking the YAML has probe fields.
- [ ] **Monitoring stack "running":** Often missing verification that metrics actually flow end-to-end — verify by opening Grafana, confirming the dashboard panels populate with real data (not "No data"), and confirming the configured alert can actually fire (test by stopping the app pod).
- [ ] **CI pipeline "green":** Often missing verification that "test" actually exercises the inference path (not just linting/import checks) and that the <10 minute budget holds on a *cold* cache run, not just warm-cache reruns.
- [ ] **`/predict` URL-fetch feature:** Often missing SSRF protection entirely — verify by manually testing `http://169.254.169.254/` and `http://localhost:<any-internal-port>/` against the deployed endpoint and confirming both are rejected.
- [ ] **werf deploy documented as "manual":** Often missing the `--dev` vs. committed-state distinction in the README — verify a fresh clone + fresh commit can `werf converge` successfully end-to-end, not just "it worked on my dirty working tree."

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|------------------|
| Docker image bloated from CUDA torch wheels | LOW | Re-pin `requirements.txt`/Dockerfile `RUN` line to `--index-url https://download.pytorch.org/whl/cpu`, rebuild; no app-code changes needed |
| Event-loop blocking under concurrency | LOW-MEDIUM | Change `/predict` from `async def` to `def` (or wrap the inference call in `asyncio.to_thread`); re-run the concurrency load test to confirm |
| CrashLoopBackOff from premature liveness kill | LOW | Add a `startupProbe` with adequate `failureThreshold × periodSeconds`; no image rebuild needed, just a manifest/values change + `werf converge` |
| minikube OOM from monitoring stack | MEDIUM | `minikube stop`, restart with higher `--cpus`/`--memory`, or swap the full `kube-prometheus-stack` for a minimal hand-rolled Prometheus+Grafana deployment scraping only the app |
| SSRF discovered after the fact | MEDIUM | Add URL/IP validation to the fetch function immediately; audit logs (if any were kept) for prior suspicious URL parameters; rotate any credentials that might have been reachable from the pod's network position |
| werf giterminism confusion mid-demo | LOW | `git status`, commit or stash, then re-run `werf converge` (or add `--dev` for the immediate iteration); document the correct flow in the README once resolved |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| Event-loop blocking on synchronous inference | API phase | Load test with 10+ concurrent requests before moving to containerization; p50/p95 should not degrade disproportionately with concurrency |
| Thread-count vs. CPU-limit mismatch | API phase (thread config) + Kubernetes phase (resource limits) | `kubectl exec` → check `/sys/fs/cgroup/cpu.stat` for `nr_throttled` after a load test against the deployed pod |
| Docker image size bloat from CUDA wheels | Docker phase | `docker images` shows <2GB; `pip show torch` inside container confirms `+cpu` |
| Non-root cache/port permission failures | Docker phase | Run the built image (not just build it) through a full predict request as the declared non-root `USER` |
| Liveness probe kills mid-model-load | Kubernetes phase | Watch a full pod restart cycle (`kubectl get pods -w`) and confirm no `CrashLoopBackOff` |
| minikube resource exhaustion with monitoring stack | Kubernetes/Monitoring phase boundary | `kubectl top nodes`/`kubectl get events` clean (no OOMKilled/Pending) after deploying app + Prometheus + Grafana together |
| werf giterminism confusion | Kubernetes/Deploy phase | README documents `--dev` vs. committed-state deploy flow; a fresh commit + `werf converge` (no `--dev`) succeeds |
| SSRF via image URL fetch | API phase | Manual test against `169.254.169.254` and internal service IPs/ports confirms rejection |
| Multipart upload decompression bomb / spoofed type | API phase | Unit test with a crafted oversized/spoofed-type file confirms clean 400, not a crash or hang |
| Prometheus histogram buckets / cardinality | Monitoring phase | Custom buckets defined around the 100ms SLO boundary; label review confirms no raw path/user-supplied values in metric labels |
| Prometheus retention/disk sizing | Monitoring phase | `--storage.tsdb.retention.time`/`.size` explicitly set; PV sized with headroom above the size limit |
| GHCR permissions/visibility | CI/CD phase | First real CI run pushes successfully with `permissions: packages: write`; package visibility (public/private) deliberately chosen |
| CI pipeline exceeding 10-minute budget | CI/CD phase | Cold-cache pipeline run timed and under budget; `type=gha` Docker cache and pip cache configured |

## Sources

- Kubernetes official docs — [Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/) (HIGH)
- Prometheus official docs — [Storage](https://prometheus.io/docs/prometheus/latest/storage/), [Histograms and summaries](https://prometheus.io/docs/practices/histograms/) (HIGH)
- OWASP — [Server Side Request Forgery Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html) (HIGH)
- Pillow official docs — [Security](https://pillow.readthedocs.io/en/latest/handbook/security.html) (HIGH)
- werf official docs — [Giterminism](https://werf.io/docs/v2/usage/project_configuration/giterminism.html), [werf converge reference](https://werf.io/docs/v2/reference/cli/werf_converge.html) (HIGH)
- minikube official docs/repo — [Registries](https://minikube.sigs.k8s.io/docs/handbook/registry/), [pushing.md handbook](https://github.com/kubernetes/minikube/blob/master/site/content/en/docs/handbook/pushing.md) (HIGH)
- pytorch/pytorch GitHub issue #146786 — CPU-only install pulling CUDA deps (HIGH — first-party repo)
- vllm-project/vllm PR #34462 — CFS-aware torch thread count in containers (MEDIUM-HIGH — first-party ML-serving project encountering the exact cgroup/thread mismatch)
- GitHub Docs — [Publishing and installing a package with GitHub Actions](https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions) (HIGH)
- Community/blog sources cross-checked across multiple independent posts (MEDIUM): FastAPI async-vs-blocking inference pattern (zentara.co, levelup.gitconnected, theneuralbase.com), PyTorch Docker image-size reduction (learnixo.io, veltrix.ge, analyticsindiamag.com/OLX case study), Prometheus cardinality explosions (dev.to, infrarunbook.com, fosskit.com), Docker rootless/non-root port binding (nickjanetakis.com, Stack Overflow), minikube resource sizing for monitoring stacks (Medium "Taking Baby Steps" post, prianshu-404daily.hashnode.dev)

---
*Pitfalls research for: ML model-serving (PyTorch/FastAPI + Docker + minikube/K8s + werf + Prometheus/Grafana + GitHub Actions CI)*
*Researched: 2026-07-06*
