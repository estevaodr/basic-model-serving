import json

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.api.dependencies import get_classifier
from app.core.config import settings
from app.schemas.prediction import ErrorDetail, PredictResponse, PredictUrlRequest
from app.services.inference import InferenceError, predict_from_bytes
from app.services.url_fetch import UrlFetchError, fetch_url_bytes

router = APIRouter(tags=["Predict"])


def _client_error(
    error: str,
    message: str,
    status_code: int = 400,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ErrorDetail(error=error, message=message).model_dump(),
    )


def _run_inference(data: bytes, classifier) -> PredictResponse:
    try:
        return predict_from_bytes(data, classifier)
    except InferenceError as exc:
        raise _client_error(exc.code, exc.message) from exc


def _predict_from_url(image_url: str, classifier) -> PredictResponse:
    try:
        data = fetch_url_bytes(
            image_url,
            timeout=settings.url_timeout,
            max_bytes=settings.max_upload_bytes,
        )
    except UrlFetchError as exc:
        raise _client_error(exc.code, exc.message, exc.status_code) from exc
    return _run_inference(data, classifier)


@router.post("/predict", response_model=PredictResponse)
def predict(request: Request, classifier=Depends(get_classifier)):
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        body = anyio.from_thread.run(request.body)
        try:
            raw = json.loads(body)
        except json.JSONDecodeError as exc:
            raise _client_error("validation_error", "Request body must be valid JSON") from exc
        try:
            payload = PredictUrlRequest.model_validate(raw)
        except ValidationError as exc:
            first = exc.errors()[0]
            raise HTTPException(
                status_code=422,
                detail=ErrorDetail(
                    error="validation_error",
                    message=first["msg"],
                ).model_dump(),
            ) from exc
        return _predict_from_url(payload.image_url, classifier)

    if "multipart/form-data" in content_type:
        form = anyio.from_thread.run(request.form)
        file = form.get("file")
        image_url = form.get("image_url")

        if file is not None and image_url:
            raise HTTPException(
                status_code=422,
                detail=ErrorDetail(
                    error="invalid_request",
                    message="Provide either file or image_url, not both",
                ).model_dump(),
            )
        if file is not None:
            data = anyio.from_thread.run(file.read)
            return _run_inference(data, classifier)
        if image_url:
            return _predict_from_url(str(image_url), classifier)

        raise HTTPException(
            status_code=422,
            detail=ErrorDetail(
                error="invalid_request",
                message="Either file or image_url is required",
            ).model_dump(),
        )

    raise HTTPException(
        status_code=422,
        detail=ErrorDetail(
            error="unsupported_media_type",
            message="Content-Type must be application/json or multipart/form-data",
        ).model_dump(),
    )
