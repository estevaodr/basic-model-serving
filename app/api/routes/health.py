from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.logging import request_id_var
from app.schemas.prediction import ErrorDetail

router = APIRouter()


def _request_id() -> str | None:
    rid = request_id_var.get("")
    return rid or None


@router.get("/health/live")
def health_live():
    return {"status": "alive"}


@router.get("/health/ready")
def health_ready(request: Request):
    if not getattr(request.app.state, "ready", False):
        return JSONResponse(
            status_code=503,
            content=ErrorDetail(
                error="not_ready",
                message="Model is not loaded yet",
                request_id=_request_id(),
            ).model_dump(),
        )
    return {"status": "ready"}
