import json

import anyio
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from app.api.dependencies import get_classifier
from app.core.config import settings
from app.core.logging import request_id_var
from app.schemas.prediction import ErrorDetail, PredictResponse, PredictUrlRequest
from app.services.inference import InferenceError, predict_from_bytes
from app.services.url_fetch import UrlFetchError, fetch_url_bytes

router = APIRouter(tags=["Predict"])

MAX_JSON_BODY_BYTES = 16384


def _request_id() -> str | None:
    rid = request_id_var.get("")
    return rid or None


def _client_error(
    error: str,
    message: str,
    status_code: int = 400,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ErrorDetail(
            error=error,
            message=message,
            request_id=_request_id(),
        ).model_dump(),
    )


def _read_upload_limited(read_fn, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    while True:
        chunk = read_fn(65536)
        if not chunk:
            break
        size += len(chunk)
        if size > max_bytes:
            raise _client_error(
                "payload_too_large",
                f"Upload exceeds maximum allowed size of {max_bytes} bytes",
            )
        chunks.append(chunk)
    return b"".join(chunks)


async def _read_json_body_limited(request: Request, max_bytes: int) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > max_bytes:
                raise _client_error(
                    "payload_too_large",
                    f"JSON body exceeds maximum allowed size of {max_bytes} bytes",
                )
        except ValueError:
            pass

    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > max_bytes:
            raise _client_error(
                "payload_too_large",
                f"JSON body exceeds maximum allowed size of {max_bytes} bytes",
            )
        chunks.append(chunk)
    return b"".join(chunks)


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


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Classify an image (upload or URL)",
    description=(
        "Submit an image for ResNet-50 top-5 ImageNet classification. "
        "Use `multipart/form-data` with a `file` field for direct upload, "
        "or `application/json` with `{\"image_url\": \"https://...\"}` "
        "to fetch an image from a public URL."
    ),
    responses={
        400: {
            "description": "Invalid image or client error",
            "model": ErrorDetail,
            "content": {
                "application/json": {
                    "example": {
                        "error": "invalid_image",
                        "message": "Could not decode image",
                        "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    }
                }
            },
        },
        422: {
            "description": "Validation or unsupported content type",
            "model": ErrorDetail,
        },
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": PredictUrlRequest.model_json_schema(),
                    "examples": {
                        "image_url": {
                            "summary": "Classify from URL",
                            "value": {
                                "image_url": "https://example.com/golden-retriever.jpg"
                            },
                        }
                    },
                },
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "file": {
                                "type": "string",
                                "format": "binary",
                                "description": "JPEG/PNG/WebP image file",
                            },
                            "image_url": {
                                "type": "string",
                                "description": "Optional URL when using multipart fallback",
                            },
                        },
                    },
                    "examples": {
                        "file_upload": {
                            "summary": "Upload image file",
                            "value": {"file": "(binary image data)"},
                        }
                    },
                },
            },
        }
    },
)
def predict(request: Request, classifier=Depends(get_classifier)):
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        body = anyio.from_thread.run(_read_json_body_limited, request, MAX_JSON_BODY_BYTES)
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
                    request_id=_request_id(),
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
                    request_id=_request_id(),
                ).model_dump(),
            )
        if file is not None:
            data = _read_upload_limited(
                lambda n: anyio.from_thread.run(file.read, n),
                settings.max_upload_bytes,
            )
            return _run_inference(data, classifier)
        if image_url:
            return _predict_from_url(str(image_url), classifier)

        raise HTTPException(
            status_code=422,
            detail=ErrorDetail(
                error="invalid_request",
                message="Either file or image_url is required",
                request_id=_request_id(),
            ).model_dump(),
        )

    raise HTTPException(
        status_code=422,
        detail=ErrorDetail(
            error="unsupported_media_type",
            message="Content-Type must be application/json or multipart/form-data",
            request_id=_request_id(),
        ).model_dump(),
    )
