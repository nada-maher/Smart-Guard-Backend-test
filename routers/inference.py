# services/inference.py
from services.detector import AbnormalBehaviorDetector
from services.notifier import Notifier
from services.redis_manager import RedisManager
from config.settings import settings
import csv
import os
from datetime import datetime
import json
import pathlib
from services.event_bus import bus

detector = AbnormalBehaviorDetector()
notifier = Notifier(webhook_url=settings.WEBHOOK_URL)
redis_manager = RedisManager()
alert_active = False

def run_inference(video_bytes, video_id=None):
    global alert_active
    print(f"Using model path: {detector.model.model_path}")
    result = detector.predict(video_bytes)
    print(f"Inference: confidence={result['confidence']:.3f}, threshold={settings.ABNORMAL_THRESHOLD}, abnormal={result['is_abnormal']}")
    saved_video_path = None

    if result["is_abnormal"]:
        if not alert_active:
            notifier.send_alert(f"Abnormal behavior detected! Confidence: {result['confidence']:.2f}")
            alert_active = True
        try:
            os.makedirs(settings.LOGS_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            base = f"{ts}_{video_id or 'unknown'}_{result['confidence']:.3f}"
            video_path = os.path.join(settings.LOGS_DIR, f"{base}.mp4")
            meta_path = os.path.join(settings.LOGS_DIR, f"{base}.json")
            with open(video_path, "wb") as vf:
                vf.write(video_bytes)
            meta = {
                "timestamp": datetime.now().isoformat(),
                "video_id": video_id or "",
                "confidence": result["confidence"],
                "threshold": settings.ABNORMAL_THRESHOLD,
                "is_abnormal": result["is_abnormal"],
                "model_path": detector.model.model_path,
                "seq_len": settings.SEQ_LEN,
                "img_size": settings.IMG_SIZE,
                "saved_video_path": str(pathlib.Path(video_path).absolute()),
            }
            with open(meta_path, "w", encoding="utf-8") as mf:
                json.dump(meta, mf)
            saved_video_path = str(pathlib.Path(video_path).absolute())
        except Exception as e:
            print("Abnormal media save failed:", e)
    else:
        if alert_active:
            notifier.send_alert("Alert resolved: Normal behavior detected.")
            alert_active = False

    if video_id:
        try:
            redis_manager.set_prediction(video_id, str(result))
        except Exception as e:
            print("Redis set failed:", e)

    if result["is_abnormal"]:
        try:
            need_header = not os.path.exists(settings.LOG_CSV_PATH) or os.path.getsize(settings.LOG_CSV_PATH) == 0
            with open(settings.LOG_CSV_PATH, "a", newline="") as f:
                w = csv.writer(f)
                if need_header:
                    w.writerow(["timestamp", "video_id", "confidence", "threshold", "is_abnormal", "model_path", "seq_len", "img_size", "saved_video_path", "event"])
                w.writerow([datetime.now().isoformat(), video_id or "", f"{result['confidence']:.6f}", settings.ABNORMAL_THRESHOLD, result["is_abnormal"], detector.model.model_path, settings.SEQ_LEN, settings.IMG_SIZE, saved_video_path or "", "alert_start"])
        except Exception as e:
            print("CSV log write failed:", e)
    else:
        try:
            need_header = not os.path.exists(settings.LOG_CSV_PATH) or os.path.getsize(settings.LOG_CSV_PATH) == 0
            with open(settings.LOG_CSV_PATH, "a", newline="") as f:
                w = csv.writer(f)
                if need_header:
                    w.writerow(["timestamp", "video_id", "confidence", "threshold", "is_abnormal", "model_path", "seq_len", "img_size", "saved_video_path", "event"])
                w.writerow([datetime.now().isoformat(), video_id or "", f"{result['confidence']:.6f}", settings.ABNORMAL_THRESHOLD, result["is_abnormal"], detector.model.model_path, settings.SEQ_LEN, settings.IMG_SIZE, "", "alert_end"])
        except Exception as e:
            print("CSV log write failed:", e)

    try:
        import asyncio
        event_payload = {
            "timestamp": datetime.now().isoformat(),
            "video_id": video_id or "",
            "confidence": result["confidence"],
            "threshold": settings.ABNORMAL_THRESHOLD,
            "is_abnormal": result["is_abnormal"],
            "model_path": detector.model.model_path,
            "seq_len": settings.SEQ_LEN,
            "img_size": settings.IMG_SIZE,
            "saved_video_path": saved_video_path or "",
            "event": "alert_start" if result["is_abnormal"] else "alert_end"
        }
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(bus.publish(event_payload))
        except RuntimeError:
            asyncio.run(bus.publish(event_payload))
    except Exception as e:
        print("SSE publish failed:", e)

    return result
