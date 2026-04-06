# services/alerts.py
from services.notifier import Notifier

notifier = Notifier(webhook_url=None)  # لو عندك URL حطيه هنا

def send_abnormal_alert(confidence: float):
    message = f" Abnormal behavior detected! Confidence: {confidence:.2f}"
    notifier.send_alert(message)
