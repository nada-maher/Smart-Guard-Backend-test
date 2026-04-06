# services/notifier.py
import requests

class Notifier:
    def __init__(self, webhook_url=None):
        self.webhook_url = webhook_url

    def send_alert(self, message: str):
        if self.webhook_url:
            payload = {"text": message}
            try:
                requests.post(self.webhook_url, json=payload)
            except Exception as e:
                print("Failed to send alert:", e)
        else:
            print("ALERT:", message)
