import time

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REQUEST_COUNT = Counter(
    "request_count",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_DURATION = Histogram(
    "request_duration",
    "Request duration in seconds",
    ["method", "path"],
    buckets=(0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0),
)
PREDICTION_COUNT = Counter("prediction_count", "Successful predictions")

metrics_router = APIRouter(tags=["Metrics"])


@metrics_router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start

        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)

        REQUEST_COUNT.labels(
            method=request.method,
            path=path,
            status=str(response.status_code),
        ).inc()
        REQUEST_DURATION.labels(method=request.method, path=path).observe(elapsed)

        return response
