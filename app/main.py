"""Basic Model Serving API.

Run as a single Uvicorn worker (one process, one model copy in memory):

    uvicorn app.main:app --host 0.0.0.0 --port 8000

Do not pass ``--workers`` — concurrent requests are handled via FastAPI's
thread pool within a single process.
"""

from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.routes import health, predict
from app.core.config import settings
from app.core.logging import RequestIdMiddleware, configure_logging
from app.metrics.prometheus import PrometheusMiddleware, metrics_router
from app.models.resnet import ResNetClassifier

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    torch.set_num_threads(settings.torch_num_threads)
    app.state.ready = False
    app.state.classifier = ResNetClassifier()
    app.state.ready = True
    yield
    app.state.ready = False
    del app.state.classifier


app = FastAPI(
    title="Basic Model Serving",
    description=(
        "Portfolio-grade ResNet-50 image classification API. "
        "POST /predict accepts either a multipart file upload or a JSON "
        "`image_url` body. Observability endpoints: GET /health/live, "
        "GET /health/ready, and GET /metrics (Prometheus)."
    ),
    lifespan=lifespan,
)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "message": str(exc.detail)},
    )


app.include_router(predict.router)
app.include_router(health.router)
app.include_router(metrics_router)
