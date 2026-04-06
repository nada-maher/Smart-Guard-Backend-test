# services/stream_processor.py
import cv2
import numpy as np
import tempfile
import datetime
import time
import shared_state
import os
from utils.preprocessing import preprocess_video
from shared_state import latest_pred
from services.frame_store import set_jpeg
from models.abnormal_model import AbnormalModel

def get_default_organization():
    """Get the default organization from the first admin user"""
    try:
        import sqlite3
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT organization FROM users WHERE role = 'admin' LIMIT 1")
        result = c.fetchone()
        conn.close()
        return result[0] if result else "SmartGuard"
    except Exception as e:
        print(f"Error getting organization: {e}")
        return "SmartGuard"

# Cooldown mechanism to reduce duplicate alerts
# Stores {video_id: last_alert_timestamp}
# Shared across all camera processing instances
last_alert_times = {}
ALERT_COOLDOWN_SECONDS = 90 # Wait 90 seconds between alerts for the same camera

def process_video_stream(video_source=0, video_id=None, organization=None):
    """
    Main loop for MJPEG video stream with abnormal behavior detection.
    This runs in a background thread.
    """
    global last_alert_times
    global latest_pred
    
    # Use cam1 as default video_id if not provided
    if video_id is None:
        video_id = "cam1"
    
    # Initialize organization
    current_organization = organization or get_default_organization()
    print(f"🔄 Starting stream processing for: {video_id}")
    print(f"Processing for organization: {current_organization}")

    # Initialize the REAL model once
    try:
        model = AbnormalModel()
        print("✅ [STREAM-PROCESSOR] Real Model Initialized")
    except Exception as e:
        print(f"❌ [STREAM-PROCESSOR] CRITICAL MODEL LOAD FAILED: {e}")
        # We don't exit here to keep the live stream running, but inference will fail
        model = None

    cap = None
    
    # Initialize fallback image for when camera is disabled
    disabled_img = np.zeros((480, 640, 3), dtype=np.uint8)
    disabled_img[:] = (20, 20, 30) # Dark navy background
    cv2.putText(disabled_img, "CAMERA DISABLED", (150, 240), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(disabled_img, "Click button to enable", (200, 300), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

    # State variables for the loop
    frame_count = 0
    frames = []
    use_fallback = False

    while True:
        # 1. Get the latest organization from shared_state
        active_org = shared_state.current_organization
            
        # 1. Check if camera should be enabled for this organization
        org_state = shared_state.get_org_state(active_org)
        if not org_state.camera_enabled:
            if cap:
                print(f"Camera disabled by user for {active_org}. Closing hardware connection.")
                cap.release()
                cap = None
            
            # Send "Disabled" frame to the stream
            try:
                ok, buf = cv2.imencode(".jpg", disabled_img)
                if ok:
                    set_jpeg(buf.tobytes())
            except:
                pass
            time.sleep(0.5)
            continue

        # 2. Ensure camera is open if enabled
        if cap is None:
            print(f"Attempting to open camera index 0...")
            # Try common indices
            for idx in [0, 1, 2]:
                # Try backends
                for backend in [cv2.CAP_DSHOW, cv2.CAP_MSMF, None]:
                    try:
                        print(f"Checking index {idx} with backend {backend}...")
                        if backend is not None:
                            test_cap = cv2.VideoCapture(idx, backend)
                        else:
                            test_cap = cv2.VideoCapture(idx)
                        
                        if test_cap.isOpened():
                            # Read one frame to confirm it works
                            ret, frame = test_cap.read()
                            if ret and frame is not None:
                                print(f"✅ Successfully opened camera {idx} with backend {backend}")
                                cap = test_cap
                                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                                use_fallback = False
                                break
                            test_cap.release()
                    except Exception as e:
                        print(f"Error opening camera {idx}: {e}")
                if cap:
                    break
                time.sleep(0.5) # Wait between indices
            
            if not cap:
                print("❌ Failed to open any camera. Using fallback simulation.")
                use_fallback = True
                # Initialize fallback image
                fallback_img = np.zeros((480, 640, 3), dtype=np.uint8)
                fallback_img[:] = (30, 30, 30) # Dark gray background
                
                # Draw a nice frame
                cv2.rectangle(fallback_img, (20, 20), (620, 460), (100, 100, 100), 2)
                
                # Add title
                cv2.putText(fallback_img, "SmartGuard - Simulation Mode", (120, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                # Add instructions
                cv2.putText(fallback_img, "Hardware camera not detected.", (160, 200), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                cv2.putText(fallback_img, "Running in simulation mode for testing.", (130, 240), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                
                # Add status box
                cv2.rectangle(fallback_img, (200, 300), (440, 380), (50, 50, 50), -1)
                cv2.rectangle(fallback_img, (200, 300), (440, 380), (0, 255, 0), 1)
                cv2.putText(fallback_img, "STATUS: ACTIVE", (240, 350), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            else:
                print("✅ Camera connection established. Disabling simulation.")
                use_fallback = False

        # 3. Capture frame
        if use_fallback:
            ret = True
            # Create a synthetic frame
            frame = fallback_img.copy()
            ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            cv2.putText(frame, f"SIM: {ts}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Add some "movement" to avoid static frame detection
            dot_x = int(320 + 200 * np.sin(frame_count * 0.1))
            cv2.circle(frame, (dot_x, 400), 10, (0, 0, 255), -1)
            time.sleep(0.033)
        else:
            try:
                ret, frame = cap.read()
                if not ret or frame is None:
                    print("Lost camera connection. Re-trying...")
                    cap.release()
                    cap = None
                    time.sleep(1)
                    continue
            except Exception as e:
                print(f"Error reading camera: {e}")
                cap.release()
                cap = None
                continue
        
        # Diagnostic for black frames
        if not use_fallback and np.mean(frame) < 1:
            cv2.putText(frame, "WARNING: BLACK FRAME", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        frame_count += 1
        
        # 4. Store frame for live stream
        try:
            ok, buf = cv2.imencode(".jpg", frame)
            if ok:
                set_jpeg(buf.tobytes())
        except Exception as e:
            print(f"Error encoding frame: {e}")

        frames.append(frame)

        # 5. Run inference every 35 frames
        if len(frames) >= 35:
            print(f"Processing 35 frames for REAL inference...")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp_name = tmp.name
                try:
                    out = cv2.VideoWriter(tmp_name, cv2.VideoWriter_fourcc(*'mp4v'), 10,
                                          (frames[0].shape[1], frames[0].shape[0]))
                    for f in frames:
                        out.write(f)
                    out.release()
                    
                    with open(tmp_name, "rb") as f:
                        video_bytes = f.read()

                    frames_tensor = preprocess_video(video_bytes)
                    
                    if model is not None:
                        is_abnormal, confidence = model.predict(frames_tensor)
                        print(f"✅ [REAL-PRED] Prediction: {confidence:.4f}, {'ABNORMAL' if is_abnormal else 'NORMAL'}")
                    else:
                        print("❌ [STREAM-PROCESSOR] Model not available, skipping inference")
                        is_abnormal, confidence = False, 0.0
                    
                    latest_pred = f"{confidence:.3f} ({'ABNORMAL' if is_abnormal else 'NORMAL'})"
                    log_inference_result(video_id, is_abnormal, confidence, active_org)
                    
                    # Broadcast alert if abnormal
                    if is_abnormal:
                        # Check cooldown for this specific camera
                        current_time = time.time()
                        last_alert_time = last_alert_times.get(video_id, 0)
                        
                        if current_time - last_alert_time < ALERT_COOLDOWN_SECONDS:
                            remaining = int(ALERT_COOLDOWN_SECONDS - (current_time - last_alert_time))
                            # Log only once every 30 seconds to avoid console spam
                            if frame_count % 900 == 0:
                                print(f"⏳ [COOLDOWN] Alert for {video_id} suppressed. Cooldown active for {remaining}s.")
                        else:
                            # IMPORTANT: Update last alert time IMMEDIATELY before starting async tasks
                            # to prevent duplicate triggers from subsequent frames while this one is processing
                            last_alert_times[video_id] = current_time
                            
                            # Determine event name and priority
                            event_name = "Abnormal Behaviour"
                            priority = "high" if confidence >= 0.5 else "medium"
                            
                            print(f"🚨 [REAL-ALERT] {event_name}! Confidence: {confidence:.3f}. Priority: {priority}. Attempting broadcast...")
                            try:
                                from main import manager
                                import asyncio
                                import json
                                
                                alert_data = {
                                    "timestamp": datetime.datetime.now().isoformat(),
                                    "video_id": video_id,
                                    "confidence": float(confidence),
                                    "is_abnormal": True,
                                    "event": event_name,
                                    "priority": priority
                                }
                                
                                # Using thread-safe way to run async broadcast from sync thread
                                if shared_state.loop and shared_state.loop.is_running():
                                    print(f"📡 Sending {priority} priority alert via WebSocket...")
                                    asyncio.run_coroutine_threadsafe(
                                        manager.broadcast(json.dumps(alert_data)), 
                                        shared_state.loop
                                    )
                                    print("✅ Alert broadcast task submitted.")
                                
                                # Send Email Alert only if confidence is greater than 70%
                                if confidence >= 0.70 and shared_state.loop and shared_state.loop.is_running():
                                    try:
                                        from services.email_service import send_abnormal_alert_email
                                        
                                        print(f"🔍 DEBUG: Sending email with organization: '{active_org}' (type: {type(active_org)})")
                                        # Run email alert asynchronously with detected organization
                                        asyncio.run_coroutine_threadsafe(
                                            send_abnormal_alert_email(
                                                float(confidence), 
                                                video_id, 
                                                event_name=event_name, 
                                                organization=active_org
                                            ),
                                            shared_state.loop
                                        )
                                        print(f"✅ Email alert task submitted for high confidence: {confidence:.2%}")
                                    except Exception as e:
                                        print(f"❌ Failed to send email alert: {e}")
                                elif confidence < 0.70:
                                    print(f"ℹ️ Skipping email alert - confidence {confidence:.2%} is below 70% threshold.")
                            except Exception as be:
                                print(f"❌ Failed to broadcast alert: {be}")
                except Exception as e:
                    print(f"Inference error: {e}")
                    # Log error but don't use false prediction
                    log_inference_result(video_id, False, 0.0, active_org)
                finally:
                    if os.path.exists(tmp_name):
                        try: os.remove(tmp_name)
                        except: pass

            frames = [] 

def log_inference_result(video_id, is_abnormal, confidence, current_organization):
    import csv
    import os
    from datetime import datetime
    
    # Ensure logs directory exists
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    # Organization-specific log file only
    safe_org_name = "".join([c if c.isalnum() else "_" for c in current_organization])
    org_csv = os.path.join(logs_dir, f"logs_{safe_org_name}.csv")
    
    # Current timestamp
    event_time = datetime.now().isoformat()
    
    # Professional format for organization-specific logs
    log_row = [
        current_organization,           # Organization
        event_time,                     # Event Time
        f"{confidence:.4f}",            # Confidence Score
        video_id                        # Camera ID
    ]
    
    # Professional headers for organization-specific files
    header = ["Organization", "Event Time", "Confidence Score", "Camera ID"]
    
    def append_to_csv(file_path, row):
        file_exists = os.path.exists(file_path)
        try:
            with open(file_path, mode="a", newline="\n", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists or os.path.getsize(file_path) == 0:
                    writer.writerow(header)
                writer.writerow(row)
        except Exception as e:
            print(f"Error logging to {file_path}: {e}")

    # Only log to organization-specific file (no global file)
    append_to_csv(org_csv, log_row)
    print(f"✅ Logged to organization-specific file: {org_csv}")
