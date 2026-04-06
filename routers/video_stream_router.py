import asyncio
import time
import numpy as np
import cv2
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from services.frame_store import get_jpeg

router = APIRouter(prefix="/stream", tags=["Stream"])

async def mjpeg_generator():
    boundary = b"--frame"
    placeholder = None
    while True:
        jpeg = get_jpeg()
        if jpeg is not None:
            yield boundary + b"\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
        else:
            if placeholder is None:
                # Create a proper test feed with camera icon and status
                img = np.zeros((480, 640, 3), dtype=np.uint8)
                # Dark blue background
                img[:] = (40, 30, 20)
                
                # Add camera icon
                cv2.circle(img, (240, 240), 30, (0, 255, 0), -1)
                cv2.circle(img, (240, 240), 8, (255, 255, 0), -1)
                
                # Add status text
                cv2.putText(img, "Smart Guard", (150, 200), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(img, "Camera Active", (150, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                
                # Add timestamp
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(img, timestamp, (20, 460), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 255, 100), 2)
                
                ok, buf = cv2.imencode(".jpg", img)
                if ok:
                    placeholder = buf.tobytes()
            if placeholder is not None:
                yield boundary + b"\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(placeholder)).encode() + b"\r\n\r\n" + placeholder + b"\r\n"
        await asyncio.sleep(0.033)

@router.get("/mjpeg")
async def mjpeg():
    return StreamingResponse(
        mjpeg_generator(), 
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*"
        }
    )
