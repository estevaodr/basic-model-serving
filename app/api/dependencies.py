from fastapi import HTTPException, Request

from app.core.logging import request_id_var
from app.schemas.prediction import ErrorDetail


def _request_id() -> str | None:
    rid = request_id_var.get("")
    return rid or None


def get_classifier(request: Request):
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(
            status_code=503,
            detail=ErrorDetail(
                error="not_ready",
                message="Model is not loaded yet",
                request_id=_request_id(),
            ).model_dump(),
        )
    return request.app.state.classifier
