# config/settings.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Use the local model path within the project
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MODEL_PATH = os.path.join(BASE_DIR, "models", "my_model_fight_cnn_bilstm10 (3).keras")
    SEQ_LEN = 35
    IMG_SIZE = 128
    CHANNELS = 3

    # Supabase config
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://chjonhyjqztktxspwlkd.supabase.co")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Email config
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
    RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

    # Twilio config
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
    TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
    RECIPIENT_PHONE_NUMBER = os.getenv("RECIPIENT_PHONE_NUMBER")

    # Redis config
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))

    # Threshold for abnormal detection
    ABNORMAL_THRESHOLD = 0.161  # Restored to old value
    LOG_CSV_PATH = os.getenv("LOG_CSV_PATH", "inference_logs.csv")
    LOGS_DIR = os.getenv("LOGS_DIR", "logs")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:5174").split(",")

settings = Settings()
