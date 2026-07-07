import io

from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.metrics.prometheus import PREDICTION_COUNT
from app.schemas.prediction import PredictionItem, PredictResponse


class InferenceError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def predict_from_bytes(data: bytes, classifier) -> PredictResponse:
    if len(data) > settings.max_upload_bytes:
        raise InferenceError(
            "payload_too_large",
            f"Upload exceeds maximum allowed size of {settings.max_upload_bytes} bytes",
        )

    try:
        image = Image.open(io.BytesIO(data))
        image = image.convert("RGB")
    except UnidentifiedImageError as exc:
        raise InferenceError("invalid_image", "Could not decode image") from exc

    predictions = classifier.predict(image)
    PREDICTION_COUNT.inc()
    return PredictResponse(
        predictions=[
            PredictionItem(label=label, confidence=confidence)
            for label, confidence in predictions
        ]
    )
