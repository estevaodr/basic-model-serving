from pydantic import BaseModel, Field

GOLDEN_RETRIEVER_PREDICTIONS = [
    {"label": "golden retriever", "confidence": 0.82},
    {"label": "Labrador retriever", "confidence": 0.09},
    {"label": "cocker spaniel", "confidence": 0.03},
    {"label": "Sussex spaniel", "confidence": 0.02},
    {"label": "Irish setter", "confidence": 0.01},
]


class PredictionItem(BaseModel):
    label: str = Field(examples=["golden retriever"])
    confidence: float = Field(ge=0, le=1, examples=[0.82])
    model_config = {
        "json_schema_extra": {
            "examples": [{"label": "golden retriever", "confidence": 0.82}]
        }
    }


class PredictResponse(BaseModel):
    predictions: list[PredictionItem]
    model_config = {
        "json_schema_extra": {
            "examples": [{"predictions": GOLDEN_RETRIEVER_PREDICTIONS}]
        }
    }


class PredictUrlRequest(BaseModel):
    image_url: str = Field(
        examples=["https://example.com/golden-retriever.jpg"],
        description="Public HTTP(S) URL of an image to classify",
    )
    model_config = {
        "json_schema_extra": {
            "examples": [{"image_url": "https://example.com/golden-retriever.jpg"}]
        }
    }


class ErrorDetail(BaseModel):
    error: str = Field(examples=["invalid_image"])
    message: str = Field(examples=["Could not decode image"])
    request_id: str | None = Field(
        default=None,
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "invalid_image",
                    "message": "Could not decode image",
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            ]
        }
    }
