from pydantic import BaseModel

class PredictionResponse(BaseModel):
    is_abnormal: bool
    confidence: float
