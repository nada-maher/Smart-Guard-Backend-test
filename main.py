# backend/main.py
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import os
import json
import csv
import cv2
import asyncio
import pandas as pd
from typing import List

# Include routers
app = FastAPI(
    title="Abnormal Behavior Detection API",
    version="1.0.0"
)

# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# WebSocket endpoint
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"🔍 WebSocket received: '{data}'")
            
            # Handle organization setting from frontend
            try:
                message = json.loads(data)
                print(f"🔍 Parsed message: {message}")
                if message.get('type') == 'set_organization':
                    organization = message.get('organization', 'SmartGuard')
                    import shared_state
                    shared_state.current_organization = organization
                    print(f"🏢 Organization set via WebSocket: {organization}")
                    print(f"🔍 Global current_organization now: '{shared_state.current_organization}'")
                    
                    # Send confirmation back to frontend
                    await websocket.send_text(json.dumps({
                        'type': 'organization_set',
                        'organization': organization,
                        'success': True
                    }))
                    continue
            except json.JSONDecodeError as e:
                print(f"🔍 JSON decode error: {e}")
                pass  # Ignore invalid JSON messages
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

from utils.log_converter import csv_to_xlsx

from shared_state import latest_pred  # shared_state
from routers.auth import router as auth_router
from routers.video_stream_router import router as stream_router
from routers.video_router import router as video_router

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:5175", "http://127.0.0.1:5175"],  # React frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(stream_router)
app.include_router(video_router)

@app.on_event("startup")
async def startup_event():
    import shared_state
    shared_state.loop = asyncio.get_event_loop()
    print("✅ Global event loop initialized in shared_state")
    
    # Start stream processor automatically
    import threading
    import workers.stream_processor as stream_processor
    
    def run_stream():
        try:
            print("🚀 Starting stream processor automatically...")
            stream_processor.process_video_stream(
                video_source=0,  # Default camera
                video_id="cam1",  # Default camera ID
                organization="SmartGuard"  # Default organization
            )
        except Exception as e:
            print(f"❌ Stream processor error: {e}")
    
    # Start stream in background thread
    stream_thread = threading.Thread(target=run_stream, daemon=True)
    stream_thread.start()
    print("✅ Stream processor thread started")

# Shared variable for latest prediction
latest_pred = None

# -----------------------------
# Root endpoint
# -----------------------------
@app.get("/")
def root():
    return {"message": "Backend is running"}

