import io

from PIL import Image, UnidentifiedImageError

from app.schemas.prediction import PredictionItem, PredictResponse


def predict_from_bytes(data: bytes, classifier) -> PredictResponse:
    try:
        image = Image.open(io.BytesIO(data))
        image = image.convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError("Could not decode image") from exc

    predictions = classifier.predict(image)
    return PredictResponse(
        predictions=[
            PredictionItem(label=label, confidence=confidence)
            for label, confidence in predictions
        ]
    )
