"""Basic Model Serving API.

Run as a single Uvicorn worker (one process, one model copy in memory):

    uvicorn app.main:app --host 0.0.0.0 --port 8000

Do not pass ``--workers`` — concurrent requests are handled via FastAPI's
thread pool within a single process.
"""

from contextlib import asynccontextmanager

import torch
from fastapi import FastAPI

from app.api.routes import health, predict
from app.core.config import settings
from app.models.resnet import ResNetClassifier


@asynccontextmanager
async def lifespan(app: FastAPI):
    torch.set_num_threads(settings.torch_num_threads)
    app.state.ready = False
    app.state.classifier = ResNetClassifier()
    app.state.ready = True
    yield
    app.state.ready = False
    del app.state.classifier


app = FastAPI(title="Basic Model Serving", lifespan=lifespan)
app.include_router(predict.router)
app.include_router(health.router)
