# routers/manual_analysis.py
from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import tempfile
import os
import asyncio
import json
from datetime import datetime
from services.detector import AbnormalBehaviorDetector
from services.notifier import Notifier
from config.settings import settings
from services.email_service import send_abnormal_alert_email
import shared_state

router = APIRouter(prefix="/api/manual", tags=["manual_analysis"])

# Initialize detector and notifier
detector = AbnormalBehaviorDetector()
notifier = Notifier(webhook_url=settings.WEBHOOK_URL)

# WebSocket connection manager for manual analysis
class ManualAnalysisManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_result(self, websocket: WebSocket, result: dict):
        try:
            await websocket.send_text(json.dumps(result))
        except:
            pass

manual_manager = ManualAnalysisManager()

@router.post("/analyze-video")
async def analyze_video_manually(
    file: UploadFile = File(...),
    video_id: str = "manual_upload",
    organization: str = "Smart Guard"
):
    """
    Manual video analysis endpoint
    Frontend sends video file, backend analyzes and returns results
    """
    try:
        # Validate file type
        if not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Read video bytes
        video_bytes = await file.read()
        
        if len(video_bytes) == 0:
            raise HTTPException(status_code=400, detail="Video file is empty")
        
        print(f"Received video for manual analysis: {video_id}, size: {len(video_bytes)} bytes")
        
        # Run inference
        result = detector.predict(video_bytes)
        
        # Prepare response
        response = {
            "timestamp": datetime.now().isoformat(),
            "video_id": video_id,
            "organization": organization,
            "confidence": float(result["confidence"]),
            "is_abnormal": bool(result["is_abnormal"]),
            "threshold": float(settings.ABNORMAL_THRESHOLD),
            "model_path": detector.model.model_path,
            "analysis_type": "manual"
        }
        
        # Log result
        from workers.stream_processor import log_inference_result
        log_inference_result(video_id, result["is_abnormal"], result["confidence"], organization)
        
        # Send alert if abnormal behavior detected
        if result["is_abnormal"]:
            alert_data = {
                "timestamp": datetime.now().isoformat(),
                "video_id": video_id,
                "confidence": float(result["confidence"]),
                "is_abnormal": True,
                "event": "Manual Analysis - Abnormal Behaviour",
                "priority": "high" if result["confidence"] >= 0.5 else "medium",
                "organization": organization
            }
            
            # Broadcast via WebSocket
            from main import manager
            if shared_state.loop and shared_state.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(json.dumps(alert_data)), 
                    shared_state.loop
                )
            
            # Send email if confidence is high
            if result["confidence"] >= 0.70 and shared_state.loop and shared_state.loop.is_running():
                try:
                    asyncio.run_coroutine_threadsafe(
                        send_abnormal_alert_email(
                            float(result["confidence"]), 
                            video_id, 
                            event_name="Manual Analysis - Abnormal Behaviour",
                            organization=organization
                        ),
                        shared_state.loop
                    )
                except Exception as e:
                    print(f"Failed to send email alert: {e}")
        
        print(f"Manual analysis completed: {result['confidence']:.3f}, {'ABNORMAL' if result['is_abnormal'] else 'NORMAL'}")
        
        return JSONResponse(content=response)
        
    except Exception as e:
        print(f"Error in manual video analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.websocket("/ws/manual-analysis")
async def manual_analysis_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time manual analysis
    Frontend can send video frames and receive analysis results
    """
    await manual_manager.connect(websocket)
    try:
        while True:
            # Receive message from frontend
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "video_frame":
                    # Handle base64 encoded video frame
                    frame_data = message.get("frame_data")
                    video_id = message.get("video_id", "manual_frame")
                    organization = message.get("organization", "Smart Guard")
                    
                    if frame_data:
                        # Decode base64 and analyze
                        import base64
                        import io
                        
                        # Remove data URL prefix if present
                        if "," in frame_data:
                            frame_data = frame_data.split(",")[1]
                        
                        frame_bytes = base64.b64decode(frame_data)
                        
                        # Analyze frame (convert to video-like format)
                        result = detector.predict(frame_bytes)
                        
                        response = {
                            "type": "analysis_result",
                            "timestamp": datetime.now().isoformat(),
                            "video_id": video_id,
                            "organization": organization,
                            "confidence": float(result["confidence"]),
                            "is_abnormal": bool(result["is_abnormal"]),
                            "threshold": float(settings.ABNORMAL_THRESHOLD)
                        }
                        
                        await manual_manager.send_result(websocket, response)
                        
            except json.JSONDecodeError:
                await manual_manager.send_result(websocket, {
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                await manual_manager.send_result(websocket, {
                    "type": "error", 
                    "message": f"Analysis error: {str(e)}"
                })
                
    except WebSocketDisconnect:
        manual_manager.disconnect(websocket)

@router.get("/status")
async def get_analysis_status():
    """
    Get current analysis system status
    """
    return {
        "status": "ready",
        "model_loaded": detector.model is not None,
        "model_path": detector.model.model_path if detector.model else None,
        "threshold": float(settings.ABNORMAL_THRESHOLD),
        "active_connections": len(manual_manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }
