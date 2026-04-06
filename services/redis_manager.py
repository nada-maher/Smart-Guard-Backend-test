# services/redis_manager.py
import redis
from config.settings import settings

class RedisManager:
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )

    def set_prediction(self, video_id, result):
        self.client.set(video_id, result)

    def get_prediction(self, video_id):
        return self.client.get(video_id)
