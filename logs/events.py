# services/events.py
import datetime

def log_event(event_type: str, message: str):
    timestamp = datetime.datetime.now().isoformat()
    print(f"[{timestamp}] [{event_type.upper()}] {message}")
