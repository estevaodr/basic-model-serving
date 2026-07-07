from pydantic import BaseModel, Field, HttpUrl


class PredictionItem(BaseModel):
    label: str = Field(examples=["golden retriever"])
    confidence: float = Field(ge=0, le=1, examples=[0.82])


class PredictResponse(BaseModel):
    predictions: list[PredictionItem]
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "predictions": [
                        {"label": "golden retriever", "confidence": 0.82},
                        {"label": "Labrador retriever", "confidence": 0.09},
                    ]
                }
            ]
        }
    }


class PredictUrlRequest(BaseModel):
    image_url: HttpUrl


class ErrorDetail(BaseModel):
    error: str
    message: str
    request_id: str | None = None