# -----------------------------
# Dashboard endpoint
# -----------------------------
@app.get("/dashboard")
def dashboard():
    import csv
    import sqlite3
    from datetime import datetime, timedelta
    
    try:
        # Read inference logs
        with open("inference_logs.csv", "r") as f:
            reader = csv.DictReader(f)
            all_rows = list(reader)
        
        # Filter for abnormal behavior
        abnormal_events = [row for row in all_rows if row.get("is_abnormal") == "True"]
        
        # Calculate statistics
        total_abnormal = len(abnormal_events)
        
        # Calculate recent abnormal events (last hour)
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        recent_abnormal = len([row for row in abnormal_events if row.get("timestamp", "") > one_hour_ago])
        
        # Get latest abnormal events (last 5)
        latest_abnormal = abnormal_events[-5:] if abnormal_events else []

        # Get real user count from local DB
        user_count = 0
        try:
            conn = sqlite3.connect("smartguard.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            user_count = c.fetchone()[0]
            conn.close()
        except:
            user_count = 15 # Fallback
        
        return {
            "users_online": user_count,
            "total_abnormal_events": total_abnormal,
            "recent_abnormal_events": recent_abnormal,
            "alerts": recent_abnormal,
            "uptime": "12h 45m",
            "system_status": "OK" if recent_abnormal < 5 else "WARNING",
            "latest_abnormal_events": latest_abnormal
        }
    except FileNotFoundError:
        # Return default values if file doesn't exist
        return {
            "users_online": 15,
            "total_abnormal_events": 0,
            "recent_abnormal_events": 0,
            "alerts": 0,
            "uptime": "12h 45m",
            "system_status": "OK",
            "latest_abnormal_events": []
        }
    except Exception as e:
        return {
            "users_online": 15,
            "total_abnormal_events": 0,
            "recent_abnormal_events": 0,
            "alerts": 0,
            "uptime": "12h 45m",
            "system_status": "OK",
            "latest_abnormal_events": [],
            "error": str(e)
        }

# -----------------------------
# Logs download endpoint (abnormal behavior only)
# Support both CSV and XLSX formats
@app.get("/logs")
def logs(format: str = "csv"):
    """Serve inference logs in CSV or XLSX format"""
    try:
        csv_file = "inference_logs.csv"
        xlsx_file = "inference_logs.xlsx"
        
        # Ensure CSV exists
        if not os.path.exists(csv_file):
            with open(csv_file, mode="w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "video_id", "confidence", "threshold", "is_abnormal", 
                                "model_path", "seq_len", "img_size", "saved_video_path", "event", "organization"])
        
        # Handle XLSX format request
        if format.lower() == "xlsx":
            # Convert to XLSX if needed
            if not os.path.exists(xlsx_file) or os.path.getmtime(csv_file) > os.path.getmtime(xlsx_file):
                csv_to_xlsx()
            
            if os.path.exists(xlsx_file):
                return FileResponse(
                    path=xlsx_file, 
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    filename="inference_logs.xlsx",
                    headers={"Content-Disposition": "attachment; filename=inference_logs.xlsx"}
                )
        
        # Default to CSV
        if os.path.exists(csv_file):
            return FileResponse(
                path=csv_file,
                media_type="text/csv",
                filename="inference_logs.csv",
                headers={"Content-Disposition": "attachment; filename=inference_logs.csv"}
            )
        
        return {"error": "Log file not found"}
    
    except Exception as e:
        print(f"Error serving logs: {e}")
        return {"error": f"Unable to serve logs file: {str(e)}"}

