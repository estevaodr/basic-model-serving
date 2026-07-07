from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import get_classifier
from app.schemas.prediction import PredictResponse
from app.services.inference import predict_from_bytes

router = APIRouter(tags=["Predict"])


@router.post("/predict", response_model=PredictResponse)
def predict(file: UploadFile = File(...), classifier=Depends(get_classifier)):
    data = file.file.read()
    return predict_from_bytes(data, classifier)
