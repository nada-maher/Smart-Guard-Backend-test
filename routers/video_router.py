from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import tempfile
from models.abnormal_model import AbnormalModel
from schemas.prediction import PredictionResponse


router = APIRouter(prefix="/video", tags=["Video"])

# Load model once
model = AbnormalModel()


@router.get("/test")
def video_test():
    return {"status": "video router working"}


# ----------- Helper: Extract 35 frames -----------
def extract_frames(video_path, target_frames=35, img_size=128):
    cap = cv2.VideoCapture(video_path)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < target_frames:
        raise HTTPException(status_code=400, detail="Video too short")

    # Pick frames equally spaced
    frame_indices = np.linspace(0, total_frames - 1, target_frames).astype(int)
    frames = []

    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.resize(frame, (img_size, img_size))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame)

    cap.release()

    # Convert to numpy
    frames = np.array(frames, dtype=np.float32)
    frames = (frames / 127.5) - 1.0  # normalize
    frames = np.expand_dims(frames, axis=0)  # shape = (1, 35, 128, 128, 3)

    return frames


# ----------- Main Predict Endpoint -----------
@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Predict Video",
)
async def predict_video(video: UploadFile = File(...)):
    if not video:
        raise HTTPException(status_code=400, detail="No video file uploaded")

    # Save uploaded video temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
            content = await video.read()
            temp_video.write(content)
            temp_path = temp_video.name
    except:
        raise HTTPException(status_code=500, detail="Failed to save uploaded video")

    # Extract frames
    try:
        frames_tensor = extract_frames(temp_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Predict using model
    try:
        is_abnormal, confidence = model.predict(frames_tensor)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Model prediction failed: " + str(e))

    return PredictionResponse(
        is_abnormal=is_abnormal,
        confidence=confidence
    )
