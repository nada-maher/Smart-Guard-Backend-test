# services/twilio_service.py
from twilio.rest import Client
from config.settings import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwilioService:
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_phone = settings.TWILIO_PHONE_NUMBER
        self.from_whatsapp = settings.TWILIO_WHATSAPP_NUMBER
        self.to_phone = settings.RECIPIENT_PHONE_NUMBER
        
        if self.account_sid and self.auth_token:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("✅ Twilio client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Twilio client: {e}")
                self.client = None
        else:
            logger.warning("⚠️ Twilio credentials missing in settings")
            self.client = None

    def send_sms_alert(self, message_body):
        """Send a standard SMS alert"""
        if not self.client:
            logger.error("Twilio client not initialized")
            return False
        
        try:
            message = self.client.messages.create(
                body=message_body,
                from_=self.from_phone,
                to=self.to_phone
            )
            logger.info(f"✅ SMS Alert sent! SID: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send SMS alert: {e}")
            return False

    def send_whatsapp_alert(self, message_body):
        """Send a WhatsApp alert"""
        if not self.client:
            logger.error("Twilio client not initialized")
            return False
        
        try:
            # Twilio WhatsApp requires 'whatsapp:' prefix
            message = self.client.messages.create(
                body=message_body,
                from_=f"whatsapp:{self.from_whatsapp}",
                to=f"whatsapp:{self.to_phone}"
            )
            logger.info(f"✅ WhatsApp Alert sent! SID: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send WhatsApp alert: {e}")
            return False

# Singleton instance
twilio_service = TwilioService()