# -----------------------------
# Organization-specific logs endpoint
# -----------------------------
def delete_temp_file(file_path: str):
    """Background task to delete temporary files"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✅ Successfully deleted temporary file: {file_path}")
    except Exception as e:
        print(f"❌ Error deleting temporary file {file_path}: {e}")

@app.get("/logs/{org_name}")
async def get_org_logs(org_name: str, background_tasks: BackgroundTasks):
    """
    Generate and serve an organization-specific report in Excel format.
    First checks for an organization-specific CSV file, falls back to main log.
    """
    try:
        # 1. Try to find organization-specific CSV file
        safe_org_name = "".join([c if c.isalnum() else "_" for c in org_name])
        org_csv = os.path.join("logs", f"logs_{safe_org_name}.csv")
        main_csv = "inference_logs.csv"
        
        target_csv = org_csv if os.path.exists(org_csv) else main_csv
        
        if not os.path.exists(target_csv):
            return {"error": f"No logs found for {org_name}"}

        # 2. Load and filter logs
        df = pd.read_csv(target_csv)
        
        # Ensure correct column names
        expected_cols = ["timestamp", "video_id", "confidence", "threshold", "is_abnormal", 
                         "model_path", "seq_len", "img_size", "saved_video_path", "event", "organization"]
        
        if len(df.columns) == len(expected_cols):
            df.columns = expected_cols
        
        # Filter if using the main CSV file (org-specific file is already filtered by definition)
        if target_csv == main_csv:
            if "organization" in df.columns:
                df = df[df["organization"].str.lower() == org_name.lower()].copy()
            else:
                return {"error": "Main log file structure is outdated."}

        if df.empty:
            return {"error": f"No logs found for organization: {org_name}"}

        # 3. Format for professionalism
        rename_map = {
            "organization": "Organization",
            "timestamp": "Event Time",
            "video_id": "Camera ID",
            "confidence": "Confidence Score",
            "threshold": "Detection Threshold",
            "is_abnormal": "Status (Abnormal)",
            "event": "Event Type",
            "saved_video_path": "Video Evidence Path"
        }
        df.rename(columns=rename_map, inplace=True)

        # Reorder columns: Organization first
        cols = list(df.columns)
        if "Organization" in cols:
            cols.insert(0, cols.pop(cols.index("Organization")))
        df = df[cols]

        # 4. Generate temporary Excel file for download
        temp_filename = f"report_{safe_org_name}_{int(asyncio.get_event_loop().time())}.xlsx"
        df.to_excel(temp_filename, index=False)

        # Schedule deletion after download
        background_tasks.add_task(delete_temp_file, temp_filename)

        return FileResponse(
            path=temp_filename,
            filename=f"SmartGuard_Report_{safe_org_name}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        print(f"❌ Error generating organization report: {e}")
        return {"error": f"Failed to generate report: {str(e)}"}

# -----------------------------
# Live video generator
# -----------------------------

async def gen_frames():
    """
    Generator that yields MJPEG frames from the stream processor
    """
    import asyncio
    import cv2
    import numpy as np
    from services.frame_store import get_jpeg
    
    while True:
        try:
            # Get frame from stream processor
            jpeg_bytes = get_jpeg()
            if jpeg_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')
            else:
                # Use a proper fallback image if no jpeg_bytes from frame_store
                img = np.zeros((480, 640, 3), dtype=np.uint8)
                img[:] = (30, 30, 30)
                # Add timestamp to fallback to see it's alive
                import datetime
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                cv2.putText(img, "INITIALIZING STREAM...", (180, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(img, ts, (260, 280), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 1)
                
                ret, buffer = cv2.imencode('.jpg', img)
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception as e:
            print(f"Frame generation error: {e}")
        
        await asyncio.sleep(0.04)  # ~25 FPS is plenty for stream preview

# -----------------------------
# Live MJPEG endpoint
# -----------------------------
@app.get("/live")
async def live():
    return StreamingResponse(
        gen_frames(),
        media_type='multipart/x-mixed-replace; boundary=frame',
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*"
        }
    )

# -----------------------------
# Endpoint to get latest prediction
# -----------------------------
@app.get("/latest_pred")
def get_latest_pred():
    from shared_state import latest_pred
    return {"prediction": str(latest_pred) if latest_pred else "No prediction yet"}

@app.post("/set-organization")
async def set_organization(request: Request):
    """Set the current organization for email notifications"""
    try:
        data = await request.json()
        organization = data.get('organization', 'SmartGuard')
        import shared_state
        shared_state.current_organization = organization
        print(f"🏢 Organization set to: {organization}")
        return {"success": True, "organization": organization}
    except Exception as e:
        print(f"❌ Error setting organization: {e}")
        return {"success": False, "error": str(e)}

@app.get("/get-organization")
async def get_current_organization():
    """Get the current organization"""
    import shared_state
    return {"organization": shared_state.current_organization}

@app.get("/test-organization")
async def test_organization():
    """Test endpoint to check current organization and debug info"""
    import shared_state
    return {
        "current_organization": shared_state.current_organization,
        "type": str(type(shared_state.current_organization)),
        "length": len(shared_state.current_organization) if isinstance(shared_state.current_organization, str) else None,
        "is_empty": not bool(shared_state.current_organization),
        "debug": "Organization test endpoint"
    }

@app.post("/test-set-organization")
async def test_set_organization(request: Request):
    """Test endpoint to manually set organization"""
    try:
        data = await request.json()
        organization = data.get('organization', 'SmartGuard')
        import shared_state
        shared_state.current_organization = organization
        print(f"🧪 TEST - Organization set to: {organization}")
        return {"success": True, "organization": organization, "message": "Test organization set"}
    except Exception as e:
        print(f"❌ Test set organization error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/start-stream-with-organization")
async def start_stream_with_organization(request: Request):
    """Start video stream with specific organization"""
    try:
        data = await request.json()
        organization = data.get('organization', 'SmartGuard')
        
        import shared_state
        shared_state.current_organization = organization
        print(f"🏢 Stream started with organization: {organization}")
        
        # Start stream processor with the specified organization
        import threading
        import workers.stream_processor as stream_processor
        
        def run_stream():
            stream_processor.process_video_stream(
                video_source=0,  # Default camera
                video_id="cam1",  # Default camera ID
                organization=organization
            )
        
        # Start stream in background thread
        stream_thread = threading.Thread(target=run_stream, daemon=True)
        stream_thread.start()
        
        return {"success": True, "organization": organization, "message": f"Stream started for {organization}"}
        
    except Exception as e:
        print(f"❌ Error starting stream with organization: {e}")
        return {"success": False, "error": str(e)}

# -----------------------------
# Camera Control Endpoints
# -----------------------------
@app.get("/camera/status")
def get_camera_status():
    """Get camera status for current organization"""
    import shared_state
    
    org_state = shared_state.get_org_state(shared_state.current_organization)
    is_stop_requested = shared_state.is_camera_stop_requested(shared_state.current_organization)
    
    return {
        "enabled": org_state.camera_enabled, 
        "organization": shared_state.current_organization,
        "stop_requested": is_stop_requested,
        "message": f"Camera {'enabled' if org_state.camera_enabled else 'disabled'} for {shared_state.current_organization}"
    }

@app.post("/camera/toggle")
def toggle_camera():
    """Toggle camera for current organization (respects stop request)"""
    import shared_state
    print(f"🔍 DEBUG: toggle_camera called, current_organization = '{shared_state.current_organization}'")
    
    try:
        # Check if camera stop is requested (prevent auto-reopen)
        if shared_state.is_camera_stop_requested(shared_state.current_organization):
            print(f"🚫 Camera toggle blocked for {shared_state.current_organization} - stop requested")
            return {"success": False, "error": "Camera stop requested, cannot toggle", "enabled": False}
            
        org_state = shared_state.get_org_state(shared_state.current_organization)
        new_status = not org_state.camera_enabled
        shared_state.set_org_camera_status(shared_state.current_organization, new_status)
        
        print(f"✅ Camera toggled for {shared_state.current_organization}: {new_status}")
        return {"success": True, "enabled": new_status, "organization": shared_state.current_organization}
    except Exception as e:
        print(f"❌ Camera toggle error: {e}")
        return {"success": False, "error": str(e)}

@app.get("/debug/test")
def debug_test():
    """Simple test endpoint"""
    return {"message": "test working", "timestamp": "now"}

# -----------------------------
# Test Email Endpoint
# -----------------------------
@app.post("/camera/stop")
def stop_camera():
    """Stop camera immediately when sign out button is pressed"""
    import shared_state
    global current_organization
    try:
        org_state = shared_state.get_org_state(current_organization)
        
        # Check if camera is already OFF (prevent unnecessary operations)
        if not org_state.camera_enabled:
            print(f"ℹ️ Camera already OFF for {current_organization} - no action needed")
            return {"success": True, "message": f"Camera already OFF for {current_organization}", "organization": current_organization, "already_off": True}
        
        # Request camera stop and prevent auto-reopen
        shared_state.request_camera_stop(current_organization)
        
        print(f"🛑 Camera stop requested for {current_organization} - auto-reopen prevented")
        return {"success": True, "message": f"Camera stop requested for {current_organization}", "organization": current_organization, "stop_requested": True}
    except Exception as e:
        print(f"❌ Error requesting camera stop for {current_organization}: {e}")
        return {"success": False, "error": str(e)}

# ... (rest of the code remains the same)
    return Response(content="", media_type="image/x-icon", status_code=204)

@app.get("/@vite/client")
def vite_client_root():
    return Response(content="", media_type="application/javascript", status_code=200)
