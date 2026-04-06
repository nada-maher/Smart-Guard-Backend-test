from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config.settings import settings

router = APIRouter(prefix="/config", tags=["Config"])

class ThresholdPayload(BaseModel):
    threshold: float

@router.get("/threshold")
def get_threshold():
    return {"threshold": settings.ABNORMAL_THRESHOLD}

@router.post("/threshold")
def set_threshold(payload: ThresholdPayload):
    t = payload.threshold
    if not (0.0 <= t <= 1.0):
        raise HTTPException(status_code=400, detail="Threshold must be between 0.0 and 1.0")
    settings.ABNORMAL_THRESHOLD = float(t)
    return {"threshold": settings.ABNORMAL_THRESHOLD}
